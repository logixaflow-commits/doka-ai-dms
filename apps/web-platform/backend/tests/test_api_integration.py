"""
Integration Tests for Enterprise AI DMS
Tests for API endpoints and database interactions
"""
import pytest
import json
from fastapi.testclient import TestClient
from datetime import datetime
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.main import create_app
from app.core.database import SessionLocal, Base, engine
from app.models.database import User, Document
from app.core.security import get_password_hash


@pytest.fixture
def app():
    """Create FastAPI app for testing"""
    app = create_app()
    return app


@pytest.fixture
def client(app):
    """Create test client"""
    return TestClient(app)


@pytest.fixture
def db_session():
    """Create database session for testing"""
    # Create tables
    Base.metadata.create_all(bind=engine)
    
    session = SessionLocal()
    
    yield session
    
    session.close()
    # Drop tables
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def test_user(db_session):
    """Create test user"""
    user = User(
        username="testuser",
        email="test@example.com",
        password_hash=get_password_hash("testpass123"),
        role="staff",
        is_active=True
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def test_admin(db_session):
    """Create test admin user"""
    admin = User(
        username="admin",
        email="admin@example.com",
        password_hash=get_password_hash("admin123"),
        role="admin",
        is_active=True
    )
    db_session.add(admin)
    db_session.commit()
    db_session.refresh(admin)
    return admin


@pytest.fixture
def auth_token(client, test_user):
    """Get authentication token"""
    response = client.post("/api/auth/login", json={
        "username": "testuser",
        "password": "testpass123"
    })
    
    assert response.status_code == 200
    data = response.json()
    return data["access_token"]


@pytest.mark.integration
class TestAuthenticationAPI:
    """Test authentication API endpoints"""
    
    def test_login_success(self, client, test_user):
        """Test successful login"""
        response = client.post("/api/auth/login", json={
            "username": "testuser",
            "password": "testpass123"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert "user" in data
    
    def test_login_invalid_credentials(self, client):
        """Test login with invalid credentials"""
        response = client.post("/api/auth/login", json={
            "username": "wronguser",
            "password": "wrongpass"
        })
        
        assert response.status_code == 401
    
    def test_get_current_user(self, client, auth_token):
        """Test getting current user"""
        response = client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "username" in data
        assert data["username"] == "testuser"


@pytest.mark.integration
class TestDocumentsAPI:
    """Test documents API endpoints"""
    
    def test_list_documents(self, client, auth_token):
        """Test listing documents"""
        response = client.get(
            "/api/documents",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
    
    def test_upload_document(self, client, auth_token, test_user):
        """Test document upload"""
        # Create test file
        from io import BytesIO
        
        file_content = b"Test document content"
        file_data = BytesIO(file_content)
        
        response = client.post(
            "/api/documents/upload",
            headers={"Authorization": f"Bearer {auth_token}"},
            files={"file": ("test.txt", file_data, "text/plain")}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "document_id" in data
    
    def test_get_document(self, client, auth_token, db_session, test_user):
        """Test getting specific document"""
        # Create test document
        doc = Document(
            original_filename="test.pdf",
            stored_filename="stored_test.pdf",
            storage_key="test_key",
            file_hash="abc123",
            file_size=1024,
            mime_type="application/pdf",
            status="pending",
            uploaded_by=test_user.id
        )
        db_session.add(doc)
        db_session.commit()
        db_session.refresh(doc)
        
        response = client.get(
            f"/api/documents/{doc.id}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == doc.id
    
    def test_delete_document(self, client, auth_token, db_session, test_admin):
        """Test document deletion (admin only)"""
        # Create test document
        doc = Document(
            original_filename="test.pdf",
            stored_filename="stored_test.pdf",
            storage_key="test_key",
            file_hash="abc123",
            file_size=1024,
            mime_type="application/pdf",
            status="pending",
            uploaded_by=test_admin.id
        )
        db_session.add(doc)
        db_session.commit()
        db_session.refresh(doc)
        
        # Get admin token
        auth_response = client.post("/api/auth/login", json={
            "username": "admin",
            "password": "admin123"
        })
        admin_token = auth_response.json()["access_token"]
        
        response = client.delete(
            f"/api/documents/{doc.id}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        assert response.status_code == 200


@pytest.mark.integration
class TestAnalysisAPI:
    """Test analysis API endpoints"""
    
    def test_detect_function(self, client, auth_token):
        """Test function detection"""
        response = client.post(
            "/api/analysis/detect-function",
            headers={"Authorization": f"Bearer {auth_token}"},
            data={"text": "Invoice No: INV-001 Total: $5000"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        assert "primary_function" in data["data"]
    
    def test_detect_fracture(self, client, auth_token):
        """Test fracture detection"""
        response = client.post(
            "/api/analysis/detect-fracture",
            headers={"Authorization": f"Bearer {auth_token}"},
            data={"text": "Document has fracture on page 3"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        assert "quality_level" in data["data"]
    
    def test_get_supported_functions(self, client, auth_token):
        """Test getting supported functions"""
        response = client.get(
            "/api/analysis/functions",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "functions" in data["data"]
        assert len(data["data"]["functions"]) > 0


@pytest.mark.integration
class TestVersioningAPI:
    """Test document versioning API endpoints"""
    
    def test_create_version(self, client, auth_token, db_session, test_user):
        """Test creating document version"""
        # Create test document
        doc = Document(
            original_filename="test.pdf",
            stored_filename="stored_test.pdf",
            storage_key="test_key",
            file_hash="abc123",
            file_size=1024,
            mime_type="application/pdf",
            status="pending",
            uploaded_by=test_user.id
        )
        db_session.add(doc)
        db_session.commit()
        db_session.refresh(doc)
        
        response = client.post(
            f"/api/versions/document/{doc.id}",
            headers={"Authorization": f"Bearer {auth_token}"},
            data={"comment": "Test version"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
    
    def test_get_document_versions(self, client, auth_token, db_session, test_user):
        """Test getting document versions"""
        # Create test document
        doc = Document(
            original_filename="test.pdf",
            stored_filename="stored_test.pdf",
            storage_key="test_key",
            file_hash="abc123",
            file_size=1024,
            mime_type="application/pdf",
            status="pending",
            uploaded_by=test_user.id
        )
        db_session.add(doc)
        db_session.commit()
        db_session.refresh(doc)
        
        response = client.get(
            f"/api/versions/document/{doc.id}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "success" == True
        assert "total_versions" in data


@pytest.mark.integration
class TestReportingAPI:
    """Test advanced reporting API endpoints"""
    
    def test_create_report_template(self, client, auth_token):
        """Test creating report template"""
        response = client.post(
            "/api/reports/templates",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={
                "name": "Test Report",
                "description": "Test report template",
                "report_type": "document",
                "columns": [
                    {"field": "id", "label": "ID"},
                    {"field": "filename", "label": "Filename"}
                ],
                "filters": []
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
    
    def test_get_report_templates(self, client, auth_token):
        """Test getting report templates"""
        response = client.get(
            "/api/reports/templates",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "templates" in data


@pytest.mark.integration
class TestRateLimitingAPI:
    """Test rate limiting API endpoints"""
    
    def test_check_rate_limit(self, client, auth_token):
        """Test checking rate limit"""
        response = client.get(
            "/api/rate-limit/check",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "allowed" in data
    
    def test_get_usage_stats(self, client, auth_token):
        """Test getting usage statistics"""
        response = client.get(
            "/api/rate-limit/usage",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "success" in data


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "integration"])