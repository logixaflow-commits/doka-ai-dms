# Retained Legacy Enterprise-Era Tests

This directory contains the retained Enterprise-era backend tests. They are not included
in the current automatic CI test discovery: `web-platform/backend/pytest.ini` selects
`../tests`, and the automatic workflow runs pytest from `web-platform/backend` without
overriding those configured test paths. The current Personal Local regression suite is
in `web-platform/tests/`.

## Overview
Historical Enterprise test suite notes: unit, integration, and end-to-end tests.

## Test Structure

### Unit Tests (`tests/test_services.py`)
- Function Detection Service tests
- Fracture Detection Service tests
- Document Versioning Service tests
- Advanced Search Service tests
- Rate Limiting Service tests
- Database Model tests

### Integration Tests (`tests/test_api_integration.py`)
- Authentication API tests
- Documents API tests
- Analysis API tests
- Versioning API tests
- Reporting API tests
- Rate Limiting API tests

### E2E Tests (`tests/test_e2e.py`)
- Document Upload Workflow
- Function Detection Workflow
- Document Approval Workflow
- User Management Workflow
- Search Workflow
- Real-time Updates Workflow
- Document Versioning Workflow
- Reporting Workflow

## Running Tests

### Install Test Dependencies
```bash
pip install -r requirements-test.txt
```

### Run All Tests
```bash
pytest
```

### Run Specific Test Types
```bash
# Unit tests only
pytest -m unit

# Integration tests only
pytest -m integration

# E2E tests only
pytest -m e2e

# With coverage
pytest --cov=app --cov-report=html
```

### Run Specific Test File
```bash
pytest tests/test_services.py
pytest tests/test_api_integration.py
pytest tests/test_e2e.py
```

## Test Coverage

Current test coverage targets:
- Unit tests: 70%+ code coverage
- Integration tests: API endpoints
- E2E tests: Critical user workflows

## Test Fixtures

- `mock_settings`: Mock settings for testing
- `test_db`: Test database session
- `app`: FastAPI app instance
- `client`: Test client
- `test_user`: Test user fixture
- `test_admin`: Test admin fixture
- `auth_token`: Authentication token fixture

## Test Data

Test fixtures should be placed in `tests/fixtures/`:
- `test_document.pdf` - Sample document for testing
- `invoice.pdf` - Sample invoice for function detection
- `sample_image.png` - Sample image for OCR testing

## Continuous Integration

These tests are designed to run in CI/CD pipelines:
- GitHub Actions
- GitLab CI
- Jenkins
- CircleCI

## Notes

- E2E tests require the application to be running on localhost:3000
- Integration tests use in-memory SQLite database
- Unit tests use mocking for external dependencies
- All tests are designed to be independent and idempotent