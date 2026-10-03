import os
import stat

import pytest

from app.core import config as config_module
from app.core import local_security


@pytest.mark.skipif(os.name != "posix", reason="POSIX file mode assertions are not portable")
def test_local_auth_state_database_is_owner_only(tmp_path, monkeypatch):
    state_path = tmp_path / "private" / "local_auth_state.sqlite3"
    monkeypatch.setattr(config_module.settings, "LOCAL_AUTH_STATE_PATH", state_path)
    monkeypatch.setattr(config_module.settings, "WORKING_ROOT", tmp_path / "workspace")
    monkeypatch.setattr(config_module.settings, "SOURCE_ROOT", tmp_path / "source")

    connection = local_security._connect_token_state()
    connection.close()

    mode = stat.S_IMODE(state_path.stat().st_mode)
    assert mode & 0o077 == 0
    assert mode & 0o600 == 0o600
