"""
Rain Check AI Voice Application
Modular Flask application initialization.
"""

from flask import Flask
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
    CORS(app)
    
    # Initialize extensions with app
    sock.init_app(app)
    scheduler.start()
    
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
        
        app.register_blueprint(health_bp)
        app.register_blueprint(audio_bp)
        app.register_blueprint(cloning_bp, url_prefix='/voices')
        app.register_blueprint(session_bp, url_prefix='/session')
        app.register_blueprint(api_bp, url_prefix='/api')
        
        logger.info("Rain Check modular application initialized (Vonage + Claude + ElevenLabs).")
        
    return app
