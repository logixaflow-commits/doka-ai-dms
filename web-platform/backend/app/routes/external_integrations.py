"""
API Routes for External System Integrations
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional, List
from loguru import logger

from app.core.database import get_db
from app.core.security import require_admin
from app.models.database import User
from app.services.external_integrations import (
    get_integration_service,
    IntegrationType,
    IntegrationStatus
)

router = APIRouter(prefix="/api/integrations", tags=["External Integrations"])


@router.post("/")
async def create_integration(
    name: str,
    integration_type: str,
    config: dict,
    webhooks: List[str] = [],
    current_user: User = Depends(require_admin)
):
    """Create new external integration"""
    try:
        if not current_user.is_admin:
            raise HTTPException(status_code=403, detail="Admin only")
        
        # Parse integration type
        integration_type_enum = IntegrationType(integration_type)
        
        integration_service = get_integration_service()
        integration = integration_service.create_integration(
            name=name,
            integration_type=integration_type_enum,
            config=config,
            webhooks=webhooks
        )
        
        return {
            "success": True,
            "integration": {
                "id": integration.id,
                "name": integration.name,
                "type": integration.type.value,
                "status": integration.status.value
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create integration: {e}")
        raise HTTPException(status_code=500, detail="An internal server error occurred. Please try again later.")


@router.get("/")
async def get_integrations(
    current_user: User = Depends(require_admin)
):
    """Get all integrations"""
    try:
        integration_service = get_integration_service()
        integrations = integration_service.get_integrations()
        
        return {
            "success": True,
            "integrations": [
                {
                    "id": integration.id,
                    "name": integration.name,
                    "type": integration.type.value,
                    "status": integration.status.value,
                    "last_sync": integration.last_sync.isoformat() if integration.last_sync else None,
                    "created_at": integration.created_at.isoformat() if integration.created_at else None
                }
                for integration in integrations
            ]
        }
        
    except Exception as e:
        logger.error(f"Failed to get integrations: {e}")
        raise HTTPException(status_code=500, detail="An internal server error occurred. Please try again later.")


@router.get("/{integration_id}")
async def get_integration(
    integration_id: str,
    current_user: User = Depends(require_admin)
):
    """Get specific integration"""
    try:
        integration_service = get_integration_service()
        integration = integration_service.get_integration(integration_id)
        
        if not integration:
            raise HTTPException(status_code=404, detail="Integration not found")
        
        return {
            "success": True,
            "integration": {
                "id": integration.id,
                "name": integration.name,
                "type": integration.type.value,
                "status": integration.status.value,
                "config": integration.config,
                "webhooks": integration.webhooks,
                "last_sync": integration.last_sync.isoformat() if integration.last_sync else None,
                "created_at": integration.created_at.isoformat() if integration.created_at else None
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get integration: {e}")
        raise HTTPException(status_code=500, detail="An internal server error occurred. Please try again later.")


@router.post("/{integration_id}/activate")
async def activate_integration(
    integration_id: str,
    current_user: User = Depends(require_admin)
):
    """Activate integration"""
    try:
        if not current_user.is_admin:
            raise HTTPException(status_code=403, detail="Admin only")
        
        integration_service = get_integration_service()
        result = integration_service.activate_integration(integration_id)
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to activate integration: {e}")
        raise HTTPException(status_code=500, detail="An internal server error occurred. Please try again later.")


@router.post("/{integration_id}/deactivate")
async def deactivate_integration(
    integration_id: str,
    current_user: User = Depends(require_admin)
):
    """Deactivate integration"""
    try:
        if not current_user.is_admin:
            raise HTTPException(status_code=403, detail="Admin only")
        
        integration_service = get_integration_service()
        result = integration_service.deactivate_integration(integration_id)
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to deactivate integration: {e}")
        raise HTTPException(status_code=500, detail="An internal server error occurred. Please try again later.")


@router.post("/{integration_id}/sync/erp")
async def sync_to_erp(
    integration_id: str,
    document_data: dict,
    current_user: User = Depends(require_admin)
):
    """Sync document to ERP system"""
    try:
        integration_service = get_integration_service()
        result = await integration_service.sync_document_to_erp(
            integration_id,
            document_data
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Failed to sync to ERP: {e}")
        raise HTTPException(status_code=500, detail="An internal server error occurred. Please try again later.")


@router.post("/{integration_id}/sync/crm")
async def sync_to_crm(
    integration_id: str,
    document_data: dict,
    current_user: User = Depends(require_admin)
):
    """Sync document to CRM system"""
    try:
        integration_service = get_integration_service()
        result = await integration_service.sync_document_to_crm(
            integration_id,
            document_data
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Failed to sync to CRM: {e}")
        raise HTTPException(status_code=500, detail="An internal server error occurred. Please try again later.")


@router.post("/{integration_id}/sync/accounting")
async def sync_to_accounting(
    integration_id: str,
    document_data: dict,
    current_user: User = Depends(require_admin)
):
    """Sync document to accounting system"""
    try:
        integration_service = get_integration_service()
        result = await integration_service.sync_document_to_accounting(
            integration_id,
            document_data
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Failed to sync to accounting: {e}")
        raise HTTPException(status_code=500, detail="An internal server error occurred. Please try again later.")


@router.post("/{integration_id}/webhook")
async def trigger_webhook(
    integration_id: str,
    webhook_index: int,
    data: dict,
    current_user: User = Depends(require_admin)
):
    """Trigger webhook integration"""
    try:
        integration_service = get_integration_service()
        result = await integration_service.trigger_webhook(
            integration_id,
            webhook_index,
            data
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Failed to trigger webhook: {e}")
        raise HTTPException(status_code=500, detail="An internal server error occurred. Please try again later.")