"""Durable, fail-closed consent storage for external AI processing.

The Personal Local runtime authenticates staff with signed local access tokens,
so consent is stored beside the local auth state in a protected SQLite database.
"""
from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.core.config import settings
from app.services.train1_safety_contracts import ConsentGrant


PURPOSES = frozenset({"document_analysis", "embedding", "duplicate_detection"})


def _connect() -> sqlite3.Connection:
    path = Path(settings.LOCAL_AUTH_STATE_PATH).expanduser()
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_symlink():
        raise OSError("LOCAL_AUTH_STATE_PATH cannot be a symlink")
    resolved = path.resolve()
    roots = [settings.WORKING_ROOT.resolve()]
    if settings.SOURCE_ROOT:
        roots.append(settings.SOURCE_ROOT.resolve())
    if any(resolved == root or resolved.is_relative_to(root) for root in roots):
        raise OSError("Consent database must remain outside SOURCE_ROOT and WORKING_ROOT")
    db = sqlite3.connect(str(resolved), timeout=15)
    try:
        if os.name == "posix":
            os.chmod(resolved, 0o600)
        db.execute("PRAGMA busy_timeout = 15000")
        db.execute("PRAGMA foreign_keys = ON")
        db.executescript(
            """
            CREATE TABLE IF NOT EXISTS ai_consent_grants (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                subject_id TEXT NOT NULL,
                purpose TEXT NOT NULL,
                scope TEXT NOT NULL,
                granted_at TEXT NOT NULL,
                revoked_at TEXT,
                revision INTEGER NOT NULL DEFAULT 1,
                UNIQUE(subject_id, purpose, scope)
            );
            CREATE TABLE IF NOT EXISTS ai_consent_audit (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                subject_id TEXT NOT NULL,
                actor_id TEXT NOT NULL,
                purpose TEXT NOT NULL,
                scope TEXT NOT NULL,
                action TEXT NOT NULL CHECK(action IN ('granted','revoked','denied')),
                occurred_at TEXT NOT NULL,
                request_id TEXT,
                metadata_json TEXT NOT NULL DEFAULT '{}'
            );
            CREATE INDEX IF NOT EXISTS idx_ai_consent_lookup
              ON ai_consent_grants(subject_id, purpose, scope, revoked_at);
            CREATE INDEX IF NOT EXISTS idx_ai_consent_audit_subject
              ON ai_consent_audit(subject_id, occurred_at);
            """
        )
        return db
    except Exception:
        db.close()
        raise


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _audit(db: sqlite3.Connection, *, subject_id: str, actor_id: str,
           purpose: str, scope: str, action: str, request_id: str | None = None) -> None:
    db.execute(
        "INSERT INTO ai_consent_audit(subject_id, actor_id, purpose, scope, action, occurred_at, request_id) VALUES(?,?,?,?,?,?,?)",
        (subject_id, actor_id, purpose, scope, action, _now(), request_id),
    )


def set_consent(*, subject_id: str, actor_id: str, purpose: str, scope: str,
                granted: bool, request_id: str | None = None) -> dict[str, Any]:
    if not subject_id or not actor_id:
        raise ValueError("Authenticated subject and actor are required")
    if purpose not in PURPOSES:
        raise ValueError("Unsupported AI consent purpose")
    if not isinstance(scope, str) or not scope.strip() or len(scope) > 512:
        raise ValueError("A non-empty, bounded resource scope is required")
    db = _connect()
    try:
        db.execute("BEGIN IMMEDIATE")
        current = db.execute(
            "SELECT id, revoked_at, revision FROM ai_consent_grants WHERE subject_id=? AND purpose=? AND scope=?",
            (subject_id, purpose, scope),
        ).fetchone()
        now = _now()
        if granted:
            if current and current[1] is None:
                _audit(db, subject_id=subject_id, actor_id=actor_id, purpose=purpose, scope=scope, action="granted", request_id=request_id)
                revision = current[2]
            elif current:
                db.execute("UPDATE ai_consent_grants SET granted_at=?, revoked_at=NULL, revision=revision+1 WHERE id=?", (now, current[0]))
                _audit(db, subject_id=subject_id, actor_id=actor_id, purpose=purpose, scope=scope, action="granted", request_id=request_id)
                revision = current[2] + 1
            else:
                db.execute("INSERT INTO ai_consent_grants(subject_id,purpose,scope,granted_at) VALUES(?,?,?,?)", (subject_id, purpose, scope, now))
                _audit(db, subject_id=subject_id, actor_id=actor_id, purpose=purpose, scope=scope, action="granted", request_id=request_id)
                revision = 1
        else:
            if current and current[1] is None:
                db.execute("UPDATE ai_consent_grants SET revoked_at=?, revision=revision+1 WHERE id=?", (now, current[0]))
            _audit(db, subject_id=subject_id, actor_id=actor_id, purpose=purpose, scope=scope, action="revoked", request_id=request_id)
            revision = (current[2] + 1) if current else 0
        db.commit()
        return {"subject_id": subject_id, "purpose": purpose, "scope": scope,
                "granted": bool(granted), "revision": revision, "updated_at": now}
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def get_consent_grant(*, subject_id: str, purpose: str, scope: str) -> ConsentGrant | None:
    if not subject_id or purpose not in PURPOSES or not scope:
        return None
    db = _connect()
    try:
        row = db.execute(
            "SELECT 1 FROM ai_consent_grants WHERE subject_id=? AND purpose=? AND scope=? AND revoked_at IS NULL",
            (subject_id, purpose, scope),
        ).fetchone()
        return ConsentGrant(subject_id, purpose, scope, True) if row else None
    finally:
        db.close()


def list_consents(*, subject_id: str) -> list[dict[str, Any]]:
    db = _connect()
    try:
        rows = db.execute(
            "SELECT purpose, scope, granted_at, revoked_at, revision FROM ai_consent_grants WHERE subject_id=? ORDER BY purpose, scope",
            (subject_id,),
        ).fetchall()
        return [{"purpose": r[0], "scope": r[1], "granted_at": r[2], "revoked_at": r[3],
                 "revision": r[4], "granted": r[3] is None} for r in rows]
    finally:
        db.close()


def list_audit(*, subject_id: str, limit: int = 100) -> list[dict[str, Any]]:
    db = _connect()
    try:
        rows = db.execute(
            "SELECT actor_id,purpose,scope,action,occurred_at,request_id FROM ai_consent_audit WHERE subject_id=? ORDER BY id DESC LIMIT ?",
            (subject_id, max(1, min(int(limit), 500))),
        ).fetchall()
        return [{"actor_id": r[0], "purpose": r[1], "scope": r[2], "action": r[3],
                 "occurred_at": r[4], "request_id": r[5]} for r in rows]
    finally:
        db.close()
