"""Compatibility import for storage contracts in local tests and flattened Workers bundles."""

try:
    from shared.storage_contracts import *  # type: ignore
except ModuleNotFoundError:
    from cloudflare_worker.shared.storage_contracts import *  # type: ignore
