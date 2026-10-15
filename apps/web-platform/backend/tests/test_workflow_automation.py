import pytest
from concurrent.futures import ThreadPoolExecutor

from app.services.workflow_automation import WorkflowAutomationService


@pytest.fixture
def service(tmp_path):
    service = WorkflowAutomationService()
    service.workflows_storage_path = tmp_path / "workflows"
    service.instances_storage_path = tmp_path / "instances"
    service.workflows_storage_path.mkdir()
    service.instances_storage_path.mkdir()
    return service


def test_workflow_rejects_empty_or_invalid_steps(service):
    with pytest.raises(ValueError, match="at least one step"):
        service.create_workflow("empty", "", "document", [], 1)
    with pytest.raises(ValueError, match="Unsupported workflow step type"):
        service.create_workflow(
            "bad",
            "",
            "document",
            [{"name": "x", "type": "unknown", "order": 0}],
            1,
        )
    with pytest.raises(ValueError, match="order must be unique"):
        service.create_workflow(
            "duplicate-order",
            "",
            "document",
            [
                {"name": "a", "type": "task", "order": 0},
                {"name": "b", "type": "task", "order": 0},
            ],
            1,
        )


def test_workflow_completion_checks_step_and_assignment(service):
    workflow = service.create_workflow(
        "approval",
        "",
        "document",
        [{"name": "approve", "type": "approval", "assigned_to": [7], "order": 0}],
        1,
    )
    instance = service.start_workflow(workflow.id, 10, 1)
    step = workflow.steps[0]

    assert service.complete_step(instance.id, "wrong", 7, {})["success"] is False
    assert service.complete_step(instance.id, step.id, 8, {})["success"] is False

    result = service.complete_step(
        instance.id, step.id, 7, {"approved": True}, idempotency_key="approve-1"
    )
    assert result["success"] is True
    assert result["instance_status"] == "completed"
    assert result["idempotency_key"] == "approve-1"

    replay = service.complete_step(
        instance.id, step.id, 7, {"approved": True}, idempotency_key="approve-1"
    )
    assert replay["success"] is False

def test_workflow_reports_failure_when_next_step_execution_fails(service, monkeypatch):
    workflow = service.create_workflow(
        "two-step",
        "",
        "document",
        [
            {"name": "approve", "type": "approval", "assigned_to": [7], "order": 0},
            {"name": "notify", "type": "notification", "order": 1},
        ],
        1,
    )
    instance = service.start_workflow(workflow.id, 10, 1)
    first_step = workflow.steps[0]
    original_execute = service._execute_step

    def fail_next(current_instance, step):
        if step.id == workflow.steps[1].id:
            current_instance.status = "failed"
            service._save_workflow_instance(current_instance)
            return
        original_execute(current_instance, step)

    monkeypatch.setattr(service, "_execute_step", fail_next)
    result = service.complete_step(instance.id, first_step.id, 7, {"approved": True})

    assert result["success"] is False
    assert result["instance_status"] == "failed"
    assert result["error"] == "Workflow failed while executing the next step"


def test_workflow_rejects_invalid_idempotency_key(service):
    workflow = service.create_workflow(
        "approval",
        "",
        "document",
        [{"name": "approve", "type": "approval", "assigned_to": [7], "order": 0}],
        1,
    )
    instance = service.start_workflow(workflow.id, 10, 1)
    step = workflow.steps[0]

    result = service.complete_step(
        instance.id, step.id, 7, {}, idempotency_key="bad key with spaces"
    )
    assert result == {"success": False, "error": "Invalid idempotency key"}


def test_workflow_rejects_reuse_with_different_idempotency_key(service):
    workflow = service.create_workflow(
        "two-step",
        "",
        "document",
        [
            {"name": "approve", "type": "approval", "assigned_to": [7], "order": 0},
            {"name": "notify", "type": "notification", "order": 1},
        ],
        1,
    )
    instance = service.start_workflow(workflow.id, 10, 1)
    step = workflow.steps[0]

    first = service.complete_step(
        instance.id, step.id, 7, {"approved": True}, idempotency_key="approve-1"
    )
    assert first["success"] is True

    conflict = service.complete_step(
        instance.id, step.id, 7, {"approved": True}, idempotency_key="approve-2"
    )
    assert conflict["success"] is False
    assert "different idempotency key" in conflict["error"]

def test_workflow_duplicate_delivery_is_serialized_by_idempotency_key(service):
    workflow = service.create_workflow(
        "duplicate-safe",
        "",
        "document",
        [
            {"name": "approve", "type": "approval", "assigned_to": [7], "order": 0},
            {"name": "notify", "type": "notification", "order": 1},
        ],
        1,
    )
    instance = service.start_workflow(workflow.id, 10, 1)
    step = workflow.steps[0]

    def deliver():
        return service.complete_step(
            instance.id,
            step.id,
            7,
            {"approved": True},
            idempotency_key="delivery-1",
        )

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: deliver(), range(2)))

    assert sorted(result["idempotent"] for result in results) == [False, True]
    assert sum(result["success"] for result in results) == 2
