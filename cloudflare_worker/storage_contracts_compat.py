"""Import storage contracts in both local tests and the flattened Worker bundle."""

try:
    from shared.storage_contracts import *  # type: ignore
except ModuleNotFoundError:
    from cloudflare_worker.shared.storage_contracts import *  # type: ignore
