#!/usr/bin/env python3
"""Mint short-lived JWTs for disposable staging users without logging credentials."""
from __future__ import annotations

import argparse
import os
from pathlib import Path
from urllib.parse import urlparse

import httpx

STAGING_SUPABASE_URL = "https://gzxybtqquzycogaowdbj.supabase.co"
STAGING_SUPABASE_HOST = "gzxybtqquzycogaowdbj.supabase.co"


def _require(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise SystemExit(f"Missing required staging test-account setting: {name}")
    if "\n" in value or "\r" in value:
        raise SystemExit(f"Invalid newline in staging test-account setting: {name}")
    return value


def _request_access_token(
    client: httpx.Client, email: str, password: str, publishable_key: str
) -> tuple[str, str]:
    parsed = urlparse(str(client.base_url))
    if parsed.scheme != "https" or parsed.hostname != STAGING_SUPABASE_HOST:
        raise SystemExit("Refusing test-user authentication unless the exact staging Supabase project is configured.")
    response = client.post(
        "/auth/v1/token?grant_type=password",
        headers={"apikey": publishable_key, "Content-Type": "application/json"},
        json={"email": email, "password": password},
    )
    if response.status_code != 200:
        # Never echo the Auth response body: providers may include user identifiers.
        raise SystemExit(f"Staging test-user authentication failed (HTTP {response.status_code}).")
    try:
        payload = response.json()
        token = str(payload.get("access_token") or "")
        user = payload.get("user") or {}
        user_id = str(user.get("id") or "")
        expires_in = int(payload.get("expires_in") or 0)
    except (TypeError, ValueError):
        raise SystemExit("Staging Auth returned an invalid token response.") from None
    if token.count(".") != 2 or len(token) < 100 or "\n" in token or "\r" in token:
        raise SystemExit("Staging Auth did not return a valid short-lived access token.")
    if not user_id or expires_in < 60:
        raise SystemExit("Staging Auth returned an incomplete user identity or token expiry.")
    return token, user_id


def _write_github_env(tokens: dict[str, str], env_path: str) -> None:
    path = Path(env_path)
    if not path.is_file():
        raise SystemExit("GITHUB_ENV is not a writable runner environment file.")
    for token in tokens.values():
        print(f"::add-mask::{token}")
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        for name, token in tokens.items():
            handle.write(f"{name}={token}\n")


def main() -> int:
    parser = argparse.ArgumentParser(description="Mint fresh staging-only Supabase Auth access tokens.")
    parser.add_argument("--mode", choices=("both", "user-a"), default="both")
    args = parser.parse_args()

    key = _require("SUPABASE_STAGING_PUBLISHABLE_KEY")
    email_a = _require("DOKA_STAGING_USER_A_EMAIL")
    password_a = _require("DOKA_STAGING_USER_A_PASSWORD")
    accounts = [("DOKA_CLOUD_USER_A_TOKEN", email_a, password_a)]
    if args.mode == "both":
        email_b = _require("DOKA_STAGING_USER_B_EMAIL")
        password_b = _require("DOKA_STAGING_USER_B_PASSWORD")
        if email_a.casefold() == email_b.casefold():
            raise SystemExit("Staging User A and User B must be distinct accounts.")
        accounts.append(("DOKA_CLOUD_USER_B_TOKEN", email_b, password_b))

    tokens: dict[str, str] = {}
    user_ids: list[str] = []
    with httpx.Client(base_url=STAGING_SUPABASE_URL, timeout=30.0, follow_redirects=False) as client:
        for env_name, email, password in accounts:
            token, user_id = _request_access_token(client, email, password, key)
            tokens[env_name] = token
            user_ids.append(user_id)
    if len(set(user_ids)) != len(user_ids):
        raise SystemExit("Staging User A and User B resolved to the same Auth identity.")
    if args.mode == "user-a":
        # Provider acceptance consumes the single-user alias; both names are job-scoped only.
        tokens["DOKA_CLOUD_USER_TOKEN"] = tokens["DOKA_CLOUD_USER_A_TOKEN"]
    _write_github_env(tokens, os.getenv("GITHUB_ENV", ""))
    print("Fresh staging-only access tokens were minted, masked, and exported for this job; values were not recorded.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
