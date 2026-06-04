"""
Rain Check AI Voice Application
Modular Flask application initialization.
"""

import os
from flask import Flask, session, redirect, request
from flask_cors import CORS
from flask_sock import Sock
from app.services.scheduler_service import CallScheduler
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize extensions
sock = Sock()
scheduler = CallScheduler()

def create_app():
    """Application factory for Rain Check."""
    app = Flask(__name__, static_folder='static', static_url_path='/static')
    app.secret_key = os.getenv('FLASK_SECRET_KEY', 'raincheck-dev-secret-2025')
    CORS(app)
    
    # Initialize extensions with app
    sock.init_app(app)
    scheduler.start()
    
    @app.before_request
    def require_login():
        """Gate all dashboard routes behind authentication."""
        # Allow unauthenticated access to these paths
        public_paths = ['/login', '/register', '/health', '/webhook/', '/ws/', '/static/']
        path = request.path
        
        if any(path.startswith(p) for p in public_paths):
            return  # Allow through
        
        if path == '/' and request.method == 'GET':
            # Root page requires auth — redirect to login if not authenticated
            if not session.get('authenticated'):
                return redirect('/login')
        elif not path.startswith('/static'):
            # API routes (voices, session, api) require auth
            if not session.get('authenticated'):
                return redirect('/login')
    
    @app.route('/')
    def index():
        return app.send_static_file('index.html')
    
    with app.app_context():
        # Import and register blueprints
        from app.routes.health import health_bp
        from app.routes.audio_stream import audio_bp
        from app.routes.voice_cloning import cloning_bp
        from app.routes.session import session_bp
        from app.routes.api import api_bp
        from app.routes.auth import auth_bp
        from app.routes.profile import profile_bp
        from app.routes.mcp_routes import mcp_bp
        
        app.register_blueprint(health_bp)
        app.register_blueprint(audio_bp)
        app.register_blueprint(auth_bp)
        app.register_blueprint(cloning_bp, url_prefix='/voices')
        app.register_blueprint(session_bp, url_prefix='/session')
        app.register_blueprint(api_bp, url_prefix='/api')
        app.register_blueprint(profile_bp, url_prefix='/profile')
        app.register_blueprint(mcp_bp, url_prefix='/api/mcp')
        
        logger.info("Rain Check modular application initialized (Vonage + Vertex AI Gemini + Google Cloud).")
        
    return app
