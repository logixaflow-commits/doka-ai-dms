"""
Advanced Reporting Service
Provides custom report builder, export functionality, and analytics
"""
import io
import csv
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from dataclasses import dataclass
from pathlib import Path
import json
import uuid
from loguru import logger


@dataclass
class ReportTemplate:
    """Report template definition"""
    id: str
    name: str
    description: str
    report_type: str  # document, user, activity, custom
    parameters: Dict[str, Any]
    columns: List[Dict[str, Any]]
    filters: List[Dict[str, Any]]
    created_by: int
    created_at: datetime


@dataclass
class ReportSchedule:
    """Report schedule definition"""
    id: str
    report_template_id: str
    schedule_type: str  # daily, weekly, monthly
    schedule_config: Dict[str, Any]
    recipients: List[str]
    created_by: int
    created_at: datetime
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None


class AdvancedReportingService:
    """Service for advanced reporting"""
    
    def __init__(self):
        self.reports_storage_path = Path("storage/reports")
        self.reports_storage_path.mkdir(parents=True, exist_ok=True)
        self.templates_storage_path = Path("storage/report_templates")
        self.templates_storage_path.mkdir(parents=True, exist_ok=True)
        self.schedules_storage_path = Path("storage/report_schedules")
        self.schedules_storage_path.mkdir(parents=True, exist_ok=True)
        
    def create_report_template(
        self,
        name: str,
        description: str,
        report_type: str,
        parameters: Dict[str, Any],
        columns: List[Dict[str, Any]],
        filters: List[Dict[str, Any]],
        created_by: int
    ) -> ReportTemplate:
        """Create new report template"""
        try:
            import uuid
            template_id = str(uuid.uuid4())
            
            template = ReportTemplate(
                id=template_id,
                name=name,
                description=description,
                report_type=report_type,
                parameters=parameters,
                columns=columns,
                filters=filters,
                created_by=created_by,
                created_at=datetime.utcnow()
            )
            
            # Save template
            self._save_report_template(template)
            
            logger.info(f"Created report template {template_id}: {name}")
            return template
            
        except Exception as e:
            logger.error(f"Failed to create report template: {e}")
            raise
    
    def generate_report(
        self,
        template_id: str,
        parameters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Generate report from template"""
        try:
            # Get template
            template = self.get_report_template(template_id)
            
            if not template:
                return {"success": False, "error": "Template not found"}
            
            # Merge parameters
            merged_params = {**template.parameters, **(parameters or {})}
            
            # Generate report data based on type
            if template.report_type == "document":
                data = self._generate_document_report(merged_params, template.columns, template.filters)
            elif template.report_type == "user":
                data = self._generate_user_report(merged_params, template.columns, template.filters)
            elif template.report_type == "activity":
                data = self._generate_activity_report(merged_params, template.columns, template.filters)
            else:
                data = self._generate_custom_report(merged_params, template.columns, template.filters)
            
            return {
                "success": True,
                "template_id": template_id,
                "template_name": template.name,
                "generated_at": datetime.utcnow().isoformat(),
                "data": data
            }
            
        except Exception as e:
            logger.error(f"Failed to generate report: {e}")
            return {"success": False, "error": str(e)}
    
    def _generate_document_report(
        self,
        parameters: Dict[str, Any],
        columns: List[Dict[str, Any]],
        filters: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Generate document report"""
        try:
            from app.core.database import SessionLocal
            from app.models.database import Document
            
            db = SessionLocal()
            
            # Build query
            query = db.query(Document).filter(Document.deleted == False)
            
            # Apply filters
            for filter_config in filters:
                field = filter_config["field"]
                operator = filter_config.get("operator", "=")
                value = filter_config.get("value")
                
                if field == "status" and value:
                    query = query.filter(Document.status == value)
                elif field == "category" and value:
                    query = query.filter(Document.category == value)
                elif field == "date_from" and value:
                    query = query.filter(Document.created_at >= value)
                elif field == "date_to" and value:
                    query = query.filter(Document.created_at <= value)
            
            # Execute query
            documents = query.all()
            
            # Generate report data
            report_data = []
            for doc in documents:
                row = {}
                for column in columns:
                    field_name = column["field"]
                    if field_name == "id":
                        row[field_name] = doc.id
                    elif field_name == "filename":
                        row[field_name] = doc.original_filename
                    elif field_name == "category":
                        row[field_name] = doc.category
                    elif field_name == "status":
                        row[field_name] = doc.status
                    elif field_name == "created_at":
                        row[field_name] = doc.created_at.isoformat() if doc.created_at else None
                    elif field_name == "file_size":
                        row[field_name] = doc.file_size
                    elif field_name == "function_type":
                        row[field_name] = doc.function_type
                    elif field_name == "quality_level":
                        row[field_name] = doc.quality_level
                    else:
                        row[field_name] = getattr(doc, field_name, None)
                
                report_data.append(row)
            
            db.close()
            return report_data
            
        except Exception as e:
            logger.error(f"Failed to generate document report: {e}")
            return []
    
    def _generate_user_report(
        self,
        parameters: Dict[str, Any],
        columns: List[Dict[str, Any]],
        filters: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Generate user report"""
        try:
            from app.core.database import SessionLocal
            from app.models.database import User
            
            db = SessionLocal()
            
            # Build query
            query = db.query(User)
            
            # Apply filters
            for filter_config in filters:
                field = filter_config["field"]
                value = filter_config.get("value")
                
                if field == "role" and value:
                    query = query.filter(User.role == value)
                elif field == "is_active" and value is not None:
                    query = query.filter(User.is_active == value)
            
            # Execute query
            users = query.all()
            
            # Generate report data
            report_data = []
            for user in users:
                row = {}
                for column in columns:
                    field_name = column["field"]
                    if field_name == "id":
                        row[field_name] = user.id
                    elif field_name == "username":
                        row[field_name] = user.username
                    elif field_name == "email":
                        row[field_name] = user.email
                    elif field_name == "role":
                        row[field_name] = user.role
                    elif field_name == "is_active":
                        row[field_name] = user.is_active
                    elif field_name == "created_at":
                        row[field_name] = user.created_at.isoformat() if user.created_at else None
                    else:
                        row[field_name] = getattr(user, field_name, None)
                
                report_data.append(row)
            
            db.close()
            return report_data
            
        except Exception as e:
            logger.error(f"Failed to generate user report: {e}")
            return []
    
    def _generate_activity_report(
        self,
        parameters: Dict[str, Any],
        columns: List[Dict[str, Any]],
        filters: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Generate activity report"""
        try:
            from app.core.database import SessionLocal
            from app.models.database import AuditLog
            
            db = SessionLocal()
            
            # Build query
            query = db.query(AuditLog)
            
            # Apply filters
            for filter_config in filters:
                field = filter_config["field"]
                value = filter_config.get("value")
                
                if field == "action" and value:
                    query = query.filter(AuditLog.action == value)
                elif field == "user_id" and value:
                    query = query.filter(AuditLog.user_id == value)
                elif field == "date_from" and value:
                    query = query.filter(AuditLog.created_at >= value)
                elif field == "date_to" and value:
                    query = query.filter(AuditLog.created_at <= value)
            
            # Execute query
            logs = query.order_by(AuditLog.created_at.desc()).limit(1000).all()
            
            # Generate report data
            report_data = []
            for log in logs:
                row = {}
                for column in columns:
                    field_name = column["field"]
                    if field_name == "id":
                        row[field_name] = log.id
                    elif field_name == "action":
                        row[field_name] = log.action
                    elif field_name == "user_id":
                        row[field_name] = log.user_id
                    elif field_name == "created_at":
                        row[field_name] = log.created_at.isoformat() if log.created_at else None
                    elif field_name == "details":
                        row[field_name] = log.details
                    else:
                        row[field_name] = getattr(log, field_name, None)
                
                report_data.append(row)
            
            db.close()
            return report_data
            
        except Exception as e:
            logger.error(f"Failed to generate activity report: {e}")
            return []
    
    def _generate_custom_report(
        self,
        parameters: Dict[str, Any],
        columns: List[Dict[str, Any]],
        filters: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Generate custom report"""
        # Placeholder for custom report generation
        return []
    
    def export_report(
        self,
        report_data: List[Dict[str, Any]],
        format: str = "csv"
    ) -> Dict[str, Any]:
        """Export report to different formats"""
        try:
            if format == "csv":
                return self._export_to_csv(report_data)
            elif format == "json":
                return self._export_to_json(report_data)
            elif format == "excel":
                return self._export_to_excel(report_data)
            else:
                return {"success": False, "error": "Unsupported format"}
                
        except Exception as e:
            logger.error(f"Failed to export report: {e}")
            return {"success": False, "error": str(e)}
    
    def _export_to_csv(self, data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Export report to CSV"""
        try:
            if not data:
                return {"success": False, "error": "No data to export"}
            
            output = io.StringIO()
            writer = csv.DictWriter(output, fieldnames=data[0].keys())
            writer.writeheader()
            writer.writerows(data)
            
            return {
                "success": True,
                "format": "csv",
                "data": output.getvalue()
            }
            
        except Exception as e:
            logger.error(f"Failed to export to CSV: {e}")
            return {"success": False, "error": str(e)}
    
    def _export_to_json(self, data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Export report to JSON"""
        try:
            return {
                "success": True,
                "format": "json",
                "data": json.dumps(data, indent=2)
            }
            
        except Exception as e:
            logger.error(f"Failed to export to JSON: {e}")
            return {"success": False, "error": str(e)}
    
    def _export_to_excel(self, data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Export report to Excel"""
        try:
            # Placeholder for Excel export
            # Would require openpyxl or similar library
            return {
                "success": False,
                "error": "Excel export requires openpyxl library"
            }
            
        except Exception as e:
            logger.error(f"Failed to export to Excel: {e}")
            return {"success": False, "error": str(e)}
    
    def get_report_template(self, template_id: str) -> Optional[ReportTemplate]:
        """Get report template by ID"""
        try:
            template_uuid = uuid.UUID(str(template_id))
            template_root = self.templates_storage_path.resolve()
            template_file = (template_root / f"{template_uuid}.json").resolve()
            try:
                template_file.relative_to(template_root)
            except ValueError as exc:
                raise ValueError("Report template path escaped its safe root.") from exc
            
            if not template_file.exists():
                return None
            
            with open(template_file, 'r') as f:
                template_data = json.load(f)
            
            template = ReportTemplate(
                id=template_data["id"],
                name=template_data["name"],
                description=template_data["description"],
                report_type=template_data["report_type"],
                parameters=template_data["parameters"],
                columns=template_data["columns"],
                filters=template_data["filters"],
                created_by=template_data["created_by"],
                created_at=datetime.fromisoformat(template_data["created_at"])
            )
            
            return template
            
        except Exception as e:
            logger.error(f"Failed to get report template: {e}")
            return None
    
    def get_all_report_templates(self) -> List[ReportTemplate]:
        """Get all report templates"""
        try:
            templates = []
            
            for template_file in self.templates_storage_path.glob("*.json"):
                with open(template_file, 'r') as f:
                    template_data = json.load(f)
                
                template = self.get_report_template(template_data["id"])
                if template:
                    templates.append(template)
            
            return templates
            
        except Exception as e:
            logger.error(f"Failed to get report templates: {e}")
            return []
    
    def _save_report_template(self, template: ReportTemplate):
        """Save report template to file"""
        template_file = self.templates_storage_path / f"{template.id}.json"
        
        template_data = {
            "id": template.id,
            "name": template.name,
            "description": template.description,
            "report_type": template.report_type,
            "parameters": template.parameters,
            "columns": template.columns,
            "filters": template.filters,
            "created_by": template.created_by,
            "created_at": template.created_at.isoformat()
        }
        
        with open(template_file, 'w') as f:
            json.dump(template_data, f, indent=2)


# Singleton instance
_reporting_service: Optional[AdvancedReportingService] = None


def get_reporting_service() -> AdvancedReportingService:
    """Get singleton reporting service"""
    global _reporting_service
    if _reporting_service is None:
        _reporting_service = AdvancedReportingService()
    return _reporting_service