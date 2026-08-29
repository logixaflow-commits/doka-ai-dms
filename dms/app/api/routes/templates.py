"""
Template Library Routes
Handles pre-built SOP template management endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session
from loguru import logger

from app.core.database import get_db
from app.core.security import require_staff
from app.models.database import User
from app.services.template_library import template_library_service
from app.models.schemas import TemplateCreate

router = APIRouter()


@router.get("/library")
async def get_library_categories(
    current_user: User = Depends(require_staff)
):
    """Get all template categories."""
    try:
        categories = template_library_service.get_categories()
        
        result = {}
        for category in categories:
            result[category] = [
                {
                    "id": t.get('id'),
                    "name": t.get('name'),
                    "description": t.get('description'),
                    "icon": t.get('icon'),
                    "steps_count": len(t.get('steps', []))
                }
                for t in template_library_service.get_templates_by_category(category)
            ]
        
        return result
        
    except Exception as e:
        logger.error(f"Failed to get library categories: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get library"
        )


@router.get("/library/{category}")
async def get_category_templates(
    category: str,
    current_user: User = Depends(require_staff)
):
    """Get templates in a specific category."""
    try:
        templates = template_library_service.get_templates_by_category(category)
        
        return {
            "category": category,
            "templates": [
                {
                    "id": t.get('id'),
                    "name": t.get('name'),
                    "description": t.get('description'),
                    "icon": t.get('icon'),
                    "steps": t.get('steps')
                }
                for t in templates
            ]
        }
        
    except Exception as e:
        logger.error(f"Failed to get category templates: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get templates"
        )


@router.get("/library/{template_id}/download")
async def download_template(
    template_id: str,
    current_user: User = Depends(require_staff)
):
    """Download template as YAML."""
    try:
        yaml_data = template_library_service.export_template(template_id)
        
        if not yaml_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Template not found"
            )
        
        return PlainTextResponse(
            content=yaml_data,
            media_type="text/yaml",
            headers={"Content-Disposition": f"attachment; filename=template_{template_id}.yaml"}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to download template: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to download template"
        )


@router.post("/library/import")
async def import_template(
    category: str,
    yaml_data: str,
    current_user: User = Depends(require_staff)
):
    """Import a custom template from YAML."""
    try:
        template = template_library_service.import_template(yaml_data, category)
        
        if not template:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid template data"
            )
        
        return {
            "message": "Template imported successfully",
            "template_id": template.get('id'),
            "template_name": template.get('name')
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to import template: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to import template"
        )


@router.post("/library/{template_id}/instantiate")
async def instantiate_template(
    template_id: str,
    document_id: int,
    current_user: User = Depends(require_staff),
    db: Session = Depends(get_db)
):
    """Create SOP instance from template."""
    try:
        sop_id = template_library_service.instantiate_template(template_id, document_id, db)
        
        if not sop_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Template not found"
            )
        
        return {
            "message": "SOP instance created successfully",
            "sop_id": sop_id,
            "template_id": template_id,
            "document_id": document_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to instantiate template: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to instantiate template"
        )