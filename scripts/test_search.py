import sys
import os
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "web-platform" / "backend"))

from app.services.safe_workspace_service import safe_workspace_service

SESSION_ID = "94af46f7dc5a4d80b4b9eda75b6080f4"

queries = [
    "plavix",
    "lantus",
    "invoice",
    "bright light",
    "myanmar",
    "receipt",
    "AWB",
    "DRC",
]

print(f"Testing {len(queries)} queries on session: {SESSION_ID}\n")
print(f"{'Query':<20} | {'Results':<10} | {'First Result'}")
print("-" * 70)

for q in queries:
    try:
        result = safe_workspace_service.search(SESSION_ID, q, limit=5)
        total = len(result.get("results", []))
        first = result["results"][0]["filename"] if total > 0 else "(none)"
        print(f"{q:<20} | {total:<10} | {first}")
    except Exception as e:
        print(f"{q:<20} | ERROR: {e}")