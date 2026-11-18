#!/bin/bash
# Starts lc_pa_capture.py in the background so RUN_SHELL_COMMAND returns
# immediately. Otherwise gcode_shell_command holds the G-code queue
# and the script's G-code commands would block until the timeout.
DIR="$(cd "$(dirname "$0")" && pwd)"
# printer_data folder, derived from this script's location
# (<printer_data>/config/scripts/<name>/), so any user name works
PD="$(cd "$DIR/../../.." && pwd)"
OUT="$PD/config/lc_pa_data"
mkdir -p "$OUT"
setsid nohup python3 "$DIR/lc_pa_capture.py" "$@" > "$OUT/last_run.log" 2>&1 < /dev/null &
echo "LC_PA: measurement started, messages follow in the console (log: lc_pa_data/last_run.log)"
