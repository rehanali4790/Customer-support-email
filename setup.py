"""Setup script for Email Agent."""
import os
import shutil
from pathlib import Path
from rich.console import Console
from rich.prompt import Prompt, Confirm

console = Console()


def setup_email_agent():
    """Interactive setup for Email Agent."""
    console.print("[bold blue]Email Agent Setup[/bold blue]\n")
    
    # Create directories
    dirs = ['data/vectordb', 'data/conversations', 'knowledge_base', 'logs']
    for dir_path in dirs:
        Path(dir_path).mkdir(parents=True, exist_ok=True)
    console.print("[green]✓ Created directories[/green]")
    
    # Setup .env file
    if not Path('.env').exists():
        console.print("\n[yellow]Setting up environment variables...[/yellow]")
        
        # OpenAI API Key
        openai_key = Prompt.ask("Enter your OpenAI API key", password=True)
        
        # Email provider
        provider = Prompt.ask(
            "Choose email provider",
            choices=["smtp", "gmail", "sendgrid"],
            default="smtp"
        )
        
        env_content = f"OPENAI_API_KEY={openai_key}\n"
        env_content += f"EMAIL_PROVIDER={provider}\n\n"
        
        if provider in ['smtp', 'gmail']:
            if provider == 'gmail':
                console.print("\n[yellow]For Gmail, use App Password: https://support.google.com/accounts/answer/185833[/yellow]")
                smtp_host = "smtp.gmail.com"
                smtp_port = "587"
                username = Prompt.ask("Gmail address")
                password = Prompt.ask("Gmail App Password", password=True)
            else:
                smtp_host = Prompt.ask("SMTP host")
                smtp_port = Prompt.ask("SMTP port", default="587")
                username = Prompt.ask("Email username")
                password = Prompt.ask("Email password", password=True)
            
            env_content += f"SMTP_HOST={smtp_host}\n"
            env_content += f"SMTP_PORT={smtp_port}\n"
            env_content += f"SMTP_USERNAME={username}\n"
            env_content += f"SMTP_PASSWORD={password}\n"
            env_content += "SMTP_USE_TLS=true\n"
            
        elif provider == 'sendgrid':
            api_key = Prompt.ask("SendGrid API key", password=True)
            from_email = Prompt.ask("From email address")
            
            env_content += f"SENDGRID_API_KEY={api_key}\n"
            env_content += f"SENDGRID_FROM_EMAIL={from_email}\n"
        
        # Vector DB settings
        env_content += "\n# Vector DB Configuration\n"
        vector_db = Prompt.ask(
            "Choose vector database",
            choices=["chroma", "faiss"],
            default="chroma"
        )
        env_content += f"VECTOR_DB_TYPE={vector_db}\n"
        env_content += "VECTOR_DB_PATH=./data/vectordb\n"
        
        # Other settings
        env_content += "\n# Other Settings\n"
        env_content += "CONVERSATION_DB_PATH=./data/conversations\n"
        env_content += "KNOWLEDGE_BASE_PATH=./knowledge_base\n"
        env_content += "HUMAN_REVIEW_REQUIRED_URGENCY=high\n"
        env_content += "HUMAN_REVIEW_COMPLEXITY_THRESHOLD=0.7\n"
        env_content += "LOG_LEVEL=INFO\n"
        
        # Write .env file
        with open('.env', 'w') as f:
            f.write(env_content)
        
        console.print("[green]✓ Created .env file[/green]")
    else:
        console.print("[yellow]⚠ .env file already exists, skipping...[/yellow]")
    
    # Knowledge base setup
    console.print("\n[yellow]Knowledge Base Setup[/yellow]")
    has_docs = Confirm.ask("Do you have documents to add to the knowledge base now?")
    
    if has_docs:
        console.print("\nPlease add your documents (PDF, TXT, MD, CSV) to the 'knowledge_base' directory.")
        console.print("Then run: python -m src.main rebuild-kb")
    else:
        console.print("\n[dim]You can add documents to 'knowledge_base' directory later.")
        console.print("Run 'python -m src.main rebuild-kb' to index them.[/dim]")
    
    # Final instructions
    console.print("\n[bold green]Setup complete! 🎉[/bold green]\n")
    console.print("[bold]Next steps:[/bold]")
    console.print("1. Add documents to the 'knowledge_base' directory")
    console.print("2. Run: [cyan]python -m src.main rebuild-kb[/cyan] to build the knowledge base")
    console.print("3. Run: [cyan]python -m src.main once[/cyan] to process emails once")
    console.print("4. Or run: [cyan]python -m src.main continuous[/cyan] for continuous monitoring\n")


if __name__ == "__main__":
    setup_email_agent()
