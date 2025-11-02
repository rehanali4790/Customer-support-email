"""Email provider factory and exports."""
from .base import BaseEmailProvider, EmailMessage, ReceivedEmail
from .smtp_provider import SMTPProvider
from .sendgrid_provider import SendGridProvider

__all__ = [
    'BaseEmailProvider',
    'EmailMessage',
    'ReceivedEmail',
    'SMTPProvider',
    'SendGridProvider',
    'get_email_provider'
]


def get_email_provider(provider_type: str, **config) -> BaseEmailProvider:
    """Factory function to get email provider.
    
    Args:
        provider_type: Type of provider ('smtp', 'gmail', 'sendgrid')
        **config: Provider-specific configuration
        
    Returns:
        Email provider instance
        
    Raises:
        ValueError: If provider type is not supported
    """
    provider_type = provider_type.lower()
    
    if provider_type in ['smtp', 'gmail']:
        return SMTPProvider(
            smtp_host=config.get('smtp_host'),
            smtp_port=config.get('smtp_port', 587),
            username=config.get('username'),
            password=config.get('password'),
            use_tls=config.get('use_tls', True),
            imap_host=config.get('imap_host'),
            imap_port=config.get('imap_port', 993)
        )
    
    elif provider_type == 'sendgrid':
        return SendGridProvider(
            api_key=config.get('api_key'),
            from_email=config.get('from_email')
        )
    
    else:
        raise ValueError(f"Unsupported email provider: {provider_type}")
