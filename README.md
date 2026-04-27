# Doomsday Cyberdeck

Portable, self-contained Pi-based field kit in a hardshell case. LiFePO4 power with solar charging, GL.iNet router serving WiFi clients, Pi server hosting offline content, modular monitoring telemetry.

> **Looking for the long version?** This README is the build guide. See [`build-rationale.md`](build-rationale.md) for the full design-decision log — every component choice, alternatives considered, and tradeoffs. The companion always-on rooftop ADS-B + Meshtastic station is documented in [`rooftop-station.md`](rooftop-station.md).
>
> **Pi software** runs from a slim Project Nomad fork: <https://github.com/ifnull/nomad-slim>.

---

## What's in the kit

| Subsystem | Components |
|-----------|------------|
| Case | Apache 4800 (or Pelican 1500), Kaizen foam, 3D printed mounting plate |
| Compute | Clockwork uConsole (primary interface) · Raspberry Pi (NVMe) running [nomad-slim](https://github.com/ifnull/nomad-slim) for offline content |
| Networking | GL.iNet GL-AR300M16-Ext "Shadow Ext" — OpenWrt AP, 2× external RP-SMA antennas through case wall |
| Comms | NooElec SMArTee XTR SDR + telescoping whip antenna |
| Power | LiFePO4 12V 5Ah / 64Wh battery · Renogy Wanderer 10A PWM controller (LI mode) · 50W solar panel · DROK 12V→5V/5A buck for Pi · separate buck for uConsole · WUPP 6-way fuse block · Blue Sea 2104 PowerPost · system disconnect + load kill switches |
| Monitoring | BT-1 Bluetooth telemetry from charge controller · Waveshare e-ink battery dashboard · SunFounder LCD1602 live ops strip |
| External power | Anderson Powerpole input (panel mount) · NOCO Genius X-Connect ring-terminal pigtail (bypasses both switches) |

## Bill of materials (summary)

| Category | Cost |
|----------|------|
| Case | $50-130 |
| uConsole | $150-200 |
| Pi 4 + NVMe storage | $70-95 |
| GL.iNet Shadow Ext + RP-SMA bulkheads + Ethernet patch | $50-60 |
| Power system | $95-160 |
| Monitoring (e-ink + LCD on hand; BT-1 module new) | $18-30 |
| 14 AWG marine wire (red + black, ~25 ft each) | $25-40 |
| Connectors, cables, foam, misc | $30-50 |
| SDR (already owned) | $0 |
| **Total** | **$428-705** |

Detailed component list with brand recommendations is in [`build-rationale.md`](build-rationale.md).

## Wiring

```
Battery (+) ──► PowerPost ──► Main Fuse ──► System Disconnect ──┬─► Charge Controller (BAT+)
                    │                                           │
                    │                                           └─► Load Kill ──► Fuse Block ──► Bucks ──► Loads
                    │
                    └─► NOCO X-Connect (+) ──► (smart-charger bypass)

Battery (−) ──► Fuse Block (−) Bus ◄── Charge Controller (BAT−), NOCO X-Connect (−), all load returns
```

**Full diagram** (regenerated from [`cyberdeck-wiring.yml`](cyberdeck-wiring.yml) by [WireViz](https://github.com/wireviz/WireViz)):

![Cyberdeck wiring](cyberdeck-wiring.svg)

To regenerate after editing the YAML:

```bash
./build-wiring-diagram.sh
```

A pre-commit hook in `.githooks/` will do this automatically when `cyberdeck-wiring.yml` is staged. Activate it once per clone:

```bash
git config core.hooksPath .githooks
```

First-time tool setup:

```bash
pip install --user wireviz       # or: pipx install wireviz
sudo apt install graphviz        # WireViz uses the `dot` binary
```

## Build phases

### Phase 1 — Compute & content
- [ ] Pi + Pi OS Lite, NVMe storage, [nomad-slim](https://github.com/ifnull/nomad-slim) installed for Kiwix-serve and content management
- [ ] GL.iNet Shadow Ext flashed/configured: SSID, WPA2 password, captive portal, Pi static lease
- [ ] Pi connected to router via short Ethernet patch
- [ ] Verify offline WiFi content serving and search
- [ ] Mount in case loosely

### Phase 2 — Power & telemetry
- [ ] Full power system: Wanderer 10A, WUPP fuse block, DROK buck for Pi server, system disconnect + load kill switches, Blue Sea 2104 PowerPost as positive distribution point
- [ ] Configure Wanderer LCD: change battery type SLD → **LI**; verify 14.4V boost / 13.6V float
- [ ] Wire DROK output to Waveshare 5V power screw terminal (trim DROK to ~5.1-5.15V no-load before connecting)
- [ ] Verify no undervoltage warnings under NVMe + fan + WiFi AP load
- [ ] Solar panel charging tested
- [ ] BT-1 module + `cyrils/renogy-bt` telemetry working on the Pi
- [ ] E-ink battery dashboard daemon + LCD1602 live ops strip running
- [ ] 3D print mounting plate (cutouts for switches, displays, PowerPost, router cradle)
- [ ] Drill 2× ~10mm holes for RP-SMA antenna bulkheads (gasketed)
- [ ] Run RP-SMA pigtails from router to bulkheads, mount stock antennas externally
- [ ] Power Shadow Ext from Wanderer's 5V/2A USB output
- [ ] Anderson Powerpole panel mount installed (single hole)
- [ ] Cable management

### Phase 3 — SDR
- [ ] SDR mounted on plate inside case, telescoping antenna installed
- [ ] gqrx, rtl_433 verified from uConsole
- [ ] Verify Meshtastic connectivity to the rooftop station (when both are deployed)

### Phase 4 — Field hardening
- [ ] Cyberdeck runtime benchmarks under various loads
- [ ] Wall charger, vehicle adapter, NOCO smart-charger paths all tested
- [ ] Spare parts kit (extra SD cards, fuses, cables, CM4)
- [ ] Documentation printed and stored in case

### Phase 5 — uConsole AIO V2 (future)
- [ ] Install HackerGadgets AIO V2 in uConsole
- [ ] Configure built-in LoRa/Meshtastic, GPS, RTL-SDR
- [ ] Retire NooElec SDR (repurpose or keep as spare)

## Operating modes

| Mode | System Disconnect | Load Kill | Notes |
|------|-------------------|-----------|-------|
| Normal operation | ON | ON | Full system live |
| Passive solar maintenance | ON | OFF | Loads off, controller charges from sun |
| Long-term storage | OFF | (any) | Zero parasitic draw; NOCO can still charge via X-Connect |

## Software

The Pi runs **[nomad-slim](https://github.com/ifnull/nomad-slim)** — a slim fork of Project Nomad targeting Raspberry Pi for the offline-content / Kiwix server role. WiFi AP, DHCP, and DNS are handled by the GL.iNet Shadow Ext (OpenWrt) — the Pi just hosts content and exposes Kiwix on a static LAN address.

See nomad-slim's repo for installation, ZIM file management, and configuration.

## Repo layout

```
.
├── README.md                    ← you are here (build guide)
├── build-rationale.md           ← full design-decision log
├── rooftop-station.md           ← companion always-on Meshtastic + ADS-B station
├── cyberdeck-wiring.yml         ← WireViz harness source
├── cyberdeck-wiring.svg         ← generated diagram (committed for inline GitHub render)
├── cyberdeck-wiring.bom.tsv     ← generated BOM
├── build-wiring-diagram.sh      ← regen script
└── .githooks/
    └── pre-commit               ← auto-regen SVG when YAML is staged
```

## Related

- **[nomad-slim](https://github.com/ifnull/nomad-slim)** — Pi software stack (Kiwix server, content management)
- **[WireViz](https://github.com/wireviz/WireViz)** — wire harness diagram tool used for the wiring source
