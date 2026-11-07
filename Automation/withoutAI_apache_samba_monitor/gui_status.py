"""
gui_status.py
=============
Tkinter dashboard for the Server Log Monitoring Automation.

Shows:
  * Two indicator "lights" implemented as buttons:
        GREEN -> everything OK
        RED   -> at least one monitored service has an issue
  * A per-service breakdown (Apache / Samba) with their individual status.
  * A live-updating "Detected Issues" console panel: whenever the monitor
    writes a new alert to alerts/alerts.log, it appears here as well as
    in the monitor's own terminal - satisfying "display the error on the
    GUI and also in the console" with one shared source of truth (the
    alerts log file).

Design note for students: the GUI does NOT decide server health itself.
It simply polls status/status.json and tails alerts/alerts.log - both
written by log_monitor.py - and reflects whatever it finds. This is a
common, robust pattern for dashboards: the automation owns the decision,
the UI just subscribes to published state. You could open several of
these dashboards at once and they would all agree.

Run:
    python gui_status.py
"""
from __future__ import annotations

import json
import tkinter as tk
from pathlib import Path
from tkinter import scrolledtext

import config

POLL_INTERVAL_MS = 2000

GREEN_ACTIVE = "#2ecc71"
GREEN_DIM = "#1e5631"
RED_ACTIVE = "#e74c3c"
RED_DIM = "#5c1a13"
AMBER = "#f1c40f"
BG = "#1c1c1c"
PANEL_BG = "#111111"
FG = "#eeeeee"


class AlertTailer:
    """Tiny in-memory tail for the GUI: remembers how many bytes of
    alerts.log it has already shown, and returns only the new lines each
    time it is polled. Offset is not persisted to disk on purpose - each
    time the GUI opens it's fine to just start tailing from "now"."""

    def __init__(self, path: Path):
        self.path = path
        self._offset = path.stat().st_size if path.exists() else 0

    def read_new_lines(self) -> list:
        if not self.path.exists():
            return []
        size = self.path.stat().st_size
        if size < self._offset:  # file was rotated/cleared
            self._offset = 0
        lines = []
        with self.path.open("r", encoding="utf-8", errors="replace") as fh:
            fh.seek(self._offset)
            for raw_line in fh:
                if raw_line.endswith("\n"):
                    lines.append(raw_line.rstrip("\n"))
            self._offset = fh.tell()
        return lines


class StatusDashboard(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Server Log Monitor - Apache & Samba")
        self.geometry("520x520")
        self.configure(bg=BG)
        self.minsize(480, 460)

        self.alert_tailer = AlertTailer(config.ALERT_LOG_FILE)

        tk.Label(
            self, text="Server Health Dashboard", font=("Segoe UI", 14, "bold"), bg=BG, fg=FG,
        ).pack(pady=(14, 4))

        # --- Indicator lights ------------------------------------------------
        light_frame = tk.Frame(self, bg=BG)
        light_frame.pack(pady=8)

        # Two indicator buttons. They are intentionally disabled (not
        # clickable) - their job is purely to display state, driven by the
        # monitor's status.json, not to be pressed by the user.
        self.green_btn = tk.Button(
            light_frame, text="GREEN\nOK", width=14, height=4,
            font=("Segoe UI", 10, "bold"), relief="raised",
            state="disabled", disabledforeground="white",
        )
        self.green_btn.grid(row=0, column=0, padx=10)

        self.red_btn = tk.Button(
            light_frame, text="RED\nISSUE", width=14, height=4,
            font=("Segoe UI", 10, "bold"), relief="raised",
            state="disabled", disabledforeground="white",
        )
        self.red_btn.grid(row=0, column=1, padx=10)

        self.status_label = tk.Label(
            self, text="Status: unknown", font=("Segoe UI", 11, "bold"), bg=BG, fg=FG,
        )
        self.status_label.pack(pady=(10, 0))

        self.updated_label = tk.Label(self, text="", bg=BG, fg="#777777", font=("Segoe UI", 13))
        self.updated_label.pack(pady=(2, 8))

        # --- Per-service breakdown -------------------------------------------
        service_frame = tk.LabelFrame(
            self, text="Services", bg=BG, fg="#999999", font=("Segoe UI", 13, "bold"),
            bd=1, relief="groove",
        )
        service_frame.pack(fill="x", padx=16, pady=(0, 10))

        self.service_labels = {}
        for name in config.SERVICES:
            row = tk.Frame(service_frame, bg=BG)
            row.pack(fill="x", padx=8, pady=4)
            tk.Label(row, text=f"{name.capitalize()}:", width=10, anchor="w",
                     bg=BG, fg=FG, font=("Segoe UI", 13, "bold")).pack(side="left")
            value_label = tk.Label(row, text="unknown", anchor="w", bg=BG, fg="#999999",
                                    font=("Segoe UI", 13), wraplength=380, justify="left")
            value_label.pack(side="left", fill="x", expand=True)
            self.service_labels[name] = value_label

        # --- Detected issues console panel ------------------------------------
        console_frame = tk.LabelFrame(
            self, text="Detected Issues (live)", bg=BG, fg="#999999",
            font=("Segoe UI", 13, "bold"), bd=1, relief="groove",
        )
        console_frame.pack(fill="both", expand=True, padx=16, pady=(0, 10))

        self.console = scrolledtext.ScrolledText(
            console_frame, height=10, bg=PANEL_BG, fg="#dddddd",
            font=("Consolas", 13), wrap="word", state="disabled", relief="flat",
        )
        self.console.pack(fill="both", expand=True, padx=6, pady=6)
        self.console.tag_configure("CRITICAL", foreground=RED_ACTIVE)
        self.console.tag_configure("WARNING", foreground=AMBER)
        self.console.tag_configure("INFO", foreground=GREEN_ACTIVE)
        self.console.tag_configure("DEFAULT", foreground="#dddddd")

        hint = ("Run log_populator.py to generate traffic and log_monitor.py to watch it. "
                "Use scripts/simulate_crash.py for an instant demo.")
        tk.Label(self, text=hint, wraplength=480, justify="center",
                 bg=BG, fg="#555555", font=("Segoe UI", 7)).pack(side="bottom", pady=6)

        self._poll()

    # -- status.json -----------------------------------------------------
    def _read_status(self) -> dict:
        try:
            with config.STATUS_FILE.open("r", encoding="utf-8") as fh:
                return json.load(fh)
        except (FileNotFoundError, json.JSONDecodeError):
            return {
                "overall_status": "UNKNOWN",
                "services": {},
                "updated_at": "",
            }

    def _apply_status(self, data: dict) -> None:
        overall = data.get("overall_status", "UNKNOWN")
        services = data.get("services", {})
        updated_at = data.get("updated_at", "")

        if overall == "OK":
            self.green_btn.configure(bg=GREEN_ACTIVE)
            self.red_btn.configure(bg=RED_DIM)
            self.status_label.configure(text="Status: OK", fg=GREEN_ACTIVE)
        elif overall in ("WARNING", "CRITICAL"):
            self.green_btn.configure(bg=GREEN_DIM)
            self.red_btn.configure(bg=RED_ACTIVE)
            self.status_label.configure(text=f"Status: {overall}", fg=RED_ACTIVE)
        else:
            self.green_btn.configure(bg=GREEN_DIM)
            self.red_btn.configure(bg=RED_DIM)
            self.status_label.configure(text="Status: UNKNOWN", fg="#999999")

        if updated_at:
            self.updated_label.configure(text=f"Last update: {updated_at}")

        for name, label in self.service_labels.items():
            info = services.get(name, {})
            status = info.get("status", "unknown")
            reason = info.get("reason", "")
            color = {"OK": GREEN_ACTIVE, "WARNING": AMBER, "CRITICAL": RED_ACTIVE}.get(status, "#999999")
            label.configure(text=f"{status} - {reason}" if reason else status, fg=color)

    # -- alerts.log --------------------------------------------------------
    def _apply_new_alerts(self, lines: list) -> None:
        if not lines:
            return
        self.console.configure(state="normal")
        for line in lines:
            tag = "DEFAULT"
            for level in ("CRITICAL", "WARNING", "INFO"):
                if f"[{level}]" in line:
                    tag = level
                    break
            self.console.insert("end", line + "\n", tag)
        self.console.see("end")
        self.console.configure(state="disabled")

    # -- polling loop --------------------------------------------------------
    def _poll(self) -> None:
        self._apply_status(self._read_status())
        self._apply_new_alerts(self.alert_tailer.read_new_lines())
        self.after(POLL_INTERVAL_MS, self._poll)


if __name__ == "__main__":
    app = StatusDashboard()
    app.mainloop()
