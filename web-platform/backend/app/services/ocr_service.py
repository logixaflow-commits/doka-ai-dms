"""
Office DMS - OCR Service
Tesseract-based OCR with Myanmar language support, image preprocessing,
and PDF handling via pdf2image.
"""
import io
import re
import tempfile
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
        self.max_file_bytes = self.config.max_file_bytes
        self.max_pdf_pages = self.config.max_pdf_pages
        self.max_image_pixels = self.config.max_image_pixels

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

    def process_file(
        self,
        file_path: str,
        mime_type: str,
        *,
        language: Optional[str] = None,
    ) -> Tuple[str, Optional[str]]:
        """
        Process a file and extract text via OCR.

        Args:
            file_path: Path to the file
            mime_type: MIME type of the file
            language: Optional configured Tesseract language override for this run.

        Returns:
            Tuple of (extracted_text, detected_language)
        """
        path = Path(file_path)
        if not path.exists():
            raise OCRError("OCR input file does not exist.")
        if path.is_symlink():
            raise OCRError("OCR does not accept symbolic-link inputs.")
        if not isinstance(mime_type, str) or mime_type not in (self.SUPPORTED_IMAGE_TYPES | self.SUPPORTED_PDF_TYPES):
            raise OCRError(f"Unsupported file type for OCR: {mime_type}")
        try:
            file_size = path.stat().st_size
        except OSError as exc:
            raise OCRError("Unable to inspect OCR input size.") from exc
        if file_size < 1:
            raise OCRError("OCR input file is empty.")
        max_file_bytes = getattr(self, "max_file_bytes", 50 * 1024 * 1024)
        if file_size > max_file_bytes:
            raise OCRError(f"OCR input exceeds the configured limit of {max_file_bytes:,} bytes.")

        selected_language = self.lang_string
        if language is not None:
            language_parts = [part.strip() for part in language.split("+")]
            if (
                not language_parts
                or any(not part or part not in self.languages for part in language_parts)
                or len(set(language_parts)) != len(language_parts)
            ):
                raise OCRError("Requested OCR language is not configured.")
            selected_language = "+".join(language_parts)

        logger.info(f"OCR processing: {path.name} (type: {mime_type}, bytes: {file_size})")

        try:
            if mime_type in self.SUPPORTED_IMAGE_TYPES:
                text = self._process_image(path, selected_language)
            else:
                with path.open("rb") as source:
                    header = source.read(5)
                if header != b"%PDF-":
                    raise OCRError("PDF input does not have a valid PDF header.")
                text = self._process_pdf(path, selected_language)

            detected_lang = self._detect_language(text)
            logger.info(f"OCR complete: {len(text)} chars extracted, language: {detected_lang}")
            return text, detected_lang

        except OCRError:
            raise
        except Exception as e:
            logger.error(f"OCR processing failed for {path.name}: {e}")
            raise OCRError(f"OCR processing failed: {e}") from e

    def _process_image(self, image_path: Path, language: Optional[str] = None) -> str:
        """Process a single image file with fallback mechanism."""
        last_error = None

        # Inspect dimensions from the image header before OpenCV decodes pixel data.
        try:
            with Image.open(str(image_path)) as image_header:
                width, height = image_header.size
            max_image_pixels = getattr(self, "max_image_pixels", self.MAX_IMAGE_PIXELS)
            if width <= 0 or height <= 0 or width * height > max_image_pixels:
                raise OCRError(
                    f"Image dimensions exceed the OCR limit of {max_image_pixels:,} pixels."
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

            text = self._recognize_image(image, language or self.lang_string)

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

    def _process_pdf(self, pdf_path: Path, language: Optional[str] = None) -> str:
        """Process a bounded PDF one page at a time to cap peak memory use."""
        all_text = []
        try:
            with pdfplumber.open(str(pdf_path)) as pdf:
                page_count = len(pdf.pages)
            max_pdf_pages = getattr(self, "max_pdf_pages", self.MAX_PDF_PAGES)
            if page_count > max_pdf_pages:
                raise OCRError(
                    f"PDF has {page_count} pages; the OCR limit is {max_pdf_pages} pages."
                )

            # Prefer direct text extraction for text-based PDFs.
            text = self._extract_pdf_text(pdf_path)
            if text and len(text.strip()) > 100:
                logger.info(f"Extracted {len(text)} chars via pdfplumber (text-based PDF)")
                return text

            # Scanned PDFs are rendered one page at a time; never retain the full
            # document as a list of page images in memory.
            poppler_path = getattr(getattr(self, "config", settings.ocr), "poppler_path", "")
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
                    **({"poppler_path": poppler_path} if poppler_path else {}),
                )
                if not images:
                    continue
                image = images[0]
                try:
                    cv_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
                    selected_language = language or self.lang_string
                    page_text = self._recognize_image(cv_image, selected_language)
                    if self.preprocessing and not self._clean_text(page_text).strip():
                        logger.info(
                            "PDF page {} produced no text after preprocessing; retrying without preprocessing.",
                            page_number,
                        )
                        unprocessed_text = self._recognize_image(
                            cv_image,
                            selected_language,
                            preprocess=False,
                        )
                        if self._clean_text(unprocessed_text).strip():
                            page_text = unprocessed_text
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

    def _layout_ocr_settings(self, image: np.ndarray) -> tuple[int, int]:
        """Use block segmentation for wide crops and sparse-text mode for pages."""
        height, width = image.shape[:2]
        if width / height >= 2:
            return 6, 5
        return self.psm, 10

    def _recognize_image(
        self,
        image: np.ndarray,
        language: str,
        *,
        preprocess: Optional[bool] = None,
    ) -> str:
        """Recognize an image, using line segmentation for Myanmar page layouts."""
        psm, threshold_constant = self._layout_ocr_settings(image)
        should_preprocess = self.preprocessing if preprocess is None else preprocess
        if should_preprocess:
            image = self._preprocess_image(image, threshold_constant=threshold_constant)

        if self._uses_line_recognition(image, language):
            lines = self._text_line_images(image)
            if 2 <= len(lines) <= 80:
                return self._recognize_text_lines(lines, language)

        pil_image = Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
        return pytesseract.image_to_string(
            pil_image,
            lang=language,
            config=f"--oem {self.oem} --psm {psm}",
            timeout=self.timeout,
        )

    @staticmethod
    def _uses_line_recognition(image: np.ndarray, language: str) -> bool:
        languages = {part.strip().lower() for part in language.split("+")}
        height, width = image.shape[:2]
        return "mya" in languages and width / height < 2

    def _text_line_images(self, image: np.ndarray) -> list[Image.Image]:
        """Segment horizontal text rows for single-line Tesseract recognition."""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
        ink = gray < 200
        active_rows = ink.mean(axis=1) > 0.001
        row_bands: list[tuple[int, int]] = []
        start = None
        for row, active in enumerate(active_rows):
            if active and start is None:
                start = row
            elif not active and start is not None:
                row_bands.append((start, row))
                start = None
        if start is not None:
            row_bands.append((start, len(active_rows)))

        merged_bands: list[tuple[int, int]] = []
        for start, end in row_bands:
            if merged_bands and start - merged_bands[-1][1] <= 12:
                merged_bands[-1] = (merged_bands[-1][0], end)
            else:
                merged_bands.append((start, end))

        line_images = []
        for start, end in merged_bands:
            top = max(0, start - 8)
            bottom = min(gray.shape[0], end + 8)
            line = gray[top:bottom]
            active_columns = np.flatnonzero((line < 200).any(axis=0))
            if not active_columns.size:
                continue
            left = max(0, int(active_columns[0]) - 20)
            right = min(gray.shape[1], int(active_columns[-1]) + 21)
            crop = gray[top:bottom, left:right]
            # Tesseract's line segmentation is sensitive to small glyph height,
            # especially Myanmar stacked marks. Normalize small line crops to a
            # minimum glyph canvas height before PSM 7 recognition; never shrink
            # an already large crop or alter the source image on disk.
            target_height = 48
            if crop.shape[0] < target_height:
                scale = target_height / crop.shape[0]
                target_width = max(1, int(round(crop.shape[1] * scale)))
                crop = cv2.resize(
                    crop,
                    (target_width, target_height),
                    interpolation=cv2.INTER_CUBIC,
                )
            line_images.append(Image.fromarray(crop).convert("RGB"))
        return line_images

    def _recognize_text_lines(self, lines: list[Image.Image], language: str) -> str:
        """Pass all detected rows to one local Tesseract process."""
        with tempfile.TemporaryDirectory(prefix="doka-ocr-lines-") as temp_dir:
            image_path = Path(temp_dir) / "text-lines.tiff"
            lines[0].save(
                image_path,
                format="TIFF",
                save_all=True,
                append_images=lines[1:],
                compression="tiff_deflate",
            )
            return pytesseract.image_to_string(
                str(image_path),
                lang=language,
                config=f"--oem {self.oem} --psm 7",
                timeout=self.timeout,
            )

    def _preprocess_image(self, image: np.ndarray, *, threshold_constant: int = 10) -> np.ndarray:
        """
        Apply adaptive thresholding while preserving the source image dimensions.
        """
        try:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image.copy()
            binary = cv2.adaptiveThreshold(
                gray, 255,
                cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                cv2.THRESH_BINARY, 41, threshold_constant
            )
            return cv2.cvtColor(binary, cv2.COLOR_GRAY2BGR)

        except Exception as e:
            logger.warning(f"Image preprocessing failed: {e}.")
            raise OCRPreprocessingError(f"Preprocessing failed: {e}") from e

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
