import os

# Automatically bind to Render's dynamic PORT environment variable (defaults to 10000 on Render)
port = os.environ.get("PORT", "10000")
bind = f"0.0.0.0:{port}"

# Optimal for Render's 512MB RAM Free Tier:
# 1 worker with 4 threads uses only ~45MB baseline RAM, leaving 460MB+ of headroom for image processing!
workers = 1
threads = 4
timeout = 120
keepalive = 5
preload_app = False
