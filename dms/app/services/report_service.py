"""
Report Service - Compliance and audit report generation
Handles access logs, document activity, and user activity reports.
"""
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from pathlib import Path
from sqlalchemy.orm import Session
from loguru import logger
import io

from app.models.database import AuditLog, Document, User
from app.models.schemas import ReportType, ReportFormat
from app.core.config import settings


class ReportService:
    """Service for generating compliance and audit reports."""

    def __init__(self):
        self.reports_dir = Path(settings.ORGANIZED_ROOT).parent / "reports"
        self.reports_dir.mkdir(parents=True, exist_ok=True)

    def generate_access_log_report(
        self,
        start_date: datetime,
        end_date: datetime,
        user_id: Optional[int] = None,
        db: Session = None
    ) -> pd.DataFrame:
        """
        Generate access log report showing who viewed what documents and when.
        
        Args:
            start_date: Report start date
            end_date: Report end date
            user_id: Optional user filter
            db: Database session
            
        Returns:
            pd.DataFrame: Access log data
        """
        try:
            query = db.query(AuditLog, User, Document).join(
                User, AuditLog.user_id == User.id
            ).outerjoin(
                Document, AuditLog.document_id == Document.id
            ).filter(
                AuditLog.timestamp >= start_date,
                AuditLog.timestamp <= end_date,
                AuditLog.action.in_(["VIEW", "DOWNLOAD", "EDIT"])
            )

            if user_id:
                query = query.filter(AuditLog.user_id == user_id)

            results = query.all()

            data = []
            for audit, user, document in results:
                data.append({
                    "Timestamp": audit.timestamp,
                    "User": user.username,
                    "User Role": user.role,
                    "Action": audit.action,
                    "Document": document.original_filename if document else "N/A",
                    "Document ID": document.id if document else None,
                    "IP Address": audit.ip_address or "N/A",
                    "User Agent": audit.user_agent or "N/A"
                })

            df = pd.DataFrame(data)
            if not df.empty:
                df = df.sort_values("Timestamp", ascending=False)
            
            return df

        except Exception as e:
            logger.error(f"Failed to generate access log report: {e}")
            return pd.DataFrame()

    def generate_document_activity_report(
        self,
        start_date: datetime,
        end_date: datetime,
        db: Session = None
    ) -> pd.DataFrame:
        """
        Generate document activity report showing uploads, approvals, rejections per user.
        
        Args:
            start_date: Report start date
            end_date: Report end date
            db: Database session
            
        Returns:
            pd.DataFrame: Document activity data
        """
        try:
            query = db.query(AuditLog, User).join(
                User, AuditLog.user_id == User.id
            ).filter(
                AuditLog.timestamp >= start_date,
                AuditLog.timestamp <= end_date,
                AuditLog.action.in_(["UPLOAD", "APPROVE", "REJECT", "EDIT"])
            )

            results = query.all()

            data = []
            for audit, user in results:
                # Extract document info from details if available
                doc_info = audit.details or {}
                document_name = doc_info.get("filename", "N/A")

                data.append({
                    "Timestamp": audit.timestamp,
                    "User": user.username,
                    "User Role": user.role,
                    "Action": audit.action,
                    "Document": document_name,
                    "Details": audit.details
                })

            df = pd.DataFrame(data)
            if not df.empty:
                df = df.sort_values("Timestamp", ascending=False)
            
            return df

        except Exception as e:
            logger.error(f"Failed to generate document activity report: {e}")
            return pd.DataFrame()

    def generate_user_activity_report(
        self,
        start_date: datetime,
        end_date: datetime,
        user_id: Optional[int] = None,
        db: Session = None
    ) -> pd.DataFrame:
        """
        Generate user activity report showing summary of all user actions.
        
        Args:
            start_date: Report start date
            end_date: Report end date
            user_id: Optional user filter
            db: Database session
            
        Returns:
            pd.DataFrame: User activity data
        """
        try:
            query = db.query(AuditLog, User).join(
                User, AuditLog.user_id == User.id
            ).filter(
                AuditLog.timestamp >= start_date,
                AuditLog.timestamp <= end_date
            )

            if user_id:
                query = query.filter(AuditLog.user_id == user_id)

            results = query.all()

            data = []
            for audit, user in results:
                data.append({
                    "Timestamp": audit.timestamp,
                    "User": user.username,
                    "User Role": user.role,
                    "Action": audit.action,
                    "Endpoint": audit.endpoint or "N/A",
                    "IP Address": audit.ip_address or "N/A",
                    "Details": audit.details
                })

            df = pd.DataFrame(data)
            if not df.empty:
                df = df.sort_values("Timestamp", ascending=False)
            
            return df

        except Exception as e:
            logger.error(f"Failed to generate user activity report: {e}")
            return pd.DataFrame()

    def generate_custom_report(
        self,
        start_date: datetime,
        end_date: datetime,
        filters: Dict[str, Any],
        db: Session = None
    ) -> pd.DataFrame:
        """
        Generate custom report with user-defined filters.
        
        Args:
            start_date: Report start date
            end_date: Report end date
            filters: Dictionary of filters (user_id, document_type, action, etc.)
            db: Database session
            
        Returns:
            pd.DataFrame: Custom report data
        """
        try:
            query = db.query(AuditLog, User).join(
                User, AuditLog.user_id == User.id
            ).outerjoin(
                Document, AuditLog.document_id == Document.id
            ).filter(
                AuditLog.timestamp >= start_date,
                AuditLog.timestamp <= end_date
            )

            # Apply filters
            if filters.get("user_id"):
                query = query.filter(AuditLog.user_id == filters["user_id"])
            
            if filters.get("action"):
                query = query.filter(AuditLog.action == filters["action"])
            
            if filters.get("document_type"):
                query = query.filter(Document.category == filters["document_type"])

            results = query.all()

            data = []
            for audit, user, document in results:
                data.append({
                    "Timestamp": audit.timestamp,
                    "User": user.username,
                    "User Role": user.role,
                    "Action": audit.action,
                    "Document": document.original_filename if document else "N/A",
                    "Document Type": document.category if document else "N/A",
                    "Details": audit.details
                })

            df = pd.DataFrame(data)
            if not df.empty:
                df = df.sort_values("Timestamp", ascending=False)
            
            return df

        except Exception as e:
            logger.error(f"Failed to generate custom report: {e}")
            return pd.DataFrame()

    def export_to_excel(
        self,
        df: pd.DataFrame,
        title: str,
        filename: Optional[str] = None
    ) -> str:
        """
        Export DataFrame to Excel file.
        
        Args:
            df: DataFrame to export
            title: Report title
            filename: Optional custom filename
            
        Returns:
            str: Path to generated file
        """
        try:
            if filename is None:
                timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
                filename = f"report_{title.replace(' ', '_')}_{timestamp}.xlsx"

            filepath = self.reports_dir / filename

            # Create Excel writer with formatting
            with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
                # Write data
                df.to_excel(writer, sheet_name='Report', index=False)
                
                # Get workbook and worksheet for formatting
                workbook = writer.book
                worksheet = writer.sheets['Report']
                
                # Add title row
                worksheet.insert_rows(1)
                worksheet['A1'] = title
                worksheet['A1'].font = {'bold': True, 'size': 14}
                worksheet.merge_cells('A1:Z1')

                # Auto-adjust column widths
                for column in worksheet.columns:
                    max_length = 0
                    column_letter = column[0].column_letter
                    for cell in column:
                        try:
                            if len(str(cell.value)) > max_length:
                                max_length = len(str(cell.value))
                        except:
                            pass
                    adjusted_width = (max_length + 2)
                    worksheet.column_dimensions[column_letter].width = adjusted_width

            logger.info(f"Excel report generated: {filepath}")
            return str(filepath)

        except Exception as e:
            logger.error(f"Failed to export to Excel: {e}")
            raise

    def export_to_pdf(
        self,
        df: pd.DataFrame,
        title: str,
        filename: Optional[str] = None
    ) -> str:
        """
        Export DataFrame to PDF file.
        
        Args:
            df: DataFrame to export
            title: Report title
            filename: Optional custom filename
            
        Returns:
            str: Path to generated file
        """
        try:
            if filename is None:
                timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
                filename = f"report_{title.replace(' ', '_')}_{timestamp}.pdf"

            filepath = self.reports_dir / filename

            # Create HTML table from DataFrame
            html_table = df.to_html(classes='report-table', index=False)
            
            # Create full HTML document
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>{title}</title>
                <style>
                    body {{ font-family: Arial, sans-serif; margin: 20px; }}
                    h1 {{ color: #1e40af; }}
                    .report-table {{ border-collapse: collapse; width: 100%; margin-top: 20px; }}
                    .report-table th {{ background-color: #1e40af; color: white; padding: 12px; text-align: left; }}
                    .report-table td {{ border: 1px solid #ddd; padding: 8px; }}
                    .report-table tr:nth-child(even) {{ background-color: #f9f9f9; }}
                    .report-table tr:hover {{ background-color: #f1f1f1; }}
                    .footer {{ margin-top: 30px; color: #666; font-size: 12px; }}
                </style>
            </head>
            <body>
                <h1>{title}</h1>
                <p>Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}</p>
                {html_table}
                <div class="footer">
                    <p>Enterprise DMS - Compliance Report</p>
                </div>
            </body>
            </html>
            """

            # Save HTML to temp file first
            temp_html = self.reports_dir / f"temp_{filename}.html"
            with open(temp_html, 'w', encoding='utf-8') as f:
                f.write(html_content)

            # Convert to PDF using weasyprint
            try:
                import weasyprint
                weasyprint.HTML(filename=str(temp_html)).write_pdf(str(filepath))
                logger.info(f"PDF report generated: {filepath}")
            except ImportError:
                # Fallback to reportlab
                try:
                    from reportlab.lib import colors
                    from reportlab.lib.pagesizes import letter
                    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
                    from reportlab.lib.styles import getSampleStyleSheet

                    doc = SimpleDocTemplate(str(filepath), pagesize=letter)
                    elements = []
                    styles = getSampleStyleSheet()

                    # Title
                    elements.append(Paragraph(title, styles['Title']))
                    elements.append(Spacer(1, 12))

                    # Data for table
                    data = [[str(col) for col in df.columns]]
                    for _, row in df.iterrows():
                        data.append([str(val) for val in row])

                    # Create table
                    table = Table(data)
                    table.setStyle(TableStyle([
                        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1e40af')),
                        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                        ('FONTSIZE', (0, 0), (-1, 0), 10),
                        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                        ('GRID', (0, 0), (-1, -1), 1, colors.black),
                    ]))

                    elements.append(table)
                    doc.build(elements)
                    logger.info(f"PDF report generated using reportlab: {filepath}")

                except ImportError:
                    logger.error("Neither weasyprint nor reportlab is available for PDF generation")
                    raise ImportError("PDF generation requires weasyprint or reportlab")

            # Clean up temp file
            temp_html.unlink(missing_ok=True)

            return str(filepath)

        except Exception as e:
            logger.error(f"Failed to export to PDF: {e}")
            raise

    def export_to_json(
        self,
        df: pd.DataFrame,
        title: str,
        filename: Optional[str] = None
    ) -> str:
        """
        Export DataFrame to JSON file.
        
        Args:
            df: DataFrame to export
            title: Report title
            filename: Optional custom filename
            
        Returns:
            str: Path to generated file
        """
        try:
            if filename is None:
                timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
                filename = f"report_{title.replace(' ', '_')}_{timestamp}.json"

            filepath = self.reports_dir / filename

            # Convert datetime objects to strings for JSON serialization
            df_json = df.copy()
            for col in df_json.columns:
                if pd.api.types.is_datetime64_any_dtype(df_json[col]):
                    df_json[col] = df_json[col].dt.strftime('%Y-%m-%d %H:%M:%S')

            # Create JSON structure
            report_data = {
                "title": title,
                "generated_at": datetime.utcnow().isoformat(),
                "total_records": len(df_json),
                "data": df_json.to_dict('records')
            }

            import json
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(report_data, f, indent=2, default=str)

            logger.info(f"JSON report generated: {filepath}")
            return str(filepath)

        except Exception as e:
            logger.error(f"Failed to export to JSON: {e}")
            raise

    def cleanup_old_reports(self, retention_days: int = 30) -> int:
        """
        Clean up old report files.
        
        Args:
            retention_days: Number of days to keep reports
            
        Returns:
            int: Number of files deleted
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=retention_days)
            deleted_count = 0

            for file in self.reports_dir.glob("report_*"):
                if datetime.fromtimestamp(file.stat().st_mtime) < cutoff_date:
                    file.unlink()
                    deleted_count += 1

            logger.info(f"Cleaned up {deleted_count} old report files")
            return deleted_count

        except Exception as e:
            logger.error(f"Failed to cleanup old reports: {e}")
            return 0


# Global report service instance
report_service = ReportService()