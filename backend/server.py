# Legacy server.py - now imports from new main application
from app.main import app

# Keep this for backward compatibility with supervisor
# The new main application is in app/main.py