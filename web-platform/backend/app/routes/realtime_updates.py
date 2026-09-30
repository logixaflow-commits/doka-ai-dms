"""
API Routes for Real-time Updates using SSE
"""
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import Optional
from loguru import logger

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.database import User
from app.services.realtime_service import get_realtime_service, event_generator

router = APIRouter(prefix="/api/realtime", tags=["Real-time"])


@router.get("/events")
async def realtime_events(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """SSE endpoint for real-time events"""
    return StreamingResponse(
        event_generator(current_user.id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@router.get("/status")
async def realtime_status(
    current_user: User = Depends(get_current_user)
):
    """Get real-time service status"""
    service = get_realtime_service()
    
    return {
        "success": True,
        "active_users": service.get_active_users(),
        "total_connections": service.get_connection_count(),
        "user_connected": current_user.id in service.get_active_users()
    }


@router.post("/test-event")
async def send_test_event(
    event_type: str,
    message: str,
    current_user: User = Depends(get_current_user)
):
    """Send test event (for debugging)"""
    service = get_realtime_service()
    
    await service.system_notification(
        f"Test event from user {current_user.username}: {message}",
        event_type
    )
    
    return {
        "success": True,
        "message": "Test event sent"
    }