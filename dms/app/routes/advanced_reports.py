"""
API Routes for Advanced Reporting
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional
from loguru import logger

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.database import User
from app.services.advanced_reporting import get_reporting_service

router = APIRouter(prefix="/api/reports", tags=["Advanced Reports"])


@router.post("/templates")
async def create_report_template(
    name: str,
    description: str,
    report_type: str,
    columns: list,
    filters: list = [],
    parameters: dict = {},
    current_user: User = Depends(get_current_user)
):
    """Create new report template"""
    try:
        reporting_service = get_reporting_service()
        template = reporting_service.create_report_template(
            name=name,
            description=description,
            report_type=report_type,
            parameters=parameters,
            columns=columns,
            filters=filters,
            created_by=current_user.id
        )
        
        return {
            "success": True,
            "template": {
                "id": template.id,
                "name": template.name,
                "description": template.description,
                "report_type": template.report_type
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to create report template: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/templates")
async def get_report_templates(
    current_user: User = Depends(get_current_user)
):
    """Get all report templates"""
    try:
        reporting_service = get_reporting_service()
        templates = reporting_service.get_all_report_templates()
        
        return {
            "success": True,
            "templates": [
                {
                    "id": t.id,
                    "name": t.name,
                    "description": t.description,
                    "report_type": t.report_type,
                    "created_by": t.created_by,
                    "created_at": t.created_at.isoformat()
                }
                for t in templates
            ]
        }
        
    except Exception as e:
        logger.error(f"Failed to get report templates: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/templates/{template_id}")
async def get_report_template(
    template_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get specific report template"""
    try:
        reporting_service = get_reporting_service()
        template = reporting_service.get_report_template(template_id)
        
        if not template:
            raise HTTPException(status_code=404, detail="Template not found")
        
        return {
            "success": True,
            "template": {
                "id": template.id,
                "name": template.name,
                "description": template.description,
                "report_type": template.report_type,
                "parameters": template.parameters,
                "columns": template.columns,
                "filters": template.filters,
                "created_by": template.created_by,
                "created_at": template.created_at.isoformat()
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get report template: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate/{template_id}")
async def generate_report(
    template_id: str,
    parameters: Optional[dict] = None,
    current_user: User = Depends(get_current_user)
):
    """Generate report from template"""
    try:
        reporting_service = get_reporting_service()
        result = reporting_service.generate_report(template_id, parameters)
        
        return result
        
    except Exception as e:
        logger.error(f"Failed to generate report: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/export")
async def export_report(
    report_data: list,
    format: str = "csv",
    current_user: User = Depends(get_current_user)
):
    """Export report to different formats"""
    try:
        reporting_service = get_reporting_service()
        result = reporting_service.export_report(report_data, format)
        
        return result
        
    except Exception as e:
        logger.error(f"Failed to export report: {e}")
        raise HTTPException(status_code=500, detail=str(e))