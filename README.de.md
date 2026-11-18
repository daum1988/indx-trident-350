# INDX Trident 350

Kalico/Klipper-Konfiguration, Makros und Werkzeuge für einen **Voron Trident 350**
mit **Bondtech INDX**-Werkzeugwechsler (9 Tools, T0–T8).

[English version → README.md](README.md)

CAD-Daten des Druckers (INDX-Umbau des Trident):
[daum1988/Voron-Trident-INDX](https://github.com/daum1988/Voron-Trident-INDX)

> Das ist die Config einer einzelnen Maschine, geteilt als Vorlage. Sie ist
> **nicht** direkt übernehmbar: Pins, Serial-IDs, Positionen und alle
> Kalibrierwerte müssen am eigenen Drucker geprüft und gemessen werden.
> Nutzung auf eigene Gefahr.

## Hardware / Software

| | |
|---|---|
| Drucker | Voron Trident 350 |
| Werkzeugwechsler | Bondtech INDX, 9 Tools, Docks vorne |
| Mainboard | BTT Manta M8P v2.0 + Raspberry Pi CM4 |
| Z-Messung | INDX-Load-Cell (Standard-Probe) |
| Bed Mesh | Eddy-Current-Scanner (`[probe_eddy_current scanner]`, Rapid Scan) |
| Firmware | [Kalico](https://docs.kalico.gg/INDX.html) |
| Oberfläche | Mainsail, KlipperScreen |
| Slicer | OrcaSlicer 2.5.x |
| Filamentverwaltung | Spoolman (eine Spule pro Tool) |

## Inhalt

```
klipper/                      Inhalt kommt nach ~/printer_data/config/
  printer.cfg                 Includes, ohne SAVE_CONFIG-Block
  config/                     M8P-Board, INDX-Toolhead, Bed Mesh, TMC-Autotune
  indx/indx_overrides.cfg     Anpassungen über den originalen Bondtech-INDX-Makros
  macros/                     START_PRINT/END_PRINT, Spoolman, PA-Kalibrierung per Load-Cell, ...
  scripts/lc_pa/              Host-Skript für die PA-Kalibrierung
  scripts/orca_lanes/         schreibt die Tool->Spulen-Zuordnung für OrcaSlicer in Moonraker
  scripts/spool_picker/       Spulenliste aus Spoolman für den Lade-Dialog
moonraker/moonraker.example.conf   die benötigten Abschnitte für moonraker.conf
orca/                         OrcaSlicer-Druckerprofil + Skript Spoolman -> Orca-Filamentprofile
bootlogo/                     Plymouth-Bootlogo für das CM4-Display
klipperscreen/                KlipperScreen-Add-on: INDX-Panel und aktives Tool in der Titelleiste
tools/nozzle_cam.html         Browserseite zum Prüfen der XY-Tool-Offsets mit Düsenkamera
docs/SPOOLMAN.de.md           Anleitung Spoolman-Einrichtung (englisch: SPOOLMAN.md)
```

**Nicht enthalten:**
- die originalen Bondtech-INDX-Dateien `indx/indx.cfg`, `indx/indx-tc-macros.cfg`,
  `indx/indx-cal.cfg`, `indx/homing.cfg` – die kommen aus
  [BondtechAB/INDX](https://github.com/BondtechAB/INDX); `indx.cfg` an die
  eigene Maschine anpassen. `printer.cfg` bindet sie ein; fehlen sie, startet
  Klipper nicht. Mehrere hier verwendete Befehle stammen aus diesen Dateien,
  z. B. `PARK_TOOL`, `CHANGE_TOOL` und das Start-Makro `INIT_STATE`
  (`indx-tc-macros.cfg`), `TOOL_POSITIONS` (`indx.cfg`), `SYNC_GLOBAL_Z` und
  `CAL_CHECK_OFFSETS` (`indx-cal.cfg`);
- `mainsail.cfg` (aus [mainsail-config](https://github.com/mainsail-crew/mainsail-config),
  bei MainsailOS schon vorhanden) und `timelapse.cfg` (kommt mit
  [moonraker-timelapse](https://github.com/mainsail-crew/moonraker-timelapse)).
  `printer.cfg` bindet beide ein; wer sie nicht nutzt, kommentiert die Zeilen aus;
- `indx_vars.cfg` (maschinenspezifische Tool-Offsets, legt INDX selbst an) und
  alles mit Netzwerkadressen oder API-Keys.

## Besonderheiten

### Pressure Advance mit der INDX-Load-Cell
`PA_CAL_LOADCELL` misst Pressure Advance pro Tool ohne Testdruck. Das Tool
extrudiert in Geschwindigkeitsstufen in den Bucket, die Load-Cell misst dabei
den Düsendruck. Aus den Kraftsprüngen wird die Druck-Zeitkonstante gefittet –
das ist der PA-Wert.

```
PA_CAL_LOADCELL TOOL=0 TEMP=230
PA_CAL_LOADCELL TOOLS=0,3,5 TEMP=230
PA_CAL_LOADCELL TOOLS=ALL TEMP=230
SET_TOOL_NOZZLE TOOL=3 D=0.6     # einmal pro Tool, nach jedem Düsenwechsel
LC_PA_SHOW / LC_PA_APPLY
```

Die Werte werden pro Tool in `save_variables` gespeichert und, wenn dem Tool
eine Spule zugeordnet ist, auch im Spoolman-Filament (Zusatzfelder
`pressure_advance_d025/_d04/_d06`, je Düsengröße). Benötigt
`gcode_shell_command` (in Kalico enthalten) und `scripts/lc_pa/` im
Config-Ordner. Mit `LC_EXTRUDE_TEST` lässt sich vorher prüfen, ob die Load-Cell
den Extrusionsdruck überhaupt sieht.

### KlipperScreen: INDX-Panel, Toolauswahl und Laden/Entladen
KlipperScreen sieht nur einen `[extruder]` und zeigt daher keine T0–T8-Knöpfe;
seine Laden/Entladen-Knöpfe senden ein nacktes `LOAD_FILAMENT` /
`UNLOAD_FILAMENT`. Dieses Repo ergänzt:

- **Lade-/Entlade-Dialog** (`macros/filament_menu.cfg`, Macro-Prompt, erscheint
  auch in Mainsail): `LOAD_FILAMENT` ohne Parameter fragt nach Tool, Material
  und Spule aus Spoolman (`scripts/spool_picker/`, scrollbare Liste nach
  Hersteller und Name). Die Spule wird dem Tool zugeordnet und ihre
  Düsentemperatur verwendet; *Without spool* zeigt stattdessen die
  Material-Presets. `UNLOAD_FILAMENT` ohne Parameter fragt nach dem Tool.
- **KlipperScreen-Add-on** `klipperscreen/indx_addon.py`: ein *INDX*-Panel mit
  allen Tools (Spulenfarbe und -name, geladen/leer, aktives Tool hervorgehoben;
  Parken, Laden, Entladen) und das aktive Tool mit Spulenfarbe in der
  Titelleiste. `LOAD_FILAMENT` / `UNLOAD_FILAMENT` führen den Ladezustand
  (`t<n>__loaded`) mit; `SET_TOOL_LOADED T=<n> LOADED=<0|1>` korrigiert ihn.

Add-on installieren (braucht eine KlipperScreen-Version mit Add-on-Unterstützung,
Einstellung `enable_addons`):

1. `klipperscreen/indx_addon.py` nach `~/printer_data/config/klipperscreen/` kopieren.
2. Per SSH in den Add-on-Ordner von KlipperScreen verlinken (wird von
   KlipperScreens Git ignoriert, Updates funktionieren also weiter):
   ```bash
   mkdir -p ~/KlipperScreen/addons && ln -sf ~/printer_data/config/klipperscreen/indx_addon.py ~/KlipperScreen/addons/indx.py
   ```
3. `klipperscreen/KlipperScreen.example.conf` in die eigene `KlipperScreen.conf`
   übernehmen (`enable_addons: True`, INDX-Menüeintrag, `spool` in der Titelleiste).
4. KlipperScreen neu starten.

### Spoolman, eine Spule pro Tool
`SET_TOOL_SPOOL T=3 ID=12` ordnet einem Tool eine Spule zu (dieselben Variablen
wie der Spoolman-Dialog in Mainsail). Bei jedem Toolwechsel wechselt die aktive
Spule in Moonraker mit, der Verbrauch landet also auf der richtigen Spule.
`orca_lanes.py` stellt die Zuordnung Tool → Filament als Moonraker-`lane_data`
bereit, damit OrcaSlicer (Printer Agent *Moonraker*) Farben und Profile
abgleichen kann. `orca/orca_spoolman_profiles.ps1` erzeugt unter Windows die
passenden Orca-Filamentprofile aus Spoolman. Ausführliche Anleitung:
[docs/SPOOLMAN.de.md](docs/SPOOLMAN.de.md).

### INDX-Overrides
`indx/indx_overrides.cfg` muss **nach** `indx/homing.cfg` eingebunden werden.
Enthält einen sicheren Z-Hop, wenn das Bett ganz unten steht, das Speichern der
gemessenen Filamentwerte aus `INDX_LOAD_FILAMENT` pro Tool, eine XY-Prüfung mit
Düsenkamera (`CAL_VERIFY_XY`) und den Spoolman-Hook beim Toolwechsel – ohne die
Bondtech-Dateien zu ändern.

### OrcaSlicer-Druckerprofil
`orca/Voron Trident 350 INDX.json` hat Maschinenlimits passend zur
Klipper-Config (300 mm/s, 3000 mm/s², Square Corner Velocity 5), damit die
Zeitschätzung stimmt. Düsen: T0–T4 0.4, T5–T6 0.6, T7–T8 0.25 – an die eigenen
anpassen. Toolwechselzeit und Startzeit im Profil sind Schätzwerte; an der
eigenen Maschine stoppen.

## Einrichtung

1. **Kalico und INDX:** Kalico und das Bondtech-INDX-Modul samt Configs nach
   Bondtech-Anleitung installieren, sodass `indx/indx.cfg`,
   `indx/indx-tc-macros.cfg`, `indx/indx-cal.cfg` und `indx/homing.cfg` im
   Config-Ordner liegen.
2. **Dateien kopieren:** den *Inhalt* von `klipper/` (nicht den Ordner selbst)
   nach `~/printer_data/config/` kopieren, sodass dort
   `~/printer_data/config/printer.cfg`, `.../config/`, `.../macros/`,
   `.../scripts/` usw. liegen. Die Makros erwarten die Skripte unter
   `~/printer_data/config/scripts/`.
3. **Includes:** `printer.cfg` prüfen. Die Reihenfolge ist wichtig:
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
4. **Weitere Module:** `config/autotune_tmc.cfg` braucht
   [klipper_tmc_autotune](https://github.com/andrewmcgr/klipper_tmc_autotune),
   `macros/shaketune.cfg` braucht [Shake&Tune](https://github.com/Frix-x/klippain-shaketune).
   Installieren oder die Dateien löschen, sonst startet Klipper nicht.
5. **Benutzername:** Die drei Abschnitte `[gcode_shell_command]`
   (`macros/lc_pa_cal.cfg`, `macros/spoolman.cfg`, `macros/filament_menu.cfg`)
   rufen die Skripte über `/home/pi/printer_data/...` auf. Heißt der
   Linux-Benutzer nicht `pi`, diese drei Pfade anpassen, sonst schlagen
   PA-Kalibrierung, Orca-Lanes und Spulen-Dialog ohne Meldung fehl. Die
   Skripte selbst finden `printer_data` von allein.
6. **Hardware:** Serial-IDs (`ls /dev/serial/by-id/`) und, falls genutzt, die
   CAN-UUID ersetzen und alle Pins mit der eigenen Verkabelung abgleichen.
7. **Moonraker:** `moonraker/moonraker.example.conf` in die eigene
   `moonraker.conf` übernehmen (Spoolman-Adresse, Timelapse, Update-Manager).
8. **Kalibrieren:** alle Kalibrierungen selbst durchführen und `SAVE_CONFIG`:
   Bett-PID, Input Shaper, INDX-Thermalmodell, Load-Cell, Eddy-Scanner,
   Tool-Offsets.
9. **Optional:** Spoolman und OrcaSlicer: [docs/SPOOLMAN.de.md](docs/SPOOLMAN.de.md);
   KlipperScreen-Add-on: siehe oben; Bootlogo: [bootlogo/README.md](bootlogo/README.md).

## Erfahrungen / Stolperfallen

- **Globaler Z-Offset nach Neustart oder Druckstart weg?** Babystepping ändert
  nur den Live-Offset. `START_PRINT` homt Z und setzt dabei den *gespeicherten*
  globalen Offset. Nach dem Babystepping `SYNC_GLOBAL_Z` ausführen, mit
  `CAL_CHECK_OFFSETS` prüfen (beide aus Bondtechs `indx-cal.cfg`). Nach einem Neustart steht live 0, bis `G28` oder
  T0 aufgenommen wird – das ist normal.
- **Verschiedene Druckplatten (glatt/strukturiert)** brauchen keinen eigenen
  Z-Offset: Z wird mit der Load-Cell direkt auf der Plattenoberfläche gemessen.
- **Ruck-Warnung in OrcaSlicer:** Bei Klipper behandelt Orca
  `machine_max_jerk_x/y` als `square_corner_velocity`. Im Prozessprofil
  *Standard-Ruck* auf 0 setzen, dann sendet Orca keine Ruck-Befehle und es gilt
  der Wert aus Klipper.
- **Pressure Advance:** in Orca den normalen PA-Wert pro Filament setzen, kein
  *adaptives PA* (schickt sehr viele `SET_PRESSURE_ADVANCE`).
- **Bauteillüfter tauschen (4010-Blower ↔ CPAP):** Die Werte
  `model_part_cooling_fan_a/k` des INDX-Thermalmodells hängen vom Lüfter und
  seinem `max_power` ab. Nach einem Lüftertausch neu messen; alte Werte passen
  oft nicht mehr.
- **Lüfterleistung:** `min_power` statt des veralteten `off_below` verwenden.
- **Bootlogo um 90° gedreht:** das PNG drehen, nicht das Plymouth-Bild.

## Danksagung

- [Bondtech INDX](https://github.com/BondtechAB/INDX) – Werkzeugwechsler und Original-Makros
- [Kalico](https://github.com/KalicoCrew/kalico), [Klipper](https://github.com/Klipper3d/klipper)
- [Spoolman](https://github.com/Donkie/Spoolman), [OrcaSlicer](https://github.com/SoftFever/OrcaSlicer)
- [klipper_tmc_autotune](https://github.com/andrewmcgr/klipper_tmc_autotune),
  [Shake&Tune](https://github.com/Frix-x/klippain-shaketune)
- Ideen für Adaptive Purge / Druckstart: Links in `macros/trident_macros.cfg`

## Lizenz

[GPL-3.0](LICENSE), wie Klipper und Kalico. Teile, die auf Makros Dritter
beruhen, unterliegen weiterhin deren Bedingungen.
