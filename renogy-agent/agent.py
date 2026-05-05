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

# Rested-LiFePO4 voltage-to-SoC table. The Wanderer's reported
# `battery_percentage` is calibrated for lead-acid and is unreliable for
# LiFePO4 (sticks at 100% across most of the discharge curve), and it can't
# see loads on the fuse block anyway. We estimate SoC from voltage instead
# and inject it into the JSON as `battery_soc_estimate`.
_SOC_TABLE = [
    (13.4, 100),
    (13.3, 95),
    (13.2, 90),
    (13.1, 80),
    (13.0, 60),
    (12.9, 50),
    (12.8, 30),
    (12.5, 15),
    (12.0, 5),
    (11.0, 0),
]


def soc_from_voltage(voltage: float) -> int:
    """Linear interpolation across the rested-LiFePO4 voltage table.

    Best accuracy at rest; under load the pack sags ~0.05-0.15 V per amp,
    so this will *underestimate* SoC during heavy draw. That's the safe
    direction for triggering low-battery actions.
    """
    if voltage >= _SOC_TABLE[0][0]:
        return 100
    if voltage <= _SOC_TABLE[-1][0]:
        return 0
    for (v_hi, p_hi), (v_lo, p_lo) in zip(_SOC_TABLE, _SOC_TABLE[1:]):
        if v_lo <= voltage <= v_hi:
            return int(round(p_lo + (p_hi - p_lo) * (voltage - v_lo) / (v_hi - v_lo)))
    return 0


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

    voltage = data.get("battery_voltage", 0) or 0
    data["battery_soc_estimate"] = soc_from_voltage(voltage)
    write_json(data)

    log.info(
        "battery: %.2fV  est=%d%%  (controller=%s%%)  load=%s  pv=%.1fV/%.1fA  status=%s",
        voltage,
        data["battery_soc_estimate"],
        data.get("battery_percentage", 0),
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
