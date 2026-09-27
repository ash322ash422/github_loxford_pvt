"""
log_populator.py
=================
Simulates TWO live services by continuously appending realistic log lines
to logs/apache_access.log and logs/samba.log:

    * Apache: an access log with normal 2xx/3xx traffic, occasional 4xx/5xx
      errors, and rare full "server crash" bursts.
    * Samba: an smbd-style event log with normal connection/auth activity,
      occasional ERROR lines, and rare full "daemon crash" bursts.

Each service runs on its own background thread with its own independent
random timing, so they behave like two unrelated servers rather than one
process alternately writing to two files - a small, deliberate example of
using threads to model independent, concurrently-running things.

Run:
    python log_populator.py

Stop with Ctrl+C (or SIGTERM).
"""
from __future__ import annotations

import logging
import random
import signal
import sys
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import List

import config

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] populator: %(message)s",
    handlers=[
        logging.FileHandler(config.POPULATOR_APP_LOG, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("server_monitor.populator")

_stop_event = threading.Event()


# def write_line(path: Path, line: str) -> None:
#     """Append a single line to a log file. Public so scripts/simulate_crash.py
#     can reuse the exact same write path as the populator."""
#     with path.open("a", encoding="utf-8") as fh:
#         fh.write(line + "\n")

def write_line(path: Path, line: str) -> None:
    """
    Append a single line to a log file. Public so scripts/simulate_crash.py
    can reuse the exact same write path as the populator.
    Append a line to a log file.

    If the file reaches MAX_LOG_SIZE, rotate it:

        access.log   -> access.log.1
        samba.log    -> samba.log.1

    Only one backup is kept. Existing .1 files are overwritten.
    """

    try:
        if path.exists() and path.stat().st_size >= config.MAX_LOG_SIZE:
            backup = path.with_name(path.name + ".1")

            # Remove previous backup if present
            if backup.exists():
                backup.unlink()

            # Rename current log -> .1
            path.rename(backup)

    except OSError as e:
        logger.warning("Failed rotating %s: %s", path, e)

    # Append to (new or existing) log
    with path.open("a", encoding="utf-8") as fh:
        fh.write(line + "\n")



# ---------------------------------------------------------------------------
# Apache access log generation
# ---------------------------------------------------------------------------
APACHE_IPS = [f"192.168.1.{i}" for i in range(2, 40)]
APACHE_PATHS = ["/", "/index.html", "/api/users", "/api/orders", "/login",
                 "/static/app.js", "/static/style.css", "/favicon.ico", "/checkout"]
APACHE_METHODS = ["GET", "GET", "GET", "POST", "PUT", "DELETE"]
APACHE_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
    "curl/8.4.0",
    "Mozilla/5.0 (X11; Linux x86_64)",
]
APACHE_OK_STATUSES = [200, 200, 200, 201, 301, 304]
APACHE_ERROR_STATUSES = [400, 401, 403, 404, 500, 502, 503, 504]


def apache_normal_line() -> str:
    status = random.choice(APACHE_OK_STATUSES)
    size = random.randint(200, 15000)
    ts = datetime.now().strftime("%d/%b/%Y:%H:%M:%S +0000")
    return (f'{random.choice(APACHE_IPS)} - - [{ts}] '
            f'"{random.choice(APACHE_METHODS)} {random.choice(APACHE_PATHS)} HTTP/1.1" '
            f'{status} {size} "-" "{random.choice(APACHE_USER_AGENTS)}"')


def apache_error_line() -> str:
    status = random.choice(APACHE_ERROR_STATUSES)
    size = random.randint(0, 500)
    ts = datetime.now().strftime("%d/%b/%Y:%H:%M:%S +0000")
    return (f'{random.choice(APACHE_IPS)} - - [{ts}] '
            f'"{random.choice(APACHE_METHODS)} {random.choice(APACHE_PATHS)} HTTP/1.1" '
            f'{status} {size} "-" "{random.choice(APACHE_USER_AGENTS)}"')


def apache_5xx_line() -> str:
    """Like apache_error_line(), but guaranteed to be a 5xx server error -
    the specific signal the monitor's WARNING threshold counts. Used by
    scripts/simulate_crash.py so a demo reliably crosses the threshold
    instead of sometimes rolling harmless 4xx client errors."""
    status = random.choice([500, 502, 503, 504])
    size = random.randint(0, 500)
    ts = datetime.now().strftime("%d/%b/%Y:%H:%M:%S +0000")
    return (f'{random.choice(APACHE_IPS)} - - [{ts}] '
            f'"{random.choice(APACHE_METHODS)} {random.choice(APACHE_PATHS)} HTTP/1.1" '
            f'{status} {size} "-" "{random.choice(APACHE_USER_AGENTS)}"')


def apache_crash_lines() -> List[str]:
    """Several 5xx responses plus an explicit Apache-error-log-style CRASH
    marker line that the monitor treats as critical."""
    lines = [apache_error_line() for _ in range(random.randint(3, 6))]
    lines.append(
        f'[{datetime.now():%a %b %d %H:%M:%S %Y}] [core:error] [pid {random.randint(1000, 9999)}] '
        f'AH00052: Server crashed unexpectedly - CRASH - child process exited, restarting'
    )
    return lines


def apache_loop() -> None:
    logger.info("Apache log thread started -> writing to %s", config.APACHE_LOG_FILE)
    while not _stop_event.is_set():
        roll = random.random()
        if roll < config.APACHE_CRASH_RATE:
            lines = apache_crash_lines()
            for line in lines:
                write_line(config.APACHE_LOG_FILE, line)
            logger.warning("Injected APACHE crash burst (%d lines)", len(lines))
            _stop_event.wait(random.uniform(5, 10))  # simulate restart downtime
        elif roll < config.APACHE_CRASH_RATE + config.APACHE_ERROR_RATE:
            write_line(config.APACHE_LOG_FILE, apache_error_line())
        else:
            write_line(config.APACHE_LOG_FILE, apache_normal_line())

        _stop_event.wait(random.uniform(config.POPULATOR_MIN_INTERVAL_SEC,
                                         config.POPULATOR_MAX_INTERVAL_SEC))
    logger.info("Apache log thread stopped.")


# ---------------------------------------------------------------------------
# Samba log generation
# ---------------------------------------------------------------------------
SAMBA_USERS = ["alice", "bob", "carol", "dave", "svc_backup", "guest"]
SAMBA_SHARES = ["Public", "Data", "HomeDrives", "Backups", "Scans"]
SAMBA_IPS = [f"192.168.1.{i}" for i in range(40, 80)]


def samba_normal_line() -> str:
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    pid = random.randint(1000, 9999)
    choice = random.random()
    if choice < 0.5:
        return (f"{ts} smbd[{pid}]: INFO: client {random.choice(SAMBA_IPS)} "
                f"connected to share '{random.choice(SAMBA_SHARES)}'")
    return (f"{ts} smbd[{pid}]: INFO: user '{random.choice(SAMBA_USERS)}' "
            f"authenticated successfully from {random.choice(SAMBA_IPS)}")


def samba_error_line() -> str:
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    pid = random.randint(1000, 9999)
    reasons = [
        "NT_STATUS_LOGON_FAILURE",
        "NT_STATUS_ACCESS_DENIED",
        "NT_STATUS_ACCOUNT_LOCKED_OUT",
        "NT_STATUS_PASSWORD_EXPIRED",
    ]
    return (f"{ts} smbd[{pid}]: ERROR: authentication failed for user "
            f"'{random.choice(SAMBA_USERS)}' from {random.choice(SAMBA_IPS)} "
            f"({random.choice(reasons)})")


def samba_crash_lines() -> List[str]:
    """Several ERROR events plus an explicit CRITICAL/PANIC line simulating
    the smbd daemon crashing and restarting."""
    lines = [samba_error_line() for _ in range(random.randint(3, 6))]
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    pid = random.randint(1000, 9999)
    lines.append(
        f"{ts} smbd[{pid}]: CRITICAL: PANIC: internal error - smbd crashed unexpectedly, restarting"
    )
    return lines


def samba_loop() -> None:
    logger.info("Samba log thread started -> writing to %s", config.SAMBA_LOG_FILE)
    while not _stop_event.is_set():
        roll = random.random()
        if roll < config.SAMBA_CRASH_RATE:
            lines = samba_crash_lines()
            for line in lines:
                write_line(config.SAMBA_LOG_FILE, line)
            logger.warning("Injected SAMBA crash burst (%d lines)", len(lines))
            _stop_event.wait(random.uniform(5, 10))  # simulate restart downtime
        elif roll < config.SAMBA_CRASH_RATE + config.SAMBA_ERROR_RATE:
            write_line(config.SAMBA_LOG_FILE, samba_error_line())
        else:
            write_line(config.SAMBA_LOG_FILE, samba_normal_line())

        _stop_event.wait(random.uniform(config.POPULATOR_MIN_INTERVAL_SEC,
                                         config.POPULATOR_MAX_INTERVAL_SEC))
    logger.info("Samba log thread stopped.")


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------
def _handle_shutdown(signum, frame):  # noqa: ARG001
    logger.info("Shutdown signal received, stopping populator threads...")
    _stop_event.set()


def run() -> None:
    signal.signal(signal.SIGINT, _handle_shutdown)
    signal.signal(signal.SIGTERM, _handle_shutdown)

    threads = [
        threading.Thread(target=apache_loop, name="apache-populator", daemon=True),
        threading.Thread(target=samba_loop, name="samba-populator", daemon=True),
    ]
    for t in threads:
        t.start()

    # Keep the main thread alive until a shutdown signal arrives, then join.
    try:
        while not _stop_event.is_set():
            time.sleep(0.5)
    except KeyboardInterrupt:
        _stop_event.set()

    for t in threads:
        t.join(timeout=15)
    logger.info("Log populator stopped cleanly.")


if __name__ == "__main__":
    run()
