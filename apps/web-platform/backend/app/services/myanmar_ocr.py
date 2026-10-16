"""
Myanmar Language OCR Service
Enhanced OCR support for Myanmar language documents
"""
import os
import subprocess
import unicodedata
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
        Extract text from image with Myanmar language support and bounding boxes
        
        Args:
            image_path: Path to image file
            language: Language code (mya for Myanmar, eng for English, mya+eng for both)
            preprocess: Whether to preprocess image for better OCR
            
        Returns:
            Dictionary with extracted text, bounding boxes, tokens and metadata
        """
        source_image_path = image_path
        if not self.is_available:
            logger.warning("Myanmar OCR not available, falling back to basic OCR")
            return self._fallback_ocr(source_image_path)
        
        skew_angle = 0.0
        try:
            # Preprocess image if requested
            if preprocess:
                prep_result = self._preprocess_image_cv(image_path)
                if prep_result:
                    image_path, skew_angle = prep_result
            
            # 1. Run Tesseract to extract plain text
            cmd_text = [
                self.tesseract_path,
                image_path,
                "stdout",
                "-l", language,
                "--oem", "3",
                "--psm", "6",
                "-c", "preserve_interword_spaces=1"
            ]
            
            res_text = subprocess.run(cmd_text, capture_output=True, text=True, timeout=30)
            
            # 2. Run Tesseract to extract TSV bounding boxes
            cmd_tsv = [
                self.tesseract_path,
                image_path,
                "stdout",
                "-l", language,
                "--oem", "3",
                "--psm", "6",
                "tsv"
            ]
            res_tsv = subprocess.run(cmd_tsv, capture_output=True, text=True, timeout=30)
            boxes = self._parse_tsv_boxes(res_tsv.stdout) if res_tsv.returncode == 0 else []

            if res_text.returncode == 0:
                raw_text = res_text.stdout.strip()
                cleaned_text = self._post_process_myanmar(raw_text)
                tokens = self.tokenize_myanmar(cleaned_text)
                
                return {
                    "success": True,
                    "text": cleaned_text,
                    "language": language,
                    "method": "tesseract_myanmar_cv",
                    "confidence": self._estimate_confidence(cleaned_text),
                    "preprocessed": preprocess,
                    "skew_angle": round(skew_angle, 2),
                    "boxes": boxes,
                    "tokens": tokens
                }
            else:
                logger.error(f"Tesseract failed: {res_text.stderr}")
                return self._fallback_ocr(source_image_path)
                
        except subprocess.TimeoutExpired:
            logger.error("Tesseract timeout")
            return self._fallback_ocr(source_image_path)
        except Exception as e:
            logger.error(f"Myanmar OCR failed: {e}")
            return self._fallback_ocr(source_image_path)
    
    def tokenize_myanmar(self, text: str) -> list:
        """Tokenize Myanmar text into searchable syllables and tokens."""
        if not text:
            return []
        import re
        normalized = text.replace('\u00a0', ' ').replace('\u200b', ' ')
        # Myanmar Syllable Break regex (Unicode U+1000 - U+109F)
        syllable_break = re.compile(r"(?<![်-႟])(?=[က-အဣဤဥဦဧဩဪဿ])")
        segmented = syllable_break.sub(' ', normalized)
        return [tok.strip() for tok in segmented.split() if tok.strip()]

    def _parse_tsv_boxes(self, tsv_data: str) -> list:
        """Parse Tesseract TSV output into bounding boxes for frontend visualization."""
        boxes = []
        if not tsv_data:
            return boxes
        lines = tsv_data.strip().splitlines()
        if len(lines) <= 1:
            return boxes
        
        for line in lines[1:]:
            parts = line.split('\t')
            if len(parts) >= 12:
                try:
                    conf = float(parts[10])
                    word = parts[11].strip()
                    if conf > 0 and word:
                        boxes.append({
                            "text": word,
                            "confidence": conf,
                            "x": int(parts[6]),
                            "y": int(parts[7]),
                            "width": int(parts[8]),
                            "height": int(parts[9]),
                            "line_num": int(parts[4]),
                            "block_num": int(parts[2])
                        })
                except (ValueError, IndexError):
                    continue
        return boxes

    def _preprocess_image_cv(self, image_path: str):
        """Advanced OpenCV preprocessing: Deskew, CLAHE contrast enhancement & Adaptive Thresholding."""
        try:
            import cv2
            import numpy as np
            
            img = cv2.imread(image_path)
            if img is None:
                return self._preprocess_image(image_path), 0.0

            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

            # 1. Deskew detection
            thresh_for_angle = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)[1]
            coords = np.column_stack(np.where(thresh_for_angle > 0))
            angle = 0.0
            if len(coords) > 50:
                rect_angle = cv2.minAreaRect(coords)[-1]
                if rect_angle < -45:
                    angle = -(90 + rect_angle)
                elif rect_angle > 45:
                    angle = 90 - rect_angle
                else:
                    angle = -rect_angle

            # Rotate if skew is between 0.8 and 45 degrees
            rotated_gray = gray
            if abs(angle) > 0.8 and abs(angle) < 45:
                (h, w) = gray.shape[:2]
                center = (w // 2, h // 2)
                M = cv2.getRotationMatrix2D(center, angle, 1.0)
                rotated_gray = cv2.warpAffine(gray, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)

            # 2. Contrast enhancement via CLAHE
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            enhanced = clahe.apply(rotated_gray)

            # 3. Denoising
            denoised = cv2.fastNlMeansDenoising(enhanced, None, 10, 7, 21)

            # 4. Adaptive Gaussian Thresholding
            binary = cv2.adaptiveThreshold(
                denoised, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 15, 8
            )

            processed_path = image_path.replace('.', '_cv_processed.')
            cv2.imwrite(processed_path, binary)
            return processed_path, angle

        except Exception as e:
            logger.warning(f"OpenCV preprocessing error, fallback to PIL: {e}")
            pil_path = self._preprocess_image(image_path)
            return pil_path, 0.0

    def _preprocess_image(self, image_path: str) -> Optional[str]:
        """Fallback PIL preprocessing for better OCR accuracy"""
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
        """Normalize OCR text without deleting potentially meaningful characters."""
        if not text:
            return ""

        # Do not strip characters such as I, l, or 1 globally: they can be valid
        # English text, identifiers, list markers, or Myanmar-document values.
        cleaned = unicodedata.normalize("NFC", text)
        cleaned = cleaned.replace("\x0c", "").replace("\x0b", "")
        lines = [" ".join(line.split()) for line in cleaned.splitlines()]
        return "\n".join(line for line in lines if line)

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