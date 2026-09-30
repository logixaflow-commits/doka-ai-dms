"""
Rule Manager Service - CRUD operations for automation rules
"""
from typing import List, Optional, Dict
from datetime import datetime
from loguru import logger

from sqlalchemy.orm import Session
from app.models.database import AutomationRule, RuleExecutionLog
from app.models.schemas import RuleCreate, RuleUpdate, RuleResponse
from app.services.rule_engine import Rule, RuleCondition, RuleAction, rule_engine


class RuleManagerService:
    """Service for managing automation rules."""

    def create_rule(
        self,
        rule_data: RuleCreate,
        created_by: int,
        db: Session
    ) -> AutomationRule:
        """
        Create a new automation rule.
        
        Args:
            rule_data: Rule creation data
            created_by: User ID creating the rule
            db: Database session
            
        Returns:
            Created rule
        """
        try:
            # Create database record
            db_rule = AutomationRule(
                name=rule_data.name,
                description=rule_data.description,
                condition=rule_data.condition,
                actions=rule_data.actions,
                enabled=rule_data.enabled,
                priority=rule_data.priority,
                logic=rule_data.logic,
                created_by=created_by,
                created_at=datetime.utcnow()
            )
            
            db.add(db_rule)
            db.commit()
            db.refresh(db_rule)
            
            # Also add to rule engine
            rule = Rule(
                rule_id=db_rule.id,
                name=db_rule.name,
                conditions=db_rule.condition,
                actions=db_rule.actions,
                enabled=db_rule.enabled,
                priority=db_rule.priority,
                logic=db_rule.logic
            )
            rule_engine.add_rule(rule)
            
            logger.info(f"Created rule: {db_rule.name} (ID: {db_rule.id})")
            return db_rule
            
        except Exception as e:
            logger.error(f"Failed to create rule: {e}")
            db.rollback()
            raise

    def get_rule(self, rule_id: int, db: Session) -> Optional[AutomationRule]:
        """Get a rule by ID."""
        return db.query(AutomationRule).filter(AutomationRule.id == rule_id).first()

    def get_all_rules(self, db: Session, enabled_only: bool = False) -> List[AutomationRule]:
        """Get all rules."""
        query = db.query(AutomationRule)
        if enabled_only:
            query = query.filter(AutomationRule.enabled == True)
        return query.order_by(AutomationRule.priority.desc(), AutomationRule.created_at.desc()).all()

    def update_rule(
        self,
        rule_id: int,
        rule_data: RuleUpdate,
        updated_by: int,
        db: Session
    ) -> Optional[AutomationRule]:
        """Update an existing rule."""
        try:
            rule = self.get_rule(rule_id, db)
            if not rule:
                return None

            # Update fields
            if rule_data.name is not None:
                rule.name = rule_data.name
            if rule_data.description is not None:
                rule.description = rule_data.description
            if rule_data.condition is not None:
                rule.condition = rule_data.condition
            if rule_data.actions is not None:
                rule.actions = rule_data.actions
            if rule_data.enabled is not None:
                rule.enabled = rule_data.enabled
            if rule_data.priority is not None:
                rule.priority = rule_data.priority
            if rule_data.logic is not None:
                rule.logic = rule_data.logic

            rule.last_triggered = None  # Reset last triggered on update
            db.commit()
            db.refresh(rule)
            
            # Rebuild rule engine
            self._rebuild_rule_engine(db)
            
            logger.info(f"Updated rule: {rule.name} (ID: {rule_id})")
            return rule
            
        except Exception as e:
            logger.error(f"Failed to update rule: {e}")
            db.rollback()
            raise

    def delete_rule(self, rule_id: int, db: Session) -> bool:
        """Delete a rule."""
        try:
            rule = self.get_rule(rule_id, db)
            if not rule:
                return False

            db.delete(rule)
            db.commit()
            
            # Remove from rule engine
            rule_engine.remove_rule(rule_id)
            
            logger.info(f"Deleted rule: {rule.name} (ID: {rule_id})")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete rule: {e}")
            db.rollback()
            raise

    def enable_rule(self, rule_id: int, db: Session) -> bool:
        """Enable a rule."""
        try:
            rule = self.get_rule(rule_id, db)
            if not rule:
                return False

            rule.enabled = True
            db.commit()
            
            self._rebuild_rule_engine(db)
            
            logger.info(f"Enabled rule: {rule.name} (ID: {rule_id})")
            return True
            
        except Exception as e:
            logger.error(f"Failed to enable rule: {e}")
            db.rollback()
            raise

    def disable_rule(self, rule_id: int, db: Session) -> bool:
        """Disable a rule."""
        try:
            rule = self.get_rule(rule_id, db)
            if not rule:
                return False

            rule.enabled = False
            db.commit()
            
            self._rebuild_rule_engine(db)
            
            logger.info(f"Disabled rule: {rule.name} (ID: {rule_id})")
            return True
            
        except Exception as e:
            logger.error(f"Failed to disable rule: {e}")
            db.rollback()
            raise

    def test_rule(self, rule_id: int, document_data: Dict, db: Session) -> Dict:
        """Test a rule against document data."""
        try:
            rule = self.get_rule(rule_id, db)
            if not rule:
                return {'error': 'Rule not found'}

            # Create temporary rule for testing
            test_rule = Rule(
                rule_id=rule.id,
                name=rule.name,
                conditions=rule.condition,
                actions=rule.actions,
                enabled=True,
                priority=rule.priority,
                logic=rule.logic
            )

            # Evaluate
            matches = test_rule.evaluate(document_data)
            
            result = {
                'rule_id': rule.id,
                'rule_name': rule.name,
                'matches': matches,
                'conditions_count': len(test_rule.conditions),
                'actions_count': len(test_rule.actions)
            }

            if matches:
                # Show what actions would be executed
                actions = test_rule.actions
                result['actions_preview'] = [
                    {'type': a.action_type, 'parameters': a.parameters}
                    for a in actions
                ]

            return result
            
        except Exception as e:
            logger.error(f"Failed to test rule: {e}")
            return {'error': str(e)}

    def log_rule_execution(
        self,
        rule_id: int,
        document_id: int,
        executed: bool,
        message: str,
        db: Session
    ) -> RuleExecutionLog:
        """Log rule execution."""
        try:
            log = RuleExecutionLog(
                rule_id=rule_id,
                document_id=document_id,
                executed=executed,
                message=message,
                timestamp=datetime.utcnow()
            )
            
            db.add(log)
            db.commit()
            db.refresh(log)
            
            return log
            
        except Exception as e:
            logger.error(f"Failed to log rule execution: {e}")
            db.rollback()
            raise

    def get_rule_execution_logs(
        self,
        rule_id: Optional[int] = None,
        document_id: Optional[int] = None,
        limit: int = 100,
        db: Session = None
    ) -> List[RuleExecutionLog]:
        """Get rule execution logs."""
        query = db.query(RuleExecutionLog)
        
        if rule_id:
            query = query.filter(RuleExecutionLog.rule_id == rule_id)
        if document_id:
            query = query.filter(RuleExecutionLog.document_id == document_id)
        
        return query.order_by(RuleExecutionLog.timestamp.desc()).limit(limit).all()

    def _rebuild_rule_engine(self, db: Session):
        """Rebuild rule engine from database."""
        try:
            rules = self.get_all_rules(db, enabled_only=True)
            
            # Clear and rebuild
            rule_engine.clear_rules()
            
            for db_rule in rules:
                rule = Rule(
                    rule_id=db_rule.id,
                    name=db_rule.name,
                    conditions=db_rule.condition,
                    actions=db_rule.actions,
                    enabled=db_rule.enabled,
                    priority=db_rule.priority,
                    logic=db_rule.logic
                )
                rule_engine.add_rule(rule)
            
            logger.info(f"Rebuilt rule engine with {len(rules)} rules")
            
        except Exception as e:
            logger.error(f"Failed to rebuild rule engine: {e}")

    def initialize_from_database(self, db: Session):
        """Initialize rule engine with rules from database."""
        self._rebuild_rule_engine(db)


# Global rule manager service instance
rule_manager_service = RuleManagerService()