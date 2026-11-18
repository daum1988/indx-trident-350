#!/bin/bash
# Starts spool_picker.py in the background. It sends the dialog back to
# Klipper through Moonraker, which would deadlock if RUN_SHELL_COMMAND
# waited for it (the G-code queue is busy until the shell command returns).
DIR="$(cd "$(dirname "$0")" && pwd)"
LOG=/home/pi/printer_data/logs/spool_picker.log
setsid nohup python3 "$DIR/spool_picker.py" "$@" > "$LOG" 2>&1 < /dev/null &
