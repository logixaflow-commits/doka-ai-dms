"""
Office DMS - Asynchronous Batch PDF OCR Queue & Progress Tracker
Provides non-blocking, page-by-page OCR execution with live progress reporting.
"""
import asyncio
import os
import time
from typing import Dict, Any, Optional
from pathlib import Path

from app.core.logging import get_logger

logger = get_logger(__name__)

class BatchOCRJob:
    def __init__(self, job_id: str, document_id: int, file_path: str, total_pages: int = 0):
        self.job_id = job_id
        self.document_id = document_id
        self.file_path = file_path
        self.total_pages = total_pages
        self.current_page = 0
        self.status = "queued"  # queued, processing, completed, failed
        self.percent = 0.0
        self.started_at = time.time()
        self.completed_at: Optional[float] = None
        self.error: Optional[str] = None
        self.pages_text: Dict[int, str] = {}

    def to_dict(self) -> Dict[str, Any]:
        elapsed = (self.completed_at or time.time()) - self.started_at
        return {
            "job_id": self.job_id,
            "document_id": self.document_id,
            "status": self.status,
            "total_pages": self.total_pages,
            "current_page": self.current_page,
            "progress_percent": round(self.percent, 1),
            "elapsed_seconds": round(elapsed, 1),
            "completed_pages": len(self.pages_text),
            "error": self.error,
        }

class BatchPDFOCRManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(BatchPDFOCRManager, cls).__new__(cls)
            cls._instance.jobs: Dict[str, BatchOCRJob] = {}
            cls._instance.doc_to_job: Dict[int, str] = {}
        return cls._instance

    def get_job_by_doc(self, doc_id: int) -> Optional[BatchOCRJob]:
        job_id = self.doc_to_job.get(doc_id)
        if job_id and job_id in self.jobs:
            return self.jobs[job_id]
        return None

    def create_job(self, doc_id: int, file_path: str) -> BatchOCRJob:
        import uuid
        job_id = f"ocr_batch_{uuid.uuid4().hex[:10]}"
        job = BatchOCRJob(job_id=job_id, document_id=doc_id, file_path=file_path)
        self.jobs[job_id] = job
        self.doc_to_job[doc_id] = job_id
        return job

    async def run_batch_ocr(self, job_id: str):
        job = self.jobs.get(job_id)
        if not job:
            return

        job.status = "processing"
        job.started_at = time.time()
        logger.info(f"Starting batch PDF OCR job {job_id} for doc {job.document_id}")

        try:
            # 1. Inspect PDF page count using pypdfium2
            import pypdfium2 as pdfium
            pdf = pdfium.PdfDocument(job.file_path)
            job.total_pages = len(pdf)

            if job.total_pages == 0:
                job.status = "completed"
                job.percent = 100.0
                job.completed_at = time.time()
                return

            from app.services.ocr_service import OCRService
            ocr = OCRService()

            # Process each page sequentially with non-blocking cooperative yields
            for page_idx in range(job.total_pages):
                job.current_page = page_idx + 1
                job.percent = (page_idx / job.total_pages) * 100.0

                try:
                    # Render page to PIL image
                    page = pdf[page_idx]
                    bitmap = page.render(scale=2.0)
                    pil_img = bitmap.to_pil()

                    # Convert to bytes for OCRService
                    import io
                    buf = io.BytesIO()
                    pil_img.save(buf, format="PNG")
                    img_bytes = buf.getvalue()

                    # Run OCR in threadpool to avoid event loop blocking
                    res = await asyncio.to_thread(ocr.process_image, img_bytes, "image/png")
                    extracted = res.get("text", "") if isinstance(res, dict) else str(res)
                    job.pages_text[page_idx + 1] = extracted
                except Exception as page_err:
                    logger.warning(f"Batch OCR page {page_idx + 1} warning: {page_err}")
                    job.pages_text[page_idx + 1] = ""

                # Yield control to event loop so other API requests remain instant
                await asyncio.sleep(0.05)

            job.current_page = job.total_pages
            job.percent = 100.0
            job.status = "completed"
            job.completed_at = time.time()
            logger.info(f"Completed batch PDF OCR job {job_id} ({job.total_pages} pages)")

        except Exception as e:
            logger.error(f"Batch OCR job {job_id} failed: {e}")
            job.status = "failed"
            job.error = str(e)
            job.completed_at = time.time()

batch_ocr_manager = BatchPDFOCRManager()
