#!/bin/bash
# Startet orca_lanes.py im Hintergrund, damit RUN_SHELL_COMMAND sofort
# zurueckkehrt und die G-Code-Warteschlange nicht blockiert (auch im Druck).
# Argumente: <tool>=<spool_id> ... (0 = keine Spule), z.B. 0=11 1=10 2=0
DIR="$(cd "$(dirname "$0")" && pwd)"
LOG=/home/pi/printer_data/logs/orca_lanes.log
setsid nohup python3 "$DIR/orca_lanes.py" "$@" > "$LOG" 2>&1 < /dev/null &
