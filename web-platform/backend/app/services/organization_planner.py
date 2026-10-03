from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from app.core.config import settings
from app.services.safe_workspace_service import safe_workspace_service, sha256_file


BUILTIN_KEYWORDS = {
    "Invoices": ["invoice", "inv", "ဘောင်ချာ", "ဘီလ်"],
    "Contracts": ["contract", "agreement", "စာချုပ်", "သဘောတူ"],
    "Licenses": ["license", "licence", "လိုင်စင်", "ခွင့်ပြု"],
    "Identity": ["nrc", "national id", "passport", "မှတ်ပုံတင်", "နိုင်ငံကူး"],
    "Customs": ["customs", "declaration", "အကောက်ခွန်"],
    "Shipping": ["bill of lading", "b/l", "bl", "container", "vessel", "shipment"],
    "Finance": ["receipt", "payment", "statement", "ငွေချေ", "ငွေလွှဲ"],
}


def normalize_stem(name: str) -> str:
    stem = Path(name).stem.casefold()
    stem = re.sub(r"([ _.-]?(copy|final|latest|new|old|updated|version|ver|v)\s*[._-]?\d*)+$", "", stem)
    stem = re.sub(r"([ _.-]\d{1,4})+$", "", stem)
    return re.sub(r"[^\w\u1000-\u109f]+", " ", stem).strip()


def safe_segment(value: str, fallback: str = "Unknown") -> str:
    cleaned = re.sub(r'[<>:"/\\|?*]+', "_", str(value)).strip(" .")
    return (cleaned[:100] or fallback)


class OrganizationPlanner:
    """Generate reviewable organization proposals. Never changes files."""

    def _category(self, item: Dict[str, Any]) -> tuple[str, float, str]:
        text = f'{item.get("filename", "")} {item.get("text_preview", "")}'.casefold()
        configured = settings.get_category_keywords()
        scores: Dict[str, int] = {}
        for category, words in {**BUILTIN_KEYWORDS, **configured}.items():
            score = sum(1 for word in words if word and word.casefold() in text)
            if score:
                scores[category] = score
        if not scores:
            return "Review", 0.25, "No reliable category signal"
        category, score = max(scores.items(), key=lambda pair: pair[1])
        confidence = min(0.95, 0.55 + score * 0.1)
        return category, confidence, f"Matched {score} rule signal(s)"

    def _folder(self, category: str, item: Dict[str, Any]) -> str:
        metadata = item.get("metadata") or {}
        supplier = metadata.get("supplier")
        year = None
        date_value = metadata.get("eta") or metadata.get("etd")
        if date_value and isinstance(date_value, str) and len(date_value) >= 4:
            year = date_value[:4]
        if not year:
            modified = item.get("modified_at", "")
            year = modified[:4] if len(modified) >= 4 else "Unknown Year"
        parts = [settings.FINAL_ROOT.name, safe_segment(category, "Review")]
        if supplier:
            parts.append(safe_segment(str(supplier), "Unknown Supplier"))
        parts.append(year)
        return "/".join(parts)

    @staticmethod
    def _fingerprint(value: Dict[str, Any]) -> str:
        import hashlib
        canonical = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def _planning_inputs(self, session_id: str) -> tuple[Dict[str, Any], Dict[str, Any]]:
        inventory = safe_workspace_service._read(
            safe_workspace_service._json_path(session_id, "inventory.json")
        )
        understanding = safe_workspace_service._read(
            safe_workspace_service._json_path(session_id, "understanding.json")
        )
        corrections = safe_workspace_service._read(
            safe_workspace_service._json_path(session_id, "ocr_corrections.json")
        )
        correction_map = corrections.get("results", {})
        for item in understanding.get("results", []):
            corrected = correction_map.get(item.get("relative_path"))
            if corrected is not None:
                item["corrected_text"] = corrected
                item["text_preview"] = corrected[:2000]
        return inventory, understanding

    def plan(self, session_id: str) -> Dict[str, Any]:
        inventory, understanding = self._planning_inputs(session_id)
        if not inventory:
            raise ValueError("Inventory is not available. Run scan first.")
        understood = {x["relative_path"]: x for x in understanding.get("results", [])}

        duplicate_paths = {p for group in inventory.get("duplicate_groups", []) for p in group}
        collision_paths = {p for group in inventory.get("filename_collision_groups_detail", []) for p in group}
        # Detect likely versions even when filenames differ by copy/final/v2/new suffixes.
        stem_groups: Dict[str, List[str]] = {}
        for item in inventory.get("inventory", []):
            stem_groups.setdefault(normalize_stem(item["filename"]), []).append(item["relative_path"])
        version_paths = {
            p for paths in stem_groups.values() if len(paths) > 1
            for p in paths
            if p not in duplicate_paths
        }
        proposals: List[Dict[str, Any]] = []

        for item in inventory.get("inventory", []):
            rel = item["relative_path"]
            enriched = {**item, **understood.get(rel, {})}
            if rel in duplicate_paths:
                proposals.append({
                    "relative_path": rel, "action": "review_duplicate",
                    "confidence": 0.99, "reason": "Exact SHA-256 duplicate",
                    "target": None,
                })
                continue
            if rel in version_paths:
                category, confidence, reason = self._category(enriched)
                target_folder = self._folder(category, enriched)
                safe_name = Path(item["filename"]).name
                proposals.append({
                    "relative_path": rel, "action": "review_version",
                    "confidence": max(0.75, confidence),
                    "reason": "Filename normalization indicates a possible copy/version family; compare contents before approval",
                    "category": category,
                    "target_folder": target_folder,
                    "suggested_filename": safe_name,
                    "target": f"{target_folder}/{safe_name}",
                })
                continue
            category, confidence, reason = self._category(enriched)
            target_folder = self._folder(category, enriched)
            safe_name = Path(item["filename"]).name
            proposals.append({
                "relative_path": rel,
                "action": "review" if rel in collision_paths or confidence < 0.7 else "suggest_move",
                "confidence": confidence,
                "reason": reason,
                "category": category,
                "target_folder": target_folder,
                "suggested_filename": safe_name,
                "target": f"{target_folder}/{safe_name}",
            })

        plan = {
            "schema_version": 3,
            "session_id": session_id,
            "inventory_sha256": self._fingerprint(inventory),
            "understanding_sha256": self._fingerprint(understanding),
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "ai_used": False,
            "requires_user_approval": True,
            "organization_allowed": False,
            "proposals_total": len(proposals),
            "review_required": sum(1 for p in proposals if p["action"].startswith("review")),
            "proposals": proposals,
        }
        session = safe_workspace_service._dir(session_id)
        safe_workspace_service._write(session / "organization_plan.json", plan)
        return plan


    def apply(self, session_id: str, approved_paths: List[str]) -> Dict[str, Any]:
        if not approved_paths:
            raise ValueError("No approved files were supplied.")
        plan = safe_workspace_service._read(safe_workspace_service._json_path(session_id, "organization_plan.json"))
        manifest = safe_workspace_service._read(safe_workspace_service._json_path(session_id, "manifest.json"))
        if not plan or not manifest:
            raise ValueError("Organization plan is not available.")
        if plan.get("session_id") != session_id:
            raise ValueError("Organization plan belongs to a different import session.")
        if not plan.get("requires_user_approval") or plan.get("organization_allowed") is not False:
            raise ValueError("Invalid organization plan state.")

        current_inventory, current_understanding = self._planning_inputs(session_id)
        if (
            plan.get("inventory_sha256") != self._fingerprint(current_inventory)
            or plan.get("understanding_sha256") != self._fingerprint(current_understanding)
        ):
            raise ValueError("Organization plan is stale; rescan/re-run OCR and build a new review plan before applying.")

        approved = set(approved_paths)
        proposals = {p["relative_path"]: p for p in plan.get("proposals", [])}
        _source_root, root = safe_workspace_service.validate_manifest_paths(session_id, manifest)
        final_root = settings.FINAL_ROOT.resolve()
        final_root.mkdir(parents=True, exist_ok=True)
        audit_path = safe_workspace_service._dir(session_id) / "organization_audit.jsonl"
        results = []

        for rel in approved:
            proposal = proposals.get(rel)
            if not proposal:
                results.append({"relative_path": rel, "status": "rejected", "reason": "Not in generated plan"})
                continue
            source = (root / rel).resolve()
            manifest_entry = manifest.get("files", {}).get(rel)
            if not manifest_entry or manifest_entry.get("verified") is not True:
                results.append({"relative_path": rel, "status": "rejected", "reason": "File is not a verified import-manifest entry"})
                continue
            if not source.is_file():
                results.append({"relative_path": rel, "status": "failed", "reason": "Working-copy file missing"})
                continue
            try:
                source.relative_to(root)
                expected_hash = str(manifest_entry.get("sha256", "")).lower()
                if len(expected_hash) != 64 or sha256_file(source).lower() != expected_hash:
                    raise ValueError("Working-copy integrity check failed; rescan and review before applying.")
                target_folder = proposal.get("target_folder")
                suggested_filename = proposal.get("suggested_filename") or Path(rel).name
                if not target_folder or not suggested_filename:
                    raise ValueError("Organization proposal is missing a safe target.")
                folder = Path(target_folder)
                folder_parts = folder.parts
                if not folder_parts or folder_parts[0] != final_root.name or any(part in ("", ".", "..") for part in folder_parts):
                    raise ValueError("Planned target folder is invalid.")
                target = (final_root / Path(*folder_parts[1:]) / Path(suggested_filename).name).resolve()
                try:
                    target.relative_to(final_root)
                except ValueError as exc:
                    raise ValueError("Planned target is outside FINAL_ROOT.") from exc
                target.parent.mkdir(parents=True, exist_ok=True)
                source_hash = sha256_file(source)
                if target.exists():
                    target_hash = sha256_file(target)
                    if target_hash == source_hash:
                        result = {"relative_path": rel, "status": "already_present", "target": str(target), "sha256": source_hash}
                    else:
                        result = {"relative_path": rel, "status": "conflict", "target": str(target), "sha256": source_hash}
                else:
                    import shutil
                    shutil.copy2(source, target)
                    target_hash = __import__("hashlib").sha256(target.read_bytes()).hexdigest()
                    if target_hash != source_hash:
                        target.unlink(missing_ok=True)
                        raise IOError("Final copy SHA-256 verification failed")
                    result = {"relative_path": rel, "status": "copied", "target": str(target), "sha256": source_hash}
            except Exception as exc:
                result = {"relative_path": rel, "status": "failed", "reason": str(exc)}

            with audit_path.open("a", encoding="utf-8") as audit:
                audit.write(json.dumps({
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "session_id": session_id,
                    "action": "COPY_TO_FINAL",
                    **result,
                }, ensure_ascii=False) + "\n")
            results.append(result)

        return {
            "session_id": session_id,
            "approved_count": len(approved),
            "results": results,
            "source_copy_preserved": True,
            "source_root_modified": False,
        }


    def undo(self, session_id: str) -> Dict[str, Any]:
        audit_path = safe_workspace_service._dir(session_id) / "organization_audit.jsonl"
        if not audit_path.exists():
            raise ValueError("No organization audit journal exists.")
        results = []
        for line in audit_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            entry = json.loads(line)
            if entry.get("action") != "COPY_TO_FINAL" or entry.get("status") != "copied":
                continue
            target = Path(entry["target"]).resolve()
            final_root = settings.FINAL_ROOT.resolve()
            try:
                target.relative_to(final_root)
            except ValueError:
                results.append({"target": str(target), "status": "rejected_outside_final_root"})
                continue
            if not target.exists():
                results.append({"target": str(target), "status": "already_missing"})
                continue
            try:
                if sha256_file(target) != entry.get("sha256"):
                    results.append({"target": str(target), "status": "skipped_changed_since_apply"})
                    continue
                target.unlink()
                results.append({"target": str(target), "status": "removed"})
            except Exception as exc:
                results.append({"target": str(target), "status": "failed", "reason": str(exc)})
        return {
            "session_id": session_id,
            "results": results,
            "source_copy_preserved": True,
            "source_root_modified": False,
        }


organization_planner = OrganizationPlanner()
