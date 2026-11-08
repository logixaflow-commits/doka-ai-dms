import os
import sys
from pathlib import Path

# Add cloudflare_worker helper directory to sys.path so tests can import worker modules
_worker_dir = Path(__file__).resolve().parent.parent / 'backend' / 'cloudflare_worker'
if str(_worker_dir) not in sys.path:
    sys.path.insert(0, str(_worker_dir))

from pathlib import Path

import pytest


@pytest.fixture
def make_symlink():
    def _make_symlink(
        link: Path,
        target: Path,
        *,
        target_is_directory: bool = False,
    ) -> None:
        try:
            link.symlink_to(target, target_is_directory=target_is_directory)
        except NotImplementedError:
            pytest.skip("Symlinks are unavailable; verify this case on Linux CI.")
        except OSError as exc:
            if (
                os.name == "nt"
                and getattr(exc, "winerror", None) == 1314
            ):
                pytest.skip(
                    "Windows symlink privilege is unavailable; enable Developer "
                    "Mode or verify this case on Linux CI."
                )
            raise

    return _make_symlink
