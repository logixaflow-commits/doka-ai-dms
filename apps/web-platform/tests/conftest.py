import os
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
