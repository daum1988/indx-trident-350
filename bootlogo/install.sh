#!/bin/bash
# Boot logo for Raspberry Pi CM4 (Raspberry Pi OS / MainsailOS)
# Usage:  bash ~/printer_data/config/bootlogo/install.sh
# The same folder must contain: logo.png, voron.plymouth, voron.script
set -e
DIR="$(cd "$(dirname "$0")" && pwd)"
THEME=/usr/share/plymouth/themes/voron

for f in logo.png voron.plymouth voron.script; do
    [ -f "$DIR/$f" ] || { echo "MISSING: $DIR/$f"; exit 1; }
done

if [ -f /boot/firmware/cmdline.txt ]; then BOOT=/boot/firmware; else BOOT=/boot; fi
echo "Boot partition: $BOOT"

# Backups (first run only)
[ -f "$BOOT/cmdline.txt.vor_bootlogo" ] || sudo cp "$BOOT/cmdline.txt" "$BOOT/cmdline.txt.vor_bootlogo"
[ -f "$BOOT/config.txt.vor_bootlogo" ]  || sudo cp "$BOOT/config.txt"  "$BOOT/config.txt.vor_bootlogo"

echo "Installing Plymouth ..."
sudo apt-get update -qq
sudo apt-get install -y plymouth plymouth-themes

echo "Copying theme ..."
sudo mkdir -p "$THEME"
sudo cp "$DIR/logo.png" "$DIR/voron.plymouth" "$DIR/voron.script" "$THEME/"
sudo sed -i 's/\r$//' "$THEME/voron.plymouth" "$THEME/voron.script"

echo "Updating cmdline.txt ..."
# everything stays on ONE line; move text output from tty1 (display) to tty3
CMD="$(head -n1 "$BOOT/cmdline.txt" | tr -d '\r')"
CMD="$(echo "$CMD" | sed 's/console=tty1/console=tty3/')"
for p in quiet splash loglevel=3 logo.nologo vt.global_cursor_default=0 plymouth.ignore-serial-consoles; do
    echo " $CMD " | grep -q " ${p%%=*}[= ]" || CMD="$CMD $p"
done
echo "$CMD" | sudo tee "$BOOT/cmdline.txt" > /dev/null
echo "  -> $CMD"

echo "Updating config.txt ..."
grep -q '^disable_splash=1' "$BOOT/config.txt" || echo 'disable_splash=1' | sudo tee -a "$BOOT/config.txt" > /dev/null

echo "Activating theme ..."
sudo plymouth-set-default-theme -R voron

echo
echo "Done. Reboot with 'sudo reboot'."
echo "Undo:         sudo cp $BOOT/cmdline.txt.vor_bootlogo $BOOT/cmdline.txt"
echo "              sudo cp $BOOT/config.txt.vor_bootlogo $BOOT/config.txt"
