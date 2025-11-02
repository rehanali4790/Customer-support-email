"""Flask API for Email Agent."""
import os
import asyncio
from flask import Flask, request, jsonify
from flask_cors import CORS
from flasgger import Swagger, swag_from
from dotenv import load_dotenv
import yaml
from pathlib import Path
import logging

from ..email_providers import get_email_provider
from ..knowledge_base import KnowledgeBase, ConversationHistory
from ..agent import EmailAgentGraph

# Load environment
load_dotenv()

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
CORS(app)

# Swagger configuration
swagger_config = {
    "headers": [],
    "specs": [
        {
            "endpoint": 'apispec',
            "route": '/apispec.json',
            "rule_filter": lambda rule: True,
            "model_filter": lambda tag: True,
        }
    ],
    "static_url_path": "/flasgger_static",
    "swagger_ui": True,
    "specs_route": "/api/docs"
}

swagger_template = {
    "swagger": "2.0",
    "info": {
        "title": "AI Email Agent API",
        "description": "Production-ready AI Email Agent with LangChain and LangGraph",
        "version": "1.0.0",
        "contact": {
            "name": "Email Agent Support",
            "email": "support@example.com"
        }
    },
    "schemes": ["http", "https"],
    "tags": [
        {"name": "Email", "description": "Email processing endpoints"},
        {"name": "Knowledge Base", "description": "Knowledge base management"},
        {"name": "Conversation", "description": "Conversation history"},
        {"name": "Health", "description": "Health check endpoints"}
    ]
}

swagger = Swagger(app, config=swagger_config, template=swagger_template)

# Global agent instance
email_agent = None


def get_agent():
    """Get or initialize the email agent."""
    global email_agent
    if email_agent is None:
        # Load configuration
        config_path = Path("config.yaml")
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        # Initialize components
        email_provider = _setup_email_provider()
        knowledge_base = _setup_knowledge_base(config)
        conversation_history = ConversationHistory(
            persist_directory=os.getenv('CONVERSATION_DB_PATH', './data/conversations')
        )
        
        # Initialize agent
        email_agent = EmailAgentGraph(
            config=config,
            knowledge_base=knowledge_base,
            conversation_history=conversation_history,
            email_provider=email_provider
        )
        logger.info("Email Agent initialized")
    
    return email_agent


def _setup_email_provider():
    """Setup email provider."""
    provider_type = os.getenv('EMAIL_PROVIDER', 'smtp').lower()
    
    if provider_type == 'smtp':
        return get_email_provider(
            provider_type='smtp',
            smtp_host=os.getenv('SMTP_HOST'),
            smtp_port=int(os.getenv('SMTP_PORT', 587)),
            username=os.getenv('SMTP_USERNAME'),
            password=os.getenv('SMTP_PASSWORD'),
            use_tls=os.getenv('SMTP_USE_TLS', 'true').lower() == 'true',
            imap_host=os.getenv('IMAP_HOST', os.getenv('SMTP_HOST')),
            imap_port=int(os.getenv('IMAP_PORT', 993))
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


def _setup_knowledge_base(config):
    """Setup knowledge base."""
    kb = KnowledgeBase(
        vector_db_type=os.getenv('VECTOR_DB_TYPE', 'chroma'),
        persist_directory=os.getenv('VECTOR_DB_PATH', './data/vectordb'),
        embedding_model=config['vector_db']['embedding_model'],
        chunk_size=config['vector_db']['chunk_size'],
        chunk_overlap=config['vector_db']['chunk_overlap']
    )
    kb.load_index()
    return kb


# ==================== Health Check ====================

@app.route('/health', methods=['GET'])
@swag_from({
    'tags': ['Health'],
    'summary': 'Health check endpoint',
    'responses': {
        200: {
            'description': 'Service is healthy',
            'schema': {
                'type': 'object',
                'properties': {
                    'status': {'type': 'string'},
                    'version': {'type': 'string'}
                }
            }
        }
    }
})
def health_check():
    """Health check endpoint."""
    return jsonify({
        'status': 'healthy',
        'version': '1.0.0'
    }), 200


# ==================== Email Processing ====================

@app.route('/api/v1/email/process', methods=['POST'])
@swag_from({
    'tags': ['Email'],
    'summary': 'Process a single email',
    'description': 'Process an email through the AI agent workflow',
    'parameters': [
        {
            'name': 'body',
            'in': 'body',
            'required': True,
            'schema': {
                'type': 'object',
                'required': ['from_email', 'subject', 'body'],
                'properties': {
                    'from_email': {'type': 'string', 'example': 'user@example.com'},
                    'to': {'type': 'array', 'items': {'type': 'string'}, 'example': ['support@mycompany.com']},
                    'subject': {'type': 'string', 'example': 'Question about product'},
                    'body': {'type': 'string', 'example': 'I need help with my account'},
                    'auto_send': {'type': 'boolean', 'example': False, 'description': 'Auto-send without human review'}
                }
            }
        }
    ],
    'responses': {
        200: {
            'description': 'Email processed successfully',
            'schema': {
                'type': 'object',
                'properties': {
                    'email_id': {'type': 'string'},
                    'classification': {'type': 'object'},
                    'draft_response': {'type': 'string'},
                    'human_review_required': {'type': 'boolean'},
                    'sent': {'type': 'boolean'}
                }
            }
        },
        400: {'description': 'Invalid request'},
        500: {'description': 'Internal server error'}
    }
})
def process_email():
    """Process a single email."""
    try:
        data = request.get_json()
        
        # Validate required fields
        if not all(k in data for k in ['from_email', 'subject', 'body']):
            return jsonify({'error': 'Missing required fields'}), 400
        
        # Create email data
        import uuid
        from datetime import datetime
        
        email_data = {
            'id': str(uuid.uuid4()),
            'from_email': data['from_email'],
            'to': data.get('to', []),
            'subject': data['subject'],
            'body': data['body'],
            'received_at': datetime.now().isoformat()
        }
        
        # Process email
        agent = get_agent()
        result = asyncio.run(agent.process_email(email_data))
        
        # Prepare response
        response = {
            'email_id': result['email_id'],
            'classification': result['classification'].dict() if result.get('classification') else None,
            'draft_response': result.get('draft_response'),
            'human_review_required': result.get('human_review_required', False),
            'sent': result.get('sent', False),
            'error': result.get('error')
        }
        
        return jsonify(response), 200
        
    except Exception as e:
        logger.error(f"Error processing email: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/v1/email/inbox', methods=['GET'])
@swag_from({
    'tags': ['Email'],
    'summary': 'Fetch unread emails from inbox',
    'parameters': [
        {
            'name': 'limit',
            'in': 'query',
            'type': 'integer',
            'default': 10,
            'description': 'Maximum number of emails to fetch'
        }
    ],
    'responses': {
        200: {
            'description': 'List of unread emails',
            'schema': {
                'type': 'object',
                'properties': {
                    'count': {'type': 'integer'},
                    'emails': {
                        'type': 'array',
                        'items': {
                            'type': 'object',
                            'properties': {
                                'id': {'type': 'string'},
                                'from_email': {'type': 'string'},
                                'subject': {'type': 'string'},
                                'body': {'type': 'string'},
                                'received_at': {'type': 'string'}
                            }
                        }
                    }
                }
            }
        }
    }
})
def fetch_inbox():
    """Fetch unread emails from inbox."""
    try:
        limit = request.args.get('limit', 10, type=int)
        agent = get_agent()
        
        emails = asyncio.run(agent.email_provider.receive_emails(limit=limit))
        
        return jsonify({
            'count': len(emails),
            'emails': [email.dict() for email in emails]
        }), 200
        
    except Exception as e:
        logger.error(f"Error fetching inbox: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/v1/email/batch-process', methods=['POST'])
@swag_from({
    'tags': ['Email'],
    'summary': 'Process all unread emails in inbox',
    'parameters': [
        {
            'name': 'body',
            'in': 'body',
            'schema': {
                'type': 'object',
                'properties': {
                    'limit': {'type': 'integer', 'default': 10}
                }
            }
        }
    ],
    'responses': {
        200: {
            'description': 'Batch processing results',
            'schema': {
                'type': 'object',
                'properties': {
                    'total': {'type': 'integer'},
                    'processed': {'type': 'integer'},
                    'sent': {'type': 'integer'},
                    'requires_review': {'type': 'integer'},
                    'errors': {'type': 'integer'}
                }
            }
        }
    }
})
def batch_process():
    """Process all unread emails."""
    try:
        data = request.get_json() or {}
        limit = data.get('limit', 10)
        
        agent = get_agent()
        approver_email = os.getenv('APPROVER_EMAIL', '').lower()
        emails = asyncio.run(agent.email_provider.receive_emails(limit=limit))
        
        stats = {
            'total': len(emails),
            'processed': 0,
            'sent': 0,
            'requires_review': 0,
            'errors': 0,
            'skipped_admin': 0
        }
        
        # Process each email
        for email in emails:
            # Skip emails from admin (to avoid processing admin's own replies)
            if approver_email and approver_email in email.from_email.lower():
                logger.info(f"Skipping admin email from {email.from_email}")
                stats['skipped_admin'] += 1
                asyncio.run(agent.email_provider.mark_as_read(email.id))
                continue
            
            email_data = {
                'id': email.id,
                'from_email': email.from_email,
                'to': email.to,
                'subject': email.subject,
                'body': email.body,
                'received_at': email.received_at
            }
            
            result = asyncio.run(agent.process_email(email_data))
            stats['processed'] += 1
            
            if result.get('sent'):
                stats['sent'] += 1
                asyncio.run(agent.email_provider.mark_as_read(email.id))
            elif result.get('human_review_required'):
                stats['requires_review'] += 1
            elif result.get('error'):
                stats['errors'] += 1
        
        return jsonify(stats), 200
        
    except Exception as e:
        logger.error(f"Error in batch processing: {e}")
        return jsonify({'error': str(e)}), 500


# ==================== Knowledge Base ====================

@app.route('/api/v1/knowledge-base/rebuild', methods=['POST'])
@swag_from({
    'tags': ['Knowledge Base'],
    'summary': 'Rebuild knowledge base from documents',
    'parameters': [
        {
            'name': 'body',
            'in': 'body',
            'schema': {
                'type': 'object',
                'properties': {
                    'documents_path': {'type': 'string', 'description': 'Path to documents directory'}
                }
            }
        }
    ],
    'responses': {
        200: {'description': 'Knowledge base rebuilt successfully'},
        500: {'description': 'Error rebuilding knowledge base'}
    }
})
def rebuild_knowledge_base():
    """Rebuild the knowledge base."""
    try:
        data = request.get_json() or {}
        documents_path = data.get('documents_path', os.getenv('KNOWLEDGE_BASE_PATH', './knowledge_base'))
        
        agent = get_agent()
        agent.knowledge_base.build_index(documents_path)
        
        return jsonify({'message': 'Knowledge base rebuilt successfully'}), 200
        
    except Exception as e:
        logger.error(f"Error rebuilding knowledge base: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/v1/knowledge-base/search', methods=['POST'])
@swag_from({
    'tags': ['Knowledge Base'],
    'summary': 'Search knowledge base',
    'parameters': [
        {
            'name': 'body',
            'in': 'body',
            'required': True,
            'schema': {
                'type': 'object',
                'required': ['query'],
                'properties': {
                    'query': {'type': 'string', 'example': 'How to reset password?'},
                    'top_k': {'type': 'integer', 'default': 3}
                }
            }
        }
    ],
    'responses': {
        200: {
            'description': 'Search results',
            'schema': {
                'type': 'object',
                'properties': {
                    'results': {
                        'type': 'array',
                        'items': {
                            'type': 'object',
                            'properties': {
                                'content': {'type': 'string'},
                                'metadata': {'type': 'object'}
                            }
                        }
                    }
                }
            }
        }
    }
})
def search_knowledge_base():
    """Search the knowledge base."""
    try:
        data = request.get_json()
        
        if 'query' not in data:
            return jsonify({'error': 'Query is required'}), 400
        
        agent = get_agent()
        top_k = data.get('top_k', 3)
        
        results = agent.knowledge_base.search(data['query'], top_k=top_k)
        
        return jsonify({
            'results': [
                {
                    'content': doc.page_content,
                    'metadata': doc.metadata
                }
                for doc in results
            ]
        }), 200
        
    except Exception as e:
        logger.error(f"Error searching knowledge base: {e}")
        return jsonify({'error': str(e)}), 500


# ==================== Conversation History ====================

@app.route('/api/v1/conversations', methods=['GET'])
@swag_from({
    'tags': ['Conversation'],
    'summary': 'List all conversations',
    'responses': {
        200: {
            'description': 'List of conversation IDs',
            'schema': {
                'type': 'object',
                'properties': {
                    'conversations': {
                        'type': 'array',
                        'items': {'type': 'string'}
                    }
                }
            }
        }
    }
})
def list_conversations():
    """List all conversations."""
    try:
        agent = get_agent()
        conversations = agent.conversation_history.list_conversations()
        
        return jsonify({'conversations': conversations}), 200
        
    except Exception as e:
        logger.error(f"Error listing conversations: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/v1/conversations/<conversation_id>', methods=['GET'])
@swag_from({
    'tags': ['Conversation'],
    'summary': 'Get conversation history',
    'parameters': [
        {
            'name': 'conversation_id',
            'in': 'path',
            'type': 'string',
            'required': True,
            'description': 'Conversation ID'
        }
    ],
    'responses': {
        200: {
            'description': 'Conversation history',
            'schema': {
                'type': 'object',
                'properties': {
                    'conversation_id': {'type': 'string'},
                    'messages': {'type': 'array'}
                }
            }
        }
    }
})
def get_conversation(conversation_id):
    """Get conversation history."""
    try:
        agent = get_agent()
        messages = agent.conversation_history.get_conversation(conversation_id)
        
        return jsonify({
            'conversation_id': conversation_id,
            'messages': messages
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting conversation: {e}")
        return jsonify({'error': str(e)}), 500


# ==================== Error Handlers ====================

@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors."""
    return jsonify({'error': 'Endpoint not found'}), 404


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors."""
    return jsonify({'error': 'Internal server error'}), 500


if __name__ == '__main__':
    app.run(
        host='0.0.0.0',
        port=int(os.getenv('API_PORT', 5000)),
        debug=os.getenv('FLASK_ENV') == 'development'
    )
