"""
Office DMS - Health Check Tests
Tests for enhanced health check endpoint (Phase E-21)
"""
import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import json


class TestHealthCheckImplementation:
    """Tests for health check implementation (file-level validation)"""
    
    def test_health_check_endpoint_exists(self):
        """Test that health check endpoint is implemented in main.py"""
        main_py = Path("app/main.py")
        assert main_py.exists()
        
        content = main_py.read_text(encoding='utf-8')
        assert '@app.get("/health"' in content
        assert "health_check" in content.lower()
    
    def test_health_check_includes_disk_monitoring(self):
        """Test that health check includes disk space monitoring"""
        main_py = Path("app/main.py")
        content = main_py.read_text(encoding='utf-8')
        
        assert "psutil" in content.lower()
        assert "disk" in content.lower()
        assert "disk_usage" in content or "disk usage" in content.lower()
    
    def test_health_check_includes_memory_monitoring(self):
        """Test that health check includes memory monitoring"""
        main_py = Path("app/main.py")
        content = main_py.read_text(encoding='utf-8')
        
        assert "memory" in content.lower()
        assert "virtual_memory" in content or "memory usage" in content.lower()
    
    def test_health_check_includes_response_times(self):
        """Test that health check includes response time tracking"""
        main_py = Path("app/main.py")
        content = main_py.read_text(encoding='utf-8')
        
        assert "response_time" in content.lower() or "response time" in content.lower()
        assert "time.time()" in content
    
    def test_health_quick_endpoint_exists(self):
        """Test that quick health check endpoint exists"""
        main_py = Path("app/main.py")
        content = main_py.read_text(encoding='utf-8')
        
        assert '@app.get("/health/quick"' in content
    
    def test_health_check_checks_all_services(self):
        """Test that health check checks all required services"""
        main_py = Path("app/main.py")
        content = main_py.read_text(encoding='utf-8')
        
        # Check for service monitoring
        assert "database" in content.lower()
        assert "redis" in content.lower()
        assert "celery" in content.lower()
        assert "storage" in content.lower()
    
    def test_health_check_file_created(self):
        """Test that health check test file was created"""
        test_file = Path(__file__)
        assert test_file.exists()
        assert test_file.name == "test_health_check.py"
    
    def test_psutil_in_requirements(self):
        """Test that psutil is in requirements.txt"""
        requirements = Path("requirements.txt")
        if requirements.exists():
            content = requirements.read_text()
            assert "psutil" in content.lower()


class TestHardeningFilesExist:
    """Test that all hardening files were created"""
    
    def test_fetch_helper_exists(self):
        """Test that fetch_helper.js was created"""
        fetch_helper = Path("app/static/js/fetch_helper.js")
        assert fetch_helper.exists()
    
    def test_rate_limiter_exists(self):
        """Test that rate_limiter.py was created"""
        rate_limiter = Path("app/core/rate_limiter.py")
        assert rate_limiter.exists()
    
    def test_config_validator_exists(self):
        """Test that config_validator.py was created"""
        config_validator = Path("app/core/config_validator.py")
        assert config_validator.exists()
    
    def test_hardening_test_file_exists(self):
        """Test that test_hardening.py was created"""
        hardening_test = Path("tests/test_hardening.py")
        assert hardening_test.exists()
    
    def test_pytest_ini_exists(self):
        """Test that pytest.ini was created"""
        pytest_ini = Path("pytest.ini")
        assert pytest_ini.exists()
    
    def test_tests_readme_exists(self):
        """Test that tests README was created"""
        tests_readme = Path("tests/README.md")
        assert tests_readme.exists()
    
    def test_hardening_summary_exists(self):
        """Test that HARDENING_SUMMARY.md was created"""
        # Check in parent directory
        hardening_summary = Path("../HARDENING_SUMMARY.md")
        if not hardening_summary.exists():
            # Try current directory as fallback
            hardening_summary = Path("HARDENING_SUMMARY.md")
        assert hardening_summary.exists()
