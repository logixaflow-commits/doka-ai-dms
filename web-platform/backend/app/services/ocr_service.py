"""
Office DMS - OCR Service
Tesseract-based OCR with Myanmar language support, image preprocessing,
and PDF handling via pdf2image.
"""
import io
import re
from pathlib import Path
from typing import Optional, Tuple

import cv2
import numpy as np
from PIL import Image
import pytesseract
import pdfplumber
from pdf2image import convert_from_path

from app.core.config import settings
from app.core.logging import get_logger
from app.core.exceptions import OCRError, OCRLanguageNotSupported, OCRPreprocessingError

logger = get_logger(__name__)


class OCRService:
    """
    OCR processing service with support for:
    - Multiple image formats (PNG, JPG, TIFF, BMP)
    - PDF documents (via pdf2image)
    - Myanmar language (Tesseract mya)
    - English language
    - Mixed Myanmar-English documents
    - Image preprocessing (deskew, denoise, contrast enhancement)
    """

    # Supported MIME types
    SUPPORTED_IMAGE_TYPES = {
        "image/png", "image/jpeg", "image/jpg", "image/tiff", "image/bmp", "image/webp"
    }
    SUPPORTED_PDF_TYPES = {"application/pdf"}
    # Bound CPU and memory use when processing untrusted or unexpectedly large PDFs.
    MAX_PDF_PAGES = 200
    MAX_IMAGE_PIXELS = 50_000_000

    def __init__(self):
        self.config = settings.ocr
        self.tesseract_cmd = self.config.tesseract_cmd
        self.myanmar_lang = self.config.myanmar_lang
        self.eng_lang = self.config.eng_lang
        self.dpi = self.config.dpi
        self.preprocessing = self.config.preprocessing
        self.oem = self.config.oem
        self.psm = self.config.psm
        self.fallback_enabled = getattr(self.config, 'fallback_enabled', True)
        self.timeout = getattr(self.config, 'timeout', 30)

        # Configure tesseract path if provided
        if self.tesseract_cmd != "tesseract":
            pytesseract.pytesseract.tesseract_cmd = self.tesseract_cmd

        # Build language string (e.g., "eng+mya")
        self.languages = [self.eng_lang]
        if self.myanmar_lang:
            self.languages.append(self.myanmar_lang)
        self.lang_string = "+".join(self.languages)

        # Check for alternative OCR engines
        self.paddleocr_available = self._check_paddleocr()
        self.easyocr_available = self._check_easyocr()

        logger.info(f"OCR Service initialized: lang={self.lang_string}, dpi={self.dpi}, preprocessing={self.preprocessing}")
        logger.info(f"OCR Fallback enabled: {self.fallback_enabled}")
        logger.info(f"PaddleOCR available: {self.paddleocr_available}")
        logger.info(f"EasyOCR available: {self.easyocr_available}")

    def _check_paddleocr(self) -> bool:
        """Check if PaddleOCR is available."""
        try:
            from paddleocr import PaddleOCR
            return True
        except ImportError:
            return False

    def _check_easyocr(self) -> bool:
        """Check if EasyOCR is available."""
        try:
            import easyocr
            return True
        except ImportError:
            return False

    def _fallback_paddleocr(self, image_path: Path) -> str:
        """Fallback to PaddleOCR if Tesseract fails."""
        try:
            from paddleocr import PaddleOCR
            
            ocr = PaddleOCR(use_angle_cls=True, lang='en')
            result = ocr.ocr(str(image_path), cls=True)
            
            if not result or not result[0]:
                return ""
            
            # Extract text from PaddleOCR results
            text_lines = []
            for line in result[0]:
                if line[1][0]:
                    text_lines.append(line[1][0])
            
            return " ".join(text_lines)
            
        except Exception as e:
            logger.warning(f"PaddleOCR fallback failed: {e}")
            return ""

    def _fallback_easyocr(self, image_path: Path) -> str:
        """Fallback to EasyOCR if Tesseract fails."""
        try:
            import easyocr
            
            reader = easyocr.Reader(['en', 'my'], gpu=False)
            result = reader.readtext(str(image_path), detail=0)
            
            return " ".join(result)
            
        except Exception as e:
            logger.warning(f"EasyOCR fallback failed: {e}")
            return ""

    def process_file(self, file_path: str, mime_type: str) -> Tuple[str, Optional[str]]:
        """
        Process a file and extract text via OCR.

        Args:
            file_path: Path to the file
            mime_type: MIME type of the file

        Returns:
            Tuple of (extracted_text, detected_language)
        """
        path = Path(file_path)
        if not path.exists():
            raise OCRError(f"File not found: {file_path}")

        logger.info(f"OCR processing: {path.name} (type: {mime_type})")

        try:
            if mime_type in self.SUPPORTED_IMAGE_TYPES:
                text = self._process_image(path)
            elif mime_type in self.SUPPORTED_PDF_TYPES:
                text = self._process_pdf(path)
            else:
                # Try pdfplumber for documents that might be PDF-like
                try:
                    text = self._process_pdf(path)
                except Exception:
                    raise OCRError(f"Unsupported file type for OCR: {mime_type}")

            detected_lang = self._detect_language(text)
            logger.info(f"OCR complete: {len(text)} chars extracted, language: {detected_lang}")
            return text, detected_lang

        except OCRError:
            raise
        except Exception as e:
            logger.error(f"OCR processing failed for {path.name}: {e}")
            raise OCRError(f"OCR processing failed: {e}") from e

    def _process_image(self, image_path: Path) -> str:
        """Process a single image file with fallback mechanism."""
        last_error = None

        # Inspect dimensions from the image header before OpenCV decodes pixel data.
        try:
            with Image.open(str(image_path)) as image_header:
                width, height = image_header.size
            if width <= 0 or height <= 0 or width * height > self.MAX_IMAGE_PIXELS:
                raise OCRError(
                    f"Image dimensions exceed the OCR limit of {self.MAX_IMAGE_PIXELS:,} pixels."
                )
        except OCRError:
            raise
        except Exception as exc:
            raise OCRError(f"Unable to inspect image dimensions: {exc}") from exc

        # Try Tesseract first
        try:
            # Load image
            image = cv2.imread(str(image_path))
            if image is None:
                # Try PIL fallback without keeping the source file handle open.
                with Image.open(str(image_path)) as source_image:
                    rgb_image = np.array(source_image.convert("RGB"))
                image = cv2.cvtColor(rgb_image, cv2.COLOR_RGB2BGR)

            if self.preprocessing:
                image = self._preprocess_image(image)

            # Convert to PIL for pytesseract
            pil_image = Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))

            # Run OCR
            custom_config = f"--oem {self.oem} --psm {self.psm}"
            text = pytesseract.image_to_string(
                pil_image,
                lang=self.lang_string,
                config=custom_config,
                timeout=self.timeout,
            )

            cleaned_text = self._clean_text(text)
            
            # Check if we got meaningful text
            if cleaned_text and len(cleaned_text.strip()) > 10:
                logger.info(f"✓ Tesseract OCR successful: {len(cleaned_text)} chars")
                return cleaned_text
            else:
                logger.warning("Tesseract returned insufficient text, trying fallback")
                last_error = "Insufficient text from Tesseract"
                
        except Exception as e:
            last_error = str(e)
            logger.warning(f"Tesseract OCR failed: {e}")
        
        # Try PaddleOCR fallback
        if self.fallback_enabled and self.paddleocr_available:
            try:
                logger.info("Attempting PaddleOCR fallback...")
                text = self._fallback_paddleocr(image_path)
                cleaned_text = self._clean_text(text)
                
                if cleaned_text and len(cleaned_text.strip()) > 10:
                    logger.info(f"✓ PaddleOCR fallback successful: {len(cleaned_text)} chars")
                    return cleaned_text
                else:
                    logger.warning("PaddleOCR returned insufficient text")
                    
            except Exception as e:
                logger.warning(f"PaddleOCR fallback failed: {e}")
        
        # Try EasyOCR fallback
        if self.fallback_enabled and self.easyocr_available:
            try:
                logger.info("Attempting EasyOCR fallback...")
                text = self._fallback_easyocr(image_path)
                cleaned_text = self._clean_text(text)
                
                if cleaned_text and len(cleaned_text.strip()) > 10:
                    logger.info(f"✓ EasyOCR fallback successful: {len(cleaned_text)} chars")
                    return cleaned_text
                else:
                    logger.warning("EasyOCR returned insufficient text")
                    
            except Exception as e:
                logger.warning(f"EasyOCR fallback failed: {e}")
        
        # All OCR engines failed
        error_msg = f"All OCR engines failed for {image_path.name}"
        if last_error:
            error_msg += f": {last_error}"
        logger.error(error_msg)
        raise OCRError(error_msg)

    def _process_pdf(self, pdf_path: Path) -> str:
        """Process a bounded PDF one page at a time to cap peak memory use."""
        all_text = []
        try:
            with pdfplumber.open(str(pdf_path)) as pdf:
                page_count = len(pdf.pages)
            if page_count > self.MAX_PDF_PAGES:
                raise OCRError(
                    f"PDF has {page_count} pages; the OCR limit is {self.MAX_PDF_PAGES} pages."
                )

            # Prefer direct text extraction for text-based PDFs.
            text = self._extract_pdf_text(pdf_path)
            if text and len(text.strip()) > 100:
                logger.info(f"Extracted {len(text)} chars via pdfplumber (text-based PDF)")
                return text

            # Scanned PDFs are rendered one page at a time; never retain the full
            # document as a list of page images in memory.
            for page_number in range(1, page_count + 1):
                images = convert_from_path(
                    str(pdf_path),
                    dpi=self.dpi,
                    fmt="png",
                    first_page=page_number,
                    last_page=page_number,
                    thread_count=1,
                    timeout=self.timeout,
                    size=3500,
                )
                if not images:
                    continue
                image = images[0]
                try:
                    cv_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
                    if self.preprocessing:
                        cv_image = self._preprocess_image(cv_image)
                    pil_image = Image.fromarray(cv2.cvtColor(cv_image, cv2.COLOR_BGR2RGB))
                    custom_config = f"--oem {self.oem} --psm {self.psm}"
                    page_text = pytesseract.image_to_string(
                        pil_image,
                        lang=self.lang_string,
                        config=custom_config,
                        timeout=self.timeout,
                    )
                    if page_text.strip():
                        all_text.append(f"--- Page {page_number} ---\\n{page_text}")
                finally:
                    image.close()

            combined_text = "\\n\\n".join(all_text)
            logger.info(f"OCR extracted {len(combined_text)} chars from {page_count} PDF pages")
            return self._clean_text(combined_text)
        except OCRError:
            raise
        except Exception as e:
            logger.error(f"PDF OCR failed for {pdf_path}: {e}")
            raise OCRError(f"PDF OCR failed: {e}") from e

    def _extract_pdf_text(self, pdf_path: Path) -> str:
        """Extract text directly from text-based PDF using pdfplumber."""
        text_parts = []
        try:
            with pdfplumber.open(str(pdf_path)) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text_parts.append(page_text)
            return "\n\n".join(text_parts)
        except Exception as e:
            logger.debug(f"pdfplumber extraction failed: {e}")
            return ""

    def _preprocess_image(self, image: np.ndarray) -> np.ndarray:
        """
        Preprocess image for better OCR accuracy.
        Steps: grayscale -> denoise -> deskew -> contrast enhancement -> thresholding
        """
        try:
            # Convert to grayscale
            if len(image.shape) == 3:
                gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            else:
                gray = image.copy()

            # Denoise
            denoised = cv2.fastNlMeansDenoising(gray, None, 10, 7, 21)

            # Deskew
            deskewed = self._deskew(denoised)

            # Contrast enhancement (CLAHE)
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            enhanced = clahe.apply(deskewed)

            # Adaptive thresholding for binarization
            binary = cv2.adaptiveThreshold(
                enhanced, 255,
                cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                cv2.THRESH_BINARY, 11, 2
            )

            # Dilate slightly to connect broken characters (especially for Myanmar)
            kernel = np.ones((1, 1), np.uint8)
            processed = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)

            return cv2.cvtColor(processed, cv2.COLOR_GRAY2BGR)

        except Exception as e:
            logger.warning(f"Image preprocessing failed: {e}. Using original image.")
            raise OCRPreprocessingError(f"Preprocessing failed: {e}") from e

    def _deskew(self, image: np.ndarray) -> np.ndarray:
        """Deskew an image using projection profile."""
        try:
            # Detect skew angle
            coords = np.column_stack(np.where(image > 0))
            if len(coords) < 100:
                return image

            angle = cv2.minAreaRect(coords)[-1]
            if angle < -45:
                angle = -(90 + angle)
            else:
                angle = -angle

            if abs(angle) < 0.5:
                return image

            # Rotate
            (h, w) = image.shape[:2]
            center = (w // 2, h // 2)
            M = cv2.getRotationMatrix2D(center, angle, 1.0)
            rotated = cv2.warpAffine(image, M, (w, h),
                                     flags=cv2.INTER_CUBIC,
                                     borderMode=cv2.BORDER_REPLICATE)
            return rotated

        except Exception:
            return image

    def _detect_language(self, text: str) -> Optional[str]:
        """Detect if text contains Myanmar script."""
        if not text:
            return None

        # Myanmar Unicode range: U+1000 to U+109F
        myanmar_chars = len(re.findall(r'[\u1000-\u109F]', text))
        total_chars = len(text.strip())

        if total_chars == 0:
            return "eng"

        myanmar_ratio = myanmar_chars / total_chars

        if myanmar_ratio > 0.3:
            return "mya+eng" if myanmar_ratio < 0.8 else "mya"
        return "eng"

    def _clean_text(self, text: str) -> str:
        """Clean OCR output: normalize whitespace, fix common OCR errors."""
        if not text:
            return ""

        # Normalize line endings
        text = text.replace("\r\n", "\n").replace("\r", "\n")

        # Remove excessive whitespace
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n{3,}", "\n\n", text)

        # Remove standalone noise characters
        lines = [line.strip() for line in text.split("\n") if len(line.strip()) > 1]
        return "\n".join(lines)

    def get_tesseract_info(self) -> dict:
        """Get Tesseract version and available languages."""
        try:
            version = pytesseract.get_tesseract_version()
            languages = pytesseract.get_languages()
            return {
                "version": str(version),
                "available_languages": languages,
                "myanmar_supported": self.myanmar_lang in languages,
                "configured_languages": self.languages,
            }
        except Exception as e:
            return {"error": str(e)}


# Singleton
ocr_service = OCRService()
