# Baseplate Layout

Two-level layout inside the Pelican-style case. A 3D-printed baseplate sits ~1.5" above the case floor, splitting components into a **topside** plane (user-facing, RF-sensitive) and an **underside** cavity (power distribution, router, heat). The battery is the exception: it passes through a rectangular cutout in the baseplate, sits on the case floor (so the case carries its weight, not the printed plate), and its upper half — including the terminals — protrudes above the baseplate surface.

## Topside

Component positions, looking down into the open case (top of image = hinge side):

| Position           | Component                       | Notes                                                                 |
| ------------------ | ------------------------------- | --------------------------------------------------------------------- |
| Top-left           | (reserved / open)               | Available for status light, momentary push button, power input, etc.  |
| Top-center         | Battery (12V), pass-through     | Sits on the case floor through a baseplate cutout; upper half + terminals protrude above the plate. Baseplate bears no battery weight. |
| Top-right          | Two toggle switches (SYSDISC, etc.) | Switch shafts protrude through the baseplate, so nothing can sit directly under them. |
| Left               | Pi enclosure                    | Vented metal enclosure. Verify enclosure fan orientation before final assembly so it doesn't recirculate against the lid foam. |
| Left edge of Pi    | Angled USB adapters             | For SDR. Mechanically brace so SDR weight doesn't stress Pi USB ports. |
| Center, beside battery cutout | BT1                  | Short RS232 run down to the Wanderer at bottom-right. Out of the wire-routing channel between Pi and fuse block. |
| Right-center       | Fuse block (WUPP)               | 12V positive bus fed from underside POST via grommet.                 |
| Bottom-right       | Renogy Wanderer SCC             | RS232 port faces toward BT1.                                          |

## Underside

Mounted to the underside of the baseplate. Antennas for the router are externally mounted on the case, so RF attenuation under the plate is not a concern.

| Position (under)   | Component                       | Rationale                                                                 |
| ------------------ | ------------------------------- | ------------------------------------------------------------------------- |
| Adjacent to battery cutout (top-center) | Blue Sea 2104 PowerPost (POST) | Mounted to the underside of the baseplate immediately beside the battery cutout. Short jumper from battery+ terminal (topside) drops through a small grommet to MAINFUSE → SYSDISC → POST. NOCO X-Connect positive ring lug also stacks at POST. Cannot sit directly under the battery anymore — that volume is occupied. |
| Under Pi (left)    | GL.iNet router (GL-AR300M16-Ext) | Farthest from BT1 (center-right topside), shortest Ethernet to Pi above, antenna pigtails to the left case wall. 5V power comes in from BUCKR on the right via USB-A→micro-USB. |
| Under fuse block (right-center) | Three buck converters: BUCKPI (Pi 5V/5A), BUCKUC (uConsole 5V/3A), BUCKR (router 5V/3A, dual USB-A) | Co-located with the WUPP fuse block that feeds them. Splits underside heat (router left, bucks right) instead of concentrating it. |

### Power topology

Reference: `cyberdeck-wiring.yml`. Key gates:

```
Battery+ → POST → MAINFUSE → SYSDISC ─┬─→ CC (Renogy Wanderer, solar charging)
                                       └─→ KILL (Load Kill) → FBPOS → BUCKPI → Pi
                                                                    → BUCKUC → uConsole
                                                                    → BUCKR  → Router (USB-A) + spare USB-A

NOCO X-Connect (+) ring lug ─→ POST   (upstream of SYSDISC, charger bypass)
NOCO X-Connect (-) ring lug ─→ FBNEG
```

- **Lid-closed (SYSDISC on / LOAD off):** Wanderer continues solar charging; all bucks (and therefore Pi, uConsole, router) are off; NOCO can charge regardless of either switch.
- **PowerPost clearance:** stacked ring lugs at POST = battery feed in + SYSDISC feed out + NOCO bypass. POST hangs from the underside of the baseplate next to the battery cutout; allow enough vertical clearance between POST and the case floor for the lug stack, since the battery body now occupies the volume directly under its own footprint and POST has to sit beside it instead.
- **Battery+ jumper:** short cable from the battery+ terminal (topside) down through a grommet at the edge of the battery cutout to MAINFUSE → SYSDISC → POST on the underside. Keep this run as short as the cutout-edge grommet allows, since it's unfused between the terminal and MAINFUSE.
- **Underside cable run:** BUCKR's USB-A out → micro-USB to the router crosses from right (under fuse block) to left (under Pi). Plan a tidy cable channel for this on the underside of the baseplate. Ethernet from Pi RJ45 drops straight down to the router below it.

## Ventilation

**Operating model** (confirmed against `cyberdeck-wiring.yml`):
- **Lid open:** SYSDISC on, LOAD KILL on. All systems running (Pi, uConsole, router, bucks, fan).
- **Lid closed:** SYSDISC on, LOAD KILL off. Wanderer continues solar charging; NOCO X-Connect can also charge (taps upstream of SYSDISC). All three bucks are downstream of LOAD KILL, so Pi, uConsole, router, and fan are all off. The Wanderer is the only meaningfully active component — and it's a mild, intermittent heat source during charging.

### Lid-open (active operation)

- **Intakes:** slots on the left and right case walls, at underside-cavity height — air enters the underside cavity from both sides.
- **Exhaust:** single fan mounted to the underside of the baseplate, center, between the Pi and Wanderer. Fan pulls cool air through the underside (across router on the left and bucks on the right) and pushes it up through a corresponding cutout in the baseplate into the open lid space.
- **Baseplate slots above bucks and router** assist the fan by giving heat dedicated paths up through the plate.
- The open lid provides effectively unlimited exhaust capacity.

### Lid-closed (charging only, loads off)

No forced airflow available (fan is downstream of LOAD), so rely on passive convection:
- **Cut side vent ports on both case walls** during initial build — low intake on one wall, high exhaust on the opposite wall, sized for natural convection out of the Wanderer's vicinity.
- These same ports also serve as the lid-closed convection vents for the underside cavity if any always-on heat sources end up there (see buck wiring note below).
- Pre-cut these ports on the bench — adding them after final assembly is significantly more annoying.
- Optional: plug them with foam during transport/storage to keep dust out.


### Fan control

- Powered from fuse block on its own low-amp fuse (~1A).
- Verify exhaust direction (arrow upward, toward open lid) before mounting.
- Optional later: PWM control via Pi GPIO tied to CPU temp or a buck-mounted DS18B20.
- Note: lid-open fan exhaust vents upward toward the operator. Not a problem, just expected behavior.

## RF considerations

- **Router under Pi (left)** and **BT1 topside center-right (below battery)** keeps the router's 2.4GHz radio diagonally opposite the BT1, minimizing desense.
- Router antennas externalized on the case wall, so the router being under the metallic Pi enclosure and buck/stud hardware doesn't matter for Wi-Fi range.
- BT1 stays topside in plastic-only surroundings (cardboard test plate → 3D-printed PLA/PETG production plate). No metal sandwiching.

## Open items / pre-print checklist

- [ ] Confirm BT1 → Wanderer RS232 cable length reaches chosen BT1 position without strain.
- [ ] Verify Pi enclosure fan direction (intake vs. exhaust) before final assembly.
- [ ] Verify exhaust fan arrow orientation (upward, toward lid) before mounting.
- [ ] Plan the underside USB-A → micro-USB cable channel from BUCKR (right) to the router (left). Keep it clear of the fan cutout.
- [ ] Plan zip-tie mount points on the printed baseplate for USB / signal cable management.
- [ ] Grommet locations: one at the edge of the battery cutout (battery+ jumper down to POST), one under fuse block (from POST back to topside), plus pass-throughs for the router Ethernet/power and the buck output rails.
- [ ] Battery cutout: size to the battery footprint with a small clearance, with rounded corners to avoid print stress risers. Confirm the battery's seated height leaves enough terminal clearance above the baseplate for ring lugs without fouling the closed lid foam.
- [ ] Confirm the case floor is flat (or shimmed flat) under the battery footprint so the battery sits stable when the deck is moved.
- [ ] Cutout in baseplate for the exhaust fan, plus dedicated vent slots above the bucks and above the router.
- [ ] Indoor vs. outdoor case use: open vent slots are fine indoors; if going IP-rated outdoors, switch to louvered covers + Gore-Tex pressure vent.
