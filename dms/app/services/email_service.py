"""
Office DMS - Email Service for SMTP Integration
Handles sending email alerts for ETA overdue, document rejection, and other notifications.
"""
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional, Dict, Any
from datetime import datetime
from loguru import logger
from app.core.config import settings


class EmailService:
    """SMTP-based email notification service."""

    def __init__(self):
        smtp_enabled = settings.__dict__.get("SMTP_ENABLED", "false")
        self.enabled = (smtp_enabled if isinstance(smtp_enabled, bool) else str(smtp_enabled).lower() == "true")
        self.smtp_server = settings.__dict__.get("SMTP_SERVER", "localhost")
        self.smtp_port = int(settings.__dict__.get("SMTP_PORT", "587"))
        self.smtp_username = settings.__dict__.get("SMTP_USERNAME", "")
        self.smtp_password = settings.__dict__.get("SMTP_PASSWORD", "")
        
        smtp_use_tls = settings.__dict__.get("SMTP_USE_TLS", "true")
        self.smtp_use_tls = (smtp_use_tls if isinstance(smtp_use_tls, bool) else str(smtp_use_tls).lower() == "true")
        
        self.from_email = settings.__dict__.get("SMTP_FROM_EMAIL", "noreply@enterprise-dms.local")
        self.from_name = settings.__dict__.get("SMTP_FROM_NAME", "Enterprise DMS")
        self.admin_email = settings.__dict__.get("ADMIN_EMAIL", "admin@enterprise-dms.local")

    def _create_message(
        self,
        to_email: str,
        subject: str,
        body: str,
        is_html: bool = False
    ) -> MIMEMultipart:
        """Create email message."""
        msg = MIMEMultipart('alternative')
        msg['From'] = f"{self.from_name} <{self.from_email}>"
        msg['To'] = to_email
        msg['Subject'] = subject

        # Attach body
        if is_html:
            msg.attach(MIMEText(body, 'html'))
        else:
            msg.attach(MIMEText(body, 'plain'))

        return msg

    def send_email(
        self,
        to_email: str,
        subject: str,
        body: str,
        is_html: bool = False
    ) -> Dict[str, Any]:
        """Send email via SMTP."""
        if not self.enabled:
            logger.warning(f"Email service disabled. Would send to {to_email}: {subject}")
            return {
                "success": False,
                "message": "Email service disabled",
                "email_sent_to": to_email
            }

        try:
            msg = self._create_message(to_email, subject, body, is_html)

            # Connect to SMTP server
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                if self.smtp_use_tls:
                    server.starttls()

                # Login if credentials provided
                if self.smtp_username and self.smtp_password:
                    server.login(self.smtp_username, self.smtp_password)

                # Send email
                server.send_message(msg)

            logger.info(f"Email sent successfully to {to_email}: {subject}")
            return {
                "success": True,
                "message": "Email sent successfully",
                "email_sent_to": to_email
            }

        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {e}")
            return {
                "success": False,
                "message": str(e),
                "email_sent_to": to_email
            }

    def send_document_rejection_alert(
        self,
        document_filename: str,
        rejection_reason: str,
        uploaded_by_email: str,
        uploaded_by_name: str
    ) -> Dict[str, Any]:
        """Send email alert when a document is rejected."""
        subject = f"Document Rejected: {document_filename}"
        
        body = f"""
Dear {uploaded_by_name},

Your document has been rejected by the review team.

Document: {document_filename}
Rejection Reason: {rejection_reason}
Date: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}

Please review the rejection reason and upload a corrected version if necessary.

Best regards,
Enterprise DMS Team
"""
        return self.send_email(uploaded_by_email, subject, body)

    def send_eta_overdue_alert(
        self,
        document_filename: str,
        eta_date: str,
        supplier_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """Send email alert when ETA is overdue."""
        subject = f"ETA Overdue Alert: {document_filename}"
        
        supplier_text = f"Supplier: {supplier_name}" if supplier_name else ""
        
        body = f"""
Admin Alert - ETA Overdue

Document: {document_filename}
{supplier_text}
ETA Date: {eta_date}
Status: OVERDUE
Alert Date: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}

This document's ETA has passed. Please take appropriate action.

Best regards,
Enterprise DMS Team
"""
        return self.send_email(self.admin_email, subject, body)

    def send_sop_deadline_alert(
        self,
        sop_name: str,
        due_date: str,
        document_filename: Optional[str] = None
    ) -> Dict[str, Any]:
        """Send email alert when SOP deadline is approaching or overdue."""
        subject = f"SOP Deadline Alert: {sop_name}"
        
        doc_text = f"Related Document: {document_filename}" if document_filename else ""
        
        body = f"""
SOP Deadline Alert

SOP: {sop_name}
{doc_text}
Due Date: {due_date}
Alert Date: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}

Please ensure the SOP is completed on time.

Best regards,
Enterprise DMS Team
"""
        return self.send_email(self.admin_email, subject, body)

    def send_suspicious_document_alert(
        self,
        document_filename: str,
        suspicious_reason: str
    ) -> Dict[str, Any]:
        """Send email alert when a suspicious document is detected."""
        subject = f"Suspicious Document Detected: {document_filename}"
        
        body = f"""
Security Alert - Suspicious Document Detected

Document: {document_filename}
Reason: {suspicious_reason}
Detection Date: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}

This document has been flagged as suspicious. Please review manually.

Best regards,
Enterprise DMS Team
"""
        return self.send_email(self.admin_email, subject, body)

    def send_duplicate_document_alert(
        self,
        document_filename: str,
        duplicate_of_filename: str,
        similarity_score: float
    ) -> Dict[str, Any]:
        """Send email alert when a duplicate document is detected."""
        subject = f"Duplicate Document Detected: {document_filename}"
        
        body = f"""
Duplicate Document Alert

Original Document: {duplicate_of_filename}
Duplicate Document: {document_filename}
Similarity Score: {similarity_score:.2%}
Detection Date: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}

A potential duplicate has been detected. Please review.

Best regards,
Enterprise DMS Team
"""
        return self.send_email(self.admin_email, subject, body)

    def send_document_expiry_alert(
        self,
        document_filename: str,
        expiry_date: datetime,
        expiry_notes: Optional[str] = None,
        uploader_email: Optional[str] = None,
        uploader_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """Send email alert when a document is expiring soon."""
        subject = f"Document Expiring Soon: {document_filename}"
        
        notes_text = f"Notes: {expiry_notes}" if expiry_notes else ""
        uploader_text = f"Dear {uploader_name}," if uploader_name else "Admin Alert"
        
        body = f"""
{uploader_text}

This document is expiring soon and requires attention.

Document: {document_filename}
Expiry Date: {expiry_date.strftime('%Y-%m-%d')}
{notes_text}
Alert Date: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}

Please review the document and take appropriate action before it expires.

Best regards,
Enterprise DMS Team
"""
        
        # Send to uploader if provided, otherwise to admin
        recipient = uploader_email if uploader_email else self.admin_email
        return self.send_email(recipient, subject, body)


    def send_report_email(
        self,
        report_filename: str,
        report_type: str,
        recipient_email: str,
        recipient_name: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        record_count: int = 0
    ) -> Dict[str, Any]:
        """Send scheduled report via email attachment."""
        subject = f"Compliance Report: {report_type}"
        
        recipient_text = f"Dear {recipient_name}," if recipient_name else "Admin Alert"
        date_range = f"{start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}" if start_date and end_date else "period"
        
        body = f"""
{recipient_text}

Your compliance report is ready for review.

Report Type: {report_type}
Period: {date_range}
Records: {record_count}
Report File: {report_filename}
Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}

Please download and review the report for compliance requirements.

Best regards,
Enterprise DMS Team
"""
        
        # Note: Actual file attachment would require additional implementation
        # For now, we'll send a notification about the report
        return self.send_email(recipient_email, subject, body)


    def send_daily_activity_report(
        self,
        recipient_email: str,
        recipient_name: Optional[str] = None,
        stats: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Send daily activity summary report."""
        subject = "Daily Activity Report - Enterprise DMS"
        
        recipient_text = f"Dear {recipient_name}," if recipient_name else "Admin Alert"
        
        stats_text = ""
        if stats:
            stats_text = f"""
Total Documents: {stats.get('total_documents', 0)}
Pending Review: {stats.get('pending', 0)}
Approved Today: {stats.get('approved_today', 0)}
Failed: {stats.get('failed', 0)}
"""
        
        body = f"""
{recipient_text}

Daily Activity Summary
{stats_text}
Report Date: {datetime.utcnow().strftime('%Y-%m-%d')}

This is your daily activity summary for Enterprise DMS.

Best regards,
Enterprise DMS Team
"""
        
        return self.send_email(recipient_email, subject, body)


    def send_weekly_summary_report(
        self,
        recipient_email: str,
        recipient_name: Optional[str] = None,
        weekly_stats: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Send weekly summary report."""
        subject = "Weekly Summary Report - Enterprise DMS"
        
        recipient_text = f"Dear {recipient_name}," if recipient_name else "Admin Alert"
        
        stats_text = ""
        if weekly_stats:
            stats_text = f"""
Total Documents This Week: {weekly_stats.get('total_documents', 0)}
Approved This Week: {weekly_stats.get('approved_count', 0)}
Rejected This Week: {weekly_stats.get('rejected_count', 0)}
Total Users: {weekly_stats.get('total_users', 0)}
"""
        
        body = f"""
{recipient_text}

Weekly Summary Report
{stats_text}
Report Period: {datetime.utcnow().strftime('%Y-%m-%d')} (End of Week)

This is your weekly summary report for Enterprise DMS.

Best regards,
Enterprise DMS Team
"""
        
        return self.send_email(recipient_email, subject, body)


# Global email service instance
email_service = EmailService()
