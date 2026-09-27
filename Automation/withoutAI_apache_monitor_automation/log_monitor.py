"""
log_monitor.py
===============
The core automation script. For EACH monitored service (Apache and Samba,
see config.SERVICES) it:

  1. Periodically reads only the NEW bytes appended to that service's log
     (like `tail -f`), remembering its position between polls (and even
     between restarts) so it never re-scans the whole file.
  2. Classifies each new line as normal / error / crash using a small
     service-specific classifier function, and keeps a sliding time-window
     count of error and crash events.
  3. Evaluates that service's health: OK / WARNING / CRITICAL, and also
     flags a suspicious silence (no log activity) as a possible outage.

It then combines both services into one overall status (the worst of the
two), and:

  * Publishes a JSON status file (status/status.json) that the Tkinter GUI
    polls to light up its green/red buttons and show a per-service
    breakdown.
  * Prints any detected issue to the console immediately.
  * Alerts administrators (console + file + optional e-mail) with a
    cooldown so the same issue doesn't spam the inbox, and sends a
    "recovered" notice when a service's health returns to OK.

Run:
    python log_monitor.py
Stop with Ctrl+C (or SIGTERM).
"""
from __future__ import annotations

import json
import logging
import re
import signal
import sys
import time
from collections import deque
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable, Deque, Dict, Optional, Tuple

import config
from utils.notifier import Alert, Notifier

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] monitor: %(message)s",
    handlers=[
        logging.FileHandler(config.MONITOR_APP_LOG, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("server_monitor.monitor")

STATUS_OK = "OK"
STATUS_WARNING = "WARNING"
STATUS_CRITICAL = "CRITICAL"

# A classifier takes one raw log line and returns "crash", "error", or None.
Classifier = Callable[[str], Optional[str]]


# ---------------------------------------------------------------------------
# Service-specific line classifiers
# ---------------------------------------------------------------------------
# Matches the status code in a combined/common apache log line, e.g.:
#   "GET / HTTP/1.1" 200 1234
#                    ^^^ this group
APACHE_STATUS_RE = re.compile(r'"\s+(\d{3})\s+\S+')
APACHE_CRASH_RE = re.compile(r'crash', re.IGNORECASE)


def classify_apache_line(line: str) -> Optional[str]:
    if APACHE_CRASH_RE.search(line):
        return "crash"
    match = APACHE_STATUS_RE.search(line)
    if match and int(match.group(1)) >= 500:
        return "error"
    return None


SAMBA_CRASH_RE = re.compile(r'PANIC|CRITICAL|crashed', re.IGNORECASE)
SAMBA_ERROR_RE = re.compile(r'\bERROR\b', re.IGNORECASE)


def classify_samba_line(line: str) -> Optional[str]:
    if SAMBA_CRASH_RE.search(line):
        return "crash"
    if SAMBA_ERROR_RE.search(line):
        return "error"
    return None


CLASSIFIERS: Dict[str, Classifier] = {
    "apache": classify_apache_line,
    "samba": classify_samba_line,
}


# ---------------------------------------------------------------------------
# Tailing
# ---------------------------------------------------------------------------
class LogTailer:
    """Reads only newly appended, complete lines of a growing log file.

    Tolerant of log rotation/truncation (if the file shrinks, we assume it
    was rotated and restart from byte 0). Persists its byte offset to disk
    so the service can be restarted without reprocessing the whole file -
    the same trick real log-shippers (Filebeat, Fluentd, etc.) use.
    """

    def __init__(self, path: Path, offset_file: Path):
        self.path = path
        self.offset_file = offset_file
        self._offset = self._load_offset()

    def _load_offset(self) -> int:
        if self.offset_file.exists():
            try:
                return json.loads(self.offset_file.read_text()).get("offset", 0)
            except (json.JSONDecodeError, OSError):
                return 0
        return 0

    def _save_offset(self) -> None:
        tmp = self.offset_file.with_suffix(".tmp")
        tmp.write_text(json.dumps({"offset": self._offset}))
        tmp.replace(self.offset_file)  # atomic replace

    def read_new_lines(self) -> list:
        if not self.path.exists():
            return []

        size = self.path.stat().st_size
        if size < self._offset:
            logger.warning("%s appears truncated/rotated - resetting offset to 0.", self.path.name)
            self._offset = 0

        lines = []
        with self.path.open("r", encoding="utf-8", errors="replace") as fh:
            fh.seek(self._offset)
            while True:
                # readline() (unlike iterating the file object) keeps tell()
                # accurate, since Python's file iterator does internal
                # read-ahead buffering that breaks tell().
                raw_line = fh.readline()
                if not raw_line:
                    break
                if raw_line.endswith("\n"):
                    lines.append(raw_line.rstrip("\n"))
                    self._offset = fh.tell()
                else:
                    # incomplete line at EOF - wait for the writer to finish it
                    break
        self._save_offset()
        return lines


# ---------------------------------------------------------------------------
# Health evaluation
# ---------------------------------------------------------------------------
@dataclass
class Event:
    timestamp: float
    kind: str  # "error" | "crash"


class HealthEvaluator:
    """Keeps a sliding window of recent error/crash events for ONE service
    and decides that service's health status from them. The classifier is
    injected, so the exact same class works for Apache, Samba, or any log
    format you add later."""

    def __init__(self, window_sec: int, error_threshold: int, crash_threshold: int, classifier: Classifier):
        self.window_sec = window_sec
        self.error_threshold = error_threshold
        self.crash_threshold = crash_threshold
        self.classifier = classifier
        self._events: Deque[Event] = deque()

    def feed_line(self, line: str) -> None:
        kind = self.classifier(line)
        if kind:
            self._events.append(Event(time.time(), kind))

    def _prune(self) -> None:
        cutoff = time.time() - self.window_sec
        while self._events and self._events[0].timestamp < cutoff:
            self._events.popleft()

    def evaluate(self) -> Tuple[str, str]:
        """Return (status, human-readable reason)."""
        self._prune()
        crash_count = sum(1 for e in self._events if e.kind == "crash")
        error_count = sum(1 for e in self._events if e.kind == "error")

        if crash_count >= self.crash_threshold:
            return STATUS_CRITICAL, (
                f"{crash_count} crash marker(s) detected in the last {self.window_sec}s of the log."
            )
        if error_count >= self.error_threshold:
            return STATUS_WARNING, (
                f"{error_count} error-level lines in the last {self.window_sec}s "
                f"(threshold is {self.error_threshold})."
            )
        return STATUS_OK, "No issues detected."


# ---------------------------------------------------------------------------
# Per-service watcher: bundles tailer + evaluator + heartbeat tracking
# ---------------------------------------------------------------------------
class ServiceWatcher:
    def __init__(self, name: str, log_file: Path, offset_file: Path, classifier: Classifier):
        self.name = name
        self.tailer = LogTailer(log_file, offset_file)
        self.evaluator = HealthEvaluator(
            config.MONITOR_WINDOW_SEC, config.ERROR_THRESHOLD, config.CRASH_THRESHOLD, classifier
        )
        self.last_activity = time.time()

    def poll(self) -> Tuple[str, str]:
        new_lines = self.tailer.read_new_lines()
        if new_lines:
            self.last_activity = time.time()
            for line in new_lines:
                self.evaluator.feed_line(line)

        status, reason = self.evaluator.evaluate()

        idle_for = time.time() - self.last_activity
        if status == STATUS_OK and idle_for > config.HEARTBEAT_TIMEOUT_SEC:
            status = STATUS_WARNING
            reason = f"No new log activity for {int(idle_for)}s; {self.name} may be unresponsive."

        return status, reason


# ---------------------------------------------------------------------------
# Status publishing (consumed by the Tkinter GUI)
# ---------------------------------------------------------------------------
_SEVERITY_RANK = {STATUS_OK: 0, STATUS_WARNING: 1, STATUS_CRITICAL: 2}


def publish_status(service_results: Dict[str, Tuple[str, str]]) -> str:
    """Write status/status.json atomically and return the overall status."""
    overall = STATUS_OK
    for status, _ in service_results.values():
        if _SEVERITY_RANK[status] > _SEVERITY_RANK[overall]:
            overall = status

    payload = {
        "overall_status": overall,
        "services": {
            name: {"status": status, "reason": reason}
            for name, (status, reason) in service_results.items()
        },
        "updated_at": datetime.now().isoformat(timespec="seconds"),
    }
    tmp = config.STATUS_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    tmp.replace(config.STATUS_FILE)  # atomic write so the GUI never reads a half-written file
    return overall


# ---------------------------------------------------------------------------
# Alerting with cooldown + recovery notice (tracked per service)
# ---------------------------------------------------------------------------
class AlertManager:
    """Decides WHEN to actually notify admins for a given service:
    immediately on a new/changed problem, then throttled by a cooldown
    while it persists, plus a single "recovered" notice when health
    returns to OK. State is tracked independently per service name."""

    def __init__(self, notifier: Notifier, cooldown_sec: int):
        self.notifier = notifier
        self.cooldown_sec = cooldown_sec
        self._last_status: Dict[str, str] = {}
        self._last_alert_time: Dict[str, float] = {}

    def handle(self, service: str, status: str, reason: str) -> None:
        now = time.time()
        last_status = self._last_status.get(service)
        last_alert_time = self._last_alert_time.get(service, 0.0)
        status_changed = status != last_status
        cooldown_elapsed = (now - last_alert_time) >= self.cooldown_sec

        if status in (STATUS_WARNING, STATUS_CRITICAL):
            if status_changed or cooldown_elapsed:
                self.notifier.notify(Alert(
                    severity=status,
                    title=f"{service.capitalize()} issue detected" if status == STATUS_WARNING
                          else f"{service.capitalize()} CRASH detected",
                    message=reason,
                ))
                self._last_alert_time[service] = now
        elif status == STATUS_OK and last_status in (STATUS_WARNING, STATUS_CRITICAL):
            self.notifier.notify(Alert(
                severity="INFO",
                title=f"{service.capitalize()} recovered",
                message=f"{service.capitalize()} health returned to normal.",
            ))

        self._last_status[service] = status


# ---------------------------------------------------------------------------
# Main service loop
# ---------------------------------------------------------------------------
_running = True


def _handle_shutdown(signum, frame):  # noqa: ARG001
    global _running
    logger.info("Shutdown signal received, stopping monitor...")
    _running = False


def run() -> None:
    signal.signal(signal.SIGINT, _handle_shutdown)
    signal.signal(signal.SIGTERM, _handle_shutdown)

    watchers = {
        name: ServiceWatcher(name, cfg["log_file"], cfg["offset_file"], CLASSIFIERS[name])
        for name, cfg in config.SERVICES.items()
    }
    alert_manager = AlertManager(Notifier(), config.ALERT_COOLDOWN_SEC)

    logger.info("Monitor started. Watching services: %s (every %ss)",
                ", ".join(watchers), config.MONITOR_POLL_INTERVAL_SEC)
    publish_status({name: (STATUS_OK, "Monitor starting up...") for name in watchers})

    while _running:
        results: Dict[str, Tuple[str, str]] = {}
        for name, watcher in watchers.items():
            status, reason = watcher.poll()
            results[name] = (status, reason)
            alert_manager.handle(name, status, reason)
            if status != STATUS_OK:
                # Console output requirement: print detected issues immediately.
                print(f"[ISSUE DETECTED] {name.upper()}: {status} - {reason}")
                logger.warning("%s status=%s reason=%s", name, status, reason)
            else:
                logger.debug("%s status=OK", name)

        overall = publish_status(results)
        logger.debug("Overall status=%s", overall)

        time.sleep(config.MONITOR_POLL_INTERVAL_SEC)

    logger.info("Monitor stopped cleanly.")


if __name__ == "__main__":
    run()
