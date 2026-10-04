"""
Pytest configuration for Enterprise DMS tests
"""
import atexit
import os
import tempfile
import sys
from pathlib import Path

# Keep Personal Local tests isolated from Office_DMS and any configured cloud
# services. The temporary directory is removed when the test process exits.
_test_runtime = tempfile.TemporaryDirectory(prefix="doka-local-tests-")
atexit.register(_test_runtime.cleanup)
_test_root = Path(_test_runtime.name)
(_test_root / "source").mkdir()

# Use a strong deterministic test key so HS256 minimum-length validation remains active.
os.environ['SECRET_KEY'] = 'doka-test-secret-key-with-more-than-32-bytes'

# Disable optional external config validation during tests.
os.environ['SKIP_CONFIG_VALIDATION'] = 'true'
os.environ.update({
    "ENVIRONMENT": "test",
    "DEBUG": "false",
    "DATABASE_URL": "sqlite://",
    "SOURCE_ROOT": str(_test_root / "source"),
    "WORKING_ROOT": str(_test_root / "workspace"),
    "FINAL_ROOT": str(_test_root / "workspace" / "Final"),
    "QUARANTINE_ROOT": str(_test_root / "workspace" / "Quarantine"),
    "BACKUP_ROOT": str(_test_root / "backups"),
    "LOCAL_AUTH_STATE_PATH": str(_test_root / "local_auth_state.sqlite3"),
    "WATCH_FOLDER": str(_test_root / "workspace" / "Watch_Folder"),
    "PROCESSING_WORKSPACE": str(_test_root / "workspace" / "Processing_Workspace"),
    "ORGANIZED_ROOT": str(_test_root / "workspace" / "Final"),
    "DUPLICATE_FOLDER": str(_test_root / "workspace" / "Duplicates"),
    "SUSPICIOUS_FOLDER": str(_test_root / "workspace" / "Quarantine" / "Suspicious"),
    "LOG_DIR": str(_test_root / "logs"),
    "SUPABASE_URL": "",
    "SUPABASE_PUBLISHABLE_KEY": "",
    "BOOTSTRAP_ADMIN_PASSWORD": "",
    "CORS_ORIGINS": "http://localhost:3000,http://localhost:5173,http://localhost:8000",
})

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
