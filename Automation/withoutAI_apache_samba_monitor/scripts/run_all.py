"""
scripts/run_all.py
===================
Convenience launcher for demos: starts the log populator and the monitor
as background subprocesses, then runs the Tkinter GUI in the foreground.
Closing the GUI window (or Ctrl+C) stops all three cleanly.

This is purely a teaching convenience - in real deployments the populator
wouldn't exist at all, and the monitor would run as its own managed
service (systemd, a container, a scheduled task, etc.), separate from any
GUI.

Usage (run from the project root):
    python scripts/run_all.py
"""
import signal
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main() -> None:
    procs = []
    try:
        print("Starting log_populator.py (apache + samba) ...")
        procs.append(subprocess.Popen([sys.executable, str(ROOT / "log_populator.py")], cwd=ROOT))

        print("Starting log_monitor.py ...")
        procs.append(subprocess.Popen([sys.executable, str(ROOT / "log_monitor.py")], cwd=ROOT))

        time.sleep(1)  # give the monitor a moment to publish an initial status

        print("Launching gui_status.py (close the window to stop everything) ...")
        subprocess.run([sys.executable, str(ROOT / "gui_status.py")], cwd=ROOT)
    finally:
        print("Shutting down background processes...")
        for proc in procs:
            proc.send_signal(signal.SIGTERM)
        for proc in procs:
            proc.wait(timeout=15)
        print("All processes stopped.")


if __name__ == "__main__":
    main()
