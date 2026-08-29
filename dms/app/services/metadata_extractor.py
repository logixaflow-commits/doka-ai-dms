"""
Office DMS - Metadata Extractor
Regex-based extraction of structured data from OCR text.
Supports: NRC numbers, Invoice numbers, BL numbers, ETA/ETD dates,
Supplier names, Container numbers, Ports, Amounts, etc.
"""

import re
from datetime import datetime
from typing import Dict, List, Optional, Any
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class MetadataExtractor:
    """
    Extracts structured metadata from document OCR text using configurable
    regex patterns. Supports both English and Myanmar text.
    """

    def __init__(self):
        self.patterns = settings.patterns
        self.suppliers = settings.suppliers
        self._compile_patterns()
        logger.info(f"MetadataExtractor initialized with {len(self.patterns)} patterns")

    def _compile_patterns(self):
        """Compile regex patterns for performance."""
        self._compiled = {}
        for name, pattern in self.patterns.items():
            try:
                self._compiled[name] = re.compile(pattern)
            except re.error as e:
                logger.warning(f"Invalid regex pattern '{name}': {e}")

    def extract(self, text: str) -> Dict[str, Any]:
        """
        Extract all metadata from OCR text.

        Returns:
            Dictionary of extracted metadata fields.
        """
        if not text or not text.strip():
            return {}

        metadata = {}

        # Extract each pattern
        metadata["nrc"] = self._extract_nrc(text)
        metadata["invoice_number"] = self._extract_invoice_number(text)
        metadata["bl_number"] = self._extract_bl_number(text)
        metadata["eta"] = self._extract_eta(text)
        metadata["etd"] = self._extract_etd(text)
        metadata["supplier"] = self._extract_supplier(text)
        metadata["consignee"] = self._extract_consignee(text)
        metadata["container_no"] = self._extract_container(text)
        metadata["port_loading"] = self._extract_port_loading(text)
        metadata["port_discharge"] = self._extract_port_discharge(text)
        metadata["amount"] = self._extract_amount(text)
        metadata["currency"] = self._extract_currency(text)
        metadata["dates"] = self._extract_all_dates(text)
        metadata["customs_reg"] = self._extract_customs_reg(text)

        # Clean None values
        metadata = {k: v for k, v in metadata.items() if v is not None}

        # Detect supplier from supplier list
        if not metadata.get("supplier"):
            detected_supplier = self._detect_supplier_from_list(text)
            if detected_supplier:
                metadata["supplier"] = detected_supplier

        logger.debug(f"Extracted metadata: {list(metadata.keys())}")
        return metadata

    def _extract_nrc(self, text: str) -> Optional[str]:
        """Extract Myanmar NRC number."""
        pattern = self._compiled.get("nrc_mm")
        if not pattern:
            return None

        matches = pattern.findall(text)
        if matches:
            # Handle tuple results from multiple capture groups
            for match in matches:
                if isinstance(match, tuple):
                    match = next((m for m in match if m), None)
                if match:
                    return self._clean_value(match)
        return None

    def _extract_invoice_number(self, text: str) -> Optional[str]:
        """Extract invoice number."""
        pattern = self._compiled.get("invoice_number")
        if not pattern:
            return None

        for match in pattern.finditer(text):
            groups = [g for g in match.groups() if g]
            if groups:
                return self._clean_value(groups[0])
        return None

    def _extract_bl_number(self, text: str) -> Optional[str]:
        """Extract Bill of Lading number."""
        pattern = self._compiled.get("bl_number")
        if not pattern:
            return None

        for match in pattern.finditer(text):
            groups = [g for g in match.groups() if g]
            if groups:
                return self._clean_value(groups[0])
        return None

    def _extract_eta(self, text: str) -> Optional[str]:
        """Extract ETA date and normalize to ISO format."""
        pattern = self._compiled.get("eta")
        if not pattern:
            return None

        match = pattern.search(text)
        if match:
            date_str = match.group(1)
            return self._normalize_date(date_str)
        return None

    def _extract_etd(self, text: str) -> Optional[str]:
        """Extract ETD date and normalize to ISO format."""
        pattern = self._compiled.get("etd")
        if not pattern:
            return None

        match = pattern.search(text)
        if match:
            date_str = match.group(1)
            return self._normalize_date(date_str)
        return None

    def _extract_supplier(self, text: str) -> Optional[str]:
        """Extract supplier/vendor name."""
        pattern = self._compiled.get("supplier")
        if not pattern:
            return None

        match = pattern.search(text)
        if match:
            return self._clean_value(match.group(1))
        return None

    def _extract_consignee(self, text: str) -> Optional[str]:
        """Extract consignee name."""
        pattern = self._compiled.get("consignee")
        if not pattern:
            return None

        match = pattern.search(text)
        if match:
            return self._clean_value(match.group(1))
        return None

    def _extract_container(self, text: str) -> Optional[str]:
        """Extract container number."""
        pattern = self._compiled.get("container_number")
        if not pattern:
            return None

        match = pattern.search(text)
        if match:
            return self._clean_value(match.group(1)).upper()
        return None

    def _extract_port_loading(self, text: str) -> Optional[str]:
        """Extract port of loading."""
        pattern = self._compiled.get("port_loading")
        if not pattern:
            return None

        match = pattern.search(text)
        if match:
            return self._clean_value(match.group(1))
        return None

    def _extract_port_discharge(self, text: str) -> Optional[str]:
        """Extract port of discharge."""
        pattern = self._compiled.get("port_discharge")
        if not pattern:
            return None

        match = pattern.search(text)
        if match:
            return self._clean_value(match.group(1))
        return None

    def _extract_amount(self, text: str) -> Optional[str]:
        """Extract total amount."""
        pattern = self._compiled.get("amount")
        if not pattern:
            return None

        match = pattern.search(text)
        if match:
            return self._clean_value(match.group(1))
        return None

    def _extract_currency(self, text: str) -> Optional[str]:
        """Extract currency code."""
        pattern = self._compiled.get("currency")
        if not pattern:
            return None

        match = pattern.search(text)
        if match:
            return self._clean_value(match.group(0)).upper()
        return None

    def _extract_all_dates(self, text: str) -> List[str]:
        """Extract all dates found in text."""
        pattern = self._compiled.get("date")
        if not pattern:
            return []

        matches = pattern.findall(text)
        normalized = []
        for match in matches:
            norm = self._normalize_date(match)
            if norm and norm not in normalized:
                normalized.append(norm)
        return normalized[:10]  # Limit to 10 dates

    def _extract_customs_reg(self, text: str) -> Optional[str]:
        """Extract customs registration number."""
        pattern = self._compiled.get("customs_reg")
        if not pattern:
            return None

        match = pattern.search(text)
        if match:
            return self._clean_value(match.group(1))
        return None

    def _detect_supplier_from_list(self, text: str) -> Optional[str]:
        """Detect supplier from configured supplier list."""
        supplier = settings.get_supplier_by_alias(text)
        if supplier:
            return supplier.name
        return None

    def _normalize_date(self, date_str: str) -> Optional[str]:
        """Normalize various date formats to ISO YYYY-MM-DD."""
        if not date_str:
            return None

        date_str = date_str.strip()

        formats = [
            "%Y-%m-%d",  # 2025-03-15
            "%Y/%m/%d",  # 2025/03/15
            "%d-%m-%Y",  # 15-03-2025
            "%d/%m/%Y",  # 15/03/2025
            "%m-%d-%Y",  # 03-15-2025
            "%m/%d/%Y",  # 03/15/2025
            "%d %b %Y",  # 15 Mar 2025
            "%d %B %Y",  # 15 March 2025
            "%b %d, %Y",  # Mar 15, 2025
            "%B %d, %Y",  # March 15, 2025
        ]

        for fmt in formats:
            try:
                dt = datetime.strptime(date_str, fmt)
                return dt.strftime("%Y-%m-%d")
            except ValueError:
                continue

        return date_str  # Return as-is if can't parse

    def _clean_value(self, value: str) -> str:
        """Clean extracted value: strip whitespace, normalize."""
        if not value:
            return value
        value = value.strip()
        value = re.sub(r"\s+", " ", value)  # Normalize whitespace
        value = value.rstrip(":-,.;")  # Remove trailing punctuation
        return value.strip()


# Singleton
metadata_extractor = MetadataExtractor()
