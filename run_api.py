"""Run the Flask API server."""
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from src.api.app import app

if __name__ == '__main__':
    port = int(os.getenv('API_PORT', 5000))
    debug = os.getenv('FLASK_ENV') == 'development'
    
    print(f"""
╔═══════════════════════════════════════════════════════╗
║         AI Email Agent API Server                     ║
╚═══════════════════════════════════════════════════════╝

Server running on: http://localhost:{port}
API Documentation: http://localhost:{port}/api/docs

Endpoints:
  GET  /health                           - Health check
  POST /api/v1/email/process             - Process single email
  GET  /api/v1/email/inbox               - Fetch inbox
  POST /api/v1/email/batch-process       - Batch process emails
  POST /api/v1/knowledge-base/rebuild    - Rebuild KB
  POST /api/v1/knowledge-base/search     - Search KB
  GET  /api/v1/conversations             - List conversations
  GET  /api/v1/conversations/<id>        - Get conversation

Press Ctrl+C to stop
════════════════════════════════════════════════════════
    """)
    
    app.run(
        host='0.0.0.0',
        port=port,
        debug=debug
    )
