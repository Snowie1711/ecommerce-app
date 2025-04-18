#!/usr/bin/env python
"""
Run script for Flask app with SocketIO support
This script detects and uses the best available async mode
"""
import os
import sys
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler()]
)

logger = logging.getLogger(__name__)

# Try to import eventlet and gevent
# We'll try each one and use the first available one
async_mode = None

def install_package(package_name):
    """Attempt to install a package and return success status"""
    try:
        logger.info(f"Attempting to install {package_name}...")
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", package_name])
        logger.info(f"Successfully installed {package_name}")
        return True
    except Exception as e:
        logger.error(f"Failed to install {package_name}: {str(e)}")
        return False

try:
    import eventlet
    eventlet.monkey_patch()
    async_mode = 'eventlet'
    logger.info("Using eventlet for async mode")
except ImportError:
    logger.warning("eventlet not found, trying gevent...")
    try:
        # Try to import gevent or offer to install it
        try:
            import gevent
            import gevent.monkey
            gevent.monkey.patch_all()
            async_mode = 'gevent'
            logger.info("Using gevent for async mode")
        except ImportError:
            # Ask if the user wants to install gevent
            if input("gevent is not installed. Would you like to install it now? (y/n): ").lower() == 'y':
                if install_package('gevent'):
                    # If installation successful, try importing again
                    try:
                        import gevent
                        import gevent.monkey
                        gevent.monkey.patch_all()
                        async_mode = 'gevent'
                        logger.info("Using gevent for async mode")
                    except ImportError:
                        logger.warning("Failed to import gevent even after installation")
                        async_mode = 'threading'
                else:
                    logger.warning("Failed to install gevent, falling back to threading mode")
                    async_mode = 'threading'
            else:
                logger.warning("gevent installation skipped, falling back to threading mode")
                async_mode = 'threading'
    except Exception as e:
        logger.warning(f"Error while handling gevent import: {str(e)}")
        logger.warning("Neither eventlet nor gevent is available. WebSocket may not work properly.")
        logger.warning("Install one of them with: pip install eventlet or pip install gevent")
        async_mode = 'threading'

# Import the Flask app and SocketIO instance
# Adjust the import path as needed for your application
try:
    from app import create_app
    from extensions import socketio
except ImportError as e:
    logger.error(f"Failed to import app or extensions: {str(e)}")
    logger.error("Make sure your app and socketio instances are properly defined")
    sys.exit(1)

def run_app(debug=True, host='127.0.0.1', port=5000):
    """
    Run the Flask app with the appropriate server
    """
    try:
        # Create the Flask app
        app = create_app()
        
        # Configure SocketIO
        if socketio.async_mode != async_mode:
            logger.info(f"Setting SocketIO async_mode to {async_mode}")
            socketio._async_mode = async_mode
        
        # Start the app with SocketIO
        logger.info(f"Starting server in {async_mode} mode on {host}:{port} (debug={debug})")
        socketio.run(app, debug=debug, host=host, port=port)
    except Exception as e:
        logger.error(f"Error starting app: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    # Parse command line arguments
    debug = True
    host = os.environ.get('FLASK_HOST', '127.0.0.1')
    port = int(os.environ.get('FLASK_PORT', 5000))
    
    # Get debug mode from environment
    if os.environ.get('FLASK_DEBUG', '').lower() in ('0', 'false', 'no'):
        debug = False
    
    # Check if app.py exists and has create_app function
    if not hasattr(sys.modules.get('app', None), 'create_app'):
        logger.warning("Could not find create_app in app.py. Make sure it's defined correctly.")
    
    # Run the app
    run_app(debug=debug, host=host, port=port)
