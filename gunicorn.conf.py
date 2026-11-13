import os

# Automatically bind to Render's dynamic PORT environment variable (defaults to 10000 on Render)
port = os.environ.get("PORT", "10000")
bind = f"0.0.0.0:{port}"

# Worker configuration optimized for free tier containers (512MB RAM)
workers = 2
threads = 2
timeout = 120
keepalive = 5
