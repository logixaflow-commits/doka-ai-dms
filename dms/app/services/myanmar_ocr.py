"""
Myanmar Language OCR Service
Enhanced OCR support for Myanmar language documents
"""
import os
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any
from loguru import logger
from app.core.config import settings
from app.core.performance import cache_result


class MyanmarOCRService:
    """Service for Myanmar language OCR processing"""
    
    def __init__(self):
        self.tesseract_path = self._find_tesseract()
        self.myanmar_data_path = self._get_myanmar_data_path()
        self.is_available = self._check_availability()
        
    def _find_tesseract(self) -> Optional[str]:
        """Find Tesseract executable"""
        possible_paths = [
            r"C:\Program Files\Tesseract-OCR\tesseract.exe",
            r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
            r"C:\Program Files\Tesseract-OCR\tesseract",
            "/usr/bin/tesseract",
            "/usr/local/bin/tesseract",
            "/opt/homebrew/bin/tesseract",
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                return path
        
        # Try to find in PATH
        try:
            result = subprocess.run(
                ["tesseract", "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                return "tesseract"
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass
        
        logger.warning("Tesseract not found in system")
        return None
    
    def _get_myanmar_data_path(self) -> Optional[str]:
        """Get Myanmar language data path for Tesseract"""
        possible_paths = [
            r"C:\Program Files\Tesseract-OCR\tessdata\mya.traineddata",
            r"C:\Program Files (x86)\Tesseract-OCR\tessdata\mya.traineddata",
            "/usr/share/tesseract-ocr/4.00/tessdata/mya.traineddata",
            "/usr/local/share/tessdata/mya.traineddata",
            "/opt/homebrew/share/tessdata/mya.traineddata",
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                return path
        
        logger.warning("Myanmar language data not found")
        return None
    
    def _check_availability(self) -> bool:
        """Check if Myanmar OCR is available"""
        return self.tesseract_path is not None and self.myanmar_data_path is not None
    
    @cache_result(ttl=7200)
    def extract_text_myanmar(
        self, 
        image_path: str, 
        language: str = "mya+eng",
        preprocess: bool = True
    ) -> Dict[str, Any]:
        """
        Extract text from image with Myanmar language support
        
        Args:
            image_path: Path to image file
            language: Language code (mya for Myanmar, eng for English, mya+eng for both)
            preprocess: Whether to preprocess image for better OCR
            
        Returns:
            Dictionary with extracted text and metadata
        """
        if not self.is_available:
            logger.warning("Myanmar OCR not available, falling back to basic OCR")
            return self._fallback_ocr(image_path)
        
        try:
            # Preprocess image if requested
            if preprocess:
                processed_path = self._preprocess_image(image_path)
                if processed_path:
                    image_path = processed_path
            
            # Run Tesseract with Myanmar language
            cmd = [
                self.tesseract_path,
                image_path,
                "stdout",
                "-l", language,
                "--oem", "3",  # LSTM OCR engine
                "--psm", "6",  # Assume uniform block of text
                "-c", "preserve_interword_spaces=1"
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                text = result.stdout.strip()
                
                # Post-process Myanmar text
                cleaned_text = self._post_process_myanmar(text)
                
                return {
                    "success": True,
                    "text": cleaned_text,
                    "language": language,
                    "method": "tesseract_myanmar",
                    "confidence": self._estimate_confidence(cleaned_text),
                    "preprocessed": preprocess
                }
            else:
                logger.error(f"Tesseract failed: {result.stderr}")
                return self._fallback_ocr(image_path)
                
        except subprocess.TimeoutExpired:
            logger.error("Tesseract timeout")
            return self._fallback_ocr(image_path)
        except Exception as e:
            logger.error(f"Myanmar OCR failed: {e}")
            return self._fallback_ocr(image_path)
    
    def _preprocess_image(self, image_path: str) -> Optional[str]:
        """Preprocess image for better OCR accuracy"""
        try:
            from PIL import Image, ImageEnhance, ImageFilter
            import numpy as np
            
            # Open image
            img = Image.open(image_path)
            
            # Convert to grayscale
            if img.mode != 'L':
                img = img.convert('L')
            
            # Enhance contrast
            enhancer = ImageEnhance.Contrast(img)
            img = enhancer.enhance(2.0)
            
            # Enhance sharpness
            enhancer = ImageEnhance.Sharpness(img)
            img = enhancer.enhance(2.0)
            
            # Apply threshold
            img_array = np.array(img)
            threshold = 128
            img_array = np.where(img_array > threshold, 255, 0).astype(np.uint8)
            img = Image.fromarray(img_array)
            
            # Save processed image
            processed_path = image_path.replace('.', '_processed.')
            img.save(processed_path)
            
            return processed_path
            
        except ImportError:
            logger.warning("PIL not available for image preprocessing")
            return None
        except Exception as e:
            logger.warning(f"Image preprocessing failed: {e}")
            return None
    
    def _post_process_myanmar(self, text: str) -> str:
        """Post-process Myanmar text for better readability"""
        # Remove common OCR artifacts
        artifacts = [
            '|', 'I', 'l', '1',  # Common confusion
            '\x0c',  # Form feed
            '\x0b',  # Vertical tab
        ]
        
        cleaned = text
        for artifact in artifacts:
            cleaned = cleaned.replace(artifact, '')
        
        # Normalize Myanmar characters
        # (This is a simplified version - full normalization would require myanmar-tools)
        myanmar_vowels = ['ါ', 'ာ', 'ိ', 'ီ', 'ု', 'ူ', 'ေ', 'ဲ', 'ဳ', 'ဴ', 'ဵ', 'ံ', '့', 'း', '္']
        
        # Remove extra whitespace
        cleaned = ' '.join(cleaned.split())
        
        return cleaned
    
    def _estimate_confidence(self, text: str) -> float:
        """Estimate OCR confidence based on text characteristics"""
        if not text:
            return 0.0
        
        # Count Myanmar characters
        myanmar_chars = sum(1 for char in text if '\u1000' <= char <= '\u109F')
        total_chars = len(text)
        
        if total_chars == 0:
            return 0.0
        
        # If mostly Myanmar text, confidence is based on Myanmar character ratio
        myanmar_ratio = myanmar_chars / total_chars
        
        # Base confidence
        confidence = 0.7
        
        # Adjust based on Myanmar character ratio
        if myanmar_ratio > 0.5:
            confidence += 0.2
        elif myanmar_ratio > 0.3:
            confidence += 0.1
        
        # Adjust based on text length (longer text usually means better accuracy)
        if total_chars > 100:
            confidence += 0.1
        
        return min(confidence, 1.0)
    
    def _fallback_ocr(self, image_path: str) -> Dict[str, Any]:
        """Fallback to basic OCR when Myanmar OCR is not available"""
        try:
            from app.services.ocr_service import OCRService
            ocr_service = OCRService()
            text = ocr_service.extract_text(image_path)
            
            return {
                "success": True,
                "text": text,
                "language": "eng",
                "method": "fallback",
                "confidence": 0.5,
                "preprocessed": False
            }
        except Exception as e:
            logger.error(f"Fallback OCR failed: {e}")
            return {
                "success": False,
                "text": "",
                "error": str(e),
                "method": "none"
            }
    
    def detect_myanmar_content(self, text: str) -> bool:
        """Detect if text contains Myanmar language content"""
        if not text:
            return False
        
        myanmar_chars = sum(1 for char in text if '\u1000' <= char <= '\u109F')
        total_chars = len(text)
        
        if total_chars == 0:
            return False
        
        myanmar_ratio = myanmar_chars / total_chars
        return myanmar_ratio > 0.1  # At least 10% Myanmar characters
    
    def get_supported_languages(self) -> list[str]:
        """Get list of supported language combinations"""
        if not self.is_available:
            return ["eng"]
        
        return [
            "mya",  # Myanmar only
            "eng",  # English only
            "mya+eng",  # Myanmar + English
            "mya+eng+chi_sim",  # Myanmar + English + Simplified Chinese
        ]
    
    def install_myanmar_data(self) -> bool:
        """
        Install Myanmar language data for Tesseract
        This is a helper method to download Myanmar traineddata
        """
        try:
            import urllib.request
            
            # Download Myanmar traineddata
            tessdata_url = "https://github.com/tesseract-ocr/tessdata/raw/main/mya.traineddata"
            
            # Determine tessdata directory
            if self.tesseract_path:
                tesseract_dir = os.path.dirname(self.tesseract_path)
                tessdata_dir = os.path.join(tesseract_dir, "tessdata")
            else:
                tessdata_dir = "/usr/share/tesseract-ocr/4.00/tessdata"
            
            os.makedirs(tessdata_dir, exist_ok=True)
            
            mya_data_path = os.path.join(tessdata_dir, "mya.traineddata")
            
            # Download
            urllib.request.urlretrieve(tessdata_url, mya_data_path)
            
            logger.info(f"Myanmar language data installed to {mya_data_path}")
            self.myanmar_data_path = mya_data_path
            self.is_available = True
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to install Myanmar language data: {e}")
            return False


# Singleton instance
_myanmar_ocr_service: Optional[MyanmarOCRService] = None


def get_myanmar_ocr_service() -> MyanmarOCRService:
    """Get singleton Myanmar OCR service"""
    global _myanmar_ocr_service
    if _myanmar_ocr_service is None:
        _myanmar_ocr_service = MyanmarOCRService()
    return _myanmar_ocr_service