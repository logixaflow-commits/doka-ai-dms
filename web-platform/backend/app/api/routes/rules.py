"""
Rule Management Routes
Handles automation rule CRUD and testing endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from loguru import logger

from app.core.database import get_db
from app.core.security import require_admin, get_current_user
from app.core.logging import log_audit, get_client_info
from app.models.database import User
from app.services.rule_manager_service import rule_manager_service
from app.services.rule_engine import rule_engine
from app.models.schemas import RuleCreate, RuleUpdate, RuleResponse

router = APIRouter()


@router.get("", response_model=list)
async def list_rules(
    enabled_only: bool = False,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all automation rules (admin only for all, staff can see enabled)."""
    try:
        # Staff can only see enabled rules
        if current_user.role != 'admin':
            enabled_only = True
        
        rules = rule_manager_service.get_all_rules(db, enabled_only=enabled_only)
        
        return [
            {
                "id": r.id,
                "name": r.name,
                "description": r.description,
                "condition": r.condition,
                "actions": r.actions,
                "enabled": r.enabled,
                "priority": r.priority,
                "logic": r.logic,
                "created_at": r.created_at,
                "last_triggered": r.last_triggered
            }
            for r in rules
        ]
        
    except Exception as e:
        logger.error(f"Failed to list rules: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list rules"
        )


@router.post("", response_model=dict)
async def create_rule(
    rule_data: RuleCreate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Create a new automation rule (admin only)."""
    try:
        rule = rule_manager_service.create_rule(rule_data, current_user.id, db)
        
        return {
            "id": rule.id,
            "name": rule.name,
            "message": "Rule created successfully"
        }
        
    except Exception as e:
        logger.error(f"Failed to create rule: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create rule"
        )


@router.put("/{rule_id}", response_model=dict)
async def update_rule(
    rule_id: int,
    rule_data: RuleUpdate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Update an existing rule (admin only)."""
    try:
        rule = rule_manager_service.update_rule(rule_id, rule_data, current_user.id, db)
        if not rule:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Rule not found"
            )
        
        return {
            "id": rule.id,
            "name": rule.name,
            "message": "Rule updated successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update rule: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update rule"
        )


@router.delete("/{rule_id}")
async def delete_rule(
    rule_id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Delete a rule (admin only)."""
    try:
        success = rule_manager_service.delete_rule(rule_id, db)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Rule not found"
            )
        
        return {"message": "Rule deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete rule: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete rule"
        )


@router.post("/{rule_id}/enable")
async def enable_rule(
    rule_id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Enable a rule (admin only)."""
    try:
        success = rule_manager_service.enable_rule(rule_id, db)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Rule not found"
            )
        
        return {"message": "Rule enabled successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to enable rule: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to enable rule"
        )


@router.post("/{rule_id}/disable")
async def disable_rule(
    rule_id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Disable a rule (admin only)."""
    try:
        success = rule_manager_service.disable_rule(rule_id, db)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Rule not found"
            )
        
        return {"message": "Rule disabled successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to disable rule: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to disable rule"
        )


@router.post("/{rule_id}/test")
async def test_rule(
    rule_id: int,
    document_data: dict,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Test a rule against document data (admin only)."""
    try:
        result = rule_manager_service.test_rule(rule_id, document_data, db)
        
        if 'error' in result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=result['error']
            )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to test rule: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to test rule"
        )


@router.get("/{rule_id}/logs")
async def get_rule_logs(
    rule_id: int,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get execution logs for a rule."""
    try:
        logs = rule_manager_service.get_rule_execution_logs(
            rule_id=rule_id,
            limit=limit,
            db=db
        )
        
        return [
            {
                "id": log.id,
                "rule_id": log.rule_id,
                "document_id": log.document_id,
                "executed": log.executed,
                "message": log.message,
                "timestamp": log.timestamp
            }
            for log in logs
        ]
        
    except Exception as e:
        logger.error(f"Failed to get rule logs: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get rule logs"
        )


@router.get("/logs")
async def get_all_logs(
    document_id: int = None,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all rule execution logs (filtered by document if provided)."""
    try:
        logs = rule_manager_service.get_rule_execution_logs(
            document_id=document_id,
            limit=limit,
            db=db
        )
        
        return [
            {
                "id": log.id,
                "rule_id": log.rule_id,
                "document_id": log.document_id,
                "executed": log.executed,
                "message": log.message,
                "timestamp": log.timestamp
            }
            for log in logs
        ]
        
    except Exception as e:
        logger.error(f"Failed to get logs: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get logs"
        )