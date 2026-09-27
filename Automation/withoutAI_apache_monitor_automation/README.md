# Server Log Monitoring Automation (Teaching Project)

A small but "industry-shaped" automation pipeline that watches TWO
simulated services - **Apache** and **Samba** - detects problems in their
logs, alerts administrators in the console, and shows live status on a
Tkinter dashboard with red/green indicator lights. Built to be read
top-to-bottom as a teaching example of a real monitoring automation.

## What it demonstrates

- **Producer/consumer processes** talking only through files (log files in,
  a status file + alert log out) - no direct coupling, so each piece can be
  started, stopped, or restarted independently.
- **Monitoring more than one log source with the same code path** - a
  generic, classifier-driven `HealthEvaluator` / `ServiceWatcher` handles
  both Apache and Samba (and can be extended to a third service by adding
  one config entry and one small classifier function).
- **Tailing a growing file safely** (offset persistence, rotation handling).
- **Concurrency** - the populator runs Apache and Samba traffic on two
  independent threads, each with its own random timing.
- **Sliding-window health evaluation** instead of reacting to a single line.
- **Alert de-duplication / cooldown** so admins aren't spammed, tracked
  independently per service.
- **Pluggable notification channels** (console, file, e-mail) via a simple
  Strategy pattern.
- **Atomic status publishing** (`status.json`) so a reader never sees a
  half-written file.
- **A GUI that only displays state** - it never computes health itself; it
  polls `status.json` and tails `alerts.log`, the same way a real dashboard
  would subscribe to a backend service.
- Graceful shutdown on Ctrl+C / SIGTERM, structured logging, and a config
  module that centralizes every tunable value.

## Project layout

```
apache_monitor_automation/
├── config.py               # all paths, thresholds, intervals, SMTP settings
├── log_populator.py        # simulates live Apache + Samba services (2 threads)
├── log_monitor.py          # THE AUTOMATION: tails both logs, detects issues,
│                            # alerts (console + file + email), publishes status
├── gui_status.py            # Tkinter dashboard: green/red buttons, per-service
│                            # breakdown, live "Detected Issues" console panel
├── utils/
│   └── notifier.py         # Console / File / Email alert channels + Notifier
├── scripts/
│   ├── simulate_crash.py    # manually inject a crash/error into either service
│   └── run_all.py          # convenience: launches populator + monitor + GUI together
├── logs/
│   ├── apache_access.log        # simulated apache access log (generated)
│   ├── samba.log                # simulated samba event log (generated)
│   ├── populator_service.log    # log_populator.py's own operational log
│   └── monitor_service.log      # log_monitor.py's own operational log
├── alerts/
│   └── alerts.log           # persisted history of every alert ever sent
├── status/
│   └── status.json          # current health, written by the monitor, read by the GUI
└── state/
    ├── apache_offset.json    # bookmark: how far the monitor has read apache_access.log
    └── samba_offset.json     # bookmark: how far the monitor has read samba.log
```

## Requirements

Python 3.9+. No third-party packages - everything (including `tkinter`) is
in the standard library. On some Linux distros you may need to install the
Tk bindings separately, e.g. `sudo apt-get install python3-tk`.

## Running it

Open three terminals in the project root (or just use the launcher, see
below).

**Terminal 1 - simulate both servers:**
```bash
python log_populator.py
```
Runs two threads that independently write to `logs/apache_access.log` and
`logs/samba.log`, each with normal traffic, occasional errors, and rare
full "crash" events.

**Terminal 2 - run the automation:**
```bash
python log_monitor.py
```
Every few seconds it reads whatever is new in *both* log files, decides if
each service is healthy, writes `status/status.json`, prints any detected
issue straight to the console, and - if there's a problem - alerts
administrators (console + `alerts/alerts.log`, and e-mail if you configure
SMTP in `config.py`).

**Terminal 3 - watch the dashboard:**
```bash
python gui_status.py
```
A window with:
- **GREEN** / **RED** indicator buttons for overall health,
- a per-service breakdown (Apache: OK, Samba: CRITICAL - reason...),
- a live "Detected Issues" panel that shows each alert as it happens,
  color-coded by severity - the same alerts also printed by the monitor's
  console.

**Or, all at once:**
```bash
python scripts/run_all.py
```

## Forcing a demo crash instantly

Rather than waiting for `log_populator.py` to randomly roll a crash, inject
one on demand:
```bash
python scripts/simulate_crash.py                              # apache crash burst -> CRITICAL
python scripts/simulate_crash.py --service samba                # samba crash burst -> CRITICAL
python scripts/simulate_crash.py --service apache --errors      # apache 5xx run -> WARNING
python scripts/simulate_crash.py --service samba --errors       # samba ERROR run -> WARNING
```
Watch the monitor's terminal print `[ISSUE DETECTED] ...` within a few
seconds, and the GUI's red button and console panel update to match.

## How detection works (log_monitor.py)

1. For each service in `config.SERVICES`, a `LogTailer` remembers the byte
   offset it last read (`state/*_offset.json`) and only reads newly
   appended, *complete* lines each poll - like `tail -f`.
2. A service-specific classifier turns each new line into `"crash"`,
   `"error"`, or `None`:
   - **Apache**: an HTTP status >= 500 in the request line -> `"error"`;
     the word "crash" (from a simulated Apache-error-log entry) -> `"crash"`.
   - **Samba**: the word `ERROR` -> `"error"`; `PANIC`, `CRITICAL`, or
     "crashed" -> `"crash"`.
3. A `HealthEvaluator` keeps a sliding window (`config.MONITOR_WINDOW_SEC`)
   of these events per service and decides:
   - `>= CRASH_THRESHOLD` crash markers -> **CRITICAL**
   - `>= ERROR_THRESHOLD` error lines -> **WARNING**
   - no new log lines for `HEARTBEAT_TIMEOUT_SEC` -> **WARNING** (service may be down)
   - otherwise -> **OK**
4. The overall status shown by the GUI is the worst of the two services.
5. `AlertManager` notifies admins immediately when a service's status
   changes, again every `ALERT_COOLDOWN_SEC` while it persists, and once
   more with a "recovered" message when it returns to OK - all tracked
   independently per service.
6. `publish_status()` writes `status/status.json` atomically (write to a
   temp file, then rename) so `gui_status.py` never reads a partial file.

## Configuring e-mail alerts

By default, `config.SMTP_HOST` is empty, so alerts only go to the console
and `alerts/alerts.log` - handy for an offline classroom demo. To enable
real e-mail, fill in `SMTP_HOST`, `SMTP_USERNAME`, `SMTP_PASSWORD`,
`ALERT_FROM_ADDR`, and `ALERT_TO_ADDRS` in `config.py`.

## Ideas for extending this as a teaching exercise

- Add a third service (e.g. `nginx` or `mysql`) by adding one entry to
  `config.SERVICES` and one small classifier function - `log_monitor.py`
  and `gui_status.py` pick it up automatically.
- Add a `SlackChannel` or `WebhookChannel` to `utils/notifier.py`.
- Parse real Apache/Samba logs instead of the populator's fake ones.
- Give each service its own thresholds instead of sharing
  `ERROR_THRESHOLD` / `CRASH_THRESHOLD` in `config.py`.
- Swap `status.json` for a tiny HTTP endpoint and make the GUI poll that
  instead, to introduce networking.
- Containerize each of the three processes to teach multi-service Docker
  Compose setups.
