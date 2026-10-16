# Enterprise AI Document Management System - Frontend Code Documentation
## Complete System with Phase 1, Phase 2, Phase 3, and Phase 4

---

## 📋 Table of Contents

1. [Project Structure](#project-structure)
2. [Technology Stack](#technology-stack)
3. [Template Structure](#template-structure)
4. [JavaScript Structure](#javascript-structure)
5. [PWA Components](#pwa-components)
6. [API Integration](#api-integration)
7. [Phase Features Summary](#phase-features-summary)

---

## 🏗️ Project Structure

```
app/
├── templates/                          # Jinja2 HTML templates
│   ├── base.html                      # Base template with sidebar
│   ├── login.html                     # Login page
│   ├── dashboard.html                  # Dashboard with analytics
│   ├── pending.html                   # Pending documents
│   ├── document_detail.html           # Document detail view
│   ├── search.html                    # Search with semantic toggle
│   ├── sop.html                       # SOP tracker
│   ├── reminders.html                 # Reminders management
│   ├── audit.html                     # Audit log (admin)
│   ├── settings.html                  # User settings with 2FA (Phase 2)
│   ├── 2fa_verify.html                # 2FA verification (Phase 2)
│   ├── admin_folder_permissions.html  # Folder permissions UI (Phase 2)
│   ├── reports.html                   # Reports page (Phase 2)
│   ├── admin_rules.html              # Rule builder UI (Phase 3)
│   └── template_library.html          # Template library (Phase 3)
└── static/                             # Static assets
    ├── css/                            # Stylesheets
    ├── js/                             # JavaScript files
    │   ├── main.js                     # Main application logic
    │   ├── 2fa.js                      # 2FA frontend (Phase 2)
    │   ├── permissions.js              # Permissions frontend (Phase 2)
    │   ├── reports.js                  # Reports frontend (Phase 2)
    │   ├── rules.js                    # Rules frontend (Phase 3)
    │   ├── templates.js                # Templates frontend (Phase 3)
    │   └── tags.js                     # Tags frontend (Phase 3)
    ├── icons/                          # Icons and images
    ├── manifest.json                   # PWA manifest (Phase 4)
    ├── sw.js                          # Service worker (Phase 4)
    └── offline.html                    # Offline fallback (Phase 4)
```

---

## ⚙️ Technology Stack

### Core Framework
- **Jinja2 Templates** - Server-side HTML rendering with FastAPI
- **Vanilla JavaScript (ES6+)** - Client-side interactivity
- **Fetch API** - HTTP requests to backend
- **WebSocket/SSE** - Real-time updates

### UI Framework
- **Tailwind CSS 3.4.19** - Utility-first CSS framework
- **Custom CSS** - Additional styling for specific components

### PWA Features (Phase 4)
- **Service Worker** - Offline caching and sync
- **Web App Manifest** - Installable PWA
- **Background Sync API** - Offline operation

---

## 📄 Template Structure

### Base Template (`templates/base.html`)
- Sidebar navigation
- User dropdown with profile
- Responsive layout
- Flash message handling
- PWA meta tags

### Authentication Templates

#### Login (`templates/login.html`)
- Username/password form
- Remember me option
- 2FA redirect support
- Error handling

### Dashboard Templates

#### Dashboard (`templates/dashboard.html`)
- Statistics cards (total docs, pending, approved, rejected)
- Urgent documents section (Phase 3)
- Recent activity (Phase 1)
- Recent rules triggered (Phase 3)
- System health widget (Phase 4)
- Quick action buttons
- SSE for real-time updates

### Document Management Templates

#### Pending Documents (`templates/pending.html`)
- Pending documents list with pagination
- Bulk approve/reject buttons
- Category filters
- Confidence display
- Quick approve/reject per document

#### Document Detail (`templates/document_detail.html`)
- Document information display
- OCR text viewer
- Metadata display
- Category and confidence
- Tags display (Phase 3)
- Urgency badge (Phase 3)
- Version history tab (Phase 4)
- Approval/rejection actions
- Document locking status
- Download and preview buttons

#### Search (`templates/search.html`)
- Search form with filters
- Semantic search toggle (Phase 3)
- Myanmar language support
- Category, status, date filters
- Search results with highlighting
- Tag filter chips (Phase 3)

### SOP Templates

#### SOP Tracker (`templates/sop.html`)
- SOP instances list
- Progress bars
- Step details
- Complete SOP button
- Due date display

#### Reminders (`templates/reminders.html`)
- Reminders list
- Create reminder form
- Priority indicators
- Dismiss action
- Due date display

### Admin Templates

#### Audit Log (`templates/audit.html`)
- Audit trail table
- User filter
- Action filter
- Date range filter
- Pagination

### Phase 2 Templates

#### Settings with 2FA (`templates/settings.html`)
- Profile information
- Change password
- 2FA enable/disable section
- QR code display (for 2FA setup)
- OTP verification
- Backup codes display
- Account information

#### 2FA Verification (`templates/2fa_verify.html`)
- OTP input form (6-digit)
- Auto-focus on load
- Lockout message display
- Retry mechanism
- Error handling

#### Folder Permissions UI (`templates/admin_folder_permissions.html`)
- Permissions overview
- Permission table with filters
- Assign permission modal
- User selection
- Folder selection
- Permission level selection (read, write, admin)
- Initialize default permissions button

#### Reports Page (`templates/reports.html`)
- Report type selection (access log, activity, user activity, custom)
- Date range picker
- User filter dropdown
- Document type filter
- Action filter
- Format selection (Excel, PDF, JSON)
- Generate button with progress tracking
- Recent reports list
- Report statistics dashboard
- Schedule report modal
- Download report button

### Phase 3 Templates

#### Rule Builder UI (`templates/admin_rules.html`)
- Rule list with enable/disable toggles
- Create rule modal with condition builder
- Action selector (set_tag, set_folder, send_email, create_reminder, etc.)
- Test button with document preview
- Execution logs viewer
- Priority sorting
- Rule statistics

#### Template Library (`templates/admin_folder_permissions.html`)
- Template category tabs
- Template cards with descriptions
- Template details view
- Steps display with assignees
- "Use Template" button
- Download as YAML button
- Import custom template button

---

## 💻 JavaScript Structure

### Core JavaScript (`static/js/main.js`)
- Authentication token handling
- API request helper functions
- Flash message display
- Modal handling
- Form submission handling
- Real-time SSE updates for dashboard
- Document approval/rejection functions
- Search functionality

### Phase 2 JavaScript Files

#### 2FA Frontend (`static/js/2fa.js`)
- Initialize 2FA setup
- Generate QR code
- Verify OTP during setup
- Enable/disable 2FA
- Regenerate backup codes
- Display backup codes

#### Permissions Frontend (`static/js/permissions.js`)
- Load and display permissions
- Assign folder permissions
- Remove folder permissions
- Initialize default permissions
- User and folder selection
- Permission level selection

#### Reports Frontend (`static/js/reports.js`)
- Report generation (sync and async)
- Status polling for async reports
- Report download handling
- Scheduled report configuration
- Report statistics loading
- Custom filters for reports
- Report cleanup functionality

### Phase 3 JavaScript Files

#### Rules Frontend (`static/js/rules.js`)
- Create rule with condition builder
- Define rule conditions (field, operator, value)
- Define rule actions (type, parameters)
- Test rule against documents
- Enable/disable rules
- View rule execution logs
- Rule priority management

#### Templates Frontend (`static/js/templates.js`)
- Load template library
- Display templates by category
- Instantiate template as SOP
- Export template as YAML
- Import custom template
- View template steps and details

#### Tags Frontend (`static/js/tags.js`)
- Generate tags for document
- View document tags
- Regenerate tags
- Search by tag
- Tag cloud display
- Urgent documents filter

---

## 📱 PWA Components (Phase 4)

### PWA Manifest (`static/manifest.json`)
```json
{
  "name": "Enterprise DMS",
  "short_name": "DMS",
  "description": "Enterprise Document Management System",
  "start_url": "/dashboard",
  "display": "standalone",
  "theme_color": "#2563eb",
  "background_color": "#ffffff",
  "icons": [
    { "src": "/static/icons/icon-192x192.png", "sizes": "192x192", "type": "image/png" },
    { "src": "/static/icons/icon-512x512.png", "sizes": "512x512", "type": "image/png" }
  ],
  "categories": ["business", "productivity"]
}
```

### Service Worker (`static/sw.js`)
- Cache static assets on install
- Network-first for API requests
- Cache-first for static assets
- Offline fallback for navigation
- Background sync for uploads
- Push notification support
- Automatic cache cleanup

### Offline Fallback (`static/offline.html`)
- Beautiful gradient background
- Animated status icon
- Connection status display
- Auto-retry functionality
- Online/offline event handling

### PWA Service (`app/services/pwa_service.py`)
- Generate manifest.json dynamically
- Generate service worker code
- Define cache strategy
- Provide offline fallback HTML

---

## 🔌 API Integration

### Authentication API Calls

#### Login
```javascript
POST /api/auth/login
Body: { username, password }
Response: { access_token, refresh_token, user }
```

#### Token Refresh
```javascript
POST /api/auth/refresh
Headers: { Authorization: "Bearer <refresh_token>" }
Response: { access_token }
```

### Document API Calls

#### Upload Document
```javascript
POST /api/documents/upload
Body: FormData with file
Headers: { Authorization: "Bearer <token>" }
Response: { document_id, status, message }
```

#### Get Documents
```javascript
GET /api/documents?page=1&limit=20&category=Invoice
Headers: { Authorization: "Bearer <token>" }
Response: { documents: [], total, page, pages }
```

#### Approve Document
```javascript
POST /api/documents/{id}/approve
Headers: { Authorization: "Bearer <token>" }
Response: { message }
```

### Phase 2 API Calls

#### 2FA Setup
```javascript
POST /api/2fa/setup
Headers: { Authorization: "Bearer <token>" }
Response: { secret, qr_code_url, backup_codes }
```

#### Verify 2FA
```javascript
POST /api/2fa/verify-setup
Body: { otp }
Headers: { Authorization: "Bearer <token>" }
Response: { success, message }
```

#### Assign Permission
```javascript
POST /api/permissions/assign
Body: { user_id, permission_id }
Headers: { Authorization: "Bearer <token>" }
Response: { message }
```

#### Generate Report
```javascript
POST /api/admin/reports/generate
Body: { report_type, start_date, end_date, format }
Headers: { Authorization: "Bearer <token>" }
Response: { report_id, status }
```

### Phase 3 API Calls

#### Generate Tags
```javascript
POST /api/documents/{id}/tags
Headers: { Authorization: "Bearer <token>" }
Response: { tags, urgency, entities }
```

#### Create Rule
```javascript
POST /api/admin/rules
Body: { name, condition: [], actions: [], enabled, priority }
Headers: { Authorization: "Bearer <token>" }
Response: { id, name, message }
```

#### Instantiate Template
```javascript
POST /api/templates/library/{template_id}/instantiate
Body: { document_id }
Headers: { Authorization: "Bearer <token>" }
Response: { message, sop_id }
```

### Phase 4 API Calls

#### Create Version
```javascript
POST /api/documents/{id}/versions
Body: FormData with file
Headers: { Authorization: "Bearer <token>" }
Response: { version, created_at }
```

#### Register Integration
```javascript
POST /api/admin/integrations
Body: { name, provider_type, base_url, auth_type, auth_config, endpoints }
Headers: { Authorization: "Bearer <token>" }
Response: { id, name }
```

#### Get Monitoring Data
```javascript
GET /api/monitoring?hours=24
Headers: { Authorization: "Bearer <token>" }
Response: { current_metrics, health, alerts }

---

## 🎯 Phase Features Summary

### Phase 1 Frontend Features
- **Analytics Dashboard**: Statistics cards with real-time updates
- **Admin Activity**: Recent admin actions display
- **Document Expiry**: Expiry date display and alerts
- **Enhanced Search**: Myanmar language support

### Phase 2 Frontend Features
- **2FA Setup**: QR code display with OTP verification
- **Settings Page**: 2FA enable/disable with backup codes
- **Permissions UI**: Drag-and-drop permission assignment
- **Reports Generator**: Interactive report generation with progress tracking
- **Scheduled Reports**: Configuration modal for recurring reports

### Phase 3 Frontend Features
- **Tag Cloud**: Clickable tags for filtering documents
- **Rule Builder**: Visual condition and action builder
- **Template Library**: Template browser with instantiations
- **Semantic Search Toggle**: Switch between keyword and semantic search
- **Urgent Documents**: Badge display and filtering

### Phase 4 Frontend Features
- **Version History**: Tab in document detail with version list
- **Version Comparison**: Diff display between versions
- **Restore Version**: One-click restore functionality
- **Integrations UI**: API provider management interface
- **Monitoring Dashboard**: Real-time system health display
- **PWA Install**: "Add to Home Screen" prompt

---

## 🔐 Security Features

1. **Token Storage**: Secure token handling
2. **CSRF Protection**: CSRF tokens in forms
3. **XSS Prevention**: Auto-escaping in templates
4. **Role-Based UI**: Menu items based on user role
5. **Session Timeout**: Automatic logout on inactivity
6. **Secure Headers**: Content Security Policy

---

## 📱 Responsive Design

1. **Mobile-First**: Optimized for mobile devices
2. **Tablet Support**: Adaptive layouts for tablets
3. **Desktop Enhancement**: Full features on desktop
4. **Touch-Friendly**: Minimum 44px touch targets
5. **Responsive Tables**: Horizontal scroll on mobile

---

## 🎨 Styling and Theming

### Tailwind CSS Configuration
- Custom color palette
- Utility classes for all components
- Responsive breakpoints
- Dark mode ready (optional)

### Custom CSS
- Animations and transitions
- Custom scrollbars
- Loading spinners
- Toast notifications
- Modal overlays

---

## 🔄 Real-Time Updates

### Server-Sent Events (SSE)
- Dashboard statistics updates
- New document notifications
- Approval status changes
- System health updates

### WebSocket Integration (Optional)
- Real-time chat
- Collaborative editing
- Live document previews

---

## 📊 Data Visualization

### Charts and Graphs
- Document category distribution
- User activity over time
- Processing trends
- System health metrics

### Progress Indicators
- SOP progress bars
- Report generation progress
- Upload progress bars
- Version progress display

---

## 🎓 Accessibility

1. **ARIA Labels**: Screen reader support
2. **Keyboard Navigation**: Full keyboard accessibility
3. **High Contrast**: WCAG AA compliant colors
4. **Focus Management**: Logical tab order
5. **Error Messages**: Clear error descriptions

---

## 📝 Notes

- All templates use Jinja2 inheritance
- JavaScript is modular and organized by feature
- API calls include proper error handling
- Responsive design prioritized
- PWA features are fully functional
- All Phase 1, 2, 3, and 4 features integrated

---

## 🛠️ Frontend Development Setup

```bash
# No build process required for vanilla JS
# Just serve the static files

# Development
cd dms
uvicorn app.main:app --reload

# Access at http://localhost:8000
# PWA will be installable on supported browsers
```

---

## 📱 PWA Testing

1. Open Chrome DevTools
2. Go to Application tab
3. Check Service Workers
4. Check Manifest
5. Test offline functionality
6. Test install prompt

---

**Generated:** 2026-06-22
**Version:** 4.0.0 (Complete with Phase 1, 2, 3, 4)
**Status:** Production Ready