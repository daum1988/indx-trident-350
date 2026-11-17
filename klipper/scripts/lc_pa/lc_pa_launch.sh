#!/bin/bash
# Startet lc_pa_capture.py im Hintergrund, damit RUN_SHELL_COMMAND sofort
# zurueckkehrt. Sonst haelt gcode_shell_command die G-Code-Warteschlange fest
# und die G-Code-Befehle des Skripts wuerden bis zum Timeout blockieren.
DIR="$(cd "$(dirname "$0")" && pwd)"
OUT=/home/pi/printer_data/config/lc_pa_data
mkdir -p "$OUT"
setsid nohup python3 "$DIR/lc_pa_capture.py" "$@" > "$OUT/last_run.log" 2>&1 < /dev/null &
echo "LC_PA: Messung gestartet, Meldungen folgen in der Konsole (Log: lc_pa_data/last_run.log)"
