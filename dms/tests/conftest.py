"""
Pytest configuration for Enterprise DMS tests
"""
import os
import sys

# Disable config validation during tests to prevent SystemExit
os.environ['SKIP_CONFIG_VALIDATION'] = 'true'

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
