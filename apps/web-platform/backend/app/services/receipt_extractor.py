"""Zero-cost Smart Invoice & Receipt Auto-Extractor.

Extracts structured financial metadata (Vendor, Total Amount, Currency, Date,
Tax, and Category) from raw OCR text without external paid APIs.
"""

from __future__ import annotations

import logging
import re
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)

# Currency patterns
CURRENCY_MAP = {
    "$": "USD",
    "€": "EUR",
    "£": "GBP",
    "¥": "JPY",
    "฿": "THB",
    "ks": "MMK",
    "mmk": "MMK",
    "kyat": "MMK",
    "kyats": "MMK",
    "ကျပ်": "MMK",
    "usd": "USD",
    "sgd": "SGD",
}

# Category classification heuristics
CATEGORY_KEYWORDS = {
    "Meals & Entertainment": ["restaurant", "cafe", "coffee", "food", "kitchen", "bakery", "dining", "bar", "bistro", "tea"],
    "Cloud & Software": ["aws", "google cloud", "azure", "github", "render", "vercel", "cloudflare", "openai", "stripe", "domain", "hosting", "subscription"],
    "Office Supplies": ["stationery", "paper", "printer", "ink", "pen", "office", "desk", "supplies"],
    "Travel & Transport": ["grab", "uber", "flight", "airline", "hotel", "taxi", "fuel", "petrol", "diesel", "parking", "toll"],
    "Utilities & Telecom": ["telecom", "mytel", "ooredoo", "telenor", "atom", "mpt", "electric", "power", "water", "internet", "wifi"],
    "Retail & Groceries": ["city mart", "marketplace", "supermarket", "mart", "store", "groceries", "retail", "pharmacy", "drugstore"],
}


class ReceiptExtractorService:
    """Intelligent parsing engine for receipts and tax invoices."""

    @classmethod
    def extract_financial_data(cls, text: str) -> dict[str, Any]:
        """Extract vendor, dates, totals, taxes, and category from OCR text."""
        if not text or not text.strip():
            return {
                "vendor": "Unknown Vendor",
                "invoice_number": None,
                "date": None,
                "currency": "MMK",
                "total_amount": 0.0,
                "tax_amount": 0.0,
                "category": "General Expense",
                "confidence": 0.0,
                "line_items": [],
            }

        lines = [line.strip() for line in text.split("\n") if line.strip()]

        vendor = cls._extract_vendor(lines)
        invoice_number = cls._extract_invoice_number(text)
        date_str = cls._extract_date(text)
        currency, total_amount = cls._extract_total(text)
        tax_amount = cls._extract_tax(text)
        category = cls._classify_category(text, vendor)
        line_items = cls._extract_line_items(lines)

        # Confidence heuristic
        signals = [
            vendor != "Unknown Vendor",
            invoice_number is not None,
            date_str is not None,
            total_amount > 0.0,
        ]
        confidence = round(sum(1.0 for s in signals if s) / len(signals), 2)

        return {
            "vendor": vendor,
            "invoice_number": invoice_number,
            "date": date_str,
            "currency": currency,
            "total_amount": total_amount,
            "tax_amount": tax_amount,
            "category": category,
            "confidence": confidence,
            "line_items": line_items,
        }

    @classmethod
    def _extract_vendor(cls, lines: list[str]) -> str:
        """Infer merchant / vendor from header lines."""
        ignore_patterns = [
            r"^(tax|invoice|receipt|official receipt|cash receipt|bill|order|table|date|tel)",
            r"^\d+",
            r"^welcome",
        ]
        for line in lines[:5]:
            clean = line.strip()
            if len(clean) < 3 or len(clean) > 50:
                continue
            if any(re.search(pat, clean, re.IGNORECASE) for pat in ignore_patterns):
                continue
            return clean
        return "Unknown Vendor"

    @classmethod
    def _extract_invoice_number(cls, text: str) -> str | None:
        """Extract invoice or receipt reference number."""
        patterns = [
            r"(?:invoice\s*(?:no|num|#|\.)?|receipt\s*(?:no|num|#|\.)?|order\s*#?)\s*[:.\-]?\s*([A-Za-z0-9\-_/]{4,25})",
            r"(?:inv|rcpt|ref)\s*[:#\-.]?\s*([A-Za-z0-9\-_]{4,25})",
        ]
        for pat in patterns:
            match = re.search(pat, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        return None

    @classmethod
    def _extract_date(cls, text: str) -> str | None:
        """Extract invoice date into standardized YYYY-MM-DD if recognizable."""
        patterns = [
            r"\b(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})\b",  # 2026-10-17
            r"\b(\d{1,2})[-/.](\d{1,2})[-/.](\d{4})\b",  # 17/10/2026
        ]
        for pat in patterns:
            match = re.search(pat, text)
            if match:
                g = match.groups()
                try:
                    if len(g[0]) == 4:
                        d = datetime(int(g[0]), int(g[1]), int(g[2]))
                    else:
                        d = datetime(int(g[2]), int(g[1]), int(g[0]))
                    return d.strftime("%Y-%m-%d")
                except ValueError:
                    continue
        return None

    @classmethod
    def _extract_total(cls, text: str) -> tuple[str, float]:
        """Extract currency and grand total amount."""
        # Find explicit total lines: Total, Grand Total, Net Total, Amount Due, Balance
        total_patterns = [
            r"(?:grand\s*total|net\s*total|total\s*amount|total|amount\s*due|balance\s*due)\s*[:\-]?\s*([^\d\n]{0,5})\s*([\d,]+(?:\.\d{1,2})?)",
        ]
        for pat in total_patterns:
            matches = re.findall(pat, text, re.IGNORECASE)
            if matches:
                # Pick the last or largest total
                raw_curr, raw_amt = matches[-1]
                amt_str = raw_amt.replace(",", "")
                try:
                    amt = float(amt_str)
                    currency = cls._detect_currency(raw_curr, text)
                    return currency, amt
                except ValueError:
                    pass

        # Fallback: scan for highest number formatted like price
        num_matches = re.findall(r"\b([0-9]{1,3}(?:,[0-9]{3})*(?:\.[0-9]{2})?)\b", text)
        clean_nums = []
        for n in num_matches:
            try:
                val = float(n.replace(",", ""))
                if 1.0 <= val < 100000000.0:
                    clean_nums.append(val)
            except ValueError:
                pass

        total = max(clean_nums) if clean_nums else 0.0
        currency = cls._detect_currency("", text)
        return currency, total

    @classmethod
    def _detect_currency(cls, prefix: str, full_text: str) -> str:
        """Infer currency from token or document text."""
        combined = (prefix + " " + full_text[:300]).lower()
        for symbol, code in CURRENCY_MAP.items():
            if symbol in combined:
                return code
        return "MMK"

    @classmethod
    def _extract_tax(cls, text: str) -> float:
        """Extract Tax, VAT, or Commercial Tax amount."""
        patterns = [
            r"(?:commercial\s*tax|tax|vat|gst)\s*(?:\(\d+%\))?\s*[:\-]?\s*([^\d\n]{0,5})\s*([\d,]+(?:\.\d{1,2})?)",
        ]
        for pat in patterns:
            match = re.search(pat, text, re.IGNORECASE)
            if match:
                try:
                    return float(match.group(2).replace(",", ""))
                except ValueError:
                    pass
        return 0.0

    @classmethod
    def _classify_category(cls, text: str, vendor: str) -> str:
        """Classify into standard accounting expense categories."""
        combined = (vendor + " " + text).lower()
        for cat, kw_list in CATEGORY_KEYWORDS.items():
            if any(kw in combined for kw in kw_list):
                return cat
        return "General Expense"

    @classmethod
    def _extract_line_items(cls, lines: list[str]) -> list[dict[str, Any]]:
        """Identify itemized product/service lines."""
        items = []
        item_regex = re.compile(r"^(.+?)\s+(\d+)\s+([0-9,]+(?:\.\d{2})?)$")
        for line in lines:
            m = item_regex.match(line)
            if m:
                desc, qty, price = m.groups()
                try:
                    items.append({
                        "description": desc.strip(),
                        "quantity": int(qty),
                        "unit_price": float(price.replace(",", "")),
                    })
                except ValueError:
                    continue
        return items[:20]  # Cap at top 20 items
