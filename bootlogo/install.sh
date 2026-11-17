#!/bin/bash
# Boot-Logo fuer Raspberry Pi CM4 (Raspberry Pi OS / MainsailOS)
# Aufruf:  bash ~/printer_data/config/bootlogo/install.sh
# Im selben Ordner muessen liegen: logo.png, voron.plymouth, voron.script
set -e
DIR="$(cd "$(dirname "$0")" && pwd)"
THEME=/usr/share/plymouth/themes/voron

for f in logo.png voron.plymouth voron.script; do
    [ -f "$DIR/$f" ] || { echo "FEHLT: $DIR/$f"; exit 1; }
done

if [ -f /boot/firmware/cmdline.txt ]; then BOOT=/boot/firmware; else BOOT=/boot; fi
echo "Boot-Partition: $BOOT"

# Sicherungen (nur beim ersten Lauf)
[ -f "$BOOT/cmdline.txt.vor_bootlogo" ] || sudo cp "$BOOT/cmdline.txt" "$BOOT/cmdline.txt.vor_bootlogo"
[ -f "$BOOT/config.txt.vor_bootlogo" ]  || sudo cp "$BOOT/config.txt"  "$BOOT/config.txt.vor_bootlogo"

echo "Plymouth installieren ..."
sudo apt-get update -qq
sudo apt-get install -y plymouth plymouth-themes

echo "Theme kopieren ..."
sudo mkdir -p "$THEME"
sudo cp "$DIR/logo.png" "$DIR/voron.plymouth" "$DIR/voron.script" "$THEME/"
sudo sed -i 's/\r$//' "$THEME/voron.plymouth" "$THEME/voron.script"

echo "cmdline.txt anpassen ..."
# alles bleibt in EINER Zeile; Textausgabe von tty1 (Display) auf tty3 verschieben
CMD="$(head -n1 "$BOOT/cmdline.txt" | tr -d '\r')"
CMD="$(echo "$CMD" | sed 's/console=tty1/console=tty3/')"
for p in quiet splash loglevel=3 logo.nologo vt.global_cursor_default=0 plymouth.ignore-serial-consoles; do
    echo " $CMD " | grep -q " ${p%%=*}[= ]" || CMD="$CMD $p"
done
echo "$CMD" | sudo tee "$BOOT/cmdline.txt" > /dev/null
echo "  -> $CMD"

echo "config.txt anpassen ..."
grep -q '^disable_splash=1' "$BOOT/config.txt" || echo 'disable_splash=1' | sudo tee -a "$BOOT/config.txt" > /dev/null

echo "Theme aktivieren ..."
sudo plymouth-set-default-theme -R voron

echo
echo "Fertig. Mit 'sudo reboot' neu starten."
echo "Rueckgaengig: sudo cp $BOOT/cmdline.txt.vor_bootlogo $BOOT/cmdline.txt"
echo "              sudo cp $BOOT/config.txt.vor_bootlogo $BOOT/config.txt"
