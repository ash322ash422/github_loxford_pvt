"""
utils/notifier.py
==================
Handles delivery of administrator alerts through multiple channels:
console, a persistent alert-log file, and (optionally) e-mail via SMTP.

Each channel implements the same `Channel.send(alert)` interface (the
classic Strategy pattern), so adding Slack / SMS / PagerDuty later is just
a matter of writing one more small class and registering it with the
Notifier - no changes needed in log_monitor.py.
"""
from __future__ import annotations

import logging
import smtplib
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from email.mime.text import MIMEText
from pathlib import Path
from typing import List, Optional

import config

logger = logging.getLogger("apache_monitor.notifier")


@dataclass
class Alert:
    """A single structured alert event."""
    severity: str            # "WARNING" | "CRITICAL" | "INFO"
    title: str
    message: str
    timestamp: datetime = field(default_factory=datetime.now)

    def as_text(self) -> str:
        return (
            f"[{self.timestamp:%Y-%m-%d %H:%M:%S}] [{self.severity}] "
            f"{self.title} - {self.message}"
        )


class Channel(ABC):
    """Base class for all notification channels."""

    @abstractmethod
    def send(self, alert: Alert) -> bool:
        """Attempt delivery. Return True on success, False on failure."""


class ConsoleChannel(Channel):
    """Prints the alert to stdout. Always available, zero configuration."""

    def send(self, alert: Alert) -> bool:
        print(f"\a[ALERT] {alert.as_text()}")  # \a rings the terminal bell
        return True


class FileChannel(Channel):
    """Appends the alert to a persistent alerts.log so there is always an
    audit trail, independent of whether e-mail is configured."""

    def __init__(self, path: Path = config.ALERT_LOG_FILE):
        self.path = path

    def send(self, alert: Alert) -> bool:
        try:
            with self.path.open("a", encoding="utf-8") as fh:
                fh.write(alert.as_text() + "\n")
            return True
        except OSError as exc:
            logger.error("Failed writing alert to file: %s", exc)
            return False


class EmailChannel(Channel):
    """Sends e-mail via SMTP. Safely disables itself if SMTP is not
    configured in config.py, so the project still runs out-of-the-box
    without any credentials."""

    def __init__(self):
        self.enabled = bool(config.SMTP_HOST and config.ALERT_TO_ADDRS)

    def send(self, alert: Alert) -> bool:
        if not self.enabled:
            logger.debug("EmailChannel disabled (no SMTP_HOST configured); skipping.")
            return False

        msg = MIMEText(alert.message)
        msg["Subject"] = f"[{alert.severity}] {alert.title}"
        msg["From"] = config.ALERT_FROM_ADDR
        msg["To"] = ", ".join(config.ALERT_TO_ADDRS)

        try:
            with smtplib.SMTP(config.SMTP_HOST, config.SMTP_PORT, timeout=10) as server:
                if config.SMTP_USE_TLS:
                    server.starttls()
                if config.SMTP_USERNAME:
                    server.login(config.SMTP_USERNAME, config.SMTP_PASSWORD)
                server.sendmail(config.ALERT_FROM_ADDR, config.ALERT_TO_ADDRS, msg.as_string())
            return True
        except (smtplib.SMTPException, OSError) as exc:
            logger.error("Failed to send alert e-mail: %s", exc)
            return False


class Notifier:
    """Fan-out notifier: pushes every alert to all configured channels and
    never lets a broken channel crash the calling automation."""

    def __init__(self, channels: Optional[List[Channel]] = None):
        self.channels = channels or [ConsoleChannel(), FileChannel(), EmailChannel()]

    def notify(self, alert: Alert) -> None:
        logger.info("Dispatching alert: %s", alert.as_text())
        for channel in self.channels:
            try:
                channel.send(alert)
            except Exception:  # noqa: BLE001 - a channel must never crash the monitor
                logger.exception(
                    "Channel %s raised an unexpected error while sending alert",
                    channel.__class__.__name__,
                )
