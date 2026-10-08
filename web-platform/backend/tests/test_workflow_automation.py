import pytest

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

    result = service.complete_step(instance.id, step.id, 7, {"approved": True})
    assert result["success"] is True
    assert result["instance_status"] == "completed"

    replay = service.complete_step(instance.id, step.id, 7, {"approved": True})
    assert replay["success"] is False
