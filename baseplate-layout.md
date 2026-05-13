# Baseplate Layout

Two-level layout inside the Pelican-style case. A 3D-printed baseplate sits ~1.5" above the case floor, splitting components into a **topside** plane (user-facing, RF-sensitive) and an **underside** cavity (power distribution, router, heat).

## Topside

Component positions, looking down into the open case (top of image = hinge side):

| Position           | Component                       | Notes                                                                 |
| ------------------ | ------------------------------- | --------------------------------------------------------------------- |
| Top-left           | Two toggle switches (SYSDISC, etc.) | Flanked left and right by intake vents on the top case wall.       |
| Left               | Pi enclosure                    | Status light, momentary push button, power input, and Pi intake vents on the left case wall. Pi enclosure fan orientation to be verified before final assembly so it doesn't recirculate against the lid foam. |
| Left edge of Pi    | Angled USB adapters             | For SDR. Mechanically brace so SDR weight doesn't stress Pi USB ports. |
| Top-center         | Battery (12V)                   | Positive terminal directly above the underside 12V stud.              |
| Top-right          | Renogy Wanderer SCC             | RS232 port faces toward BT1.                                          |
| Right-center       | BT1                             | Topside, right of Wanderer. Short RS232 run. Kept away from router below. Cable secured against fan vibration. |
| Bottom-center      | Fuse block                      | 12V positive bus fed from underside stud via grommet.                 |
| Bottom-right       | 80mm exhaust fan                | Powered from fuse block on its own low-amp fuse (~1A). Verify exhaust direction (arrow outward) before mounting. Optional later: PWM control via Pi GPIO tied to CPU temp or a buck-mounted DS18B20. |

## Underside

Mounted to the underside of the baseplate. Antennas for the router are externally mounted on the case, so RF attenuation under the plate is not a concern.

| Position (under)   | Component                       | Rationale                                                                 |
| ------------------ | ------------------------------- | ------------------------------------------------------------------------- |
| Under battery      | 12V distribution stud           | Battery+ drops straight down through a grommet → disconnect → stud. Shortest, most symmetric feed point. |
| Under fuse block (right) | Buck converter(s)         | Co-located with fuse block; short runs for 12V in and stepped-down rails out. Warmest non-router component, placed near exhaust side. |
| Under Pi (left)    | Wi-Fi router                    | Short Ethernet to Pi above. Puts router's 2.4GHz radio on the opposite side of the deck from BT1. Antenna pigtails run to the left case wall. |

### Power topology

```
Battery+ → grommet → disconnect → 12V stud → ┬→ Buck converter(s)  (right)
                                              ├→ Router            (left)
                                              └→ grommet → Fuse block (topside)
```

Leave extra clearance around the stud in the printed baseplate — stacked ring lugs (battery feed + 2-3 distribution legs) build up taller than expected.

## Ventilation

Two independent airflow paths.

**Topside (diagonal sweep):**
- Intake: slots on the top case wall, flanking the toggle switches (left and right).
- Exhaust: 80mm fan, bottom-right.
- Sweeps across Pi → battery → Wanderer toward the fan.

**Underside (heat source plane):**
- Default approach: cut airflow slots in the baseplate directly above the bucks and above the router so the topside exhaust fan also pulls underside heat up through them.
- Upgrade if router/bucks run hot: add a small (40mm) underside fan as exhaust on the opposite case wall from a dedicated underside intake — independent loop from the topside.

Wire pass-through slots alone are not a reliable airflow path between layers — they help, but plan dedicated vent slots.

## RF considerations

- **Router under Pi (left)** and **BT1 topside-right (near Wanderer)** keeps the router's 2.4GHz radio diagonally opposite the BT1, minimizing desense.
- Router antennas externalized on the case wall, so the router being under the metallic Pi enclosure and buck/stud hardware doesn't matter for Wi-Fi range.
- BT1 stays topside in plastic-only surroundings (cardboard test plate → 3D-printed PLA/PETG production plate). No metal sandwiching.

## Open items / pre-print checklist

- [ ] Confirm BT1 → Wanderer RS232 cable length reaches chosen BT1 position without strain.
- [ ] Verify Pi enclosure fan direction (intake vs. exhaust) before final assembly.
- [ ] Verify 80mm fan arrow orientation before mounting.
- [ ] Decide whether underside cooling = baseplate slots only, or slots + dedicated underside fan.
- [ ] Plan zip-tie mount points on the printed baseplate for USB / signal cable management (especially the coiled USB near the fan).
- [ ] Grommet locations: one under battery+ (to stud), one under fuse block (from stud back to topside).
- [ ] Indoor vs. outdoor case use: open vent slots are fine indoors; if going IP-rated outdoors, switch to louvered covers + Gore-Tex pressure vent.
