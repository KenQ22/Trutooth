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
import subprocess
import sys
import time


def _run_fastapi(*, reload: bool = False) -> int:
    """Run the FastAPI server process and return its exit code."""
    cmd = [
        sys.executable,
        "-m",
        "uvicorn",
        "trutooth.api:app",
        "--host",
        "127.0.0.1",
        "--port",
        "8000",
    ]
    if reload:
        cmd.append("--reload")
    return subprocess.run(cmd, check=False).returncode


def _run_flask() -> int:
    """Run the Flask web UI process and return its exit code."""
    cmd = [sys.executable, "-m", "trutooth.web_ui"]
    return subprocess.run(cmd, check=False).returncode


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


def launch_fastapi(reload: bool = False):
    """Launch FastAPI server."""
    print("🚀 Starting FastAPI REST API on http://127.0.0.1:8000")
    print("📖 API docs available at http://127.0.0.1:8000/docs")
    if reload:
        print("🔁 Auto-reload enabled")
    _run_fastapi(reload=reload)


def launch_flask():
    """Launch Flask Web UI."""
    print("🌐 Starting Flask Web UI on http://127.0.0.1:5000")
    _run_flask()


def launch_both(reload_api: bool = False):
    """Launch both FastAPI and Flask using separate subprocesses."""
    print("🚀 Starting both interfaces...")
    print("   - FastAPI REST API: http://127.0.0.1:8000")
    print("   - Flask Web UI:     http://127.0.0.1:5000")
    print("\nPress Ctrl+C to stop both servers\n")

    processes = []
    try:
        api_cmd = [
            sys.executable,
            "-m",
            "uvicorn",
            "trutooth.api:app",
            "--host",
            "127.0.0.1",
            "--port",
            "8000",
        ]
        if reload_api:
            api_cmd.append("--reload")
        processes.append(("FastAPI", subprocess.Popen(api_cmd)))

        time.sleep(1)
        web_cmd = [sys.executable, "-m", "trutooth.web_ui"]
        processes.append(("Flask", subprocess.Popen(web_cmd)))

        while True:
            time.sleep(0.5)
            for name, proc in processes:
                exit_code = proc.poll()
                if exit_code is not None:
                    print(f"\n{name} exited with code {exit_code}")
                    return
    except KeyboardInterrupt:
        print("\n\n⏹️  Shutting down servers...")
    finally:
        for name, proc in processes:
            if proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait()
        if processes:
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
    parser.add_argument(
        "--reload",
        action="store_true",
        help="Enable auto-reload for the FastAPI server"
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
        launch_fastapi(reload=args.reload)
    elif args.mode == "web":
        launch_flask()
    elif args.mode == "both":
        launch_both(reload_api=args.reload)


if __name__ == "__main__":
    main()
