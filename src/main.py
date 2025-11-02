"""Main application entry point."""
import os
import asyncio
import logging
from pathlib import Path
from dotenv import load_dotenv
import yaml
from rich.console import Console
from rich.logging import RichHandler

from email_providers import get_email_provider
from knowledge_base import KnowledgeBase, ConversationHistory
from agent import EmailAgentGraph

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    handlers=[RichHandler(rich_tracebacks=True)]
)
logger = logging.getLogger(__name__)
console = Console()


class EmailAgent:
    """Main email agent application."""
    
    def __init__(self, config_path: str = "config.yaml", env_path: str = ".env"):
        """Initialize the email agent.
        
        Args:
            config_path: Path to configuration file
            env_path: Path to environment file
        """
        # Load environment variables
        load_dotenv(env_path)
        
        # Load configuration
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        # Initialize components
        self.email_provider = self._setup_email_provider()
        self.knowledge_base = self._setup_knowledge_base()
        self.conversation_history = ConversationHistory(
            persist_directory=os.getenv('CONVERSATION_DB_PATH', './data/conversations')
        )
        
        # Initialize agent graph
        self.agent = EmailAgentGraph(
            config=self.config,
            knowledge_base=self.knowledge_base,
            conversation_history=self.conversation_history,
            email_provider=self.email_provider
        )
        
        logger.info("Email Agent initialized successfully")
    
    def _setup_email_provider(self):
        """Setup email provider based on configuration."""
        provider_type = os.getenv('EMAIL_PROVIDER', 'smtp').lower()
        
        if provider_type == 'smtp':
            return get_email_provider(
                provider_type='smtp',
                smtp_host=os.getenv('SMTP_HOST'),
                smtp_port=int(os.getenv('SMTP_PORT', 587)),
                username=os.getenv('SMTP_USERNAME'),
                password=os.getenv('SMTP_PASSWORD'),
                use_tls=os.getenv('SMTP_USE_TLS', 'true').lower() == 'true'
            )
        elif provider_type == 'gmail':
            return get_email_provider(
                provider_type='gmail',
                smtp_host='smtp.gmail.com',
                smtp_port=587,
                username=os.getenv('GMAIL_ADDRESS'),
                password=os.getenv('GMAIL_APP_PASSWORD'),
                use_tls=True,
                imap_host='imap.gmail.com'
            )
        elif provider_type == 'sendgrid':
            return get_email_provider(
                provider_type='sendgrid',
                api_key=os.getenv('SENDGRID_API_KEY'),
                from_email=os.getenv('SENDGRID_FROM_EMAIL')
            )
        else:
            raise ValueError(f"Unsupported email provider: {provider_type}")
    
    def _setup_knowledge_base(self):
        """Setup knowledge base."""
        kb = KnowledgeBase(
            vector_db_type=os.getenv('VECTOR_DB_TYPE', 'chroma'),
            persist_directory=os.getenv('VECTOR_DB_PATH', './data/vectordb'),
            embedding_model=self.config['vector_db']['embedding_model'],
            chunk_size=self.config['vector_db']['chunk_size'],
            chunk_overlap=self.config['vector_db']['chunk_overlap']
        )
        
        # Try to load existing index
        kb.load_index()
        
        # If no index exists, build from documents
        if kb.vectorstore is None:
            knowledge_base_path = os.getenv('KNOWLEDGE_BASE_PATH', './knowledge_base')
            if Path(knowledge_base_path).exists():
                console.print(f"[yellow]Building knowledge base from {knowledge_base_path}...[/yellow]")
                kb.build_index(knowledge_base_path)
            else:
                console.print(f"[red]Warning: Knowledge base path not found: {knowledge_base_path}[/red]")
                console.print("[yellow]Creating empty knowledge base. Add documents later.[/yellow]")
        
        return kb
    
    async def run_once(self):
        """Process emails once."""
        console.print("[bold blue]Checking for new emails...[/bold blue]")
        
        try:
            # Receive emails
            emails = await self.email_provider.receive_emails(limit=10)
            
            if not emails:
                console.print("[yellow]No new emails found.[/yellow]")
                return
            
            console.print(f"[green]Found {len(emails)} new email(s)[/green]")
            
            # Process each email
            for email in emails:
                console.print(f"\n[bold]Processing email: {email.subject}[/bold]")
                
                email_data = {
                    'id': email.id,
                    'from_email': email.from_email,
                    'to': email.to,
                    'subject': email.subject,
                    'body': email.body,
                    'received_at': email.received_at
                }
                
                # Process through agent
                result = await self.agent.process_email(email_data)
                
                if result.get('sent'):
                    console.print(f"[green]✓ Email processed and sent successfully[/green]")
                    # Mark as read
                    await self.email_provider.mark_as_read(email.id)
                elif result.get('error'):
                    console.print(f"[red]✗ Error: {result['error']}[/red]")
                else:
                    console.print(f"[yellow]⚠ Email processed but not sent (human declined)[/yellow]")
                
        except Exception as e:
            logger.error(f"Error in run_once: {e}")
            console.print(f"[red]Error: {e}[/red]")
    
    async def run_continuous(self, interval: int = 60):
        """Run continuously, checking for emails at intervals.
        
        Args:
            interval: Check interval in seconds
        """
        console.print(f"[bold green]Email Agent running in continuous mode (checking every {interval}s)[/bold green]")
        console.print("[dim]Press Ctrl+C to stop[/dim]\n")
        
        try:
            while True:
                await self.run_once()
                console.print(f"\n[dim]Waiting {interval} seconds before next check...[/dim]")
                await asyncio.sleep(interval)
        except KeyboardInterrupt:
            console.print("\n[yellow]Stopping email agent...[/yellow]")
    
    def rebuild_knowledge_base(self, documents_path: str = None):
        """Rebuild the knowledge base from documents.
        
        Args:
            documents_path: Path to documents directory (optional)
        """
        if documents_path is None:
            documents_path = os.getenv('KNOWLEDGE_BASE_PATH', './knowledge_base')
        
        console.print(f"[yellow]Rebuilding knowledge base from {documents_path}...[/yellow]")
        self.knowledge_base.build_index(documents_path)
        console.print("[green]Knowledge base rebuilt successfully![/green]")


async def main():
    """Main entry point."""
    import sys
    
    # Check if .env exists
    if not Path('.env').exists():
        console.print("[red]Error: .env file not found![/red]")
        console.print("[yellow]Please copy .env.example to .env and configure it.[/yellow]")
        sys.exit(1)
    
    # Initialize agent
    agent = EmailAgent()
    
    # Check command line arguments
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == 'once':
            await agent.run_once()
        elif command == 'rebuild-kb':
            agent.rebuild_knowledge_base()
        elif command == 'continuous':
            interval = int(sys.argv[2]) if len(sys.argv) > 2 else 60
            await agent.run_continuous(interval)
        else:
            console.print(f"[red]Unknown command: {command}[/red]")
            console.print("\nUsage:")
            console.print("  python -m src.main once           - Process emails once")
            console.print("  python -m src.main continuous [N] - Run continuously (check every N seconds)")
            console.print("  python -m src.main rebuild-kb     - Rebuild knowledge base")
    else:
        # Default: run once
        await agent.run_once()


if __name__ == "__main__":
    asyncio.run(main())
