"""
Production Email Service with SMTP Configuration
This module handles email notifications for enterprise features
"""
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from typing import Optional, List
from loguru import logger
from dataclasses import dataclass


@dataclass
class EmailConfig:
    """Email configuration settings"""
    smtp_server: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    use_tls: bool = True
    from_email: str = "noreply@enterprise-dms.local"
    from_name: str = "Enterprise DMS"
    admin_email: str = "admin@enterprise-dms.local"


class ProductionEmailService:
    """Production email service with retry logic and error handling"""
    
    def __init__(self, config: Optional[EmailConfig] = None):
        self.config = config or self._load_config()
        self.enabled = self._check_enabled()
        
    def _load_config(self) -> EmailConfig:
        """Load email configuration from environment"""
        return EmailConfig(
            smtp_server=os.getenv("SMTP_SERVER", "smtp.gmail.com"),
            smtp_port=int(os.getenv("SMTP_PORT", "587")),
            smtp_username=os.getenv("SMTP_USERNAME", ""),
            smtp_password=os.getenv("SMTP_PASSWORD", ""),
            use_tls=os.getenv("SMTP_USE_TLS", "true").lower() == "true",
            from_email=os.getenv("SMTP_FROM_EMAIL", "noreply@enterprise-dms.local"),
            from_name=os.getenv("SMTP_FROM_NAME", "Enterprise DMS"),
            admin_email=os.getenv("ADMIN_EMAIL", "admin@enterprise-dms.local")
        )
    
    def _check_enabled(self) -> bool:
        """Check if email service is enabled"""
        if not self.config.smtp_username or not self.config.smtp_password:
            logger.warning("Email service disabled: Missing SMTP credentials")
            return False
        
        if os.getenv("SMTP_ENABLED", "false").lower() != "true":
            logger.info("Email service disabled: SMTP_ENABLED=false")
            return False
        
        return True
    
    def send_email(
        self,
        to_emails: List[str],
        subject: str,
        body: str,
        html_body: Optional[str] = None,
        attachments: Optional[List[str]] = None
    ) -> bool:
        """Send email with retry logic"""
        if not self.enabled:
            logger.warning("Email service is disabled")
            return False
        
        try:
            message = MIMEMultipart("alternative")
            message["From"] = f"{self.config.from_name} <{self.config.from_email}>"
            message["To"] = ", ".join(to_emails)
            message["Subject"] = subject
            
            # Add plain text body
            text_part = MIMEText(body, "plain")
            message.attach(text_part)
            
            # Add HTML body if provided
            if html_body:
                html_part = MIMEText(html_body, "html")
                message.attach(html_part)
            
            # Add attachments if provided
            if attachments:
                for attachment_path in attachments:
                    if os.path.exists(attachment_path):
                        with open(attachment_path, "rb") as f:
                            part = MIMEBase("application", "octet-stream")
                            part.set_payload(f.read())
                            encoders.encode_base64(part)
                            part.add_header(
                                "Content-Disposition",
                                f"attachment; filename={os.path.basename(attachment_path)}"
                            )
                            message.attach(part)
            
            # Send email
            with smtplib.SMTP(self.config.smtp_server, self.config.smtp_port) as server:
                if self.config.use_tls:
                    server.starttls()
                server.login(self.config.smtp_username, self.config.smtp_password)
                server.send_message(message)
            
            logger.info(f"Email sent successfully to {to_emails}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return False
    
    def send_document_rejection(
        self,
        to_email: str,
        document_name: str,
        rejection_reason: str,
        reviewer_name: str
    ) -> bool:
        """Send document rejection notification"""
        subject = f"Document Rejected: {document_name}"
        body = f"""
Dear User,

Your document "{document_name}" has been rejected by {reviewer_name}.

Rejection Reason:
{rejection_reason}

Please review the document and make necessary corrections.

Best regards,
Enterprise DMS Team
"""
        
        html_body = f"""
<html>
<body>
    <h2>Document Rejected: {document_name}</h2>
    <p>Dear User,</p>
    <p>Your document <strong>"{document_name}"</strong> has been rejected by <strong>{reviewer_name}</strong>.</p>
    
    <h3>Rejection Reason:</h3>
    <p>{rejection_reason}</p>
    
    <p>Please review the document and make necessary corrections.</p>
    
    <p>Best regards,<br>Enterprise DMS Team</p>
</body>
</html>
"""
        
        return self.send_email([to_email], subject, body, html_body)
    
    def send_eta_overdue(
        self,
        to_email: str,
        document_name: str,
        eta_date: str,
        overdue_days: int
    ) -> bool:
        """Send ETA overdue notification"""
        subject = f"ETA Overdue Alert: {document_name}"
        body = f"""
Dear User,

The ETA for document "{document_name}" has passed by {overdue_days} days.

Original ETA: {eta_date}
Overdue by: {overdue_days} days

Please take immediate action to update the ETA or resolve the issue.

Best regards,
Enterprise DMS Team
"""
        
        html_body = f"""
<html>
<body>
    <h2>ETA Overdue Alert: {document_name}</h2>
    <p>Dear User,</p>
    <p>The ETA for document <strong>"{document_name}"</strong> has passed by <strong>{overdue_days} days</strong>.</p>
    
    <h3>Details:</h3>
    <ul>
        <li>Original ETA: {eta_date}</li>
        <li>Overdue by: {overdue_days} days</li>
    </ul>
    
    <p>Please take immediate action to update the ETA or resolve the issue.</p>
    
    <p>Best regards,<br>Enterprise DMS Team</p>
</body>
</html>
"""
        
        return self.send_email([to_email], subject, body, html_body)
    
    def send_suspicious_document_alert(
        self,
        to_email: str,
        document_name: str,
        suspicious_reason: str
    ) -> bool:
        """Send suspicious document alert"""
        subject = f"Security Alert: Suspicious Document Detected"
        body = f"""
Dear Admin,

A suspicious document has been detected:

Document: {document_name}
Reason: {suspicious_reason}

Please review this document immediately.

Best regards,
Enterprise DMS Security System
"""
        
        html_body = f"""
<html>
<body>
    <h2>Security Alert: Suspicious Document Detected</h2>
    <p>Dear Admin,</p>
    <p>A suspicious document has been detected:</p>
    
    <h3>Document Details:</h3>
    <ul>
        <li>Document: <strong>{document_name}</strong></li>
        <li>Reason: <strong>{suspicious_reason}</strong></li>
    </ul>
    
    <p>Please review this document immediately.</p>
    
    <p>Best regards,<br>Enterprise DMS Security System</p>
</body>
</html>
"""
        
        return self.send_email([self.config.admin_email], subject, body, html_body)
    
    def send_system_alert(
        self,
        subject: str,
        message: str,
        priority: str = "normal"
    ) -> bool:
        """Send system alert to admin"""
        body = f"""
System Alert - Priority: {priority}

{message}

Time: {logger.opt(record=True).format(datetime='<green>{time:YYYY-MM-DD HH:mm:ss}</green>')}
"""
        
        return self.send_email([self.config.admin_email], subject, body)


# Singleton instance
_email_service: Optional[ProductionEmailService] = None


def get_email_service() -> ProductionEmailService:
    """Get singleton email service instance"""
    global _email_service
    if _email_service is None:
        _email_service = ProductionEmailService()
    return _email_service