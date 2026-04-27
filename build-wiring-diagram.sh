#!/usr/bin/env bash
#
# Regenerates the wiring diagram from cyberdeck-wiring.yml.
#
# Outputs (committed alongside the YAML so GitHub renders the SVG inline):
#   cyberdeck-wiring.svg     - embed in markdown via ![]()
#   cyberdeck-wiring.png     - raster fallback
#   cyberdeck-wiring.html    - interactive (hover for tooltips, etc.)
#   cyberdeck-wiring.bom.tsv - auto-generated bill of materials
#
# First-time setup (any one of these works):
#   pip install --user wireviz
#   pipx install wireviz
#   uv tool install wireviz
#
# Then from this directory:
#   ./build-wiring-diagram.sh
#
# Requires Graphviz (the `dot` binary) on PATH:
#   sudo apt install graphviz       # Debian/Ubuntu
#   brew install graphviz           # macOS

set -euo pipefail

cd "$(dirname "$0")"

SOURCE="cyberdeck-wiring.yml"

if [[ ! -f "$SOURCE" ]]; then
    echo "Error: $SOURCE not found in $(pwd)" >&2
    exit 1
fi

if ! command -v wireviz >/dev/null 2>&1; then
    echo "Error: wireviz not installed." >&2
    echo "Install with one of:" >&2
    echo "  pip install --user wireviz" >&2
    echo "  pipx install wireviz" >&2
    echo "  uv tool install wireviz" >&2
    exit 1
fi

if ! command -v dot >/dev/null 2>&1; then
    echo "Error: graphviz (dot) not installed; wireviz needs it to lay out the diagram." >&2
    echo "Install with:" >&2
    echo "  sudo apt install graphviz   (Debian/Ubuntu)" >&2
    echo "  brew install graphviz       (macOS)" >&2
    exit 1
fi

echo "Regenerating wiring diagram from $SOURCE..."
# -f hpstg = html, png, svg, tsv, AND graphviz (.gv).
# By default WireViz omits the .gv; we need it to post-process the layout.
wireviz -f hpstg "$SOURCE"

# WireViz defaults to a left-to-right (LR) layout, which renders wide on
# GitHub and gets aggressively scaled down to fit the page width. Force a
# top-to-bottom (TB) layout by rewriting the intermediate .gv file and
# re-rendering with dot. Use Python for robust regex (sed was unreliable
# across WireViz output variations).
GV="cyberdeck-wiring.gv"
if [[ -f "$GV" ]]; then
    echo
    python3 - "$GV" <<'PYEOF'
import re, sys, pathlib
gv = pathlib.Path(sys.argv[1])
content = gv.read_text()

# Find any rankdir lines (case-insensitive, optional quotes/spacing)
pattern = re.compile(r'(rankdir\s*=\s*)(["\']?)(LR|RL|TB|BT)\2', re.IGNORECASE)
matches = pattern.findall(content)
print(f"[wireviz-postprocess] rankdir occurrences before: {len(matches)} -> {matches}")

# Replace any LR/RL with TB
new = pattern.sub(lambda m: f'{m.group(1)}{m.group(2)}TB{m.group(2)}', content)

# If no rankdir found at all, inject TB right after the opening brace.
if 'rankdir' not in new.lower():
    print("[wireviz-postprocess] no rankdir found; injecting rankdir=TB")
    new = re.sub(r'((?:di)?graph[^{]*\{)',
                 r'\1\n\trankdir=TB;\n\tnodesep=0.25;\n\tranksep=0.4;',
                 new, count=1)
elif 'nodesep' not in new.lower():
    # rankdir already (now TB); add tighter spacing.
    new = re.sub(r'((?:di)?graph[^{]*\{)',
                 r'\1\n\tnodesep=0.25;\n\tranksep=0.4;',
                 new, count=1)

gv.write_text(new)

# Verify
matches_after = pattern.findall(new)
print(f"[wireviz-postprocess] rankdir occurrences after:  {len(matches_after)} -> {matches_after}")
PYEOF

    echo
    echo "Re-rendering SVG/PNG with edited .gv..."
    # Belt-and-suspenders: also pass -Grankdir=TB on the command line so dot
    # uses TB even if the .gv edit somehow didn't take.
    dot -Grankdir=TB -Gnodesep=0.25 -Granksep=0.4 -Tsvg -o cyberdeck-wiring.svg "$GV"
    dot -Grankdir=TB -Gnodesep=0.25 -Granksep=0.4 -Tpng -o cyberdeck-wiring.png "$GV"
fi

echo
echo "Done. Generated files:"
ls -1 cyberdeck-wiring.{svg,png,html,bom.tsv} 2>/dev/null || true
echo
echo "Embed in markdown:"
echo '  ![Cyberdeck wiring](cyberdeck-wiring.svg)'
