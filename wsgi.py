import os
import sys
import traceback

# Force UTF-8 output encoding
os.environ.setdefault('PYTHONIOENCODING', 'utf-8')

try:
    from app import create_app
    from app.config import FLASK_PORT, FLASK_HOST
    app = create_app()
except Exception as e:
    # Log the full traceback so Render logs show the actual crash reason
    print("=" * 60, file=sys.stderr)
    print("FATAL: Application failed to start", file=sys.stderr)
    print("=" * 60, file=sys.stderr)
    traceback.print_exc(file=sys.stderr)
    print("=" * 60, file=sys.stderr)
    sys.exit(1)

if __name__ == '__main__':
    # Ensure logs directory exists
    os.makedirs('logs', exist_ok=True)
    
    app.run(
        host=FLASK_HOST,
        port=FLASK_PORT,
        debug=(os.getenv('FLASK_ENV') == 'development')
    )
