from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from app.core.config import settings
from app.services.safe_workspace_service import safe_workspace_service


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
        parts = [settings.FINAL_ROOT.name, category]
        if supplier:
            parts.append(re.sub(r'[<>:"/\\|?*]', "_", str(supplier)).strip()[:80])
        parts.append(year)
        return "/".join(parts)

    def plan(self, session_id: str) -> Dict[str, Any]:
        inventory = safe_workspace_service._read(safe_workspace_service._json_path(session_id, "inventory.json"))
        understanding = safe_workspace_service._read(safe_workspace_service._json_path(session_id, "understanding.json"))
        if not inventory:
            raise ValueError("Inventory is not available. Run scan first.")
        understood = {x["relative_path"]: x for x in understanding.get("results", [])}

        duplicate_paths = {p for group in inventory.get("duplicate_groups", []) for p in group}
        collision_paths = {p for group in inventory.get("filename_collision_groups_detail", []) for p in group}
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
            "schema_version": 1,
            "session_id": session_id,
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
        return {k: v for k, v in plan.items() if k != "proposals"}


organization_planner = OrganizationPlanner()
