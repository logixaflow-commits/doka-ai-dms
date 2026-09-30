"""
Real-time Updates Service using Server-Sent Events (SSE)
Provides real-time document updates, user activity tracking, and collaborative features
"""
import json
import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime
from dataclasses import dataclass, asdict
from loguru import logger
from fastapi import Request
from sse_starlette.sse import EventSourceResponse


@dataclass
class RealtimeEvent:
    """Real-time event data"""
    event_type: str
    data: Dict[str, Any]
    timestamp: datetime
    user_id: Optional[int] = None
    document_id: Optional[int] = None


class RealtimeService:
    """Service for real-time updates using SSE"""
    
    def __init__(self):
        self.active_connections: Dict[int, List[asyncio.Queue]] = {}
        self.event_queue: asyncio.Queue = asyncio.Queue()
        self.is_running = False
        
    async def connect(self, user_id: int) -> asyncio.Queue:
        """Connect user to real-time updates"""
        if user_id not in self.active_connections:
            self.active_connections[user_id] = []
        
        # Create queue for this connection
        queue = asyncio.Queue()
        self.active_connections[user_id].append(queue)
        
        logger.info(f"User {user_id} connected to real-time updates")
        return queue
    
    async def disconnect(self, user_id: int, queue: asyncio.Queue):
        """Disconnect user from real-time updates"""
        if user_id in self.active_connections:
            if queue in self.active_connections[user_id]:
                self.active_connections[user_id].remove(queue)
            
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
        
        logger.info(f"User {user_id} disconnected from real-time updates")
    
    async def broadcast_event(self, event: RealtimeEvent):
        """Broadcast event to all connected users"""
        event_data = {
            "type": event.event_type,
            "data": event.data,
            "timestamp": event.timestamp.isoformat(),
            "user_id": event.user_id,
            "document_id": event.document_id
        }
        
        # Broadcast to all users
        for user_id, queues in self.active_connections.items():
            for queue in queues:
                try:
                    await queue.put(event_data)
                except Exception as e:
                    logger.error(f"Failed to send event to user {user_id}: {e}")
    
    async def send_to_user(self, user_id: int, event: RealtimeEvent):
        """Send event to specific user"""
        if user_id not in self.active_connections:
            return
        
        event_data = {
            "type": event.event_type,
            "data": event.data,
            "timestamp": event.timestamp.isoformat(),
            "user_id": event.user_id,
            "document_id": event.document_id
        }
        
        for queue in self.active_connections[user_id]:
            try:
                await queue.put(event_data)
            except Exception as e:
                logger.error(f"Failed to send event to user {user_id}: {e}")
    
    async def send_to_document_subscribers(self, document_id: int, event: RealtimeEvent):
        """Send event to users subscribed to document"""
        # This would require tracking document subscriptions
        # For now, broadcast to all users
        await self.broadcast_event(event)
    
    async def document_status_update(self, document_id: int, status: str, user_id: int):
        """Send document status update event"""
        event = RealtimeEvent(
            event_type="document_status_update",
            data={
                "document_id": document_id,
                "status": status,
                "updated_by": user_id
            },
            timestamp=datetime.utcnow(),
            user_id=user_id,
            document_id=document_id
        )
        await self.broadcast_event(event)
    
    async def document_created(self, document_id: int, filename: str, user_id: int):
        """Send document created event"""
        event = RealtimeEvent(
            event_type="document_created",
            data={
                "document_id": document_id,
                "filename": filename,
                "created_by": user_id
            },
            timestamp=datetime.utcnow(),
            user_id=user_id,
            document_id=document_id
        )
        await self.broadcast_event(event)
    
    async def document_updated(self, document_id: int, changes: Dict[str, Any], user_id: int):
        """Send document updated event"""
        event = RealtimeEvent(
            event_type="document_updated",
            data={
                "document_id": document_id,
                "changes": changes,
                "updated_by": user_id
            },
            timestamp=datetime.utcnow(),
            user_id=user_id,
            document_id=document_id
        )
        await self.broadcast_event(event)
    
    async def user_activity(self, user_id: int, activity: str, details: Dict[str, Any]):
        """Send user activity event"""
        event = RealtimeEvent(
            event_type="user_activity",
            data={
                "user_id": user_id,
                "activity": activity,
                "details": details
            },
            timestamp=datetime.utcnow(),
            user_id=user_id
        )
        await self.broadcast_event(event)
    
    async def system_notification(self, message: str, level: str = "info"):
        """Send system notification"""
        event = RealtimeEvent(
            event_type="system_notification",
            data={
                "message": message,
                "level": level
            },
            timestamp=datetime.utcnow()
        )
        await self.broadcast_event(event)
    
    async def collaborative_edit(self, document_id: int, user_id: int, edit_data: Dict[str, Any]):
        """Send collaborative edit event"""
        event = RealtimeEvent(
            event_type="collaborative_edit",
            data={
                "document_id": document_id,
                "user_id": user_id,
                "edit": edit_data
            },
            timestamp=datetime.utcnow(),
            user_id=user_id,
            document_id=document_id
        )
        await self.send_to_document_subscribers(document_id, event)
    
    def get_active_users(self) -> List[int]:
        """Get list of active users"""
        return list(self.active_connections.keys())
    
    def get_connection_count(self) -> int:
        """Get total number of active connections"""
        return sum(len(queues) for queues in self.active_connections.values())


# Singleton instance
_realtime_service: Optional[RealtimeService] = None


def get_realtime_service() -> RealtimeService:
    """Get singleton realtime service"""
    global _realtime_service
    if _realtime_service is None:
        _realtime_service = RealtimeService()
    return _realtime_service


async def event_generator(user_id: int):
    """Generate SSE events for a user"""
    service = get_realtime_service()
    queue = await service.connect(user_id)
    
    try:
        while True:
            # Wait for event
            event_data = await queue.get()
            
            # Send event
            yield {
                "event": event_data["type"],
                "data": json.dumps(event_data)
            }
            
    except asyncio.CancelledError:
        await service.disconnect(user_id, queue)
    except Exception as e:
        logger.error(f"Event generator error for user {user_id}: {e}")
        await service.disconnect(user_id, queue)