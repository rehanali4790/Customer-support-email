"""Base email provider interface."""
from abc import ABC, abstractmethod
from typing import List, Dict, Any
from pydantic import BaseModel, EmailStr


class EmailMessage(BaseModel):
    """Email message model."""
    to: List[EmailStr]
    subject: str
    body: str
    from_email: EmailStr
    cc: List[EmailStr] = []
    bcc: List[EmailStr] = []
    reply_to: str = None


class ReceivedEmail(BaseModel):
    """Received email model."""
    id: str
    from_email: str
    to: List[str]
    subject: str
    body: str
    received_at: str
    headers: Dict[str, Any] = {}


class BaseEmailProvider(ABC):
    """Base class for email providers."""
    
    @abstractmethod
    async def send_email(self, message: EmailMessage) -> bool:
        """Send an email message.
        
        Args:
            message: Email message to send
            
        Returns:
            True if successful, False otherwise
        """
        pass
    
    @abstractmethod
    async def receive_emails(self, limit: int = 10) -> List[ReceivedEmail]:
        """Receive emails.
        
        Args:
            limit: Maximum number of emails to retrieve
            
        Returns:
            List of received emails
        """
        pass
    
    @abstractmethod
    async def mark_as_read(self, email_id: str) -> bool:
        """Mark an email as read.
        
        Args:
            email_id: ID of the email to mark as read
            
        Returns:
            True if successful, False otherwise
        """
        pass
