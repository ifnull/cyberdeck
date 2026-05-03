#!/usr/bin/env python3
"""
Cyberdeck Renogy telemetry agent.

- Polls the Renogy BT-1 over BLE via the cyrils/renogy-bt library.
- Writes the latest reading atomically to /run/renogy/latest.json (tmpfs).
- Triggers a graceful shutdown after N consecutive low-voltage readings.

Layout assumed:
    /opt/renogy-bt/            <- vendored library (root-owned, git-pullable)
    ~/renogy-agent/agent.py    <- this script
    ~/renogy-agent/config.ini  <- BT-1 MAC, device_id, polling settings

Sudoers (one-time):
    pi ALL=(root) NOPASSWD: /sbin/shutdown
"""

import configparser
import json
import logging
import subprocess
import sys
from pathlib import Path

# Make the vendored library importable.
sys.path.insert(0, "/opt/renogy-bt")
from renogybt import RoverClient  # noqa: E402

# ---------------------------------------------------------------------------
# Tunables
# ---------------------------------------------------------------------------
JSON_PATH = Path("/run/renogy/latest.json")  # tmpfs; no SD wear
LOW_VOLTAGE = 11.8                           # volts; below this counts as "low"
LOW_HITS = 5                                 # consecutive low readings before action
SHUTDOWN_MINUTES = 1                         # shutdown -h +N
DRY_RUN = True                               # flip to False once you've verified
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
log = logging.getLogger("renogy-agent")

low_streak = 0


def write_json(data: dict) -> None:
    """Atomically write the latest reading so readers never see partial JSON."""
    JSON_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = JSON_PATH.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, indent=2))
    tmp.replace(JSON_PATH)


def trigger_shutdown(voltage: float) -> None:
    msg = f"battery {voltage:.2f}V below {LOW_VOLTAGE}V for {LOW_HITS} polls"
    log.warning("LOW BATTERY -> shutdown: %s", msg)
    # TODO: SSH-poweroff the GL.iNet router here once OpenWrt is flashed and
    # a no-password ssh key is installed (see renogy-agent/README.md).
    if DRY_RUN:
        log.warning("DRY_RUN=True; would have run: shutdown -h +%d", SHUTDOWN_MINUTES)
        return
    subprocess.run(
        [
            "sudo",
            "/sbin/shutdown",
            "-h",
            f"+{SHUTDOWN_MINUTES}",
            f"Cyberdeck low battery: {msg}",
        ],
        check=False,
    )


def on_data(client, data: dict) -> None:
    global low_streak
    write_json(data)

    voltage = data.get("battery_voltage", 0) or 0
    pct = data.get("battery_percentage", 0)
    log.info(
        "battery: %.2fV %s%%  load=%s  pv=%.1fV/%.1fA  status=%s",
        voltage,
        pct,
        data.get("load_status"),
        data.get("pv_voltage", 0) or 0,
        data.get("pv_current", 0) or 0,
        data.get("charging_status"),
    )

    if 0 < voltage < LOW_VOLTAGE:
        low_streak += 1
        log.warning("LOW reading %d/%d (%.2fV)", low_streak, LOW_HITS, voltage)
        if low_streak >= LOW_HITS:
            trigger_shutdown(voltage)
    else:
        if low_streak:
            log.info("voltage recovered (%.2fV); resetting low streak", voltage)
        low_streak = 0


def on_error(client, error) -> None:
    log.error("BT-1 error: %s", error)


def main() -> None:
    cfg_path = Path(__file__).parent / "config.ini"
    if not cfg_path.exists():
        log.error("config not found: %s", cfg_path)
        sys.exit(1)

    cfg = configparser.ConfigParser(inline_comment_prefixes=("#", ";"))
    cfg.read(cfg_path)

    RoverClient(cfg, on_data, on_error).start()


if __name__ == "__main__":
    main()
