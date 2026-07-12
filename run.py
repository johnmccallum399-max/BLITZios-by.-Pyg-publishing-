#!/usr/bin/env python3
"""Launcher: starts the API server and the Streamlit UI together."""

import subprocess
import sys
import time

BANNER = r"""
    ==========================================================
    |                                                        |
    |     BLITZ INTELLIGENCE OS                              |
    |     Strategic Research & Decision Intelligence         |
    |                                                        |
    ==========================================================
"""


def check_dependencies() -> bool:
    missing = []
    for module in ("uvicorn", "fastapi", "streamlit", "langgraph"):
        try:
            __import__(module)
        except ImportError:
            missing.append(module)
    if missing:
        print(f"ERROR: missing dependencies: {', '.join(missing)}")
        print("Fix:   pip install -r requirements.txt")
        return False
    return True


def print_mode():
    from src.core.config import Config

    mode = Config.capability_mode()
    print(f"Mode: {mode['label']}")
    print(f"  What to expect: {mode['expect']}")
    if mode["upgrade"]:
        print(f"  To upgrade:     {mode['upgrade']}")
    print()


def start_services():
    print("Starting BLITZ OS...")

    print("  API server -> http://localhost:8000  (docs at /docs)")
    api_process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "src.api.routes:app", "--port", "8000"],
    )

    time.sleep(3)

    print("  UI         -> http://localhost:8501")
    ui_process = subprocess.Popen(
        [sys.executable, "-m", "streamlit", "run", "src/ui/streamlit_app.py",
         "--server.port", "8501"],
    )

    print("\nBLITZ OS is running. Press Ctrl+C to stop.\n")
    try:
        api_process.wait()
    except KeyboardInterrupt:
        print("\nStopping BLITZ OS...")
    finally:
        api_process.terminate()
        ui_process.terminate()
        print("All services stopped.")


if __name__ == "__main__":
    print(BANNER)
    if not check_dependencies():
        sys.exit(1)
    print_mode()
    start_services()
