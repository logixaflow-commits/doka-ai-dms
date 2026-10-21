"""Receipt upload boundary.

The vision extraction implementation is intentionally disabled until a real OCR
pipeline is wired in. Never return fabricated invoice totals as verified data.
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from app.core.local_security import require_local_staff

router = APIRouter(prefix="/receipt", tags=["receipt-vision"])

MAX_RECEIPT_UPLOAD_BYTES = 20 * 1024 * 1024
UPLOAD_CHUNK_BYTES = 1024 * 1024
ALLOWED_RECEIPT_MIME_TYPES = {
    "application/pdf",
    "image/jpeg",
    "image/png",
    "image/tiff",
    "image/webp",
}


@router.post("/scan-vision")
async def scan_receipt_image(
    file: UploadFile = File(...),
    language: Optional[str] = Form("bilingual"),
    subject_id: str = Depends(require_local_staff),
):
    """Validate and bound receipt uploads; return 501 until OCR is real.

    Authentication is required because receipts contain sensitive financial data.
    The route deliberately does not synthesize merchant names, dates, or totals.
    """
    del language, subject_id  # Accepted for API compatibility; extraction is not enabled.
    try:
        mime_type = (file.content_type or "").split(";", 1)[0].strip().lower()
        if mime_type not in ALLOWED_RECEIPT_MIME_TYPES:
            raise HTTPException(status_code=415, detail="Only PDF or supported image uploads are accepted.")

        if file.size is not None and file.size > MAX_RECEIPT_UPLOAD_BYTES:
            raise HTTPException(status_code=413, detail="Receipt upload exceeds the 20 MiB limit.")

        # Do not trust Content-Length or UploadFile.size alone. Count actual bytes
        # in bounded chunks so an unknown/misreported size cannot bypass the cap.
        total = 0
        while True:
            chunk = await file.read(min(UPLOAD_CHUNK_BYTES, MAX_RECEIPT_UPLOAD_BYTES - total + 1))
            if not chunk:
                break
            total += len(chunk)
            if total > MAX_RECEIPT_UPLOAD_BYTES:
                raise HTTPException(status_code=413, detail="Receipt upload exceeds the 20 MiB limit.")

        raise HTTPException(
            status_code=501,
            detail="Receipt extraction is not configured. No receipt data was processed or verified.",
        )
    finally:
        await file.close()
