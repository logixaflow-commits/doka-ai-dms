"""
AI Tagging Service - Automatic entity extraction and tag generation
Uses spaCy for NLP and keyword extraction for intelligent tagging.
"""
import re
from typing import List, Dict, Optional, Set
from loguru import logger
import json

# Try to import spaCy (optional - falls back to regex if not available)
try:
    import spacy
    SPACY_AVAILABLE = True
    # Load small English model
    try:
        nlp = spacy.load("en_core_web_sm")
    except OSError:
        logger.warning("spaCy model 'en_core_web_sm' not found. Using fallback extraction.")
        SPACY_AVAILABLE = False
        nlp = None
except ImportError:
    logger.warning("spaCy not installed. Using fallback extraction.")
    SPACY_AVAILABLE = False
    nlp = None

# Try to import RAKE for keyword extraction
try:
    from rake_nltk import Rake
    RAKE_AVAILABLE = True
    rake = Rake()
except ImportError:
    logger.warning("RAKE not installed. Using simple keyword extraction.")
    RAKE_AVAILABLE = False
    rake = None


class AITaggingService:
    """Service for AI-powered document tagging and entity extraction."""

    def __init__(self):
        # Myanmar-specific patterns
        self.patterns = {
            'nrc': r'(?:[၀-၉]{1,2}[/\s][က-အ][က-အ]{2}\s*\([^)]{2,10}\)\s*[၀-၉]{6,10}|[0-9]{1,2}[/\\][A-Za-z][A-Za-z]{2}\s*\([A-Za-z]{3,20}\)\s*[0-9]{6,10})',
            'invoice_number': r'(?:invoice\s*(?:no|number|#|ref)\.?\s*[:\-\s]*([A-Z0-9\-/]{3,30})|inv\s*(?:no|#)?\.?\s*[:\-\s]*([A-Z0-9\-/]{3,30}))',
            'bl_number': r'(?:bill\s*of\s*lading\s*(?:no|number|#)\.?\s*[:\-\s]*([A-Z0-9\-/]{5,30})|b/l\s*(?:no|#)?\.?\s*[:\-\s]*([A-Z0-9\-/]{5,30}))',
            'container': r'(?:container\s*(?:no|number|#)?\.?\s*[:\-\s]*([A-Z]{4}\d{7}))',
            'customs_code': r'(?:hs\s*code|harmonized\s*code)\s*[:\-\s]*([0-9]{4,10})',
            'amount': r'(?:total\s*amount|amount)\s*[:\-\s]*([A-Z]{2,4}\s*[\d,]+\.?\d{0,2})',
            'eta': r'(?:eta|estimated\s*arrival)\s*[:\-\s]*(\d{4}[-/]\d{1,2}[-/]\d{1,2}|\d{1,2}\s+[A-Za-z]{3,9}\s+\d{4})',
            'etd': r'(?:etd|estimated\s*departure|departure\s*date)\s*[:\-\s]*(\d{4}[-/]\d{1,2}[-/]\d{1,2}|\d{1,2}\s+[A-Za-z]{3,9}\s+\d{4})',
        }

        # Urgency keywords
        self.urgent_keywords = [
            'urgent', 'immediately', 'asap', 'emergency', 'critical', 
            'priority', 'expedite', 'rush', 'immediate', 'deadline',
            'overnight', 'express', 'fast-track', 'time-sensitive'
        ]

        # Logistics-related keywords
        self.logistics_keywords = [
            'shipment', 'delivery', 'freight', 'cargo', 'logistics',
            'transport', 'shipping', 'import', 'export', 'customs',
            'warehouse', 'container', 'port', 'harbor', 'terminal'
        ]

    def extract_entities(self, text: str) -> Dict[str, List[str]]:
        """
        Extract entities from document text using NLP.
        
        Args:
            text: OCR text from document
            
        Returns:
            Dict with extracted entities (suppliers, dates, amounts, etc.)
        """
        if not text:
            return {}

        entities = {
            'suppliers': [],
            'dates': [],
            'amounts': [],
            'invoice_numbers': [],
            'bl_numbers': [],
            'nrc_numbers': [],
            'containers': [],
            'customs_codes': [],
            'ports': [],
            'contacts': []
        }

        # Extract using regex patterns
        for key, pattern in self.patterns.items():
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                if key == 'invoice_number':
                    # Extract the actual invoice number
                    for match in matches:
                        if isinstance(match, tuple):
                            entities['invoice_numbers'].extend([m for m in match if m])
                        else:
                            entities['invoice_numbers'].append(match)
                elif key == 'bl_number':
                    for match in matches:
                        if isinstance(match, tuple):
                            entities['bl_numbers'].extend([m for m in match if m])
                        else:
                            entities['bl_numbers'].append(match)
                elif key == 'nrc':
                    entities['nrc_numbers'].extend(matches)
                elif key == 'container':
                    entities['containers'].extend(matches)
                elif key == 'customs_code':
                    entities['customs_codes'].extend(matches)
                elif key == 'amount':
                    entities['amounts'].extend(matches)
                elif key in ['eta', 'etd']:
                    entities['dates'].extend(matches)

        # Use spaCy for advanced NLP if available
        if SPACY_AVAILABLE and nlp:
            try:
                doc = nlp(text[:50000])  # Process first 50k chars to avoid timeout
                
                # Extract persons (for contacts)
                entities['contacts'] = [ent.text for ent in doc.ents if ent.label_ == 'PERSON']
                
                # Extract organizations (for suppliers)
                entities['suppliers'] = [ent.text for ent in doc.ents if ent.label_ == 'ORG']
                
                # Extract dates
                entities['dates'].extend([ent.text for ent in doc.ents if ent.label_ in ['DATE', 'TIME']])
                
                # Extract locations (for ports)
                entities['ports'] = [ent.text for ent in doc.ents if ent.label_ in ['GPE', 'LOC', 'FAC']]
                
            except Exception as e:
                logger.warning(f"spaCy processing failed: {e}")

        # Deduplicate and clean up
        for key in entities:
            entities[key] = list(set(entities[key]))[:10]  # Limit to 10 entities per type

        return entities

    def generate_tags(self, text: str, entities: Optional[Dict] = None) -> List[str]:
        """
        Generate relevant tags from document text.
        
        Args:
            text: OCR text from document
            entities: Pre-extracted entities (optional)
            
        Returns:
            List of tags
        """
        if not text:
            return []

        tags = set()
        entities = entities or self.extract_entities(text)

        # Add entity-based tags
        if entities.get('suppliers'):
            tags.update([f"Supplier: {s[:20]}" for s in entities['suppliers'][:3]])
        
        if entities.get('invoice_numbers'):
            tags.add("Has Invoice")
        
        if entities.get('bl_numbers'):
            tags.add("Has BL")
        
        if entities.get('nrc_numbers'):
            tags.add("Contains NRC")
        
        if entities.get('containers'):
            tags.add("Has Container")

        # Use RAKE for keyword extraction if available
        if RAKE_AVAILABLE and rake:
            try:
                rake.extract_keywords_from_text(text)
                keywords = rake.get_ranked_phrases()[:10]  # Top 10 keywords
                tags.update([k.title() for k in keywords if len(k) > 3])
            except Exception as e:
                logger.warning(f"RAKE extraction failed: {e}")
        else:
            # Fallback: extract significant words
            words = re.findall(r'\b[a-z]{4,}\b', text.lower())
            from collections import Counter
            word_counts = Counter(words)
            common_words = [w for w, c in word_counts.most_common(15) if c > 2]
            tags.update([w.title() for w in common_words])

        # Add category-based tags
        text_lower = text.lower()
        if any(kw in text_lower for kw in ['invoice', 'bill', 'payment']):
            tags.add("Invoice")
        if any(kw in text_lower for kw in ['bill of lading', 'bl', 'waybill']):
            tags.add("Bill of Lading")
        if any(kw in text_lower for kw in ['nrc', 'national registration', 'citizen']):
            tags.add("NRC")
        if any(kw in text_lower for kw in ['fda', 'food and drug']):
            tags.add("FDA")
        if any(kw in text_lower for kw in ['license', 'permit', 'import license']):
            tags.add("License")
        if any(kw in text_lower for kw in ['customs', 'cusdec', 'declaration']):
            tags.add("Customs")

        # Add logistics tags
        if any(kw in text_lower for kw in self.logistics_keywords):
            tags.add("Logistics")

        # Clean up tags
        cleaned_tags = []
        for tag in tags:
            tag = tag.strip()
            if len(tag) > 2 and len(tag) < 30:  # Reasonable length
                cleaned_tags.append(tag)

        return sorted(list(set(cleaned_tags)))[:20]  # Limit to 20 tags

    def classify_urgency(self, text: str) -> str:
        """
        Classify document urgency based on keywords.
        
        Args:
            text: Document text
            
        Returns:
            'urgent', 'normal', or 'low'
        """
        if not text:
            return 'normal'

        text_lower = text.lower()
        urgent_count = sum(1 for kw in self.urgent_keywords if kw in text_lower)

        if urgent_count >= 2:
            return 'urgent'
        elif urgent_count == 1:
            return 'normal'
        else:
            # Check for deadlines or dates
            if re.search(r'\d{1,2}\s*(?:days?|weeks?|months?)\s*(?:remaining|left|to go)', text_lower):
                return 'normal'
            return 'low'

    def extract_customs_code(self, text: str) -> Optional[str]:
        """
        Extract Myanmar Customs HS code from text.
        
        Args:
            text: Document text
            
        Returns:
            HS code string or None
        """
        if not text:
            return None

        # Myanmar HS codes are typically 4-8 digits
        pattern = r'(?:hs\s*code|harmonized\s*code|customs\s*code)\s*[:\-\s]*([0-9]{4,8})'
        match = re.search(pattern, text, re.IGNORECASE)
        
        if match:
            return match.group(1)
        
        # Alternative: look for 4-8 digit numbers that could be HS codes
        numbers = re.findall(r'\b[0-9]{4,8}\b', text)
        for num in numbers:
            if len(num) in [4, 6, 8]:
                return num
        
        return None

    def extract_document_metadata(self, text: str) -> Dict:
        """
        Extract comprehensive metadata from document.
        
        Args:
            text: Document text
            
        Returns:
            Dictionary with all extracted metadata
        """
        entities = self.extract_entities(text)
        tags = self.generate_tags(text, entities)
        urgency = self.classify_urgency(text)
        customs_code = self.extract_customs_code(text)

        return {
            'entities': entities,
            'tags': tags,
            'urgency': urgency,
            'customs_code': customs_code,
            'has_invoice': bool(entities.get('invoice_numbers')),
            'has_bl': bool(entities.get('bl_numbers')),
            'has_nrc': bool(entities.get('nrc_numbers')),
        }


# Global AI tagging service instance
ai_tagging_service = AITaggingService()