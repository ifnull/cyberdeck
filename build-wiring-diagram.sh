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
wireviz "$SOURCE"

echo
echo "Done. Generated files:"
ls -1 cyberdeck-wiring.{svg,png,html,bom.tsv} 2>/dev/null || true
echo
echo "Embed in markdown:"
echo '  ![Cyberdeck wiring](cyberdeck-wiring.svg)'
