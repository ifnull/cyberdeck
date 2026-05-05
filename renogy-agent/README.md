# renogy-agent

Pi-side telemetry agent for the cyberdeck's Renogy Wanderer 10A charge controller, polling over BLE via the [`cyrils/renogy-bt`](https://github.com/cyrils/renogy-bt) library.

## What it does

- Connects to the Renogy BT-1 Bluetooth dongle plugged into the Wanderer's RJ12 port.
- Polls the controller on a configurable interval and parses the Modbus response into a Python dict (battery voltage / SoC / current, PV voltage / current / power, controller temperature, charging status, etc.).
- Atomically writes the latest reading to `/run/renogy/latest.json` (tmpfs — no SD-card wear) so downstream consumers (e-ink dashboard, LCD1602 ops strip, MQTT bridge) can poll the file without IPC.
- Watches battery voltage and triggers a graceful `shutdown -h` after N consecutive low-voltage readings, so the Pi powers off cleanly before the LiFePO4 BMS yanks power.
- Runs as a systemd service with auto-restart, surviving reboots and BT-1 hiccups.

## Files in this directory

```
renogy-agent/
├── README.md                          ← this doc
├── agent.py                           ← the agent
├── config.ini                         ← BT-1 MAC, device_id, polling settings
└── systemd/
    └── renogy-agent.service           ← systemd unit
```

These files belong on the Pi at `/home/pi/renogy-agent/`. The systemd unit is installed to `/etc/systemd/system/`.

## Architecture decisions

- **Vendored library lives at `/opt/renogy-bt/`** (root-owned, `git pull`-able). The agent adds it to `sys.path` rather than `pip install`-ing, so the library can be updated independently without touching project code.
- **State file is in `/run/renogy/` (tmpfs)**, not `/var/lib/`. Writes don't wear the SD card; the file is recreated on every poll anyway, so volatility is fine.
- **Atomic JSON writes** (`tmp` file + `rename()`) so dashboard readers never see a partially-written file.
- **`systemd-tmpfiles` creates `/run/renogy/`** on every boot, so both the service and any interactive runs can write to it without sudo.
- **`Restart=always`** because the upstream library exits cleanly after each read cycle (one connect → one read batch → disconnect). The unit just relaunches every ~15 s, treating each poll as a fresh process. Inelegant but bulletproof.
- **Library handles its own asyncio loop and BLE lifecycle** via `RoverClient(...).start()` — don't try to wrap it with your own `asyncio.run()` (the library expects to own the loop and future).

## First-time setup on the Pi

### 1. System packages

```bash
sudo apt update
sudo apt install -y bluetooth bluez python3-pip git
sudo systemctl enable --now bluetooth
hciconfig             # expect "hci0 ... UP RUNNING"
```

### 2. Vendor the library

```bash
sudo git clone https://github.com/cyrils/renogy-bt /opt/renogy-bt
# library deps:
sudo pip3 install bleak --break-system-packages
```

(Pi OS Bookworm protects system Python; `--break-system-packages` is acceptable here since we're installing one well-known dep into the system interpreter that the agent runs under.)

### 3. Find the BT-1's MAC address

Plug the BT-1 into the Wanderer's RJ12 port (the controller powers it; the LED should pulse blue).

```bash
sudo bluetoothctl
power on
scan on
# wait for an entry like:
#   [NEW] Device XX:XX:XX:XX:XX:XX BT-TH-XXXXXXXX
scan off
exit
```

Copy the MAC. **Close the Renogy app on your phone** before scanning — the BT-1 only allows one client at a time.

### 4. Project files

Drop the contents of this directory onto the Pi:

```bash
mkdir -p ~/renogy-agent
# scp agent.py and config.ini onto the Pi here
```

Edit `~/renogy-agent/config.ini`:

```ini
[device]
adapter   = hci0
mac_addr  = XX:XX:XX:XX:XX:XX         # from step 3
alias     = BT-TH-XXXXXXXX
type      = RNG_CTRL                  # Wanderer / Rover / Adventurer
device_id = 1                         # Wanderer 10A factory default — NOT 255

[data]
enable_polling     = true
poll_interval      = 60
temperature_unit   = F
fields             =                  # blank = all fields

[remote_logging]
enabled = false
[mqtt]
enabled = false
[pvoutput]
enabled = false
```

> **`device_id` is the most common gotcha.** The upstream example config defaults to `255` (broadcast); the Wanderer 10A doesn't respond to broadcast and times out. Set it to `1`.

### 5. Sudoers entry for shutdown

The agent triggers `shutdown` from the `pi` user when battery voltage hits the low threshold:

```bash
sudo visudo -f /etc/sudoers.d/renogy-shutdown
```

Add:
```
pi ALL=(root) NOPASSWD: /sbin/shutdown
```

### 6. Persistent tmpfs directory

`/run` is wiped on reboot and only root can `mkdir` under it. Pre-stage a `systemd-tmpfiles` entry so `/run/renogy/` exists from boot onward, owned by `pi:pi`:

```bash
sudo tee /etc/tmpfiles.d/renogy.conf <<'EOF'
d /run/renogy 0755 pi pi -
EOF
sudo systemd-tmpfiles --create /etc/tmpfiles.d/renogy.conf
ls -la /run/renogy/    # expect: drwxr-xr-x pi pi
```

### 7. First interactive run

```bash
cd ~/renogy-agent
python3 agent.py
```

Expected (~15 s end-to-end):
```
INFO Init RoverClient: BT-TH-XXXXXXXX => XX:XX:XX:XX:XX:XX
INFO Starting discovery...
INFO Devices found: ...
INFO Found matching device BT-TH-XXXXXXXX => XX:XX:XX:XX:XX:XX
INFO Client connection: True
INFO subscribed to notification ...
INFO writing to ... [1, 3, 0, 12, 0, 8, 132, 15]      ← leading 1 = device_id
INFO on_data_received: read operation success           ← x4, one per register block
INFO on_read_operation_complete
INFO battery: 13.30V 100%  load=off  pv=0.0V/0.0A  status=deactivated
```

Then the script exits cleanly. Check the JSON:
```bash
cat /run/renogy/latest.json
```

### 8. Install the systemd service

```bash
sudo cp ~/renogy-agent/systemd/renogy-agent.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now renogy-agent
journalctl -u renogy-agent -f
```

The unit will launch the agent, the agent will run one poll cycle and exit, systemd will restart it after `RestartSec=15`, and so on. After ~30-40 s you should see `/run/renogy/latest.json` updating.

### 9. Reboot test

```bash
sudo reboot
```

After reboot, within ~30 s of login: `cat /run/renogy/latest.json` should show fresh data. This proves the whole chain (tmpfiles.d → service auto-start → BLE discovery → JSON write) works from cold.

## Known quirks

### `battery_percentage` is unreliable — use `battery_voltage` (and `battery_soc_estimate`)

The Wanderer's reported `battery_percentage` field is wrong for this build, for two compounding reasons:

1. **The controller can't see the loads.** In our wiring, the Pi / uConsole / router all draw from the fuse block, which taps the **battery terminals upstream of the Wanderer's load output**. The controller's load output isn't used at all. From the Wanderer's perspective, no current is leaving — so the battery "must" still be at 100%.
2. **The SoC table is calibrated for lead-acid.** LiFePO4 has an extremely flat discharge curve; the Wanderer's lookup just sits at 100% across most of the usable range.

The agent works around this by interpolating SoC from `battery_voltage` against a rested-LiFePO4 voltage table and injecting the result into the JSON as `battery_soc_estimate`:

| Rested voltage | Estimated SoC |
|---|---|
| 13.4 V+ | 100% |
| 13.2 V | 90% |
| 13.0 V | 60% |
| 12.9 V | 50% |
| 12.5 V | 15% |
| 12.0 V | 5% |
| 11.0 V | 0% (BMS protect imminent) |

Caveats:
- Voltage sags ~0.05–0.15 V per amp under load, so `battery_soc_estimate` will **underestimate** SoC while the Pi is busy. That's the safe direction for triggering low-battery actions.
- The middle of the LiFePO4 curve (~50–80% SoC, ~12.9–13.1 V) is genuinely flat — no instrument reads it accurately from voltage alone. A coulomb-counting shunt (Victron SmartShunt or similar, ~$110) is the real fix; out of scope for the portable kit.
- **`battery_percentage` is left in the JSON as-is** for parity with upstream, but downstream consumers (e-ink dashboard, etc.) should read `battery_soc_estimate` instead.
- LVD shutdown logic uses `battery_voltage` directly against `LOW_VOLTAGE = 11.8 V`. SoC estimation is only for display.

## Tuning

Edit `agent.py` then `sudo systemctl restart renogy-agent`.

| Constant | Default | Meaning |
|---|---|---|
| `LOW_VOLTAGE` | `11.8` | Volts. Below this counts as a "low" reading. ~5-10% real LiFePO4 SoC; leaves headroom above the BMS cutoff so the Pi can shut down cleanly. |
| `LOW_HITS` | `5` | Consecutive low readings before triggering shutdown. With 60 s polls = 5 minutes of sustained low. |
| `SHUTDOWN_MINUTES` | `1` | Argument to `shutdown -h +N`. Gives systemd ~60 s to flush services. |
| `DRY_RUN` | `True` | When `True`, logs `would have run: shutdown ...` instead of actually shutting down. **Flip to `False` after verifying the dry-run path works.** |

## Going live (after dry-run verification)

1. Verify dry-run by temporarily setting `LOW_VOLTAGE = 14.0` (above current battery voltage). After `LOW_HITS` polls, you should see the warning and the dry-run "would have run" log line. **No actual shutdown.**
2. Reset `LOW_VOLTAGE = 11.8`.
3. Set `DRY_RUN = False`.
4. `sudo systemctl restart renogy-agent`.

## Downstream consumers

Anything that needs the latest reading polls `/run/renogy/latest.json`. Suggested cadence per consumer:

| Consumer | Suggested poll | Stale threshold |
|---|---|---|
| E-ink battery dashboard | 60-300 s (e-ink is slow to refresh) | 3× poll interval — show "STALE" if older |
| LCD1602 live ops strip | 5-10 s | 60 s |
| MQTT bridge to Home Assistant (future) | 30-60 s | publish "unavailable" if older |

The atomic-write pattern means you never need to coordinate with the agent — `cat`, `json.load()`, etc. are always safe.

## Troubleshooting

### `Timed out! Please check your device_id!`
- `grep device_id ~/renogy-agent/config.ini` — confirm it's `1`, not `255`.
- Close the Renogy app on your phone (BT-1 = single-client only).
- Power-cycle the Wanderer (toggle System Disconnect off, count to 15, on) to reset the BT-1's internal state machine after rapid connect/disconnect cycles.

### `Device not found: BT-TH-...`
- BT-1 isn't advertising. Same fixes as above.
- Check `hciconfig` shows `UP RUNNING`; if `DOWN`, `sudo hciconfig hci0 up`.

### `PermissionError: [Errno 13] '/run/renogy'`
- Tmpfiles entry didn't run. Re-apply: `sudo systemd-tmpfiles --create /etc/tmpfiles.d/renogy.conf`.
- Confirm: `ls -la /run/renogy/` shows `pi:pi` ownership.

### `'NoneType' object has no attribute 'call_later'` or `'RoverClient' object has no attribute 'future'`
- You're trying to drive the library's async machinery yourself. Don't. Use `RoverClient(...).start()` and let it own the loop.

### `invalid literal for int() with base 10: '255 # ...'`
- `configparser` not handling inline `#` comments. The agent sets `inline_comment_prefixes=("#", ";")` to match the upstream's behavior; if you forked the script, restore that.

### Service starts then immediately deactivates with `status=0/SUCCESS`
- That's the library's normal exit pattern after one read cycle. With `Restart=always` (the default in our unit), systemd relaunches it. If you accidentally have `Restart=on-failure`, change it to `always`.

## Future enhancements

- [ ] **Router auto-halt on low battery** — once OpenWrt is flashed on the GL.iNet, install a no-password SSH key from the Pi to the router and have `trigger_shutdown()` SSH `poweroff` to the router before shutting down the Pi. Reduces residual draw to near-zero in the low-battery scenario. Marker comment is in `agent.py` inside `trigger_shutdown()`.
- [ ] **Persistent connection / one-process polling** — current pattern restarts the script on every poll cycle. Wrap `client.start()` in a loop with `time.sleep(poll_interval)` so one BLE connection serves many reads. Eliminates the BT-1 stress from rapid reconnects and cuts CPU/log noise. Premature optimization until it actually matters.
- [ ] **MQTT publish** — once a broker is running on the Pi (mosquitto), turn on `[mqtt] enabled = true` in `config.ini` and let the upstream library publish there directly. Cleaner decoupling for multi-consumer scenarios than reading JSON files.

## Related

- Upstream library: <https://github.com/cyrils/renogy-bt>
- Hardware context (charge controller spec, BT-1 wiring, fuse policy): see `../build-rationale.md`
