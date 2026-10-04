"""Unit tests for the prepared-statement D1 adapter."""
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from cloudflare_worker.d1 import D1Database, D1DatabaseError


class JsValue:
    def __init__(self, value):
        self.value = value

    def to_py(self):
        return self.value


class FakeStatement:
    def __init__(self, sql, binding):
        self.sql = sql
        self.binding = binding
        self.parameters = ()
        self.bind_calls = 0

    def bind(self, *parameters):
        self.bind_calls += 1
        self.parameters = parameters
        return self

    async def run(self):
        if self.binding.run_error:
            raise RuntimeError("private driver detail")
        return JsValue(self.binding.run_result)

    async def first(self):
        if self.binding.first_error:
            raise RuntimeError("private driver detail")
        return JsValue(self.binding.first_result)


class FakeBinding:
    def __init__(self):
        self.statements = []
        self.run_result = {"success": True, "results": []}
        self.first_result = None
        self.run_error = False
        self.first_error = False
        self.batch_error = False

    def prepare(self, sql):
        statement = FakeStatement(sql, self)
        self.statements.append(statement)
        return statement

    async def batch(self, statements):
        if self.batch_error:
            raise RuntimeError("private driver detail")
        return JsValue([
            {"success": True, "results": [], "meta": {"changes": 1}}
            for _ in statements
        ])


def test_all_uses_prepared_bindings_and_returns_rows():
    binding = FakeBinding()
    binding.run_result = {
        "success": True,
        "results": [{"id": "doc-1", "filename": "a.pdf"}],
    }
    db = D1Database(binding)

    rows = pytest.importorskip("asyncio").run(
        db.all("SELECT * FROM documents WHERE owner_id = ?", ("owner-1",))
    )

    assert rows == [{"id": "doc-1", "filename": "a.pdf"}]
    assert binding.statements[0].sql == "SELECT * FROM documents WHERE owner_id = ?"
    assert binding.statements[0].parameters == ("owner-1",)


def test_first_returns_none_or_a_plain_mapping():
    binding = FakeBinding()
    db = D1Database(binding)
    asyncio = pytest.importorskip("asyncio")

    assert asyncio.run(db.first("SELECT id FROM documents WHERE id = ?", ("missing",))) is None
    binding.first_result = {"id": "doc-1"}
    assert asyncio.run(db.first("SELECT id FROM documents WHERE id = ?", ("doc-1",))) == {"id": "doc-1"}


def test_execute_returns_write_metadata_and_does_not_interpolate_values():
    binding = FakeBinding()
    binding.run_result = {"success": True, "results": [], "meta": {"changes": 1}}
    db = D1Database(binding)

    result = pytest.importorskip("asyncio").run(
        db.execute("UPDATE documents SET filename = ? WHERE id = ?", ("x.pdf", "doc-1"))
    )

    assert result["meta"]["changes"] == 1
    assert binding.statements[0].sql == "UPDATE documents SET filename = ? WHERE id = ?"
    assert binding.statements[0].parameters == ("x.pdf", "doc-1")


def test_batch_prepares_all_statements_for_atomic_d1_execution():
    binding = FakeBinding()
    db = D1Database(binding)
    asyncio = pytest.importorskip("asyncio")

    result = asyncio.run(db.batch([
        ("UPDATE documents SET status = ? WHERE id = ?", ("review", "doc-1")),
        ("INSERT INTO outbox_events(id, event_type) VALUES (?, ?)", ("evt-1", "document.updated")),
    ]))

    assert len(result) == 2
    assert len(binding.statements) == 2
    assert binding.statements[0].parameters == ("review", "doc-1")
    assert binding.statements[1].parameters == ("evt-1", "document.updated")


def test_batch_rejects_empty_statement_list():
    db = D1Database(FakeBinding())
    with pytest.raises(ValueError, match="at least one"):
        pytest.importorskip("asyncio").run(db.batch([]))


def test_non_scalar_parameters_are_rejected_before_prepare():
    binding = FakeBinding()
    db = D1Database(binding)
    with pytest.raises(TypeError, match="scalar"):
        pytest.importorskip("asyncio").run(
            db.all("SELECT ?", ({"unsafe": "object"},))
        )
    assert binding.statements == []


def test_query_failures_are_wrapped_without_leaking_driver_details():
    binding = FakeBinding()
    binding.run_error = True
    db = D1Database(binding)

    with pytest.raises(D1DatabaseError, match="D1 query failed") as error:
        pytest.importorskip("asyncio").run(db.all("SELECT 1"))
    assert "private driver detail" not in str(error.value)


def test_binding_is_resolved_from_asgi_scope():
    binding = FakeBinding()
    request = SimpleNamespace(scope={"env": SimpleNamespace(DOKA_DB=binding)})
    assert D1Database.from_request(request)._binding is binding


def test_missing_binding_fails_closed():
    request = SimpleNamespace(scope={"env": SimpleNamespace()})
    with pytest.raises(D1DatabaseError, match="not configured"):
        D1Database.from_request(request)


def test_d1_result_failure_is_not_returned_as_success():
    binding = FakeBinding()
    binding.run_result = {"success": False, "results": []}
    db = D1Database(binding)
    with pytest.raises(D1DatabaseError, match="not successful"):
        pytest.importorskip("asyncio").run(db.all("SELECT 1"))
