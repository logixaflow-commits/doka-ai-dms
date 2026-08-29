"""
Document Function Detection Module
Advanced AI-powered detection of document functions and types
"""
import os
from typing import Dict, List, Optional, Any
from enum import Enum
from dataclasses import dataclass
from loguru import logger
from app.services.unified_ai_service import UnifiedAIService
from app.core.performance import cache_result


class DocumentFunction(Enum):
    """Document function types"""
    INVOICE = "invoice"
    BILL_OF_LADING = "bill_of_lading"
    PURCHASE_ORDER = "purchase_order"
    DELIVERY_NOTE = "delivery_note"
    RECEIPT = "receipt"
    CONTRACT = "contract"
    CERTIFICATE = "certificate"
    LICENSE = "license"
    INSURANCE = "insurance"
    QUOTATION = "quotation"
    PROFORMA_INVOICE = "proforma_invoice"
    PACKING_LIST = "packing_list"
    QUALITY_CERTIFICATE = "quality_certificate"
    INSPECTION_REPORT = "inspection_report"
    CUSTOMS_DECLARATION = "customs_declaration"
    UNKNOWN = "unknown"


class DocumentQuality(Enum):
    """Document quality levels"""
    EXCELLENT = "excellent"
    GOOD = "good"
    ACCEPTABLE = "acceptable"
    POOR = "poor"
    FRACTURED = "fractured"
    DAMAGED = "damaged"
    INCOMPLETE = "incomplete"
    UNREADABLE = "unreadable"


@dataclass
class FunctionDetectionResult:
    """Result of function detection"""
    primary_function: DocumentFunction
    confidence: float
    alternative_functions: List[tuple[DocumentFunction, float]]
    detected_keywords: List[str]
    detected_patterns: List[str]
    analysis_metadata: Dict[str, Any]


@dataclass
class FractureDetectionResult:
    """Result of fracture/damage detection"""
    quality_level: DocumentQuality
    damage_detected: bool
    damage_type: Optional[str]
    damage_severity: str  # "low", "medium", "high", "critical"
    affected_areas: List[str]
    confidence: float
    recommended_actions: List[str]
    analysis_metadata: Dict[str, Any]


class FunctionDetectionService:
    """Service for detecting document functions using AI"""
    
    def __init__(self):
        self.ai_service = UnifiedAIService()
        self.function_keywords = self._load_function_keywords()
        self.function_patterns = self._load_function_patterns()
        
    def _load_function_keywords(self) -> Dict[DocumentFunction, List[str]]:
        """Load keywords for each document function"""
        return {
            DocumentFunction.INVOICE: [
                "invoice", "bill", "amount", "due date", "payment terms", "tax", "total",
                "invoice no", "inv-", "invoice number", "billing address", "ship to"
            ],
            DocumentFunction.BILL_OF_LADING: [
                "bill of lading", "b/l", "bl", "carrier", "vessel", "port of loading",
                "port of discharge", "freight", "consignee", "shipper", "notify party",
                "container no", "seal no", "master bill of lading"
            ],
            DocumentFunction.PURCHASE_ORDER: [
                "purchase order", "po", "p.o.", "order no", "item", "quantity",
                "unit price", "delivery date", "requested by", "approved by", "po number"
            ],
            DocumentFunction.DELIVERY_NOTE: [
                "delivery note", "dn", "delivery", "received", "goods", "quantity",
                "condition", "signature", "delivered by", "received by"
            ],
            DocumentFunction.RECEIPT: [
                "receipt", "received", "amount paid", "payment", "cash", "card",
                "transaction", "acknowledgement", "paid by", "received from"
            ],
            DocumentFunction.CONTRACT: [
                "contract", "agreement", "terms and conditions", "party a", "party b",
                "obligations", "termination", "breach", "effective date", "expiry date"
            ],
            DocumentFunction.CERTIFICATE: [
                "certificate", "cert", "certified", "authentication", "valid until",
                "issued by", "certificate no", "registration", "license", "permit"
            ],
            DocumentFunction.LICENSE: [
                "license", "licence", "permit", "authorization", "valid until",
                "issued by", "license no", "registration", "expiry", "renewal"
            ],
            DocumentFunction.INSURANCE: [
                "insurance", "policy", "coverage", "premium", "deductible",
                "insured", "insurer", "policy no", "effective date", "expiry date"
            ],
            DocumentFunction.QUOTATION: [
                "quotation", "quote", "quote no", "valid until", "terms", "unit price",
                "total amount", "prepared by", "quotation date"
            ],
            DocumentFunction.PROFORMA_INVOICE: [
                "proforma invoice", "proforma", "p.i.", "pre-shipment document",
                "customs", "commercial invoice", "bank details", "payment terms"
            ],
            DocumentFunction.PACKING_LIST: [
                "packing list", "package", "cargo", "weight", "measurement",
                "gross weight", "net weight", "marks and numbers", "container"
            ],
            DocumentFunction.QUALITY_CERTIFICATE: [
                "quality certificate", "quality report", "inspection", "conformity",
                "approved", "rejected", "quality control", "qc", "qa"
            ],
            DocumentFunction.INSPECTION_REPORT: [
                "inspection report", "inspection", "examined", "findings", "defects",
                "inspector", "inspection date", "conformity", "non-conformity"
            ],
            DocumentFunction.CUSTOMS_DECLARATION: [
                "customs declaration", "customs", "declaration", "import", "export",
                "duty", "tariff", "hs code", "declarant", "customs broker"
            ]
        }
    
    def _load_function_patterns(self) -> Dict[DocumentFunction, List[str]]:
        """Load regex patterns for each document function"""
        return {
            DocumentFunction.INVOICE: [
                r'invoice\s+no[:\s]+[\w-]+',
                r'inv[-/]?\s*[\d]+',
                r'total[:\s]*[.\d,]+',
                r'due\s+date[:\s]*[\d{4}-\d{2}-\d{2}]'
            ],
            DocumentFunction.BILL_OF_LADING: [
                r'bill\s+of\s+lading',
                r'b/l\s*no[:\s]+[\w-]+',
                r'container\s+no[:\s]+[\w-]+',
                r'port\s+of\s+(?:loading|discharge)[:\s]+[\w\s]+'
            ],
            DocumentFunction.PURCHASE_ORDER: [
                r'purchase\s+order',
                r'p\.o\.\s*no[:\s]+[\w-]+',
                r'order\s+no[:\s]+[\w-]+',
                r'unit\s+price[:\s]*[.\d,]+'
            ],
            DocumentFunction.DELIVERY_NOTE: [
                r'delivery\s+note',
                r'dn\s*no[:\s]+[\w-]+',
                r'received\s+by',
                r'delivered\s+by'
            ],
            DocumentFunction.RECEIPT: [
                r'receipt',
                r'received',
                r'amount\s+paid',
                r'payment\s+method'
            ],
            DocumentFunction.CONTRACT: [
                r'contract',
                r'agreement',
                'terms\s+and\s+conditions',
                r'party\s+[ab]\s*\:'
            ],
            DocumentFunction.CERTIFICATE: [
                r'certificate',
                r'certified',
                r'valid\s+until',
                r'issued\s+by'
            ],
            DocumentFunction.LICENSE: [
                r'license',
                r'permit',
                r'authorization',
                r'valid\s+until'
            ],
            DocumentFunction.INSURANCE: [
                r'insurance',
                r'policy\s+no',
                r'coverage',
                r'premium'
            ],
            DocumentFunction.QUOTATION: [
                r'quotation',
                r'quote\s+no',
                r'valid\s+until',
                r'unit\s+price'
            ],
            DocumentFunction.PROFORMA_INVOICE: [
                r'proforma\s+invoice',
                r'p\.i\.',
                r'commercial\s+invoice',
                r'pre-shipment'
            ],
            DocumentFunction.PACKING_LIST: [
                r'packing\s+list',
                r'gross\s+weight',
                r'net\s+weight',
                r'marks\s+and\s+numbers'
            ],
            DocumentFunction.QUALITY_CERTIFICATE: [
                r'quality\s+certificate',
                r'quality\s+report',
                r'inspection\s+report',
                r'conformity'
            ],
            DocumentFunction.INSPECTION_REPORT: [
                r'inspection\s+report',
                r'examined',
                r'findings',
                r'defects'
            ],
            DocumentFunction.CUSTOMS_DECLARATION: [
                r'customs\s+declaration',
                r'import\s+declaration',
                r'hs\s+code',
                r'duty'
            ]
        }
    
    @cache_result(ttl=3600)
    def detect_function(self, text: str, metadata: Optional[Dict] = None) -> FunctionDetectionResult:
        """Detect document function using AI and keyword analysis"""
        if not text:
            return FunctionDetectionResult(
                primary_function=DocumentFunction.UNKNOWN,
                confidence=0.0,
                alternative_functions=[],
                detected_keywords=[],
                detected_patterns=[],
                analysis_metadata={}
            )
        
        # Keyword-based detection
        function_scores = {}
        detected_keywords = {}
        detected_patterns = {}
        
        for function, keywords in self.function_keywords.items():
            score = 0
            found_keywords = []
            
            for keyword in keywords:
                if keyword.lower() in text.lower():
                    score += 1
                    found_keywords.append(keyword)
            
            if score > 0:
                function_scores[function] = score
                detected_keywords[function] = found_keywords
        
        # Pattern-based detection
        for function, patterns in self.function_patterns.items():
            pattern_score = 0
            found_patterns = []
            
            for pattern in patterns:
                import re
                if re.search(pattern, text, re.IGNORECASE):
                    pattern_score += 2
                    found_patterns.append(pattern)
            
            if pattern_score > 0:
                function_scores[function] = function_scores.get(function, 0) + pattern_score
                detected_patterns[function] = found_patterns
        
        # Sort by score
        sorted_functions = sorted(function_scores.items(), key=lambda x: x[1], reverse=True)
        
        if not sorted_functions:
            return FunctionDetectionResult(
                primary_function=DocumentFunction.UNKNOWN,
                confidence=0.0,
                alternative_functions=[],
                detected_keywords=[],
                detected_patterns=[],
                analysis_metadata={"method": "keyword_only"}
            )
        
        # Calculate confidence
        primary_function, primary_score = sorted_functions[0]
        total_score = sum(score for _, score in sorted_functions)
        confidence = primary_score / total_score if total_score > 0 else 0.0
        
        # Alternative functions
        alternative_functions = [
            (func, score / total_score if total_score > 0 else 0.0)
            for func, score in sorted_functions[1:5]
        ]
        
        # AI-enhanced detection (if available)
        ai_confidence = 0.0
        if self.ai_service.is_available():
            try:
                ai_result = self.ai_service.classify_document(text, metadata)
                if ai_result and ai_result.get("confidence", 0) > 0.7:
                    ai_confidence = ai_result["confidence"]
                    ai_function = ai_result.get("category", "")
                    # Combine keyword and AI results
                    if ai_function:
                        confidence = (confidence + ai_confidence) / 2
            except Exception as e:
                logger.warning(f"AI function detection failed: {e}")
        
        return FunctionDetectionResult(
            primary_function=primary_function,
                confidence=confidence,
            alternative_functions=alternative_functions,
            detected_keywords=list(detected_keywords.get(primary_function, [])),
            detected_patterns=list(detected_patterns.get(primary_function, [])),
            analysis_metadata={
                "method": "hybrid",
                "ai_confidence": ai_confidence,
                "keyword_confidence": confidence
            }
        )


class FractureDetectionService:
    """Service for detecting document damage, fractures, and quality issues"""
    
    def __init__(self):
        self.ai_service = UnifiedAIService()
        self.damage_keywords = self._load_damage_keywords()
        self.quality_indicators = self._load_quality_indicators()
    
    def _load_damage_keywords(self) -> Dict[str, List[str]]:
        """Load keywords related to damage and fractures"""
        return {
            "fracture": [
                "fracture", "crack", "broken", "split", "torn", "damaged",
                "shattered", "fragmented", "incomplete", "partial"
            ],
            "quality_issue": [
                "smudged", "blurry", "unreadable", "faded", "stained",
                "watermark", "corrupted", "defective", "irregular"
            ],
            "incomplete": [
                "incomplete", "missing page", "page missing", "incomplete",
                "partial", "torn edge", "cut off", "truncated"
            ]
        }
    
    def _load_quality_indicators(self) -> Dict[str, List[str]]:
        """Load quality indicators"""
        return {
            "excellent": [
            "clear", "sharp", "readable", "intact", "complete",
                "high quality", "excellent condition", "perfect"
            ],
            "good": [
                "clear", "readable", "intact", "good condition",
                "acceptable quality", "minor issues"
            ],
            "poor": [
                "blurry", "faded", "low quality", "difficult to read",
                "poor condition", "damaged"
            ],
            "fractured": [
                "fracture", "crack", "broken", "split", "torn",
                "shattered", "fragmented"
            ]
        }
    
    @cache_result(ttl=3600)
    def detect_fracture(
        self, 
        text: str, 
        image_data: Optional[bytes] = None,
        metadata: Optional[Dict] = None
    ) -> FractureDetectionResult:
        """Detect fractures, damage, and quality issues in documents"""
        if not text and not image_data:
            return FractureDetectionResult(
                quality_level=DocumentQuality.UNKNOWN,
                damage_detected=False,
                damage_type=None,
                damage_severity="unknown",
                affected_areas=[],
                confidence=0.0,
                recommended_actions=[],
                analysis_metadata={"method": "no_data"}
            )
        
        # Text-based damage detection
        damage_detected = False
        damage_type = None
        damage_severity = "low"
        affected_areas = []
        confidence = 0.0
        
        # Check for damage keywords
        for damage_category, keywords in self.damage_keywords.items():
            for keyword in keywords:
                if keyword.lower() in text.lower():
                    damage_detected = True
                    damage_type = damage_category
                    affected_areas.append(f"Text contains: {keyword}")
                    break
            if damage_detected:
                break
        
        # Check quality indicators
        quality_scores = {}
        for quality, indicators in self.quality_indicators.items():
            score = 0
            for indicator in indicators:
                if indicator.lower() in text.lower():
                    score += 1
            if score > 0:
                quality_scores[quality] = score
        
        # Determine quality level
        if quality_scores:
            sorted_quality = sorted(quality_scores.items(), key=lambda x: x[1], reverse=True)
            best_quality = sorted_quality[0][0]
            confidence = sorted_quality[0][1] / sum(score for _, score in quality_scores)
        else:
            best_quality = DocumentQuality.ACCEPTABLE
            confidence = 0.5
        
        # Determine damage severity
        if damage_detected:
            if damage_type == "fracture":
                damage_severity = "critical"
            elif damage_type == "incomplete":
                damage_severity = "high"
            else:
                damage_severity = "medium"
        else:
            if best_quality == DocumentQuality.POOR:
                damage_severity = "medium"
            elif best_quality == DocumentQuality.ACCEPTABLE:
                damage_severity = "low"
        
        # Generate recommended actions
        recommended_actions = self._generate_recommended_actions(
            best_quality, damage_detected, damage_severity
        )
        
        # AI-enhanced detection (if available)
        ai_confidence = 0.0
        if self.ai_service.is_available() and image_data:
            try:
                ai_result = self.ai_service.analyze_image_quality(image_data)
                if ai_result:
                    ai_confidence = ai_result.get("confidence", 0)
                    ai_quality = ai_result.get("quality", "unknown")
                    if ai_quality != "unknown":
                        best_quality = DocumentQuality(ai_quality)
                        confidence = (confidence + ai_confidence) / 2
            except Exception as e:
                logger.warning(f"AI fracture detection failed: {e}")
        
        return FractureDetectionResult(
            quality_level=best_quality,
            damage_detected=damage_detected,
            damage_type=damage_type,
            damage_severity=damage_severity,
            affected_areas=affected_areas,
            confidence=confidence,
            recommended_actions=recommended_actions,
            analysis_metadata={
                "method": "hybrid",
                "ai_confidence": ai_confidence,
                "text_confidence": confidence
            }
        )
    
    def _generate_recommended_actions(
        self, 
        quality: DocumentQuality, 
        damage_detected: bool, 
        severity: str
    ) -> List[str]:
        """Generate recommended actions based on detection results"""
        actions = []
        
        if damage_detected:
            if severity == "critical":
                actions.extend([
                    "Document is critically damaged - require replacement",
                    "Notify document owner immediately",
                    "Flag for manual review",
                    "Consider scanning higher quality version"
                ])
            elif severity == "high":
                actions.extend([
                    "Document has significant damage - review required",
                    "Consider rescanning if original available",
                    "Flag for quality control review"
                ])
            elif severity == "medium":
                actions.extend([
                    "Document has quality issues - review recommended",
                    "May require enhanced OCR processing"
                ])
        else:
            if quality == DocumentQuality.POOR:
                actions.extend([
                    "Document quality is poor - consider rescanning",
                    "Enhance OCR preprocessing if possible",
                    "Manual review recommended"
                ])
            elif quality == DocumentQuality.ACCEPTABLE:
                actions.extend([
                    "Document quality is acceptable",
                    "Standard processing applies"
                ])
            elif quality == DocumentQuality.GOOD:
                actions.extend([
                    "Document quality is good",
                    "Standard processing applies"
                ])
            elif quality == DocumentQuality.EXCELLENT:
                actions.extend([
                    "Document quality is excellent",
                    "Processing with standard quality settings"
                ])
        
        return actions


# Singleton instances
_function_service: Optional[FunctionDetectionService] = None
_fracture_service: Optional[FractureDetectionService] = None


def get_function_detection_service() -> FunctionDetectionService:
    """Get singleton function detection service"""
    global _function_service
    if _function_service is None:
        _function_service = FunctionDetectionService()
    return _function_service


def get_fracture_detection_service() -> FractureDetectionService:
    """Get singleton fracture detection service"""
    global _fracture_service
    if _fracture_service is None:
        _fracture_service = FractureDetectionService()
    return _fracture_service