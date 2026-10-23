import time

import pytest
from app.models.database import Base, Document, OCRBatchJobRecord
from app.services import pdf_batch_ocr
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool


@pytest.fixture
def persistent_ocr_manager(monkeypatch):
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    test_session = sessionmaker(bind=engine, expire_on_commit=False)
    monkeypatch.setattr(pdf_batch_ocr, "SessionLocal", test_session)

    db = test_session()
    db.add(Document(id=91001, filename="sample.pdf", file_path="/tmp/sample.pdf"))
    db.commit()
    db.close()

    manager = pdf_batch_ocr.BatchPDFOCRManager()
    manager.jobs.clear()
    manager.doc_to_job.clear()
    yield manager, test_session

    manager.jobs.clear()
    manager.doc_to_job.clear()
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


def test_completed_ocr_job_survives_manager_cache_restart(persistent_ocr_manager):
    manager, session_factory = persistent_ocr_manager
    job = manager.create_job(91001, "/tmp/sample.pdf")
    job.status = "completed"
    job.total_pages = 2
    job.current_page = 2
    job.percent = 100.0
    job.pages_text = {1: "invoice", 2: "total 20"}
    job.completed_at = time.time()
    manager._persist_job(job)

    # Simulate a new process: only the database survives.
    manager.jobs.clear()
    manager.doc_to_job.clear()
    restored = manager.get_job_by_doc(91001)

    assert restored is not None
    assert restored.job_id == job.job_id
    assert restored.status == "completed"
    assert restored.percent == 100.0
    assert restored.pages_text == {1: "invoice", 2: "total 20"}

    db = session_factory()
    try:
        record = db.query(OCRBatchJobRecord).filter_by(job_id=job.job_id).one()
        assert record.status == "completed"
        assert record.percent == 100.0
        assert record.pages_text == {"1": "invoice", "2": "total 20"}
    finally:
        db.close()


def test_interrupted_ocr_job_is_marked_failed_after_restart(persistent_ocr_manager):
    manager, session_factory = persistent_ocr_manager
    job = manager.create_job(91001, "/tmp/sample.pdf")
    job.status = "processing"
    job.worker_id = "previous-process"
    job.heartbeat_at = time.time() - pdf_batch_ocr._STALE_WORKER_SECONDS - 1
    job.total_pages = 5
    job.current_page = 2
    job.percent = 40.0
    job.pages_text = {1: "first page", 2: "second page"}
    manager._persist_job(job)

    manager.jobs.clear()
    manager.doc_to_job.clear()
    restored = manager.get_job_by_doc(91001)

    assert restored is not None
    assert restored.status == "failed"
    assert "OCR worker stopped" in restored.error
    assert restored.current_page == 2
    assert restored.pages_text == {1: "first page", 2: "second page"}

    db = session_factory()
    try:
        record = db.query(OCRBatchJobRecord).filter_by(job_id=job.job_id).one()
        assert record.status == "failed"
        assert "OCR worker stopped" in record.error
        assert record.completed_at is not None
    finally:
        db.close()


def test_active_job_owned_by_another_worker_is_not_marked_failed(persistent_ocr_manager):
    manager, _ = persistent_ocr_manager
    job = manager.create_job(91001, "/tmp/sample.pdf")
    job.status = "processing"
    job.worker_id = "another-live-worker"
    job.heartbeat_at = time.time()
    job.current_page = 1
    job.total_pages = 4
    job.percent = 25.0
    manager._persist_job(job)

    manager.jobs.clear()
    manager.doc_to_job.clear()
    observed = manager.get_job_by_doc(91001)

    assert observed is not None
    assert observed.status == "processing"
    assert observed.percent == 25.0
    assert job.job_id not in manager.jobs
