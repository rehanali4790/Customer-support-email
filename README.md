# 🤖 AI Email Support Agent

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![LangChain](https://img.shields.io/badge/LangChain-0.1+-green.svg)](https://langchain.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

An intelligent, production-ready email support automation system powered by LangChain, LangGraph, and OpenAI GPT-4. Automatically processes customer emails with context-aware responses using RAG (Retrieval-Augmented Generation), smart escalation to human specialists, and comprehensive conversation tracking.

## ✨ Key Features

- **🎯 Intelligent Email Classification** - AI-powered categorization by type, urgency, and complexity
- **📚 RAG-Powered Responses** - Context-aware replies using your knowledge base via vector search (ChromaDB/FAISS)
- **🚀 Smart Escalation System** - Automatically routes complex/urgent cases to human specialists
- **💬 Conversation Memory** - Maintains conversation history for context-aware multi-turn interactions
- **📧 Multi-Provider Support** - Works with SMTP/IMAP, Gmail, and SendGrid
- **🔄 Agentic Workflow** - Built with LangGraph for robust state management
- **🌐 RESTful API** - Easy integration with existing systems
- **📊 Real-time Monitoring** - Comprehensive logging and conversation tracking

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Customer Email                            │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
          ┌──────────────────────┐
          │  Email Classification │ ◄── OpenAI GPT-4
          │  (Category, Urgency,  │
          │   Complexity)         │
          └──────────┬────────────┘
                     │
                     ▼
          ┌──────────────────────┐
          │  Context Retrieval    │ ◄── Vector DB (Chroma/FAISS)
          │  (Knowledge Base      │
          │   Search)             │
          └──────────┬────────────┘
                     │
                     ▼
          ┌──────────────────────┐
          │  Response Generation  │ ◄── OpenAI GPT-4 + Context
          │  (AI Draft)           │
          └──────────┬────────────┘
                     │
                     ▼
          ┌──────────────────────┐
          │  Smart Router         │
          └──────────┬────────────┘
                     │
        ┌────────────┴────────────┐
        │                         │
        ▼                         ▼
┌────────────────┐      ┌──────────────────┐
│ Simple/Low     │      │ Complex/High     │
│ Urgency        │      │ Urgency          │
│                │      │                  │
│ ✓ Auto-send    │      │ ✓ Hold customer  │
│   AI response  │      │ ✓ Notify admin   │
│                │      │ ✓ Provide draft  │
└────────────────┘      └──────────────────┘
```

## 🚀 Quick Start

### Prerequisites

- Python 3.10 or higher
- OpenAI API key ([Get one here](https://platform.openai.com/api-keys))
- Email account with SMTP/IMAP access (Hostinger, Gmail, etc.) or SendGrid account

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/email_Agent.git
   cd email_Agent
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   
   # On Windows
   venv\Scripts\activate
   
   # On Linux/Mac
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run interactive setup**
   ```bash
   python setup.py
   ```
   
   Or manually configure:
   
5. **Configure environment** (if not using setup.py)
   ```bash
   cp .env.example .env
   # Edit .env with your credentials
   ```

6. **Add knowledge base documents**
   ```bash
   # Add your FAQs, documentation, policies to ./knowledge_base/
   # Supports: .txt, .md, .pdf, .csv
   ```
7. **Start the API server**
   ```bash
   python run_api.py
   ```

Visit `http://localhost:5000/api/docs` for interactive Swagger documentation.

## ⚙️ Configuration

### Environment Variables (`.env`)

```bash
# OpenAI API Key (Required)
OPENAI_API_KEY=sk-...

# Email Provider Configuration
EMAIL_PROVIDER=smtp  # Options: smtp, gmail, sendgrid

# SMTP Configuration (Hostinger, etc.)
SMTP_HOST=smtp.hostinger.com
SMTP_PORT=587
SMTP_USERNAME=support@yourdomain.com
SMTP_PASSWORD=your_password
SMTP_USE_TLS=true

# IMAP for receiving emails
IMAP_HOST=imap.hostinger.com
IMAP_PORT=993

# Gmail Configuration (Alternative)
GMAIL_ADDRESS=your_email@gmail.com
GMAIL_APP_PASSWORD=your_16_char_app_password

# SendGrid Configuration (Alternative)
SENDGRID_API_KEY=SG.xxx
SENDGRID_FROM_EMAIL=support@yourdomain.com

# Admin Configuration
ADMIN_EMAIL=admin@yourdomain.com

# Storage Paths
VECTOR_DB_TYPE=chroma  # Options: chroma, faiss
VECTOR_DB_PATH=./data/vectordb
CONVERSATION_DB_PATH=./data/conversations
KNOWLEDGE_BASE_PATH=./knowledge_base

# Application Settings
API_PORT=5000
LOG_LEVEL=INFO
```

### Agent Configuration (`config.yaml`)

```yaml
agent:
  model: "gpt-4-turbo-preview"  # or gpt-4o-mini for cost savings
  temperature: 0.7
  max_tokens: 1000

classification:
  categories:
    - technical
    - general
    - sales
    - support
    - billing
    - feedback
  urgency_levels:
    - low
    - medium
    - high
    - critical

human_in_loop:
  enabled: true
  triggers:
    - urgency: ["high", "critical"]  # Only escalate high/critical
    - complexity_score: 0.7          # Escalate if complexity >= 0.7
    - sensitive_topics: ["refund", "complaint", "legal", "cancellation"]

vector_db:
  chunk_size: 1000
  chunk_overlap: 200
  embedding_model: "text-embedding-3-small"
  top_k: 3  # Number of context chunks to retrieve
```

## 📚 API Endpoints

### Health Check
```bash
GET /health
```

### Email Processing

**Process Single Email**
```bash
POST /api/v1/email/process
Content-Type: application/json

{
  "from_email": "customer@example.com",
  "subject": "Password reset help",
  "body": "I forgot my password, how do I reset it?"
}
```

**Batch Process Unread Emails**
```bash
POST /api/v1/email/batch-process
Content-Type: application/json

{
  "limit": 10
}
```

**Get Inbox**
```bash
GET /api/v1/email/inbox?limit=20
```

### Knowledge Base

**Rebuild Knowledge Base**
```bash
POST /api/v1/knowledge-base/rebuild
```

**Search Knowledge Base**
```bash
POST /api/v1/knowledge-base/search
Content-Type: application/json

{
  "query": "refund policy",
  "top_k": 3
}
```

### Conversations

**List All Conversations**
```bash
GET /api/v1/conversations
```

**Get Specific Conversation**
```bash
GET /api/v1/conversations/<conversation_id>
```

## 🎯 How It Works

### 1. Email Classification
The AI analyzes each incoming email to determine:
- **Category**: billing, technical, general, sales, support, feedback
- **Urgency**: low, medium, high, critical
- **Complexity Score**: 0.0 to 1.0 (simple to complex)
- **Sensitive Topics**: refunds, cancellations, complaints, legal issues

### 2. Context Retrieval (RAG)
- Searches your knowledge base using semantic similarity
- Retrieves top-k most relevant document chunks
- Uses OpenAI embeddings (`text-embedding-3-small`)
- Powered by ChromaDB or FAISS vector database

### 3. Response Generation
Generates personalized responses using:
- Email classification context
- Retrieved knowledge base chunks
- Customer name extraction
- Professional AI persona (FRIDAY)
- Automatic signature addition

### 4. Smart Decision Making

**Auto-Handle (No Escalation):**
- ✅ Low or medium urgency
- ✅ Low complexity (< 0.7)
- ✅ Simple questions with clear answers in knowledge base
- → Sends AI-generated response immediately

**Escalate to Human:**
- ⚠️ High or critical urgency
- ⚠️ High complexity (>= 0.7)
- ⚠️ Sensitive topics requiring human judgment
- → Sends holding response to customer
- → Forwards to admin with AI draft and full context




### Key Metrics to Track
- **Response Time**: Time to process and respond to emails
- **Classification Accuracy**: Correct categorization rate
- **Escalation Rate**: % of emails escalated to humans
- **Knowledge Base Hit Rate**: % of queries answered from KB
- **Customer Satisfaction**: CSAT scores from follow-ups

### Conversation History
All conversations are stored in `data/conversations/<email_id>.json` with:
- Full email thread
- Classification details
- Retrieved context
- AI responses
- Timestamps



## 🔧 Advanced Usage

### Custom Email Providers

Extend `src/email_providers/base.py`:

```python
from src.email_providers.base import EmailProvider

class CustomProvider(EmailProvider):
    async def receive_emails(self, limit=10):
        # Your implementation
        pass
    
    async def send_email(self, message):
        # Your implementation
        pass
```

### Custom Classification Rules

Modify `src/agent/nodes.py`:

```python
def _check_human_review_required(self, classification):
    # Add your custom escalation logic
    if "vip_customer" in classification.get("tags", []):
        return True
    # ... existing logic
```

### Webhook Integration

Add webhook support in `src/api/app.py`:

```python
@app.route('/webhooks/email', methods=['POST'])
def email_webhook():
    data = request.json
    # Process webhook payload
    result = await agent.process_email(data)
    return jsonify(result)
```

## 🤝 Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Setup

```bash
# Install dev dependencies
pip install -r requirements-dev.txt

# Code formatting
black src/

# Linting
flake8 src/

# Type checking
mypy src/
```

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **[LangChain](https://langchain.com/)** - LLM application framework
- **[LangGraph](https://langchain-ai.github.io/langgraph/)** - Agentic workflow orchestration
- **[OpenAI](https://openai.com/)** - GPT-4 and embedding models
- **[ChromaDB](https://www.trychroma.com/)** - Vector database
- **[FAISS](https://github.com/facebookresearch/faiss)** - Efficient similarity search




---

**Built with ❤️ by [Rehan Ali](https://github.com/rehanali4790)**

⭐ Star this repo if you find it useful!
