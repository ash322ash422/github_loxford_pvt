"""
scripts/simulate_crash.py
==========================
Teaching helper: manually injects a crash burst (or a batch of plain error
lines) directly into a chosen service's log file, so students can watch
log_monitor.py detect it and gui_status.py flip to RED on demand, instead
of waiting for log_populator.py to roll a random one.

Usage (run from the project root):
    python scripts/simulate_crash.py                       # apache crash burst (CRITICAL)
    python scripts/simulate_crash.py --service samba        # samba crash burst (CRITICAL)
    python scripts/simulate_crash.py --service apache --errors  # apache errors only (WARNING)
    python scripts/simulate_crash.py --service samba --errors   # samba errors only (WARNING)
"""
import argparse
import sys
from pathlib import Path

# Allow running this script directly from the scripts/ folder.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config
import log_populator as populator


def main() -> None:
    parser = argparse.ArgumentParser(description="Manually inject a test event into a service log.")
    parser.add_argument("--service", choices=["apache", "samba"], default="apache",
                         help="which service's log to inject into (default: apache)")
    parser.add_argument("--errors", action="store_true",
                         help="inject error-level lines only (WARNING), instead of a full crash burst (CRITICAL)")
    args = parser.parse_args()

    log_file = config.SERVICES[args.service]["log_file"]

    if args.service == "apache":
        error_line_fn = populator.apache_5xx_line
        crash_lines_fn = populator.apache_crash_lines
    else:
        error_line_fn = populator.samba_error_line
        crash_lines_fn = populator.samba_crash_lines

    if args.errors:
        for _ in range(6):
            populator.write_line(log_file, error_line_fn())
        print(f"Injected 6 error-level lines into {log_file}")
    else:
        lines = crash_lines_fn()
        for line in lines:
            populator.write_line(log_file, line)
        print(f"Injected a {args.service.upper()} crash burst ({len(lines)} lines) into {log_file}")


if __name__ == "__main__":
    main()
