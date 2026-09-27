"""
Turns main.py into an automation by polling the inbox on a repeating
interval instead of running once and exiting.

This is intentionally simple (a sleep loop) so it's easy to explain in
class. For production use, prefer a real scheduler (cron, systemd timer,
or Cloud Scheduler) or Gmail push notifications (see README note below).

Run with: python scheduler.py
Stop with: Ctrl+C
"""
import time
import traceback
from datetime import datetime

from main import process_inbox

POLL_INTERVAL_SECONDS = 5 * 60  # check inbox every 5 minutes


def run_forever():
    print(f"Starting automated polling every {POLL_INTERVAL_SECONDS}s. Ctrl+C to stop.")
    while True:
        try:
            print(f"\n[{datetime.now().isoformat(timespec='seconds')}] Checking inbox...")
            process_inbox()
        except Exception:
            # Don't let one bad email or a transient API error kill the loop
            print("Error during this run -- will retry next interval:")
            traceback.print_exc()

        time.sleep(POLL_INTERVAL_SECONDS)


if __name__ == "__main__":
    run_forever()