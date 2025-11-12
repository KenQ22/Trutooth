"""Unified launcher for TruTooth interfaces.

Allows users to choose between:
- FastAPI REST API (for programmatic access)
- Flask Web UI (for browser-based monitoring)
- Both running simultaneously

Usage:
    python launch_trutooth.py --mode api      # FastAPI only
    python launch_trutooth.py --mode web      # Flask Web UI only
    python launch_trutooth.py --mode both     # Both interfaces (API on 8000, Web on 5000)
"""
import argparse
import sys
import subprocess
import time
from pathlib import Path


def check_dependencies():
    """Check if required dependencies are installed."""
    try:
        import flask
        import flask_sqlalchemy
        flask_available = True
    except ImportError:
        flask_available = False
    
    try:
        import fastapi
        import uvicorn
        fastapi_available = True
    except ImportError:
        fastapi_available = False
    
    return flask_available, fastapi_available


def launch_fastapi():
    """Launch FastAPI server."""
    print("🚀 Starting FastAPI REST API on http://127.0.0.1:8000")
    print("📖 API docs available at http://127.0.0.1:8000/docs")
    subprocess.run([
        sys.executable, "-m", "uvicorn",
        "trutooth.api:app",
        "--host", "127.0.0.1",
        "--port", "8000",
        "--reload"
    ])


def launch_flask():
    """Launch Flask Web UI."""
    print("🌐 Starting Flask Web UI on http://127.0.0.1:5000")
    subprocess.run([
        sys.executable, "-m", "trutooth.web_ui"
    ])


def launch_both():
    """Launch both FastAPI and Flask in separate processes."""
    print("🚀 Starting both interfaces...")
    print("   - FastAPI REST API: http://127.0.0.1:8000")
    print("   - Flask Web UI:     http://127.0.0.1:5000")
    print("\nPress Ctrl+C to stop both servers\n")
    
    import multiprocessing
    
    # Start FastAPI in separate process
    api_process = multiprocessing.Process(
        target=lambda: subprocess.run([
            sys.executable, "-m", "uvicorn",
            "trutooth.api:app",
            "--host", "127.0.0.1",
            "--port", "8000"
        ])
    )
    
    # Start Flask in separate process
    web_process = multiprocessing.Process(
        target=lambda: subprocess.run([
            sys.executable, "-m", "trutooth.web_ui"
        ])
    )
    
    try:
        api_process.start()
        time.sleep(1)  # Give API time to start
        web_process.start()
        
        # Wait for both processes
        api_process.join()
        web_process.join()
    except KeyboardInterrupt:
        print("\n\n⏹️  Shutting down servers...")
        api_process.terminate()
        web_process.terminate()
        api_process.join()
        web_process.join()
        print("✅ Servers stopped")


def main():
    parser = argparse.ArgumentParser(
        description="Launch TruTooth monitoring interfaces"
    )
    parser.add_argument(
        "--mode",
        choices=["api", "web", "both"],
        default="web",
        help="Which interface to launch (default: web)"
    )
    
    args = parser.parse_args()
    
    # Check dependencies
    flask_available, fastapi_available = check_dependencies()
    
    if args.mode in ["web", "both"] and not flask_available:
        print("❌ Error: Flask dependencies not installed")
        print("   Install with: pip install flask flask-sqlalchemy")
        sys.exit(1)
    
    if args.mode in ["api", "both"] and not fastapi_available:
        print("❌ Error: FastAPI dependencies not installed")
        print("   Install with: pip install fastapi uvicorn")
        sys.exit(1)
    
    # Launch appropriate interface
    if args.mode == "api":
        launch_fastapi()
    elif args.mode == "web":
        launch_flask()
    elif args.mode == "both":
        launch_both()


if __name__ == "__main__":
    main()
