"""Small, prepared-statement-only adapter for Cloudflare D1 Python bindings.

This module is deliberately not wired into the active Supabase-backed Worker
until a D1 database and binding have been provisioned and migration gates pass.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any


class D1DatabaseError(RuntimeError):
    """A safe, non-sensitive D1 operation failure."""


def _to_python(value: Any) -> Any:
    """Convert Pyodide JS proxies into Python values when supported."""
    if value is None:
        return None
    converter = getattr(value, "to_py", None)
    if callable(converter):
        return converter()
    return value


def _get_member(value: Any, name: str, default: Any = None) -> Any:
    value = _to_python(value)
    if isinstance(value, Mapping):
        return value.get(name, default)
    try:
        return getattr(value, name)
    except (AttributeError, TypeError):
        return default


def _validate_sql(sql: str) -> str:
    if not isinstance(sql, str) or not sql.strip():
        raise ValueError("SQL statement must be a non-empty string.")
    return sql


def _validate_parameters(parameters: Sequence[Any]) -> tuple[Any, ...]:
    values = tuple(parameters)
    if any(not isinstance(value, (str, int, float, bool, type(None))) for value in values):
        raise TypeError("D1 parameters must be scalar strings, numbers, booleans or null.")
    return values


def _prepared(binding: Any, sql: str, parameters: Sequence[Any]):
    query = _validate_sql(sql)
    values = _validate_parameters(parameters)
    statement = binding.prepare(query)
    return statement.bind(*values) if values else statement


class D1Database:
    """Prepared-statement wrapper around a Cloudflare D1 binding."""

    def __init__(self, binding: Any):
        if binding is None or not callable(getattr(binding, "prepare", None)):
            raise D1DatabaseError("The configured D1 binding is unavailable.")
        self._binding = binding

    @classmethod
    def from_request(cls, request: Any, binding_name: str = "DOKA_DB") -> "D1Database":
        scope = getattr(request, "scope", None) or {}
        environment = scope.get("env") if isinstance(scope, Mapping) else None
        if environment is None:
            raise D1DatabaseError("Cloudflare Worker bindings are unavailable.")

        try:
            binding = getattr(environment, binding_name)
        except (AttributeError, TypeError):
            try:
                binding = environment[binding_name]
            except (KeyError, TypeError, AttributeError):
                binding = None

        if binding is None:
            raise D1DatabaseError(f"Required D1 binding '{binding_name}' is not configured.")
        return cls(binding)

    async def all(self, sql: str, parameters: Sequence[Any] = ()) -> list[dict[str, Any]]:
        statement = _prepared(self._binding, sql, parameters)
        try:
            result = _to_python(await statement.run())
        except Exception as exc:
            raise D1DatabaseError("D1 query failed.") from exc

        if _get_member(result, "success", True) is False:
            raise D1DatabaseError("D1 query was not successful.")
        rows = _to_python(_get_member(result, "results", []))
        if rows is None:
            return []
        if not isinstance(rows, list):
            raise D1DatabaseError("D1 returned an invalid row collection.")
        return rows

    async def first(self, sql: str, parameters: Sequence[Any] = ()) -> dict[str, Any] | None:
        statement = _prepared(self._binding, sql, parameters)
        try:
            result = await statement.first()
        except Exception as exc:
            raise D1DatabaseError("D1 query failed.") from exc
        row = _to_python(result)
        if row is not None and not isinstance(row, Mapping):
            raise D1DatabaseError("D1 returned an invalid row.")
        return dict(row) if row is not None else None

    async def execute(self, sql: str, parameters: Sequence[Any] = ()) -> dict[str, Any]:
        statement = _prepared(self._binding, sql, parameters)
        try:
            result = _to_python(await statement.run())
        except Exception as exc:
            raise D1DatabaseError("D1 write failed.") from exc
        if _get_member(result, "success", True) is False:
            raise D1DatabaseError("D1 write was not successful.")
        if not isinstance(result, Mapping):
            raise D1DatabaseError("D1 returned an invalid write result.")
        return dict(result)

    async def batch(
        self,
        statements: Sequence[tuple[str, Sequence[Any]]],
    ) -> list[dict[str, Any]]:
        """Execute a non-empty prepared-statement batch atomically in D1."""
        if not statements:
            raise ValueError("D1 batch must contain at least one statement.")

        prepared = [
            _prepared(self._binding, sql, parameters)
            for sql, parameters in statements
        ]
        try:
            results = _to_python(await self._binding.batch(prepared))
        except Exception as exc:
            raise D1DatabaseError("D1 batch failed and was rolled back.") from exc

        if not isinstance(results, list) or len(results) != len(prepared):
            raise D1DatabaseError("D1 returned an invalid batch result.")
        normalized = []
        for result in results:
            result = _to_python(result)
            if _get_member(result, "success", True) is False:
                raise D1DatabaseError("D1 batch was not successful.")
            if not isinstance(result, Mapping):
                raise D1DatabaseError("D1 returned an invalid batch item.")
            normalized.append(dict(result))
        return normalized
