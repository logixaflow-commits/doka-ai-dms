"""
Office DMS - Asynchronous Batch PDF OCR Queue & Progress Tracker.
Job state is persisted in the application database so restarts are observable.
"""
import asyncio
import os
import time
import uuid
from typing import Any

from app.core.database import SessionLocal
from app.core.logging import get_logger
from app.models.database import OCRBatchJobRecord

logger = get_logger(__name__)
_WORKER_ID = f"{os.getpid()}:{uuid.uuid4().hex}"
_STALE_WORKER_SECONDS = 300


class BatchOCRJob:
    def __init__(
        self,
        job_id: str,
        document_id: int,
        file_path: str,
        total_pages: int = 0,
        current_page: int = 0,
        status: str = "queued",
        percent: float = 0.0,
        worker_id: str | None = None,
        heartbeat_at: float | None = None,
        started_at: float | None = None,
        completed_at: float | None = None,
        error: str | None = None,
        pages_text: dict[int, str] | None = None,
    ):
        self.job_id = job_id
        self.document_id = document_id
        self.file_path = file_path
        self.total_pages = total_pages
        self.current_page = current_page
        self.status = status
        self.percent = percent
        self.worker_id = worker_id
        self.heartbeat_at = heartbeat_at
        self.started_at = started_at if started_at is not None else time.time()
        self.completed_at = completed_at
        self.error = error
        self.pages_text = pages_text or {}

    def to_dict(self) -> dict[str, Any]:
        elapsed = (self.completed_at or time.time()) - self.started_at
        return {
            "job_id": self.job_id,
            "document_id": self.document_id,
            "status": self.status,
            "total_pages": self.total_pages,
            "current_page": self.current_page,
            "progress_percent": round(self.percent, 1),
            "elapsed_seconds": round(max(0.0, elapsed), 1),
            "completed_pages": len(self.pages_text),
            "error": self.error,
        }


class BatchPDFOCRManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.jobs = {}
            cls._instance.doc_to_job = {}
        return cls._instance

    @staticmethod
    def _from_record(record: OCRBatchJobRecord) -> BatchOCRJob:
        raw_pages = record.pages_text or {}
        pages = {}
        for key, value in raw_pages.items():
            try:
                pages[int(key)] = str(value)
            except (TypeError, ValueError):
                continue
        return BatchOCRJob(
            job_id=record.job_id,
            document_id=record.document_id,
            file_path=record.file_path,
            total_pages=record.total_pages,
            current_page=record.current_page,
            status=record.status,
            percent=record.percent,
            worker_id=record.worker_id,
            heartbeat_at=record.heartbeat_at,
            started_at=record.started_at,
            completed_at=record.completed_at,
            error=record.error,
            pages_text=pages,
        )

    def _persist_job(self, job: BatchOCRJob) -> None:
        db = SessionLocal()
        try:
            record = db.query(OCRBatchJobRecord).filter(
                OCRBatchJobRecord.job_id == job.job_id
            ).first()
            if record is None:
                record = OCRBatchJobRecord(
                    job_id=job.job_id,
                    document_id=job.document_id,
                    file_path=job.file_path,
                    started_at=job.started_at,
                )
                db.add(record)
            record.document_id = job.document_id
            record.file_path = job.file_path
            record.status = job.status
            record.total_pages = job.total_pages
            record.current_page = job.current_page
            record.percent = job.percent
            record.worker_id = job.worker_id
            record.heartbeat_at = job.heartbeat_at
            record.started_at = job.started_at
            record.completed_at = job.completed_at
            record.error = job.error
            record.pages_text = {str(key): value for key, value in job.pages_text.items()}
            db.commit()
        except Exception:
            db.rollback()
            logger.exception(f"Failed to persist batch OCR job {job.job_id}")
            raise
        finally:
            db.close()

    def get_job_by_doc(self, doc_id: int) -> BatchOCRJob | None:
        cached_job_id = self.doc_to_job.get(doc_id)
        cached_job = self.jobs.get(cached_job_id) if cached_job_id else None

        db = SessionLocal()
        try:
            record = (
                db.query(OCRBatchJobRecord)
                .filter(OCRBatchJobRecord.document_id == doc_id)
                .order_by(OCRBatchJobRecord.created_at.desc(), OCRBatchJobRecord.job_id.desc())
                .first()
            )
            if record is None:
                return None
            if (
                cached_job is not None
                and cached_job.job_id == record.job_id
                and cached_job.worker_id == _WORKER_ID
            ):
                return cached_job
            job = self._from_record(record)
            if job.status in ("queued", "processing"):
                now = time.time()
                stale = (
                    job.heartbeat_at is None
                    or now - job.heartbeat_at > _STALE_WORKER_SECONDS
                )
                lost_local_task = job.worker_id == _WORKER_ID and job.job_id not in self.jobs
                if stale or lost_local_task:
                    job.status = "failed"
                    job.error = "OCR worker stopped before completion; please retry the job."
                    job.completed_at = now
                    job.heartbeat_at = now
                    record.status = job.status
                    record.error = job.error
                    record.completed_at = job.completed_at
                    record.heartbeat_at = job.heartbeat_at
                    db.commit()
                elif job.worker_id != _WORKER_ID:
                    # Another worker owns this active job. Return its persisted
                    # progress without caching a stale copy in this process.
                    return job
            self.jobs[job.job_id] = job
            self.doc_to_job[doc_id] = job.job_id
            return job
        except Exception:
            db.rollback()
            logger.exception(f"Failed to load persisted batch OCR job for document {doc_id}")
            raise
        finally:
            db.close()

    def create_job(self, doc_id: int, file_path: str) -> BatchOCRJob:
        import uuid

        job_id = f"ocr_batch_{uuid.uuid4().hex[:10]}"
        now = time.time()
        job = BatchOCRJob(
            job_id=job_id, document_id=doc_id, file_path=file_path,
            worker_id=_WORKER_ID, heartbeat_at=now,
        )
        # Persist before returning or scheduling the background task. If the
        # database is unavailable, fail the request instead of losing the job.
        self._persist_job(job)
        self.jobs[job_id] = job
        self.doc_to_job[doc_id] = job_id
        return job

    async def run_batch_ocr(self, job_id: str):
        job = self.jobs.get(job_id)
        if not job:
            db = SessionLocal()
            try:
                record = db.query(OCRBatchJobRecord).filter(
                    OCRBatchJobRecord.job_id == job_id
                ).first()
                if record is None:
                    return
                job = self._from_record(record)
                self.jobs[job_id] = job
                self.doc_to_job[job.document_id] = job_id
            finally:
                db.close()

        job.status = "processing"
        job.worker_id = _WORKER_ID
        job.started_at = time.time()
        job.heartbeat_at = job.started_at
        self._persist_job(job)
        logger.info(f"Starting batch PDF OCR job {job_id} for document {job.document_id}")
        pdf = None

        try:
            import pypdfium2 as pdfium

            pdf = pdfium.PdfDocument(job.file_path)
            job.total_pages = len(pdf)
            self._persist_job(job)

            if job.total_pages == 0:
                job.status = "completed"
                job.percent = 100.0
                job.completed_at = time.time()
                job.heartbeat_at = job.completed_at
                self._persist_job(job)
                return

            from app.services.ocr_service import OCRService
            ocr = OCRService()

            for page_idx in range(job.total_pages):
                job.current_page = page_idx + 1
                try:
                    page = pdf[page_idx]
                    bitmap = page.render(scale=2.0)
                    pil_img = bitmap.to_pil()
                    import io
                    buf = io.BytesIO()
                    pil_img.save(buf, format="PNG")
                    img_bytes = buf.getvalue()
                    res = await asyncio.to_thread(ocr.process_image, img_bytes, "image/png")
                    extracted = res.get("text", "") if isinstance(res, dict) else str(res)
                    job.pages_text[page_idx + 1] = extracted
                except Exception as page_err:  # noqa: BLE001 - one page failure must not abort the batch
                    logger.warning(f"Batch OCR page {page_idx + 1} warning: {page_err}")
                    job.pages_text[page_idx + 1] = ""

                job.percent = (job.current_page / job.total_pages) * 100.0
                job.heartbeat_at = time.time()
                self._persist_job(job)
                await asyncio.sleep(0.05)

            job.status = "completed"
            job.percent = 100.0
            job.completed_at = time.time()
            job.heartbeat_at = job.completed_at
            self._persist_job(job)
            logger.info(f"Completed batch PDF OCR job {job_id} ({job.total_pages} pages)")

        except Exception:
            logger.exception(f"Batch OCR job {job_id} failed")
            job.status = "failed"
            job.error = "OCR processing failed; check server logs and retry."
            job.completed_at = time.time()
            job.heartbeat_at = job.completed_at
            try:
                self._persist_job(job)
            except Exception:
                logger.exception(f"Failed to persist terminal failure for OCR job {job_id}")
        finally:
            if pdf is not None:
                try:
                    pdf.close()
                except Exception:
                    logger.debug(f"Unable to close PDF handle for OCR job {job_id}", exc_info=True)


batch_ocr_manager = BatchPDFOCRManager()
