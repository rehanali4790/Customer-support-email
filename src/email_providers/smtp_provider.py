"""SMTP email provider implementation."""
import aiosmtplib
import imaplib
import email
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List
from datetime import datetime
import logging
import asyncio
from concurrent.futures import ThreadPoolExecutor

from .base import BaseEmailProvider, EmailMessage, ReceivedEmail

logger = logging.getLogger(__name__)


class SMTPProvider(BaseEmailProvider):
    """SMTP email provider."""
    
    def __init__(
        self,
        smtp_host: str,
        smtp_port: int,
        username: str,
        password: str,
        use_tls: bool = True,
        imap_host: str = None,
        imap_port: int = 993
    ):
        """Initialize SMTP provider.
        
        Args:
            smtp_host: SMTP server hostname
            smtp_port: SMTP server port
            username: Email username
            password: Email password
            use_tls: Whether to use TLS
            imap_host: IMAP server hostname (for receiving)
            imap_port: IMAP server port
        """
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.username = username
        self.password = password
        self.use_tls = use_tls
        self.imap_host = imap_host or smtp_host.replace('smtp', 'imap')
        self.imap_port = imap_port
    
    async def send_email(self, message: EmailMessage) -> bool:
        """Send email via SMTP."""
        try:
            msg = MIMEMultipart()
            msg['From'] = str(message.from_email)
            msg['To'] = ', '.join(str(addr) for addr in message.to)
            msg['Subject'] = message.subject
            
            if message.cc:
                msg['Cc'] = ', '.join(str(addr) for addr in message.cc)
            if message.reply_to:
                msg['Reply-To'] = message.reply_to
            
            msg.attach(MIMEText(message.body, 'plain'))
            
            async with aiosmtplib.SMTP(
                hostname=self.smtp_host,
                port=self.smtp_port,
                start_tls=self.use_tls,
                use_tls=False  # Don't use implicit TLS, use STARTTLS instead
            ) as smtp:
                await smtp.login(self.username, self.password)
                await smtp.send_message(msg)
            
            logger.info(f"Email sent successfully to {message.to}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return False
    
    async def receive_emails(self, limit: int = 10) -> List[ReceivedEmail]:
        """Receive emails via IMAP."""
        try:
            # Use ThreadPoolExecutor to run blocking IMAP operations
            loop = asyncio.get_event_loop()
            mail = await loop.run_in_executor(None, lambda: imaplib.IMAP4_SSL(self.imap_host, self.imap_port, timeout=30))
            await loop.run_in_executor(None, mail.login, self.username, self.password)
            await loop.run_in_executor(None, mail.select, 'inbox')
            
            # Search for unseen emails
            _, message_numbers = await loop.run_in_executor(None, mail.search, None, 'UNSEEN')
            
            emails = []
            for num in message_numbers[0].split()[:limit]:
                _, msg_data = await loop.run_in_executor(None, mail.fetch, num, '(RFC822)')
                email_body = msg_data[0][1]
                email_message = email.message_from_bytes(email_body)
                
                # Extract body
                body = ""
                if email_message.is_multipart():
                    for part in email_message.walk():
                        if part.get_content_type() == "text/plain":
                            body = part.get_payload(decode=True).decode()
                            break
                else:
                    body = email_message.get_payload(decode=True).decode()
                
                received_email = ReceivedEmail(
                    id=num.decode(),
                    from_email=email_message['From'],
                    to=[email_message['To']],
                    subject=email_message['Subject'] or "",
                    body=body,
                    received_at=email_message['Date'] or datetime.now().isoformat(),
                    headers=dict(email_message.items())
                )
                emails.append(received_email)
            
            await loop.run_in_executor(None, mail.close)
            await loop.run_in_executor(None, mail.logout)
            
            return emails
            
        except Exception as e:
            logger.error(f"Failed to receive emails: {e}")
            return []
    
    async def mark_as_read(self, email_id: str) -> bool:
        """Mark email as read."""
        try:
            loop = asyncio.get_event_loop()
            mail = await loop.run_in_executor(None, lambda: imaplib.IMAP4_SSL(self.imap_host, self.imap_port, timeout=30))
            await loop.run_in_executor(None, mail.login, self.username, self.password)
            await loop.run_in_executor(None, mail.select, 'inbox')
            
            await loop.run_in_executor(None, mail.store, email_id.encode(), '+FLAGS', '\\Seen')
            
            await loop.run_in_executor(None, mail.close)
            await loop.run_in_executor(None, mail.logout)
            return True
            
        except Exception as e:
            logger.error(f"Failed to mark email as read: {e}")
            return False
