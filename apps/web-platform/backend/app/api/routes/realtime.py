"""
Office DMS - Real-time Updates with Server-Sent Events (SSE)
Provides real-time dashboard updates for document processing status.
"""
import asyncio
import json
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.core.database import get_db
from app.core.security import get_current_user, require_staff
from app.core.logging import get_logger
from app.models.database import Document

logger = get_logger(__name__)
router = APIRouter()


async def event_generator(db: Session, current_user_id: int):
    """
    SSE event generator that sends updates when document status changes.
    """
    last_pending_count = 0
    last_checked = datetime.utcnow()
    
    while True:
        try:
            # Check for status changes every 2 seconds
            await asyncio.sleep(2)
            
            now = datetime.utcnow()
            
            # Get current pending count
            pending_statuses = ["pending", "processing", "unknown", "completed"]
            current_pending_count = db.query(Document).filter(
                Document.status.in_(pending_statuses)
            ).count()
            
            # Check if count changed
            if current_pending_count != last_pending_count:
                data = {
                    "type": "pending_count_update",
                    "data": {
                        "count": current_pending_count,
                        "previous_count": last_pending_count,
                        "timestamp": now.isoformat()
                    }
                }
                yield f"data: {json.dumps(data)}\n\n"
                last_pending_count = current_pending_count
            
            # Periodically send full stats update every 30 seconds
            if (now - last_checked).seconds >= 30:
                total_docs = db.query(Document).count()
                approved_today = db.query(Document).filter(
                    Document.status == "approved",
                    Document.approved_at >= now.replace(hour=0, minute=0, second=0)
                ).count()
                rejected_today = db.query(Document).filter(
                    Document.status == "rejected",
                    Document.approved_at >= now.replace(hour=0, minute=0, second=0)
                ).count()
                
                stats_data = {
                    "type": "stats_update",
                    "data": {
                        "pending_count": current_pending_count,
                        "total_documents": total_docs,
                        "approved_today": approved_today,
                        "rejected_today": rejected_today,
                        "timestamp": now.isoformat()
                    }
                }
                yield f"data: {json.dumps(stats_data)}\n\n"
                last_checked = now
            
            # Send heartbeat every 10 seconds to keep connection alive
            if (now - last_checked).seconds >= 10:
                yield f"data: {json.dumps({'type': 'heartbeat', 'timestamp': now.isoformat()})}\n\n"
        
        except asyncio.CancelledError:
            logger.info("SSE connection cancelled")
            break
        except Exception as e:
            logger.error(f"SSE generator error: {e}")
            error_data = {
                "type": "error",
                "data": {
                    "message": "Connection error",
                    "timestamp": datetime.utcnow().isoformat()
                }
            }
            yield f"data: {json.dumps(error_data)}\n\n"
            break


@router.get("/events")
async def sse_events(
    request: Request,
    current_user = Depends(require_staff),
    db: Session = Depends(get_db),
):
    """
    SSE endpoint for real-time dashboard updates.
    
    Usage in frontend:
    const eventSource = new EventSource('/api/realtime/events');
    eventSource.onmessage = (event) => {
        const data = JSON.parse(event.data);
        console.log('Real-time update:', data);
    };
    """
    # Check if client accepts SSE
    accept_header = request.headers.get("accept", "")
    if "text/event-stream" not in accept_header:
        return StreamingResponse(
            iter([b"Client must accept text/event-stream"]),
            media_type="text/plain",
            status=406
        )
    
    return StreamingResponse(
        event_generator(db, current_user.id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        }
    )


@router.get("/pending-count")
async def get_pending_count(
    current_user = Depends(require_staff),
    db: Session = Depends(get_db),
):
    """
    Simple endpoint to get current pending count (for polling fallback).
    """
    pending_statuses = ["pending", "processing", "unknown", "completed"]
    count = db.query(Document).filter(Document.status.in_(pending_statuses)).count()
    
    return {
        "count": count,
        "timestamp": datetime.utcnow().isoformat()
    }