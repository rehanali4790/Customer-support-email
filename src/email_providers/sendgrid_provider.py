"""SendGrid email provider implementation."""
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Email, To, Content
from typing import List
import logging

from .base import BaseEmailProvider, EmailMessage, ReceivedEmail

logger = logging.getLogger(__name__)


class SendGridProvider(BaseEmailProvider):
    """SendGrid email provider."""
    
    def __init__(self, api_key: str, from_email: str):
        """Initialize SendGrid provider.
        
        Args:
            api_key: SendGrid API key
            from_email: Default from email address
        """
        self.client = SendGridAPIClient(api_key)
        self.default_from_email = from_email
    
    async def send_email(self, message: EmailMessage) -> bool:
        """Send email via SendGrid."""
        try:
            sg_message = Mail(
                from_email=Email(str(message.from_email) or self.default_from_email),
                to_emails=[To(str(addr)) for addr in message.to],
                subject=message.subject,
                plain_text_content=Content("text/plain", message.body)
            )
            
            if message.cc:
                sg_message.cc = [Email(str(addr)) for addr in message.cc]
            if message.bcc:
                sg_message.bcc = [Email(str(addr)) for addr in message.bcc]
            if message.reply_to:
                sg_message.reply_to = Email(message.reply_to)
            
            response = self.client.send(sg_message)
            
            if response.status_code in [200, 201, 202]:
                logger.info(f"Email sent successfully via SendGrid to {message.to}")
                return True
            else:
                logger.error(f"SendGrid returned status code: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to send email via SendGrid: {e}")
            return False
    
    async def receive_emails(self, limit: int = 10) -> List[ReceivedEmail]:
        """Receive emails via SendGrid Inbound Parse.
        
        Note: SendGrid requires webhook configuration for receiving emails.
        This is a placeholder implementation.
        """
        logger.warning("SendGrid receive_emails requires webhook configuration")
        return []
    
    async def mark_as_read(self, email_id: str) -> bool:
        """Mark email as read.
        
        Note: SendGrid doesn't have a native mark-as-read feature.
        """
        logger.warning("SendGrid doesn't support mark_as_read natively")
        return True
