"""Gunicorn configuration for production deployment."""
import os
import multiprocessing

# Load from environment or use defaults
bind = f"0.0.0.0:{os.getenv('API_PORT', '5000')}"
workers = int(os.getenv('GUNICORN_WORKERS', multiprocessing.cpu_count() * 2 + 1))
worker_class = 'sync'
worker_connections = 1000
timeout = 120
keepalive = 5

# Logging
accesslog = os.getenv('GUNICORN_ACCESS_LOG', 'logs/access.log')
errorlog = os.getenv('GUNICORN_ERROR_LOG', 'logs/error.log')
loglevel = os.getenv('LOG_LEVEL', 'info').lower()
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Process naming
proc_name = 'email_agent_api'

# Server mechanics
daemon = False
pidfile = None
umask = 0
user = None
group = None
tmp_upload_dir = None

# SSL (uncomment for HTTPS)
# keyfile = 'path/to/keyfile'
# certfile = 'path/to/certfile'

# Preload app for better performance
preload_app = True

# Restart workers after this many requests (prevents memory leaks)
max_requests = 1000
max_requests_jitter = 50

print(f"""
Gunicorn Configuration:
  - Bind: {bind}
  - Workers: {workers}
  - Timeout: {timeout}s
  - Log Level: {loglevel}
""")
