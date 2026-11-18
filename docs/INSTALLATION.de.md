# Installation

[English version → INSTALLATION.md](INSTALLATION.md) ·
[README](../README.de.md)

Diese Anleitung beschreibt die **Grundinstallation**: Am Ende startet Klipper
mit der Config aus diesem Repo ohne Fehler, und X/Y lassen sich homen. Die
Kalibrierung folgt in [CALIBRATION.de.md](CALIBRATION.de.md); die Erweiterungen
(Spoolman, OrcaSlicer, KlipperScreen, Düsenkamera, Bootlogo) haben eigene
Anleitungen.

> Das ist die Config einer einzelnen Maschine. Pins, Serial-IDs, Positionen
> und alle Kalibrierwerte müssen am eigenen Drucker geprüft und gemessen
> werden.

## Vor dem Start

**Muss schon funktionieren:**
- Der Drucker ist mechanisch fertig und verkabelt: Voron Trident mit Bondtech
  INDX, Docks, Toolhead-Platine, Mainboard. Dieses Repo nutzt ein BTT Manta
  M8P v2.0 mit CM4; bei einem anderen Board `config/Trident_M8P_v2.0_config.cfg`
  neu schreiben.
- MainsailOS (oder Klipper/Kalico + Moonraker + Mainsail von Hand
  installiert), Netzwerk und SSH-Zugang zum Pi, `git` installiert.
- [Kalico](https://docs.kalico.gg/INDX.html) mit INDX-Modul. Eine
  Mindestversion ist nicht bekannt; die Version nehmen, die Bondtechs
  INDX-Anleitung verlangt.
- Bondtechs INDX-Configs aus [BondtechAB/INDX](https://github.com/BondtechAB/INDX),
  `indx/indx.cfg` an die eigene Maschine angepasst (Anzahl Tools,
  Dock-Richtung, Probe-Position).

**Muss noch nicht erledigt sein:** die Kalibrierung. Läuft der Drucker schon
mit Bondtechs Original-Config und ist kalibriert, bleiben die Werte erhalten:
`indx/indx.cfg` und `indx_vars.cfg` fasst dieses Repo nicht an, und der
`SAVE_CONFIG`-Block wird in Schritt 2 zurückkopiert. Bereits erledigte
Kalibrierschritte kann man dann überspringen.

**Wer liefert was:**

| Kommt von | Inhalt |
|---|---|
| Kalico | Firmware, INDX-Modul (`[indx]`, `INDX_LOAD_FILAMENT`, Thermalmodell, Load-Cell) |
| Bondtech | `indx/indx.cfg`, `indx/indx-tc-macros.cfg` (Toolwechsel, `PARK_TOOL`, `CHANGE_TOOL`), `indx/indx-cal.cfg` (Kalibrier-Makros), `indx/homing.cfg` |
| dieses Repo | Board- und Toolhead-Config, Druck-Makros, `indx/indx_overrides.cfg`, Anbindung von Spoolman/Orca/KlipperScreen, PA-Kalibrierung per Load-Cell |

## Grundinstallation und Erweiterungen

| Teil | Wofür | Anleitung |
|---|---|---|
| **Grundinstallation** | Drucker startet, Toolwechsel funktioniert | diese Anleitung |
| **Kalibrierung** | Drucken | [CALIBRATION.de.md](CALIBRATION.de.md) |
| Spoolman | eine Spule pro Tool, Verbrauch buchen, Spulenliste im Lade-Dialog | [SPOOLMAN.de.md](SPOOLMAN.de.md) |
| OrcaSlicer-Anbindung | Druckerprofil, Filamentprofile und Farben aus Spoolman | [ORCASLICER.de.md](ORCASLICER.de.md) |
| KlipperScreen-Add-on | INDX-Panel, aktives Tool in der Titelleiste | [KLIPPERSCREEN.de.md](KLIPPERSCREEN.de.md) |
| Düsenkamera | XY-Tool-Offsets | [CALIBRATION.de.md, Schritt 6](CALIBRATION.de.md#6-xy-tool-offsets-düsenkamera) |
| Bootlogo (optional) | Logo auf dem Display beim Booten | [bootlogo/README.md](../bootlogo/README.md#deutsch) |

Der Lade-/Entlade-Dialog (`macros/filament_menu.cfg`) gehört zur
Grundinstallation; er funktioniert mit und ohne Spoolman.

## Schritte

### 1. Kalico und INDX

Kalico installieren und INDX-Modul und -Configs nach Bondtechs Anleitung
einrichten, sodass diese Dateien in `~/printer_data/config/indx/` liegen:
`indx.cfg`, `indx-tc-macros.cfg`, `indx-cal.cfg`, `homing.cfg`.

**Erwartetes Ergebnis:** Klipper startet mit Bondtechs Original-Config; die
Mainsail-Konsole zeigt beim Start den INDX-Status.

### 2. Sichern und Dateien kopieren (SSH)

Das Kopieren überschreibt gleichnamige Dateien, auch `printer.cfg`, in der
eventuell schon der eigene `SAVE_CONFIG`-Block steht. Deshalb zuerst den ganzen
Config-Ordner sichern:

```bash
cp -r ~/printer_data/config ~/printer_data/config.bak-$(date +%F)
```
```bash
cd ~ && git clone https://github.com/daum1988/indx-trident-350
```
```bash
cp -r ~/indx-trident-350/klipper/. ~/printer_data/config/
```

Das kopiert den *Inhalt* von `klipper/` (nicht den Ordner selbst). Die Makros
erwarten die Skripte in `~/printer_data/config/scripts/`.

Hatte die alte `printer.cfg` einen `SAVE_CONFIG`-Block (die Zeilen mit `#*#`
am Ende; dort speichert Klipper Kalibrierergebnisse), ihn aus der Sicherung
ans Ende der neuen `printer.cfg` kopieren.

**Erwartetes Ergebnis:** `ls ~/printer_data/config` zeigt `printer.cfg`,
`config/`, `macros/`, `scripts/` und `indx/` (Bondtechs Dateien plus
`indx_overrides.cfg`).

### 3. Includes

`printer.cfg` bindet die übrigen Dateien mit `[include ...]`-Zeilen ein. Die
Reihenfolge ist wichtig:

```ini
[include mainsail.cfg]
[include config/*.cfg]
[include macros/*.cfg]
[include timelapse.cfg]            # nur mit moonraker-timelapse
[include indx/indx.cfg]
[include indx/indx-tc-macros.cfg]
[include indx/indx-cal.cfg]
[include indx/homing.cfg]
[include indx/indx_overrides.cfg]  # muss nach indx/homing.cfg stehen
```

`mainsail.cfg` bringt MainsailOS mit, `timelapse.cfg`
[moonraker-timelapse](https://github.com/mainsail-crew/moonraker-timelapse).
Die Zeile von allem, was man nicht nutzt, auskommentieren.

### 4. Weitere Module

- `config/autotune_tmc.cfg` braucht
  [klipper_tmc_autotune](https://github.com/andrewmcgr/klipper_tmc_autotune),
- `macros/shaketune.cfg` braucht [Shake&Tune](https://github.com/Frix-x/klippain-shaketune).

Installieren oder die Dateien löschen, sonst startet Klipper nicht.

### 5. Mit oder ohne Spoolman

`macros/spoolman.cfg` schaltet bei jedem Toolwechsel die aktive
Spoolman-Spule um. Das braucht einen funktionierenden Abschnitt `[spoolman]`
in `moonraker.conf`; ohne ihn bricht Kalico den Toolwechsel mit einem Fehler ab
(*Remote method ... not registered*), im Druck damit auch den Druck.

- **Mit Spoolman:** wie in [SPOOLMAN.de.md](SPOOLMAN.de.md) einrichten (geht
  auch nach dieser Anleitung; bis dahin keinen Toolwechsel ausführen).
- **Ohne Spoolman:** `macros/spoolman.cfg` löschen und in
  `macros/filament_menu.cfg` `variable_use_spoolman: 0` setzen. Der
  Lade-Dialog bietet dann Material-Presets statt Spulen an.

### 6. Benutzername

Drei Abschnitte `[gcode_shell_command]` (`macros/lc_pa_cal.cfg`,
`macros/spoolman.cfg`, `macros/filament_menu.cfg`) rufen Skripte über
`/home/pi/printer_data/...` auf. Den eigenen Benutzernamen zeigt `whoami`.
Ist er nicht `pi`, die Pfade ersetzen:

```bash
cd ~/printer_data/config/macros && sed -i "s#/home/pi/#$HOME/#g" lc_pa_cal.cfg filament_menu.cfg spoolman.cfg
```

(Ohne Spoolman meldet `sed` die fehlende `spoolman.cfg`; das ist in Ordnung.)
Sonst schlagen PA-Kalibrierung, Orca-Lanes und Spulen-Dialog ohne Meldung
fehl. Die Skripte selbst finden `printer_data` von allein.

**Erwartetes Ergebnis:** `grep -rn "/home/" ~/printer_data/config/macros/`
zeigt nur noch den eigenen Home-Ordner.

### 7. Hardware

- Serial-IDs: `ls /dev/serial/by-id/` und die `serial:`-Zeilen in `config/`
  ersetzen. Bei CAN die `canbus_uuid` ersetzen.
- Alle Pins mit der eigenen Verkabelung abgleichen (Motoren, Heizungen,
  Thermistoren, Lüfter, Endschalter).

### 8. Moonraker

`moonraker/moonraker.example.conf` in die eigene `moonraker.conf` übernehmen,
aber nur die Abschnitte für Installiertes: `[spoolman]` nur mit Spoolman
(Schritt 5), `[timelapse]` nur mit moonraker-timelapse, jeden
`[update_manager ...]` nur, wenn das Modul installiert ist. Danach:

```bash
sudo systemctl restart moonraker
```

**Erwartetes Ergebnis:** Mainsail zeigt keine Moonraker-Warnungen
(Glocke / Benachrichtigungen); mit Spoolman erscheint das Spoolman-Panel im
Dashboard.

### 9. Erster Start

`FIRMWARE_RESTART` in der Mainsail-Konsole.

**Erwartetes Ergebnis:**
- Klipper ist *ready*, kein Config-Fehler. Ein Fehler nennt Datei und
  Abschnitt; siehe [TROUBLESHOOTING.de.md](TROUBLESHOOTING.de.md).
- `LC_PA_SHOW` antwortet (Makros aus diesem Repo sind geladen).
- `CAL_CHECK_OFFSETS` antwortet (Bondtechs Kalibrier-Makros sind geladen).
- `G28 X Y` homt X und Y.

**Z noch nicht homen.** Z wird mit der Load-Cell gemessen (die Düse ist der
Taster), und die muss zuerst kalibriert werden:
[CALIBRATION.de.md](CALIBRATION.de.md), Schritt 1.

## Spätere Updates

```bash
cd ~/indx-trident-350 && git pull
```

Danach **nicht** einfach wie in Schritt 2 alles erneut kopieren. Das
überschreibt die Anpassungen aus der Einrichtung:
- `printer.cfg` verliert ihren `SAVE_CONFIG`-Block,
- ohne Spoolman (Schritt 5) ist `macros/spoolman.cfg` wieder da und
  `variable_use_spoolman` wieder `1`, dann bricht jeder Toolwechsel ab,
- die `/home/pi`-Pfade (Schritt 6) stehen wieder auf `pi`,
- Serial-IDs, CAN-UUID und Pins in `config/` (Schritt 7) sind wieder die vom
  Original.

Vorher vergleichen und nur übernehmen, was man will. Dieser Befehl listet nur
geänderte oder neue Repo-Dateien (Dateien, die nur im eigenen Config-Ordner
liegen, etwa `moonraker.conf` oder Bondtechs `indx/`-Dateien, werden
ausgefiltert):

```bash
diff -rq ~/indx-trident-350/klipper/ ~/printer_data/config/ | grep -v "^Only in $HOME/printer_data"
```

Danach einzelne Dateien mit `diff` ansehen, z. B.
`diff ~/indx-trident-350/klipper/macros/filament_menu.cfg ~/printer_data/config/macros/filament_menu.cfg`.

Wer doch alles kopiert: vorher sichern, danach den `SAVE_CONFIG`-Block aus
der Sicherung zurückholen und die Schritte 5–7 wiederholen. Das
KlipperScreen-Add-on und die Düsenkamera-Seite sind ebenfalls Kopien: bei
Änderungen wie in ihren Anleitungen neu kopieren.
