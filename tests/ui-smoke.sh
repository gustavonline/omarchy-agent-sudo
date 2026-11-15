#!/bin/bash
# Compile a fresh, hidden instance against the installed Omarchy components.
set -euo pipefail
plugin_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
omarchy_path=${OMARCHY_PATH:-/usr/share/omarchy}
fixture=$(mktemp -d)
trap 'rm -rf -- "$fixture"' EXIT
ln -s "$omarchy_path/shell/Commons" "$fixture/Commons"
ln -s "$omarchy_path/shell/Ui" "$fixture/Ui"
# Load a private copy with a no-op adapter: never register source skills or
# query/request real access when testing a hidden component.
cp "$plugin_dir/Panel.qml" "$fixture/Panel.qml"
cat > "$fixture/agent-access" <<'STUB'
#!/bin/sh
[ "$1" != status ] || printf '%s\n' '{"ready":true,"enrolled":true,"maxMinutes":240,"active":false,"pending":false}'
STUB
chmod +x "$fixture/agent-access"
python3 - "$fixture/Panel.qml" "$fixture/shell.qml" <<'PY'
import json,sys
from pathlib import Path
panel=Path(sys.argv[1])
panel.write_text(panel.read_text().replace('id: root', 'id: root\n  property alias smokeDurationInput: durationInput', 1))
source=json.dumps(str(panel.resolve()))
Path(sys.argv[2]).write_text('''import QtQuick
import Quickshell
ShellRoot {
  Loader {
    source: '''+source+'''
    onLoaded: {
      if (item.clock(65) !== "01:05") throw new Error("Countdown format failed")
      if (item.clock(3661) !== "1:01:01") throw new Error("Long countdown failed")
      item.status = {maxMinutes: 240, ready: true, enrolled: true}
      if (item.maxMinutes !== 240 || item.defaultMinutes !== 5) throw new Error("Installed limit/default mismatch")
      item.durationHours = true
      item.selectedMinutes = 120
      if (item.unitFactor !== 60 || item.durationLimit !== 240) throw new Error("Hour normalization failed")
      const editor = item.smokeDurationInput
      item.customDuration = true
      editor.field.contentItem.text = "1.5"
      if (item.durationInputValid) throw new Error("Fractional input was accepted")
      editor.field.contentItem.text = "2"
      if (!item.durationInputValid) throw new Error("Whole hour input was rejected")
      item.status = {maxMinutes: 15}
      if (item.maxMinutes !== 15) throw new Error("Old root ceiling was hidden")
      console.log("AGENT_ACCESS_COMPONENT_READY")
      Qt.callLater(function() { Qt.quit() })
    }
  }
  Timer { interval: 8000; running: true; onTriggered: Qt.quit() }
}
''')
PY
result=0
timeout 12 quickshell -p "$fixture" --no-color >"$fixture/log" 2>&1 || result=$?
cat "$fixture/log"
(( result == 0 )) || exit "$result"
grep -q AGENT_ACCESS_COMPONENT_READY "$fixture/log"
if grep -Eq 'ReferenceError|TypeError|Unable to assign|Type .* unavailable' "$fixture/log"; then
  exit 1
fi
