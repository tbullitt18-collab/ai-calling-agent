from app import create_app
import os
from app.config import FLASK_PORT, FLASK_HOST

app = create_app()

if __name__ == '__main__':
    # Ensure logs directory exists
    os.makedirs('logs', exist_ok=True)
    
    app.run(
        host=FLASK_HOST,
        port=FLASK_PORT,
        debug=(os.getenv('FLASK_ENV') == 'development')
    )
