"""
Integration Management Routes
Handles external API provider integration endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from loguru import logger

from app.core.database import get_db
from app.core.security import require_admin, get_current_user
from app.models.database import User
from app.services.external_api_service import get_external_api_service
from app.models.schemas import IntegrationCreate, IntegrationUpdate

router = APIRouter()


@router.get("")
async def list_integrations(
    enabled_only: bool = False,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all external API integrations (admin sees all, staff sees enabled)."""
    try:
        # Staff can only see enabled integrations
        if current_user.role != 'admin':
            enabled_only = True
        
        api_service = get_external_api_service(db)
        providers = api_service.list_all_providers(enabled_only=enabled_only)
        
        return {
            "integrations": [
                {
                    "id": p.id,
                    "name": p.name,
                    "provider_type": p.provider_type,
                    "base_url": p.base_url,
                    "auth_type": p.auth_type,
                    "enabled": p.enabled,
                    "created_at": p.created_at,
                    "last_used": p.last_used
                }
                for p in providers
            ]
        }
        
    except Exception as e:
        logger.error(f"Failed to list integrations: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list integrations"
        )


@router.post("")
async def create_integration(
    integration_data: IntegrationCreate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Create a new API integration (admin only)."""
    try:
        api_service = get_external_api_service(db)
        provider = api_service.register_api_provider(
            name=integration_data.name,
            provider_type=integration_data.provider_type,
            base_url=integration_data.base_url,
            auth_type=integration_data.auth_type,
            auth_config=integration_data.auth_config,
            endpoints=integration_data.endpoints,
            webhook_secret=integration_data.webhook_secret
        )
        
        return {
            "id": provider.id,
            "name": provider.name,
            "message": "Integration created successfully"
        }
        
    except Exception as e:
        logger.error(f"Failed to create integration: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create integration"
        )


@router.put("/{integration_id}")
async def update_integration(
    integration_id: int,
    integration_data: IntegrationUpdate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Update an existing integration (admin only)."""
    try:
        api_service = get_external_api_service(db)
        provider = api_service.update_api_provider(
            provider_id=integration_id,
            name=integration_data.name,
            base_url=integration_data.base_url,
            auth_config=integration_data.auth_config,
            endpoints=integration_data.endpoints,
            enabled=integration_data.enabled
        )
        
        if not provider:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Integration not found"
            )
        
        return {
            "id": provider.id,
            "name": provider.name,
            "message": "Integration updated successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update integration: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update integration"
        )


@router.delete("/{integration_id}")
async def delete_integration(
    integration_id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Delete an integration (admin only)."""
    try:
        api_service = get_external_api_service(db)
        success = api_service.delete_api_provider(integration_id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Integration not found"
            )
        
        return {"message": "Integration deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete integration: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete integration"
        )


@router.post("/{integration_id}/test")
async def test_integration(
    integration_id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Test connection to an integration (admin only)."""
    try:
        api_service = get_external_api_service(db)
        result = api_service.test_connection(integration_id)
        
        return result
        
    except Exception as e:
        logger.error(f"Failed to test integration: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to test integration"
        )


@router.get("/{integration_id}/logs")
async def get_integration_logs(
    integration_id: int,
    limit: int = 100,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Get API call logs for an integration."""
    try:
        api_service = get_external_api_service(db)
        logs = api_service.get_provider_logs(integration_id, limit)
        
        return {
            "integration_id": integration_id,
            "logs": [
                {
                    "id": log.id,
                    "endpoint": log.endpoint,
                    "status_code": log.status_code,
                    "error": log.error,
                    "timestamp": log.timestamp
                }
                for log in logs
            ]
        }
        
    except Exception as e:
        logger.error(f"Failed to get integration logs: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get logs"
        )