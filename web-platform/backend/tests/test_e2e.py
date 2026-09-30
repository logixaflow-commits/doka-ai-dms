"""
End-to-End Tests for Enterprise AI DMS
Tests for complete user workflows using Playwright
"""
import pytest
from playwright.sync_api import sync_playwright
import json
import time
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.mark.e2e
class TestDocumentUploadWorkflow:
    """Test complete document upload workflow"""
    
    def test_complete_upload_workflow(self):
        """Test complete document upload and processing workflow"""
        with sync_playwright() as p:
            # Launch browser
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            
            try:
                # Navigate to application
                page.goto("http://localhost:3000")
                
                # Login
                page.fill('input[name="username"]', "admin")
                page.fill('input[name="password"]', "admin123")
                page.click('button[type="submit"]')
                
                # Wait for dashboard
                page.wait_for_selector('text=Document Management')
                
                # Navigate to upload page
                page.click('text=Upload Document')
                
                # Upload file
                page.set_input_files('input[type="file"]', "tests/fixtures/test_document.pdf")
                
                # Click upload button
                page.click('button:has-text("Upload")')
                
                # Wait for upload completion
                page.wait_for_selector('text=Document uploaded successfully', timeout=10000)
                
                # Verify document appears in list
                page.goto("http://localhost:3000/documents")
                page.wait_for_selector('text=test_document.pdf')
                
                # Verify processing status
                assert page.text_locator('text=test_document.pdf').is_visible()
                
            finally:
                browser.close()
    
    def test_function_detection_workflow(self):
        """Test function detection workflow"""
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            
            try:
                # Login
                page.goto("http://localhost:3000")
                page.fill('input[name="username"]', "admin")
                page.fill('input[name="password"]', "admin123")
                page.click('button[type="submit"]')
                
                # Upload invoice document
                page.click('text=Upload Document')
                page.set_input_files('input[type="file"]', "tests/fixtures/invoice.pdf")
                page.click('button:has-text("Upload")')
                
                # Wait for upload
                page.wait_for_selector('text=Document uploaded successfully', timeout=10000)
                
                # Navigate to documents
                page.goto("http://localhost:3000/documents")
                
                # Check for function type in document list
                page.wait_for_selector('text=invoice', timeout=15000)
                
                # Verify function detection worked
                assert page.text_locator('text=invoice').is_visible()
                
            finally:
                browser.close()
    
    def test_document_approval_workflow(self):
        """Test document approval workflow"""
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            
            try:
                # Login as admin
                page.goto("http://localhost:3000")
                page.fill('input[name="username"]', "admin")
                page.fill('input[name="password"]', "admin123")
                page.click('button[type="submit"]')
                
                # Navigate to documents
                page.goto("http://localhost:3000/documents")
                
                # Select pending document
                page.click('button:has-text("Approve")')
                
                # Fill approval form
                page.fill('input[name="target_folder"]', "/Approved/Invoices")
                page.click('button:has-text("Submit")')
                
                # Verify document status changed
                page.wait_for_selector('text=approved', timeout=5000)
                
                # Verify document moved to approved folder
                assert page.text_locator('text=approved').is_visible()
                
            finally:
                browser.close()


@pytest.mark.e2e
class TestUserManagementWorkflow:
    """Test user management workflow"""
    
    def test_create_user_workflow(self):
        """Test creating new user workflow"""
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            
            try:
                # Login as admin
                page.goto("http://localhost:3000")
                page.fill('input[name="username"]', "admin")
                page.fill('input[name="password"]', "admin123")
                page.click('button[type="submit"]')
                
                # Navigate to user management
                page.click('text=Users')
                page.click('text=Add User')
                
                # Fill user form
                page.fill('input[name="username"]', "newuser")
                page.fill('input[name="email"]', "newuser@example.com")
                page.fill('input[name="password"]', "newuser123")
                page.fill('input[name="full_name"]', "New User")
                page.select_option('select[name="role"]', "staff")
                
                # Submit form
                page.click('button:has-text("Create User")')
                
                # Verify user created
                page.wait_for_selector('text=newuser', timeout=5000)
                
                # Verify user appears in list
                assert page.text_locator('text=newuser').is_visible()
                
            finally:
                browser.close()
    
    def test_role_based_access_workflow(self):
        """Test role-based access control"""
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            
            try:
                # Login as staff user
                page.goto("http://localhost:3000")
                page.fill('input[name="username"]', "staff")
                page.fill('input[name="password"]', "staff123")
                page.click('button[type="submit"]')
                
                # Try to access admin-only page
                page.goto("http://localhost:3000/admin")
                
                # Should be denied access
                assert page.text_locator('text=Access Denied').is_visible() or \
                       page.text_locator('text=403').is_visible()
                
            finally:
                browser.close()


@pytest.mark.e2e
class TestSearchWorkflow:
    """Test search functionality workflow"""
    
    def test_basic_search_workflow(self):
        """Test basic document search"""
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            
            try:
                # Login
                page.goto("http://localhost:3000")
                page.fill('input[name="username"]', "admin")
                page.fill('input[name="password"]', "admin123")
                page.click('button[type="submit"]')
                
                # Navigate to documents
                page.goto("http://localhost:3000/documents")
                
                # Search for document
                page.fill('input[placeholder*="Search"]', "invoice")
                page.keyboard.press('Enter')
                
                # Wait for search results
                page.wait_for_selector('text=invoice', timeout=5000)
                
                # Verify search results
                assert page.text_locator('text=invoice').is_visible()
                
            finally:
                browser.close()
    
    def test_advanced_search_workflow(self):
        """Test advanced search with filters"""
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            
            try:
                # Login
                page.goto("http://localhost:3000")
                page.fill('input[name="username"]', "admin")
                page.fill('input[name="password"]', "admin123")
                page.click('button[type="submit"]')
                
                # Navigate to documents
                page.goto("http://localhost:3000/documents")
                
                # Click advanced search
                page.click('button:has-text("Advanced Search")')
                
                # Set filters
                page.select_option('select[name="category"]', "Invoice")
                page.select_option('select[name="status"]', "pending")
                
                # Apply search
                page.click('button:has-text("Search")')
                
                # Wait for results
                page.wait_for_selector('text=Invoice', timeout=5000)
                
                # Verify filtered results
                assert page.text_locator('text=Invoice').is_visible()
                
            finally:
                browser.close()


@pytest.mark.e2e
class TestRealtimeUpdatesWorkflow:
    """Test real-time updates workflow"""
    
    def test_realtime_document_updates(self):
        """Test real-time document status updates"""
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            
            try:
                # Login
                page.goto("http://localhost:3000")
                page.fill('input[name="username"]', "admin")
                page.fill('input[name="password"]', "admin123")
                page.click('button[type="submit"]')
                
                # Connect to SSE
                page.goto("http://localhost:3000/documents")
                
                # Upload document in one context
                context = browser.new_context()
                upload_page = context.new_page()
                upload_page.goto("http://localhost:3000/documents")
                upload_page.click('text=Upload Document')
                upload_page.set_input_files('input[type="file"]', "tests/fixtures/test.pdf")
                upload_page.click('button:has-text("Upload")')
                
                # Wait for real-time update on main page
                page.wait_for_selector('text=test.pdf', timeout=10000)
                
                # Verify document appeared without refresh
                assert page.text_locator('text=test.pdf').is_visible()
                
                context.close()
                
            finally:
                browser.close()


@pytest.mark.e2e
class TestDocumentVersioningWorkflow:
    """Test document versioning workflow"""
    
    def test_version_creation_workflow(self):
        """Test creating document versions"""
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            
            try:
                # Login
                page.goto("http://localhost:3000")
                page.fill('input[name="username"]', "admin")
                page.fill('input[name="password"]', "admin123")
                page.click('button[type="submit"]')
                
                # Navigate to documents
                page.goto("http://localhost:3000/documents")
                
                # Click on document
                page.click('text=test_document.pdf')
                
                # Click on versions tab
                page.click('text=Versions')
                
                # Create new version
                page.click('button:has-text("Create Version")')
                page.fill('textarea[name="comment"]', "New version for testing")
                page.click('button:has-text("Save")')
                
                # Verify version created
                page.wait_for_selector('text=New version for testing', timeout=5000)
                
                # Verify version appears in list
                assert page.text_locator('text=Version 2').is_visible()
                
            finally:
                browser.close()
    
    def test_version_rollback_workflow(self):
        """Test version rollback workflow"""
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            
            try:
                # Login
                page.goto("http://localhost:3000")
                page.fill('input[name="username"]', "admin")
                page.fill('input[name="password"]', "admin123")
                page.click('button[type="submit"]')
                
                # Navigate to document versions
                page.goto("http://localhost:3000/documents")
                page.click('text=test_document.pdf')
                page.click('text=Versions')
                
                # Click rollback button
                page.click('button:has-text("Rollback")')
                
                # Confirm rollback
                page.click('button:has-text("Confirm")')
                
                # Verify rollback success
                page.wait_for_selector('text=Rollback successful', timeout=5000)
                
                # Verify version updated
                assert page.text_locator('text=Rollback successful').is_visible()
                
            finally:
                browser.close()


@pytest.mark.e2e
class TestReportingWorkflow:
    """Test reporting workflow"""
    
    def test_report_generation_workflow(self):
        """Test report generation and export"""
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            
            try:
                # Login
                page.goto("http://localhost:3000")
                page.fill('input[name="username"]', "admin")
                page.fill('input[name="password"]', "admin123")
                page.click('button[type="submit"]')
                
                # Navigate to reports
                page.click('text=Reports')
                
                # Click create report
                page.click('button:has-text("Create Report")')
                
                # Select report type
                page.select_option('select[name="report_type"]', "document")
                
                # Set report parameters
                page.fill('input[name="name"]', "Document Activity Report")
                page.click('button:has-text("Generate")')
                
                # Wait for report generation
                page.wait_for_selector('text=Report generated', timeout=10000)
                
                # Export report
                page.click('button:has-text("Export")')
                page.select_option('select[name="format"]', "csv")
                page.click('button:has-text("Download")')
                
                # Verify download started
                assert page.text_locator('text=Download started').is_visible()
                
            finally:
                browser.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "e2e"])