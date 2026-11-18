#!/bin/bash
# Starts orca_lanes.py in the background so RUN_SHELL_COMMAND returns
# immediately and does not block the G-code queue (also while printing).
# Arguments: <tool>=<spool_id> ... (0 = no spool), e.g. 0=11 1=10 2=0
DIR="$(cd "$(dirname "$0")" && pwd)"
# printer_data folder, derived from this script's location
# (<printer_data>/config/scripts/<name>/), so any user name works
PD="$(cd "$DIR/../../.." && pwd)"
LOG="$PD/logs/orca_lanes.log"
setsid nohup python3 "$DIR/orca_lanes.py" "$@" > "$LOG" 2>&1 < /dev/null &
