# API Documentation

## Base URL
- Development: `http://localhost:8000`
- Production: `https://yourdomain.com`

## Authentication

Most endpoints require JWT authentication. Include the token in the Authorization header:

```
Authorization: Bearer <your-jwt-token>
```

## Response Format

All API responses follow this format:

```json
{
  "success": true/false,
  "data": {},
  "error": "Error message (if success is false)"
}
```

## Endpoints

### Authentication

#### Login
```http
POST /api/auth/login
Content-Type: application/json

{
  "username": "admin",
  "password": "password"
}
```

**Response:**
```json
{
  "success": true,
  "access_token": "ACCESS_TOKEN_PLACEHOLDER",
  "refresh_token": "REFRESH_TOKEN_PLACEHOLDER",
  "user": {
    "id": 1,
    "username": "admin",
    "email": "admin@example.com",
    "role": "admin"
  }
}
```

#### Logout
```http
POST /api/auth/logout
Authorization: Bearer <token>
```

#### Get Current User
```http
GET /api/auth/me
Authorization: Bearer <token>
```

### Documents

#### List Documents
```http
GET /api/documents?page=1&limit=20&status=pending&category=Invoice
Authorization: Bearer <token>
```

**Response:**
```json
{
  "success": true,
  "items": [
    {
      "id": 1,
      "original_filename": "invoice.pdf",
      "category": "Invoice",
      "status": "pending",
      "function_type": "invoice",
      "quality_level": "excellent",
      "created_at": "2025-01-01T00:00:00Z"
    }
  ],
  "total": 100,
  "page": 1,
  "limit": 20
}
```

#### Upload Document
```http
POST /api/documents/upload
Authorization: Bearer <token>
Content-Type: multipart/form-data

file: <binary file>
```

**Response:**
```json
{
  "success": true,
  "document_id": 1,
  "message": "Document uploaded successfully"
}
```

#### Get Document Details
```http
GET /api/documents/{id}
Authorization: Bearer <token>
```

**Response:**
```json
{
  "success": true,
  "id": 1,
  "original_filename": "invoice.pdf",
  "category": "Invoice",
  "status": "pending",
  "function_type": "invoice",
  "function_confidence": 0.95,
  "quality_level": "excellent",
  "has_damage": false,
  "created_at": "2025-01-01T00:00:00Z",
  "extracted_metadata": {
    "amount": 5000,
    "vendor": "ABC Company"
  }
}
```

#### Delete Document
```http
DELETE /api/documents/{id}
Authorization: Bearer <token>
```

### Analysis

#### Detect Document Function
```http
POST /api/analysis/detect-function
Authorization: Bearer <token>
Content-Type: application/json

{
  "text": "Invoice No: INV-001 Total: $5000"
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "primary_function": "invoice",
    "confidence": 0.95,
    "detected_keywords": ["invoice", "total"],
    "all_functions": [
      {"function": "invoice", "confidence": 0.95}
    ]
  }
}
```

#### Detect Document Quality
```http
POST /api/analysis/detect-fracture
Authorization: Bearer <token>
Content-Type: application/json

{
  "text": "Document has fracture on page 3"
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "quality_level": "poor",
    "damage_detected": true,
    "damage_type": "fracture",
    "damage_severity": "medium",
    "recommended_actions": [
      "replace document",
      "contact sender"
    ]
  }
}
```

#### Comprehensive Analysis
```http
POST /api/analysis/comprehensive
Authorization: Bearer <token>
Content-Type: application/json

{
  "text": "Invoice No: INV-001 Total: $5000"
}
```

### Search

#### Advanced Search
```http
POST /api/search/advanced
Authorization: Bearer <token>
Content-Type: application/json

{
  "query": "find all invoices",
  "filters": {
    "category": "Invoice",
    "status": "approved",
    "date_from": "2025-01-01",
    "date_to": "2025-12-31"
  },
  "semantic": true,
  "natural_language": true
}
```

**Response:**
```json
{
  "success": true,
  "results": [
    {
      "id": 1,
      "filename": "invoice.pdf",
      "relevance_score": 0.95,
      "snippet": "Invoice No: INV-001 Total: $5000"
    }
  ],
  "total": 10,
  "method": "semantic"
}
```

#### Search Suggestions
```http
GET /api/search/suggestions?q=inv&limit=5
Authorization: Bearer <token>
```

### Document Versions

#### Create Version
```http
POST /api/versions/document/{document_id}
Authorization: Bearer <token>
Content-Type: application/json

{
  "comment": "Updated document"
}
```

**Response:**
```json
{
  "success": true,
  "version": {
    "id": "version-uuid",
    "version_number": 2,
    "comment": "Updated document",
    "created_at": "2025-01-01T00:00:00Z"
  }
}
```

#### Get Document Versions
```http
GET /api/versions/document/{document_id}
Authorization: Bearer <token>
```

**Response:**
```json
{
  "success": true,
  "document_id": 1,
  "total_versions": 3,
  "versions": [
    {
      "id": "version-uuid-1",
      "version_number": 1,
      "comment": "Initial version",
      "created_at": "2025-01-01T00:00:00Z"
    }
  ]
}
```

#### Rollback to Version
```http
POST /api/versions/document/{document_id}/rollback/{version_id}
Authorization: Bearer <token>
```

#### Compare Versions
```http
GET /api/versions/document/{document_id}/compare/{version_id_1}/{version_id_2}
Authorization: Bearer <token>
```

### Reports

#### Create Report Template
```http
POST /api/reports/templates
Authorization: Bearer <token>
Content-Type: application/json

{
  "name": "Document Activity Report",
  "description": "Report on document activity",
  "report_type": "document",
  "columns": [
    {"field": "id", "label": "ID"},
    {"field": "filename", "label": "Filename"}
  ],
  "filters": []
}
```

#### Get Report Templates
```http
GET /api/reports/templates
Authorization: Bearer <token>
```

#### Generate Report
```http
POST /api/reports/generate/{template_id}
Authorization: Bearer <token>
Content-Type: application/json

{
  "parameters": {
    "date_from": "2025-01-01",
    "date_to": "2025-12-31"
  }
}
```

#### Export Report
```http
POST /api/reports/export
Authorization: Bearer <token>
Content-Type: application/json

{
  "report_data": [...],
  "format": "csv"
}
```

### External Integrations

#### Create Integration
```http
POST /api/integrations
Authorization: Bearer <token>
Content-Type: application/json

{
  "name": "SAP Integration",
  "integration_type": "erp",
  "config": {
    "erp_type": "sap",
    "api_url": "https://sap.example.com/api",
    "api_key": "your-api-key"
  },
  "webhooks": []
}
```

#### Get Integrations
```http
GET /api/integrations
Authorization: Bearer <token>
```

#### Activate Integration
```http
POST /api/integrations/{integration_id}/activate
Authorization: Bearer <token>
```

#### Sync to ERP
```http
POST /api/integrations/{integration_id}/sync/erp
Authorization: Bearer <token>
Content-Type: application/json

{
  "document_data": {
    "id": 1,
    "function_type": "invoice",
    "extracted_metadata": {}
  }
}
```

#### Sync to CRM
```http
POST /api/integrations/{integration_id}/sync/crm
Authorization: Bearer <token>
Content-Type: application/json

{
  "document_data": {
    "id": 1,
    "function_type": "invoice",
    "extracted_metadata": {}
  }
}
```

### Rate Limiting

#### Check Rate Limit
```http
GET /api/rate-limit/check
Authorization: Bearer <token>
```

**Response:**
```json
{
  "allowed": true,
  "limit": 10000,
  "remaining": 9995
}
```

#### Get Usage Stats
```http
GET /api/rate-limit/usage
Authorization: Bearer <token>
```

**Response:**
```json
{
  "success": true,
  "user_id": 1,
  "date_from": "2025-01-01",
  "date_to": "2025-01-31",
  "total_requests": 1000,
  "successful_requests": 950,
  "failed_requests": 50,
  "success_rate": 0.95,
  "avg_response_time_ms": 150.5
}
```

### Real-time Updates

#### SSE Events
```http
GET /api/realtime/events
Authorization: Bearer <token>
Accept: text/event-stream
```

**Event Format:**
```
event: document_status_update
data: {"document_id": 1, "status": "approved"}

event: user_activity
data: {"user_id": 1, "activity": "uploaded_document"}
```

### Preview

#### Get Document Preview
```http
GET /api/preview/document/{document_id}
Authorization: Bearer <token>
```

#### Add Annotation
```http
POST /api/preview/document/{document_id}/annotations
Authorization: Bearer <token>
Content-Type: application/json

{
  "type": "highlight",
  "page": 1,
  "x": 100,
  "y": 200,
  "width": 50,
  "height": 20,
  "text": "Important note"
}
```

#### Get Annotations
```http
GET /api/preview/document/{document_id}/annotations
Authorization: Bearer <token>
```

### Workflow Automation

#### Create Workflow
```http
POST /api/workflows
Authorization: Bearer <token>
Content-Type: application/json

{
  "name": "Invoice Approval Workflow",
  "description": "Workflow for invoice approval",
  "document_type": "invoice",
  "steps": [
    {
      "name": "Manager Approval",
      "type": "approval",
      "assigned_to": [2, 3],
      "order": 1
    }
  ]
}
```

#### Start Workflow
```http
POST /api/workflows/{workflow_id}/start
Authorization: Bearer <token>
Content-Type: application/json

{
  "document_id": 1,
  "initial_data": {}
}
```

#### Complete Workflow Step
```http
POST /api/workflows/instances/{instance_id}/steps/{step_id}/complete
Authorization: Bearer <token>
Content-Type: application/json

{
  "result": {
    "approved": true,
    "comment": "Approved"
  }
}
```

### Monitoring

#### Prometheus Metrics
```http
GET /metrics
```

**Available Metrics:**
- `http_requests_total` - Total HTTP requests
- `http_request_duration_seconds` - Request duration
- `documents_total` - Total documents processed
- `ocr_operations_total` - OCR operations
- `function_detection_operations_total` - Function detection operations
- `errors_total` - Total errors
- `cpu_usage_percent` - CPU usage
- `memory_usage_bytes` - Memory usage

## Error Codes

| Code | Description |
|------|-------------|
| 200 | Success |
| 201 | Created |
| 400 | Bad Request |
| 401 | Unauthorized |
| 403 | Forbidden |
| 404 | Not Found |
| 429 | Too Many Requests (Rate Limit) |
| 500 | Internal Server Error |

## Rate Limiting

Default rate limits:
- Staff: 60 requests/minute, 1000 requests/hour, 10000 requests/day
- Admin: 120 requests/minute, 2000 requests/hour, 20000 requests/day

Rate limit headers:
```
X-RateLimit-Limit: 10000
X-RateLimit-Remaining: 9995
X-RateLimit-Reset: 1640995200
```

## Pagination

Most list endpoints support pagination:
- `page` - Page number (default: 1)
- `limit` - Items per page (default: 20, max: 100)

## Filtering

Most list endpoints support filtering:
- `status` - Filter by status
- `category` - Filter by category
- `date_from` - Filter by date range (start)
- `date_to` - Filter by date range (end)

## Sorting

Most list endpoints support sorting:
- `sort_by` - Field to sort by
- `sort_order` - Sort order (asc/desc)

## Webhooks

Webhook payload format:
```json
{
  "event": "document.uploaded",
  "timestamp": "2025-01-01T00:00:00Z",
  "data": {
    "document_id": 1,
    "filename": "invoice.pdf"
  }
}
```

## SDKs

### Python SDK
```python
from dms_client import DMSClient

client = DMSClient(
    base_url="http://localhost:8000",
    api_key="your-api-key"
)

# Upload document
document = client.upload_document("invoice.pdf")

# Search documents
results = client.search_documents("invoice")
```

### JavaScript SDK
```javascript
import { DMSClient } from '@enterprise-ai/dms-sdk';

const client = new DMSClient({
  baseUrl: 'http://localhost:8000',
  apiKey: 'your-api-key'
});

// Upload document
const document = await client.uploadDocument('invoice.pdf');

// Search documents
const results = await client.searchDocuments('invoice');
```

## Support

For API support:
- Documentation: https://docs.yourdomain.com
- Email: api-support@yourdomain.com
- Status Page: https://status.yourdomain.com