#!/usr/bin/env python3
"""Launcher: starts the API server and the Streamlit UI together."""

import os
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


def check_api_key() -> bool:
    from dotenv import load_dotenv

    load_dotenv()
    if not (os.getenv("OPENAI_API_KEY") or os.getenv("ANTHROPIC_API_KEY")):
        print("WARNING: no LLM API key set in .env — running in heuristic mode.")
    if not os.getenv("SERPAPI_API_KEY"):
        print("WARNING: SERPAPI_API_KEY not set — web evidence will be mocked.")
    return True


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
    check_api_key()
    start_services()
