# Monitoring & Analytics Setup

## Overview
Enterprise AI DMS အတွက် Prometheus နှင့့ Grafana ကို အသုံးပြုပြီး monitoring နှင့့ analytics စနစ်ဖြစ်ပါသည်။

## Components

### Prometheus
- **Port**: 9090
- **Purpose**: Metrics collection and storage
- **Config**: `monitoring/prometheus/prometheus.yml`

### Grafana
- **Port**: 3001
- **Purpose**: Dashboard visualization
- **Credentials**: admin / admin123
- **Dashboards**: 
  - `dms-overview.json` - System overview
  - `dms-document-processing.json` - Document processing metrics
  - `dms-system-monitoring.json` - System monitoring

## Installation & Setup

### 1. Start Monitoring Stack
```bash
cd monitoring
docker-compose -f docker-compose.monitoring.yml up -d
```

### 2. Access Grafana
- URL: http://localhost:3001
- Username: admin
- Password: admin123

### 3. Access Prometheus
- URL: http://localhost:9090

## Available Metrics

### HTTP Metrics
- `http_requests_total` - Total HTTP requests
- `http_request_duration_seconds` - Request duration
- `http_requests_in_progress` - Requests in progress

### Document Metrics
- `documents_total` - Total documents processed
- `documents_processing_time_seconds` - Processing time
- `documents_upload_size_bytes` - Upload size

### AI Metrics
- `ocr_operations_total` - OCR operations
- `ocr_processing_time_seconds` - OCR processing time
- `function_detection_operations_total` - Function detection
- `fracture_detection_operations_total` - Fracture detection

### Database Metrics
- `database_connections_active` - Active connections
- `database_query_duration_seconds` - Query duration

### System Metrics
- `cpu_usage_percent` - CPU usage
- `memory_usage_bytes` - Memory usage
- `disk_usage_bytes` - Disk usage

### User Metrics
- `users_total` - Total users
- `active_sessions` - Active sessions

### Error Metrics
- `errors_total` - Total errors

## Dashboards

### 1. Overview Dashboard
- Total documents
- Active users
- HTTP request rate
- Documents by status
- Documents by category
- Average response time
- Error rate

### 2. Document Processing Dashboard
- Document processing time
- OCR operations
- OCR processing time
- Function detection operations
- Fracture detection operations
- Documents by quality level

### 3. System Monitoring Dashboard
- CPU usage
- Memory usage
- Disk usage
- Database connections
- Database query duration
- Active sessions
- Error rate

## Prometheus Metrics Endpoint

Metrics ကို application မှ `/metrics` endpoint တွင် ရရှိနိုင်ပါသည်:
- http://localhost:8000/metrics

## Alerting (Optional)

Alerts ကို Prometheus Alertmanager နှင့့ configure လုပ်နိုင်ပါသည်:
- High error rate
- High response time
- High CPU/memory usage
- Database connection issues

## Integration with Production

Production environment တွင်:
1. Prometheus ကို separate server တွင် deploy လုပ်ပါ
2. Grafana ကို reverse proxy နှင့့ secure လုပ်ပါ
3. SSL/TLS certificates ကို configure လုပ်ပါ
4. Authentication ကို enable လုပ်ပါ
5. Backup နှင့့ retention policies ကို configure လုပ်ပါ

## Troubleshooting

### Grafana မှ Prometheus ကို connect မဖြစ်ပါ
1. Network settings ကို check လုပ်ပါ
2. Prometheus URL ကို verify လုပ်ပါ
3. Docker network ကို check လုပ်ပါ

### Metrics မတွေ့ပါ
1. Application ကို restart လုပ်ပါ
2. `/metrics` endpoint ကို test လုပ်ပါ
3. Prometheus config ကို check လုပ်ပါ