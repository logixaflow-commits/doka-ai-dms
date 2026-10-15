#!/usr/bin/env python3
"""End-to-End Production Verification & Smoke Test Script for Doka-AI-DMS.

Designed for post-deployment automated health check and synthetic transaction verification.
Usage:
  python scripts/verify_production.py --backend-url http://127.0.0.1:8002 --frontend-url http://127.0.0.1:5173
"""

import argparse
import os
import sys
import time
import urllib.request
import json
from typing import Dict, Any, Tuple


class SmokeTester:
    def __init__(self, backend_url: str, frontend_url: str, timeout: int = 10):
        self.backend_url = backend_url.rstrip("/")
        self.frontend_url = frontend_url.rstrip("/")
        self.timeout = timeout
        self.passed = 0
        self.failed = 0

    def log(self, status: str, check_name: str, detail: str = ""):
        prefix = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}]"
        badge = f"[{status}]"
        print(f"{prefix} {badge:<8} {check_name:<40} {detail}", flush=True)

    def request(self, url: str) -> Tuple[int, bytes, Dict[str, str]]:
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Doka-Production-Verification/1.0",
                "Accept": "application/json, text/html",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                status = resp.status
                body = resp.read()
                headers = dict(resp.headers)
                return status, body, headers
        except urllib.error.HTTPError as e:
            return e.code, e.read(), dict(e.headers)
        except Exception as exc:
            return 0, str(exc).encode(), {}

    def test_backend_health(self):
        url = f"{self.backend_url}/health"
        status, body, _ = self.request(url)
        if status == 200:
            try:
                data = json.loads(body.decode("utf-8"))
                if data.get("status") == "healthy":
                    self.passed += 1
                    self.log("PASS", "Backend /health", f"Status: {data.get('status')}, SourceReadOnly: {data.get('source_read_only')}")
                    return
            except json.JSONDecodeError:
                pass
        self.failed += 1
        self.log("FAIL", "Backend /health", f"HTTP {status} - Response: {body.decode('utf-8', errors='ignore')[:120]}")

    def test_backend_config(self):
        url = f"{self.backend_url}/api/config"
        status, body, _ = self.request(url)
        if status == 200:
            try:
                data = json.loads(body.decode("utf-8"))
                if "edition" in data:
                    self.passed += 1
                    self.log("PASS", "Backend /api/config", f"Edition: {data.get('edition')}, WorkspaceConfigured: {data.get('workspace_root_configured')}")
                    return
            except json.JSONDecodeError:
                pass
        self.failed += 1
        self.log("FAIL", "Backend /api/config", f"HTTP {status}")

    def test_backend_ai_usage(self):
        url = f"{self.backend_url}/api/ai/usage"
        status, body, _ = self.request(url)
        if status == 200:
            try:
                data = json.loads(body.decode("utf-8"))
                providers = list(data.get("providers", {}).keys())
                self.passed += 1
                self.log("PASS", "Backend /api/ai/usage", f"Active providers: {', '.join(providers) if providers else 'None'}")
                return
            except json.JSONDecodeError:
                pass
        self.failed += 1
        self.log("FAIL", "Backend /api/ai/usage", f"HTTP {status}")

    def test_frontend_root(self):
        url = f"{self.frontend_url}/"
        status, body, _ = self.request(url)
        content = body.decode("utf-8", errors="ignore")
        if status == 200 and ("<div" in content or "html" in content.lower()):
            self.passed += 1
            self.log("PASS", "Frontend Root (/) SPA", f"HTTP 200 - {len(body)} bytes delivered")
        else:
            self.failed += 1
            self.log("FAIL", "Frontend Root (/) SPA", f"HTTP {status}")

    def test_telegram_connectivity(self):
        token = os.getenv("TELEGRAM_BOT_TOKEN")
        if not token:
            self.log("SKIP", "Telegram Bot Connectivity", "TELEGRAM_BOT_TOKEN not provided in env")
            return

        tg_url = f"https://api.telegram.org/bot{token}/getMe"
        status, body, _ = self.request(tg_url)
        if status == 200:
            try:
                data = json.loads(body.decode("utf-8"))
                if data.get("ok"):
                    bot_name = data.get("result", {}).get("username", "Unknown")
                    self.passed += 1
                    self.log("PASS", "Telegram Bot Connectivity", f"Bot @{bot_name} connected successfully")
                    return
            except json.JSONDecodeError:
                pass
        self.failed += 1
        self.log("FAIL", "Telegram Bot Connectivity", f"HTTP {status}")

    def run_all(self) -> bool:
        print("==================================================================")
        print("  DOKA-AI-DMS PRODUCTION SMOKE & INTEGRITY VERIFICATION SUITE   ")
        print("==================================================================")
        self.test_backend_health()
        self.test_backend_config()
        self.test_backend_ai_usage()
        self.test_frontend_root()
        self.test_telegram_connectivity()
        print("------------------------------------------------------------------")
        print(f"Results: {self.passed} PASSED, {self.failed} FAILED")
        print("==================================================================")
        return self.failed == 0


def main():
    parser = argparse.ArgumentParser(description="Doka-AI-DMS Smoke Test Suite")
    parser.add_argument("--backend-url", default=os.getenv("BACKEND_URL", "http://127.0.0.1:8002"))
    parser.add_argument("--frontend-url", default=os.getenv("FRONTEND_URL", "http://127.0.0.1:5173"))
    parser.add_argument("--timeout", type=int, default=10)
    args = parser.parse_args()

    tester = SmokeTester(args.backend_url, args.frontend_url, args.timeout)
    success = tester.run_all()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
