# Boot logo (Plymouth) for Raspberry Pi CM4 / MainsailOS

[Deutsch ↓](#deutsch)

Shows a centred logo on the attached display instead of the Linux boot text.

## The logo

No logo is shipped; use an image you have the rights to. `install.sh` stops
with `MISSING: .../logo.png` if there is none.

- Format: **PNG**, named `logo.png`, in this folder. Transparency is fine,
  the background is black.
- Size: ideally about half the display height and roughly square, e.g.
  300–500 px for an 800×480 or 1024×600 display. Larger images are scaled
  down to 80 % of the screen.
- The image is shown exactly as it is: if your display is mounted rotated,
  rotate the PNG (see below).

## Check first

The script expects the Raspberry Pi boot files `cmdline.txt` and
`config.txt` in `/boot/firmware/` (current Raspberry Pi OS / MainsailOS) or
`/boot/` (older versions):

```bash
ls -l /boot/firmware/cmdline.txt /boot/firmware/config.txt /boot/cmdline.txt /boot/config.txt 2>/dev/null
```

Expected: both files in one of the two folders. Then check that
`cmdline.txt` is a single line (the Pi only reads the first line; the script
keeps only that one):

```bash
F=/boot/firmware/cmdline.txt; [ -f $F ] || F=/boot/cmdline.txt; wc -l < $F; cat $F
```

`wc -l` prints `0` or `1`. If neither folder has the files (e.g. not a
Raspberry Pi, or a different OS), do not run the script.

## Install

1. Put `logo.png` into this folder.
2. Copy the folder to the Pi, e.g. `~/printer_data/config/bootlogo/`.
3. Via SSH: `bash ~/printer_data/config/bootlogo/install.sh`.
4. **Before rebooting**, check that the script saved the original boot files
   (the undo below needs them):
   ```bash
   ls -l /boot/firmware/*.vor_bootlogo /boot/*.vor_bootlogo 2>/dev/null
   ```
   Both `cmdline.txt.vor_bootlogo` and `config.txt.vor_bootlogo` must be
   listed. Then `sudo reboot`.

## What the script changes

- installs `plymouth` and `plymouth-themes` (apt),
- copies the theme to `/usr/share/plymouth/themes/voron/` and makes it the
  default theme,
- **`cmdline.txt`** (in `/boot/firmware/` or `/boot/`): moves the console from
  `tty1` (display) to `tty3` and adds `quiet splash loglevel=3 logo.nologo
  vt.global_cursor_default=0 plymouth.ignore-serial-consoles`,
- **`config.txt`**: adds `disable_splash=1` (no rainbow screen).

Before the first change it saves `cmdline.txt.vor_bootlogo` and
`config.txt.vor_bootlogo` next to the originals (only once, so running the
script again keeps the original backup). Running it again is safe.

**Undo** (restores the boot files; Plymouth stays installed but no longer
shows anything):

```bash
BOOT=/boot/firmware; [ -f $BOOT/cmdline.txt ] || BOOT=/boot
ls -l $BOOT/cmdline.txt.vor_bootlogo $BOOT/config.txt.vor_bootlogo
```

Only if both files are listed:

```bash
sudo cp $BOOT/cmdline.txt.vor_bootlogo $BOOT/cmdline.txt
sudo cp $BOOT/config.txt.vor_bootlogo $BOOT/config.txt
sudo reboot
```

A broken `cmdline.txt` can keep the Pi from booting. If that happens, mount the
boot partition on another computer (SD card in a card reader, CM4 eMMC via
`rpiboot`) and copy the `.vor_bootlogo` files back.

## Logo appears rotated?

The framebuffer is not rotated during boot (display rotation from
KlipperScreen/X applies later). Plymouth's own rotate function clips
non-square images, so rotate the PNG itself in the opposite direction and run
`install.sh` again.

---

## Deutsch

Zeigt beim Booten ein zentriertes Logo auf dem angeschlossenen Display statt
des Linux-Starttextes.

### Das Logo

Es wird kein Logo mitgeliefert; ein Bild verwenden, an dem man die Rechte hat.
Fehlt es, bricht `install.sh` mit `MISSING: .../logo.png` ab.

- Format: **PNG**, Name `logo.png`, in diesem Ordner. Transparenz ist möglich,
  der Hintergrund ist schwarz.
- Größe: am besten etwa halbe Displayhöhe und ungefähr quadratisch, z. B.
  300–500 px bei einem Display mit 800×480 oder 1024×600. Größere Bilder werden
  auf 80 % des Bildschirms verkleinert.
- Das Bild wird genau so angezeigt, wie es ist: Ist das Display gedreht
  eingebaut, das PNG drehen (siehe unten).

### Vorher prüfen

Das Skript erwartet die Raspberry-Pi-Bootdateien `cmdline.txt` und
`config.txt` in `/boot/firmware/` (aktuelles Raspberry Pi OS / MainsailOS)
oder `/boot/` (ältere Versionen):

```bash
ls -l /boot/firmware/cmdline.txt /boot/firmware/config.txt /boot/cmdline.txt /boot/config.txt 2>/dev/null
```

Erwartet: beide Dateien in einem der beiden Ordner. Dann prüfen, ob
`cmdline.txt` aus einer einzigen Zeile besteht (der Pi liest nur die erste
Zeile; das Skript behält nur diese):

```bash
F=/boot/firmware/cmdline.txt; [ -f $F ] || F=/boot/cmdline.txt; wc -l < $F; cat $F
```

`wc -l` gibt `0` oder `1` aus. Liegen die Dateien in keinem der Ordner (z. B.
kein Raspberry Pi oder ein anderes System), das Skript nicht ausführen.

### Installation

1. `logo.png` in diesen Ordner legen.
2. Den Ordner auf den Pi kopieren, z. B. nach `~/printer_data/config/bootlogo/`.
3. Per SSH: `bash ~/printer_data/config/bootlogo/install.sh`.
4. **Vor dem Neustart** prüfen, ob das Skript die originalen Bootdateien
   gesichert hat (das Rückgängigmachen unten braucht sie):
   ```bash
   ls -l /boot/firmware/*.vor_bootlogo /boot/*.vor_bootlogo 2>/dev/null
   ```
   Es müssen `cmdline.txt.vor_bootlogo` und `config.txt.vor_bootlogo`
   erscheinen. Dann `sudo reboot`.

### Was das Skript ändert

- installiert `plymouth` und `plymouth-themes` (apt),
- kopiert das Theme nach `/usr/share/plymouth/themes/voron/` und macht es zum
  Standard-Theme,
- **`cmdline.txt`** (in `/boot/firmware/` oder `/boot/`): verlegt die Konsole
  von `tty1` (Display) auf `tty3` und ergänzt `quiet splash loglevel=3
  logo.nologo vt.global_cursor_default=0 plymouth.ignore-serial-consoles`,
- **`config.txt`**: ergänzt `disable_splash=1` (kein Regenbogenbild).

Vor der ersten Änderung legt es `cmdline.txt.vor_bootlogo` und
`config.txt.vor_bootlogo` neben den Originalen ab (nur einmal; bei weiteren
Läufen bleibt die erste Sicherung erhalten). Mehrfaches Ausführen ist
unbedenklich.

**Rückgängig machen** (stellt die Boot-Dateien wieder her; Plymouth bleibt
installiert, zeigt aber nichts mehr an):

```bash
BOOT=/boot/firmware; [ -f $BOOT/cmdline.txt ] || BOOT=/boot
ls -l $BOOT/cmdline.txt.vor_bootlogo $BOOT/config.txt.vor_bootlogo
```

Nur wenn beide Dateien aufgelistet werden:

```bash
sudo cp $BOOT/cmdline.txt.vor_bootlogo $BOOT/cmdline.txt
sudo cp $BOOT/config.txt.vor_bootlogo $BOOT/config.txt
sudo reboot
```

Eine kaputte `cmdline.txt` kann den Start des Pi verhindern. Dann die Boot-Partition
an einem anderen Rechner einbinden (SD-Karte im Kartenleser, CM4-eMMC über
`rpiboot`) und die `.vor_bootlogo`-Dateien zurückkopieren.

### Logo um 90° gedreht?

Beim Booten ist der Framebuffer nicht gedreht (die Displaydrehung von
KlipperScreen/X greift erst später). Die Drehfunktion von Plymouth schneidet
nicht-quadratische Bilder ab. Deshalb das PNG selbst in die Gegenrichtung
drehen und `install.sh` erneut ausführen.
