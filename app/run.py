#!/usr/bin/env python3
"""
Launch script for the Flight Planning LLM Web Application
"""

import os
import sys
from pathlib import Path

def load_env_file():
    """Load environment variables from .env file"""
    env_path = Path(__file__).parent / '.env'
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                if line.strip() and not line.startswith('#'):
                    key, value = line.strip().split('=', 1)
                    os.environ[key] = value

def main():
    print("[DEBUG] Loading environment variables...")
    load_env_file()
    
    print("[DEBUG] Adding parent directory to sys.path...")
    parent_dir = Path(__file__).parent.parent
    sys.path.insert(0, str(parent_dir))
    
    print("[DEBUG] Ensuring required directories exist...")
    app_dir = Path(__file__).parent
    os.makedirs(app_dir / 'uploads', exist_ok=True)
    os.makedirs(app_dir / 'static', exist_ok=True)
    
    print("[DEBUG] Setting environment variables for Flask...")
    os.environ.setdefault('FLASK_ENV', 'development')
    os.environ.setdefault('FLASK_DEBUG', '1')
    
    print("[DEBUG] Importing Flask app...")
    from app import app
    
    # Configuration for SSH access
    host = os.environ.get('FLASK_HOST', '0.0.0.0')  # Bind to all interfaces for SSH access
    port = int(os.environ.get('FLASK_PORT', '5001'))  # Default to port 5000
    debug = os.environ.get('FLASK_DEBUG', '1') == '1'
    
    print("Starting Flight Planning LLM Web Application...")
    print(f"Server will be accessible at: http://{host}:{port}")
    print("For SSH access, use: http://your-server-ip:5000")
    print("Press Ctrl+C to stop the server")
    
    print(f"[DEBUG] Running Flask app on {host}:{port}...")
    app.run(debug=debug, host=host, port=port, threaded=True)

if __name__ == '__main__':
    main() 