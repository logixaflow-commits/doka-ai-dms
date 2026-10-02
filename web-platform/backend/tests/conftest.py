"""
Pytest configuration for Enterprise DMS tests
"""
import os
import sys

# Use a strong deterministic test key so HS256 minimum-length validation remains active.
os.environ.setdefault('SECRET_KEY', 'doka-test-secret-key-with-more-than-32-bytes')

# Disable optional external config validation during tests.
os.environ['SKIP_CONFIG_VALIDATION'] = 'true'

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
