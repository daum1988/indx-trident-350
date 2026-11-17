#!/bin/bash
# Starts orca_lanes.py in the background so RUN_SHELL_COMMAND returns
# immediately and does not block the G-code queue (also while printing).
# Arguments: <tool>=<spool_id> ... (0 = no spool), e.g. 0=11 1=10 2=0
DIR="$(cd "$(dirname "$0")" && pwd)"
LOG=/home/pi/printer_data/logs/orca_lanes.log
setsid nohup python3 "$DIR/orca_lanes.py" "$@" > "$LOG" 2>&1 < /dev/null &
