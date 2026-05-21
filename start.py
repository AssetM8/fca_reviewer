"""
start.py — Smart Regulatory Reviewer launcher
Starts the FastAPI backend and Streamlit frontend in parallel,
then opens the browser automatically.

Usage:
    python start.py          (uses .venv if present, else system Python)
"""

import subprocess
import sys
import time
import webbrowser
import os
import threading
from pathlib import Path

ROOT = Path(__file__).parent.resolve()


def get_python() -> str:
    """Return the Python executable inside .venv if it exists, else sys.executable."""
    venv_win   = ROOT / ".venv" / "Scripts" / "python.exe"
    venv_posix = ROOT / ".venv" / "bin" / "python"
    if venv_win.exists():
        return str(venv_win)
    if venv_posix.exists():
        return str(venv_posix)
    return sys.executable


PYTHON = get_python()

BACKEND_CMD = [
    PYTHON, "-m", "uvicorn",
    "backend.api:app",
    "--host", "0.0.0.0",
    "--port", "8001",
]

FRONTEND_CMD = [
    PYTHON, "-m", "streamlit", "run",
    str(ROOT / "app.py"),
    "--server.port", "8501",
    "--server.headless", "true",
    "--browser.gatherUsageStats", "false",
]

BANNER = """
+------------------------------------------------------------------+
|        Smart Regulatory Reviewer - HKIA FCA AI Tool             |
|                  Deloitte  DAIS Hackathon 2026                   |
+------------------------------------------------------------------+
|  Backend  ->  http://localhost:8001                              |
|  Frontend ->  http://localhost:8501  (opening in browser...)     |
|                                                                  |
|  Press Ctrl+C to stop both services.                             |
+------------------------------------------------------------------+
"""


def stream_output(proc, prefix, colour_code):
    """Stream subprocess output with a coloured prefix."""
    colour = f"\033[{colour_code}m"
    reset  = "\033[0m"
    for line in iter(proc.stdout.readline, b""):
        text = line.decode("utf-8", errors="replace").rstrip()
        if text:
            print(f"{colour}[{prefix}]{reset} {text}", flush=True)


def wait_for_backend(timeout=45):
    """Poll until the backend /health endpoint responds."""
    import urllib.request
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            urllib.request.urlopen("http://localhost:8001/health", timeout=2)
            return True
        except Exception:
            time.sleep(0.5)
    return False


def check_env():
    """Warn if .env is missing."""
    env_path = ROOT / ".env"
    if not env_path.exists():
        print("\033[93m[WARN]\033[0m .env file not found!")
        print("       Create it with:")
        print("         LLM_BASE_URL=https://nova.deloitte.com.cn/del/v1")
        print("         LLM_API_KEY=<your-key>")
        print("         LLM_MODEL=Kimi-K2.5")
        print()


def main():
    os.chdir(ROOT)
    processes = []

    print(BANNER)
    print(f"\033[92m[INFO]\033[0m Using Python: {PYTHON}")
    check_env()

    try:
        # ── Start backend ──────────────────────────────────────────────────
        print("\033[92m[INFO]\033[0m Starting FastAPI backend on port 8001...")
        backend = subprocess.Popen(
            BACKEND_CMD,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            cwd=ROOT,
        )
        processes.append(backend)
        threading.Thread(
            target=stream_output, args=(backend, "BACKEND", "32"), daemon=True
        ).start()

        # ── Quick sanity check — did the process die immediately? ──────────
        time.sleep(2)
        if backend.poll() is not None:
            print("\033[91m[ERROR]\033[0m Backend failed to start.")
            print("        Make sure you are running from inside the fca_reviewer folder")
            print("        and that your .venv is activated or packages are installed:")
            print(f"        {PYTHON} -m pip install -r requirements.txt")
            input("\nPress Enter to exit...")
            return

        # ── Wait for backend to be healthy ─────────────────────────────────
        print("\033[92m[INFO]\033[0m Waiting for backend to be ready...")
        if wait_for_backend(timeout=45):
            print("\033[92m[INFO]\033[0m Backend is ready \u2713")
        else:
            print("\033[93m[WARN]\033[0m Backend not responding after 45s - starting frontend anyway.")

        # ── Start frontend ─────────────────────────────────────────────────
        print("\033[92m[INFO]\033[0m Starting Streamlit frontend on port 8501...")
        frontend = subprocess.Popen(
            FRONTEND_CMD,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            cwd=ROOT,
        )
        processes.append(frontend)
        threading.Thread(
            target=stream_output, args=(frontend, "FRONTEND", "36"), daemon=True
        ).start()

        # ── Quick sanity check ─────────────────────────────────────────────
        time.sleep(2)
        if frontend.poll() is not None:
            print("\033[91m[ERROR]\033[0m Streamlit failed to start.")
            print(f"        Try: {PYTHON} -m pip install streamlit")
            input("\nPress Enter to exit...")
            return

        # ── Open browser ───────────────────────────────────────────────────
        time.sleep(3)
        print("\033[92m[INFO]\033[0m Opening browser at http://localhost:8501 ...")
        webbrowser.open("http://localhost:8501")
        print("\n\033[92m[INFO]\033[0m Both services running. Press Ctrl+C to stop.\n")

        # ── Keep alive ─────────────────────────────────────────────────────
        while True:
            for proc in processes:
                if proc.poll() is not None:
                    print(f"\033[91m[ERROR]\033[0m A service exited unexpectedly. Shutting down.")
                    raise KeyboardInterrupt
            time.sleep(1)

    except KeyboardInterrupt:
        print("\n\033[92m[INFO]\033[0m Shutting down services...")
    finally:
        for proc in processes:
            try:
                proc.terminate()
                proc.wait(timeout=5)
            except Exception:
                try:
                    proc.kill()
                except Exception:
                    pass
        print("\033[92m[INFO]\033[0m All services stopped. Goodbye.")


if __name__ == "__main__":
    main()