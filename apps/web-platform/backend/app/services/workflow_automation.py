"""
Workflow Automation Service
Provides custom approval workflows, conditional routing, and automated task assignments
"""
import uuid
import os
import tempfile
from contextlib import contextmanager
from typing import Optional, List, Dict, Any
from datetime import datetime
from dataclasses import dataclass
from enum import Enum
import json
from pathlib import Path
from loguru import logger


class WorkflowStatus(Enum):
    """Workflow status"""
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class TaskStatus(Enum):
    """Task status"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    SKIPPED = "skipped"
    FAILED = "failed"


@dataclass
class WorkflowStep:
    """Workflow step definition"""
    id: str
    name: str
    type: str  # approval, task, notification, condition
    assigned_to: Optional[List[int]]  # User IDs
    conditions: Optional[Dict[str, Any]]
    actions: Optional[List[Dict[str, Any]]]
    order: int


@dataclass
class Workflow:
    """Workflow definition"""
    id: str
    name: str
    description: str
    document_type: str
    steps: List[WorkflowStep]
    status: WorkflowStatus
    created_by: int
    created_at: datetime
    updated_at: Optional[datetime] = None


@dataclass
class WorkflowInstance:
    """Workflow instance (running workflow)"""
    id: str
    workflow_id: str
    document_id: int
    current_step: int
    status: str
    started_by: int
    started_at: datetime
    completed_at: Optional[datetime] = None
    data: Optional[Dict[str, Any]] = None


class WorkflowAutomationService:
    """Service for workflow automation"""
    
    def __init__(self):
        self.workflows_storage_path = Path("storage/workflows")
        self.workflows_storage_path.mkdir(parents=True, exist_ok=True)
        self.instances_storage_path = Path("storage/workflow_instances")
        self.instances_storage_path.mkdir(parents=True, exist_ok=True)
        
    def create_workflow(
        self,
        name: str,
        description: str,
        document_type: str,
        steps: List[Dict[str, Any]],
        created_by: int
    ) -> Workflow:
        """Create new workflow"""
        try:
            workflow_id = str(uuid.uuid4())
            
            if not steps:
                raise ValueError("Workflow must contain at least one step.")
            allowed_types = {"approval", "task", "notification", "condition"}
            workflow_steps = []
            seen_orders = set()
            for step_data in steps:
                step_type = str(step_data.get("type", "")).strip().lower()
                if step_type not in allowed_types:
                    raise ValueError("Unsupported workflow step type: " + (step_type or "missing"))
                if "name" not in step_data or not str(step_data["name"]).strip():
                    raise ValueError("Workflow steps require a non-empty name.")
                order = step_data.get("order")
                if not isinstance(order, int) or order < 0 or order in seen_orders:
                    raise ValueError("Workflow step order must be unique, integer, and non-negative.")
                seen_orders.add(order)
                step = WorkflowStep(
                    id=str(uuid.uuid4()),
                    name=str(step_data["name"]).strip(),
                    type=step_type,
                    assigned_to=step_data.get("assigned_to"),
                    conditions=step_data.get("conditions"),
                    actions=step_data.get("actions"),
                    order=order
                )
                workflow_steps.append(step)
            
            # Sort steps by order
            workflow_steps.sort(key=lambda x: x.order)
            
            workflow = Workflow(
                id=workflow_id,
                name=name,
                description=description,
                document_type=document_type,
                steps=workflow_steps,
                status=WorkflowStatus.DRAFT,
                created_by=created_by,
                created_at=datetime.utcnow()
            )
            
            # Save workflow
            self._save_workflow(workflow)
            
            logger.info(f"Created workflow {workflow_id}: {name}")
            return workflow
            
        except Exception as e:
            logger.error(f"Failed to create workflow: {e}")
            raise
    
    def start_workflow(
        self,
        workflow_id: str,
        document_id: int,
        started_by: int,
        initial_data: Optional[Dict[str, Any]] = None
    ) -> WorkflowInstance:
        """Start workflow instance"""
        try:
            # Get workflow
            workflow = self.get_workflow(workflow_id)
            
            if not workflow:
                raise ValueError("Workflow not found")
            
            # Create instance
            instance_id = str(uuid.uuid4())
            instance = WorkflowInstance(
                id=instance_id,
                workflow_id=workflow_id,
                document_id=document_id,
                current_step=0,
                status="in_progress",
                started_by=started_by,
                started_at=datetime.utcnow(),
                data=initial_data or {}
            )
            
            # Save instance
            self._save_workflow_instance(instance)
            
            # Execute first step. A failed first step must never look successful.
            self._execute_step(instance, workflow.steps[0])
            if instance.status == "failed":
                raise RuntimeError("Workflow failed while executing its first step.")
            
            logger.info(f"Started workflow instance {instance_id}")
            return instance
            
        except Exception as e:
            logger.error(f"Failed to start workflow: {e}")
            raise
    
    def _execute_step(self, instance: WorkflowInstance, step: WorkflowStep):
        """Execute workflow step"""
        try:
            logger.info(f"Executing step {step.name} for instance {instance.id}")
            
            if step.type == "approval":
                self._handle_approval_step(instance, step)
            elif step.type == "task":
                self._handle_task_step(instance, step)
            elif step.type == "notification":
                self._handle_notification_step(instance, step)
            elif step.type == "condition":
                self._handle_condition_step(instance, step)
            
            # Update instance
            instance.current_step += 1
            self._save_workflow_instance(instance)
            
        except Exception as e:
            logger.error(f"Failed to execute step: {e}")
            instance.status = "failed"
            self._save_workflow_instance(instance)
    
    def _handle_approval_step(self, instance: WorkflowInstance, step: WorkflowStep):
        """Handle approval step"""
        # This would send approval requests to assigned users
        logger.info(f"Approval step {step.name} assigned to {step.assigned_to}")
        
        # Update instance data
        if "approvals" not in instance.data:
            instance.data["approvals"] = []
        
        instance.data["approvals"].append({
            "step_id": step.id,
            "step_name": step.name,
            "assigned_to": step.assigned_to,
            "status": "pending",
            "created_at": datetime.utcnow().isoformat()
        })
    
    def _handle_task_step(self, instance: WorkflowInstance, step: WorkflowStep):
        """Handle task step"""
        # This would create tasks for assigned users
        logger.info(f"Task step {step.name} assigned to {step.assigned_to}")
        
        # Update instance data
        if "tasks" not in instance.data:
            instance.data["tasks"] = []
        
        instance.data["tasks"].append({
            "step_id": step.id,
            "step_name": step.name,
            "assigned_to": step.assigned_to,
            "status": "pending",
            "created_at": datetime.utcnow().isoformat()
        })
    
    def _handle_notification_step(self, instance: WorkflowInstance, step: WorkflowStep):
        """Handle notification step"""
        # This would send notifications
        logger.info(f"Notification step {step.name} executed")
        
        # Update instance data
        if "notifications" not in instance.data:
            instance.data["notifications"] = []
        
        instance.data["notifications"].append({
            "step_id": step.id,
            "step_name": step.name,
            "sent_at": datetime.utcnow().isoformat()
        })
    
    def _handle_condition_step(self, instance: WorkflowInstance, step: WorkflowStep):
        """Handle condition step"""
        # This would evaluate conditions and route accordingly
        logger.info(f"Condition step {step.name} evaluated")
        
        if step.conditions:
            # Evaluate conditions
            condition_met = self._evaluate_conditions(step.conditions, instance.data)
            
            instance.data["conditions"] = instance.data.get("conditions", [])
            instance.data["conditions"].append({
                "step_id": step.id,
                "step_name": step.name,
                "conditions": step.conditions,
                "result": condition_met,
                "evaluated_at": datetime.utcnow().isoformat()
            })
    
    def _evaluate_conditions(self, conditions: Dict[str, Any], data: Dict[str, Any]) -> bool:
        """Evaluate workflow conditions"""
        # Simple condition evaluation
        if conditions.get("document_status"):
            return data.get("document_status") == conditions["document_status"]
        
        if conditions.get("document_type"):
            return data.get("document_type") == conditions["document_type"]
        
        return True
    
    def complete_step(
        self,
        instance_id: str,
        step_id: str,
        user_id: int,
        result: Dict[str, Any],
        idempotency_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Complete the active workflow step exactly once with a durable key."""
        try:
            if idempotency_key is not None:
                idempotency_key = str(idempotency_key).strip()
                if not idempotency_key or len(idempotency_key) > 128 or any(
                    char not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._:-"
                    for char in idempotency_key
                ):
                    return {"success": False, "error": "Invalid idempotency key"}
            with self._lock_workflow_instance(instance_id):
                return self._complete_step_locked(instance_id, step_id, user_id, result, idempotency_key)
        except Exception as e:
            logger.error(f"Failed to complete step: {e}")
            return {"success": False, "error": str(e)}

    def _complete_step_locked(
        self,
        instance_id: str,
        step_id: str,
        user_id: int,
        result: Dict[str, Any],
        idempotency_key: Optional[str],
    ) -> Dict[str, Any]:
        try:
            instance = self.get_workflow_instance(instance_id)
            if not instance:
                return {"success": False, "error": "Instance not found"}
            workflow = self.get_workflow(instance.workflow_id)
            if not workflow:
                return {"success": False, "error": "Workflow not found"}
            if instance.status in {"completed", "cancelled", "failed"}:
                return {"success": False, "error": f"Instance is already {instance.status}"}

            if "step_results" not in instance.data:
                instance.data["step_results"] = []
            existing = [
                item for item in instance.data["step_results"]
                if item.get("step_id") == step_id and item.get("user_id") == user_id
            ]
            if existing:
                recorded_key = existing[0].get("idempotency_key")
                if idempotency_key is None or recorded_key == idempotency_key:
                    return {
                        "success": True,
                        "idempotent": True,
                        "instance_status": instance.status,
                        "current_step": instance.current_step,
                        "idempotency_key": recorded_key,
                    }
                return {
                    "success": False,
                    "idempotent": False,
                    "error": "Workflow step has already been completed with a different idempotency key",
                }

            if instance.current_step <= 0 or instance.current_step > len(workflow.steps):
                return {"success": False, "error": "Workflow instance has an invalid current step"}

            expected_step = workflow.steps[instance.current_step - 1]
            if step_id != expected_step.id:
                return {
                    "success": False,
                    "error": "Step does not match the active workflow step",
                    "expected_step_id": expected_step.id,
                }
            assigned = expected_step.assigned_to or []
            if assigned and user_id not in assigned:
                return {"success": False, "error": "User is not assigned to the active workflow step"}

            effective_key = idempotency_key or f"legacy:{instance_id}:{step_id}:{user_id}"
            instance.data["step_results"].append({
                "step_id": step_id,
                "user_id": user_id,
                "idempotency_key": effective_key,
                "result": result,
                "completed_at": datetime.utcnow().isoformat()
            })
            if instance.current_step >= len(workflow.steps):
                instance.status = "completed"
                instance.completed_at = datetime.utcnow()
            else:
                self._execute_step(instance, workflow.steps[instance.current_step])
                if instance.status == "failed":
                    self._save_workflow_instance(instance)
                    return {
                        "success": False,
                        "idempotent": False,
                        "instance_status": "failed",
                        "current_step": instance.current_step,
                        "error": "Workflow failed while executing the next step",
                    }
            self._save_workflow_instance(instance)
            return {
                "success": True,
                "idempotent": False,
                "instance_status": instance.status,
                "current_step": instance.current_step,
                "idempotency_key": effective_key,
            }
        except Exception as e:
            logger.error(f"Failed to complete step: {e}")
            return {"success": False, "error": str(e)}

    @contextmanager
    def _lock_workflow_instance(self, instance_id: str):
        """Serialize instance transitions and keep the lock durable across processes on POSIX."""
        lock_path = self.instances_storage_path / f"{instance_id}.lock"
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        lock_file = open(lock_path, "a+")
        try:
            try:
                import fcntl
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
            except ImportError:
                pass
            yield
        finally:
            try:
                import fcntl
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
            except ImportError:
                pass
            lock_file.close()

    def get_workflow(self, workflow_id: str) -> Optional[Workflow]:
        """Get workflow by ID"""
        try:
            workflow_file = self.workflows_storage_path / f"{workflow_id}.json"
            
            if not workflow_file.exists():
                return None
            
            with open(workflow_file, 'r') as f:
                workflow_data = json.load(f)
            
            steps = []
            for step_data in workflow_data["steps"]:
                step = WorkflowStep(
                    id=step_data["id"],
                    name=step_data["name"],
                    type=step_data["type"],
                    assigned_to=step_data.get("assigned_to"),
                    conditions=step_data.get("conditions"),
                    actions=step_data.get("actions"),
                    order=step_data["order"]
                )
                steps.append(step)
            
            workflow = Workflow(
                id=workflow_data["id"],
                name=workflow_data["name"],
                description=workflow_data["description"],
                document_type=workflow_data["document_type"],
                steps=steps,
                status=WorkflowStatus(workflow_data["status"]),
                created_by=workflow_data["created_by"],
                created_at=datetime.fromisoformat(workflow_data["created_at"]),
                updated_at=datetime.fromisoformat(workflow_data["updated_at"]) if workflow_data.get("updated_at") else None
            )
            
            return workflow
            
        except Exception as e:
            logger.error(f"Failed to get workflow: {e}")
            return None
    
    def get_workflow_instance(self, instance_id: str) -> Optional[WorkflowInstance]:
        """Get workflow instance by ID"""
        try:
            instance_file = self.instances_storage_path / f"{instance_id}.json"
            
            if not instance_file.exists():
                return None
            
            with open(instance_file, 'r') as f:
                instance_data = json.load(f)
            
            instance = WorkflowInstance(
                id=instance_data["id"],
                workflow_id=instance_data["workflow_id"],
                document_id=instance_data["document_id"],
                current_step=instance_data["current_step"],
                status=instance_data["status"],
                started_by=instance_data["started_by"],
                started_at=datetime.fromisoformat(instance_data["started_at"]),
                completed_at=datetime.fromisoformat(instance_data["completed_at"]) if instance_data.get("completed_at") else None,
                data=instance_data.get("data")
            )
            
            return instance
            
        except Exception as e:
            logger.error(f"Failed to get workflow instance: {e}")
            return None
    
    def get_workflows_by_document_type(self, document_type: str) -> List[Workflow]:
        """Get workflows for specific document type"""
        try:
            workflows = []
            
            for workflow_file in self.workflows_storage_path.glob("*.json"):
                with open(workflow_file, 'r') as f:
                    workflow_data = json.load(f)
                
                if workflow_data["document_type"] == document_type:
                    workflow = self.get_workflow(workflow_data["id"])
                    if workflow:
                        workflows.append(workflow)
            
            return workflows
            
        except Exception as e:
            logger.error(f"Failed to get workflows by document type: {e}")
            return []
    
    def _save_workflow(self, workflow: Workflow):
        """Save workflow to file"""
        workflow_file = self.workflows_storage_path / f"{workflow.id}.json"
        
        workflow_data = {
            "id": workflow.id,
            "name": workflow.name,
            "description": workflow.description,
            "document_type": workflow.document_type,
            "steps": [
                {
                    "id": step.id,
                    "name": step.name,
                    "type": step.type,
                    "assigned_to": step.assigned_to,
                    "conditions": step.conditions,
                    "actions": step.actions,
                    "order": step.order
                }
                for step in workflow.steps
            ],
            "status": workflow.status.value,
            "created_by": workflow.created_by,
            "created_at": workflow.created_at.isoformat(),
            "updated_at": workflow.updated_at.isoformat() if workflow.updated_at else None
        }
        
        with open(workflow_file, 'w') as f:
            json.dump(workflow_data, f, indent=2)
    
    def _save_workflow_instance(self, instance: WorkflowInstance):
        """Save workflow instance to file"""
        instance_file = self.instances_storage_path / f"{instance.id}.json"
        
        instance_data = {
            "id": instance.id,
            "workflow_id": instance.workflow_id,
            "document_id": instance.document_id,
            "current_step": instance.current_step,
            "status": instance.status,
            "started_by": instance.started_by,
            "started_at": instance.started_at.isoformat(),
            "completed_at": instance.completed_at.isoformat() if instance.completed_at else None,
            "data": instance.data
        }
        
        fd, temp_name = tempfile.mkstemp(
            prefix=f".{instance.id}.", suffix=".tmp", dir=str(self.instances_storage_path)
        )
        try:
            with os.fdopen(fd, "w") as f:
                json.dump(instance_data, f, indent=2)
                f.flush()
                os.fsync(f.fileno())
            os.replace(temp_name, instance_file)
        finally:
            if os.path.exists(temp_name):
                os.unlink(temp_name)


# Singleton instance
_workflow_service: Optional[WorkflowAutomationService] = None


def get_workflow_service() -> WorkflowAutomationService:
    """Get singleton workflow service"""
    global _workflow_service
    if _workflow_service is None:
        _workflow_service = WorkflowAutomationService()
    return _workflow_service