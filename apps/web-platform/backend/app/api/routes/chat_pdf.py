"""
Chat with PDF — DOKA Document AI Chat (v1).

Uses full-text extraction (PyMuPDF) + LLM for document Q&A.
No pgvector required for v1 — semantic search is a Phase 2 upgrade.

Endpoints:
  POST /api/docs/chat              — ask a question across selected documents
  GET  /api/docs/{doc_id}/extract  — preview extracted text from a document
  GET  /api/docs/chat/status       — feature availability check
"""
from __future__ import annotations

import logging
import os

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db

log = logging.getLogger("doka.chat_pdf")
router = APIRouter(tags=["chat-pdf"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class ChatRequest(BaseModel):
    document_ids: list[int]
    question: str


class ChatResponse(BaseModel):
    answer: str
    sources: list[dict]
    method: str


# ---------------------------------------------------------------------------
# PDF text extraction
# ---------------------------------------------------------------------------

def _extract_pdf_text(file_path: str, max_chars: int = 6000) -> str:
    """Extract plain text from a PDF file using PyMuPDF (fitz)."""
    try:
        import fitz  # PyMuPDF
        doc = fitz.open(file_path)
        text = ""
        for page in doc:
            text += page.get_text()
            if len(text) > max_chars:
                break
        doc.close()
        return text[:max_chars]
    except ImportError:
        log.warning("PyMuPDF not installed — run: pip install pymupdf")
        return ""
    except Exception as exc:
        log.warning(f"PDF extract failed for {file_path}: {exc}")
        return ""


# ---------------------------------------------------------------------------
# LLM call — tries UnifiedAIService, falls back to OpenRouter direct
# ---------------------------------------------------------------------------

def _call_llm_sync(context: str, question: str) -> str:
    system = (
        "You are a document assistant. Answer questions based ONLY on the provided "
        "document context. If the answer is not in the context, say: "
        "'This information is not found in the provided documents.'"
    )
    user = f"Document Context:\n{context}\n\nQuestion: {question}"

    # Attempt 1 — UnifiedAIService
    try:
        from app.services.ai_service import UnifiedAIService  # type: ignore
        import asyncio
        svc = UnifiedAIService()
        loop = asyncio.new_event_loop()
        result = loop.run_until_complete(svc.complete(system, user))
        loop.close()
        if result:
            return result
    except Exception:
        pass

    # Attempt 2 — OpenRouter direct (free tier)
    try:
        import httpx
        api_key = os.getenv("OPENROUTER_API_KEY", "").strip()
        if not api_key:
            return ""
        resp = httpx.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={
                "model": "meta-llama/llama-3.1-8b-instruct:free",
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
            },
            timeout=30.0,
        )
        resp.raise_for_status()
        choices = resp.json().get("choices") or []
        return ((choices[0] if choices else {}).get("message") or {}).get("content", "")
    except Exception as exc:
        log.error(f"OpenRouter fallback failed: {exc}")
        return ""


# ---------------------------------------------------------------------------
# Helper — get document from DB flexibly
# ---------------------------------------------------------------------------

def _get_document(db: Session, doc_id: int):
    """Try known Document models in order."""
    # Primary: DOKA Document in app.models.database
    try:
        from app.models.database import Document  # type: ignore
        return db.query(Document).filter(Document.id == doc_id).first()
    except Exception:
        pass
    # Fallback: brain_soul standalone model (unlikely to have files, but safe)
    return None


def _get_file_path(doc) -> str:
    return (
        getattr(doc, "file_path", None)
        or getattr(doc, "storage_path", None)
        or getattr(doc, "local_path", None)
        or ""
    )


def _get_title(doc) -> str:
    return (
        getattr(doc, "title", None)
        or getattr(doc, "filename", None)
        or getattr(doc, "original_filename", None)
        or getattr(doc, "name", None)
        or f"Document #{doc.id}"
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/api/docs/chat", response_model=ChatResponse)
def chat_with_documents(
    payload: ChatRequest,
    db: Session = Depends(get_db),
):
    """Answer a question based on selected documents via PDF text extraction."""
    if not payload.document_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provide at least one document_id.",
        )
    if not payload.question.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Question cannot be empty.",
        )

    sources: list[dict] = []
    context_parts: list[str] = []

    for doc_id in payload.document_ids[:5]:  # cap at 5 docs to avoid token overflow
        doc = _get_document(db, doc_id)
        if not doc:
            continue

        title = _get_title(doc)
        file_path = _get_file_path(doc)
        text = ""

        if file_path and file_path.lower().endswith(".pdf"):
            text = _extract_pdf_text(file_path)
        elif hasattr(doc, "content") and doc.content:
            text = str(doc.content)[:6000]

        if text:
            context_parts.append(f"=== {title} ===\n{text}")
            sources.append({
                "id": doc_id,
                "title": title,
                "chars_extracted": len(text),
                "method": "pdf-extract" if file_path.lower().endswith(".pdf") else "content-field",
            })

    if not context_parts:
        return ChatResponse(
            answer=(
                "Could not extract text from the selected documents. "
                "Ensure the files are readable PDFs and PyMuPDF is installed."
            ),
            sources=[],
            method="extraction-failed",
        )

    combined_context = "\n\n".join(context_parts)[:8000]
    answer = _call_llm_sync(combined_context, payload.question)

    if not answer:
        answer = "Unable to generate an answer at this time. Please try again later."

    return ChatResponse(
        answer=answer,
        sources=sources,
        method="full-text-extract",
    )


@router.get("/api/docs/{doc_id}/extract")
def extract_document_preview(
    doc_id: int,
    db: Session = Depends(get_db),
):
    """Extract and preview up to 2000 chars of text from a document."""
    doc = _get_document(db, doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")

    file_path = _get_file_path(doc)
    text = _extract_pdf_text(file_path, max_chars=2000) if file_path else ""
    return {
        "doc_id": doc_id,
        "title": _get_title(doc),
        "file_path": file_path,
        "chars_extracted": len(text),
        "preview": text[:500],
    }


@router.get("/api/docs/chat/status")
def chat_status():
    """Return availability status of the Chat-with-PDF feature."""
    try:
        import fitz  # noqa: F401
        pdf_ok = True
    except ImportError:
        pdf_ok = False

    api_key_ok = bool(os.getenv("OPENROUTER_API_KEY", "").strip())

    return {
        "chat_available": pdf_ok and api_key_ok,
        "pdf_extraction": pdf_ok,
        "llm_key_configured": api_key_ok,
        "pgvector_available": False,
        "method": "full-text-extract" if pdf_ok else "unavailable",
        "note": "v1 uses full-text extraction. pgvector semantic search is Phase 2.",
        "install_missing": ([] if pdf_ok else ["pip install pymupdf"]),
    }
