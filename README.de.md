# INDX Trident 350

Kalico/Klipper-Konfiguration, Makros und Hilfsprogramme für einen **Voron Trident 350**
mit **Bondtech INDX**-Werkzeugwechsler (9 Tools, T0–T8).

[English version → README.md](README.md)

CAD-Daten des Druckers (INDX-Umbau des Trident):
[daum1988/Voron-Trident-INDX](https://github.com/daum1988/Voron-Trident-INDX)

> Das ist die Config einer einzelnen Maschine, geteilt als Vorlage. Sie ist
> **nicht** direkt übernehmbar: Pins, Serial-IDs und Positionen müssen am
> eigenen Drucker geprüft werden. Kalibrierwerte müssen für die eigene
> Maschine gültig sein; die Werte einer funktionierenden INDX-Installation
> werden übernommen. Nutzung auf eigene Gefahr.

**Ausgangspunkt:** eine funktionierende Bondtech-INDX-Installation auf Kalico
(Bondtechs Anleitung durchgearbeitet, Toolwechsel und Z-Homing
funktionieren). Dieses Repo ergänzt die Anbindung von Spoolman, OrcaSlicer und
KlipperScreen, einen Lade-/Entlade-Dialog, eine PA-Kalibrierung per Load-Cell
und eine Düsenkamera-Seite und bringt Board-Config und Druck-Makros dieser
Maschine mit. Die Doku von Bondtech und Kalico ersetzt es nicht.

## Hardware / Software

| | |
|---|---|
| Drucker | Voron Trident 350 |
| Werkzeugwechsler | Bondtech INDX, 9 Tools, Docks vorne |
| Mainboard | BTT Manta M8P v2.0 + Raspberry Pi CM4 |
| Z-Messung | INDX-Load-Cell (Standard-Probe) |
| Bed Mesh | Eddy-Current-Scanner (`[probe_eddy_current scanner]`, Rapid Scan) |
| Purge-Bucket | [Voron Trident Purge Bucket & Nozzle Brush, INDX-Remix](https://www.printables.com/model/1921254-voron-trident-purge-bucket-nozzle-brush-indx) (basiert auf [diesem Modell](https://www.printables.com/model/1077344-voron-trident-purge-bucket-nozzle-brush)) |
| Firmware | [Kalico](https://docs.kalico.gg/INDX.html) |
| Oberfläche | Mainsail, KlipperScreen |
| Slicer | OrcaSlicer 2.5.x |
| Filamentverwaltung | Spoolman (eine Spule pro Tool) |

## Funktionen

- **Pressure Advance mit der Load-Cell:** `PA_CAL_LOADCELL` misst PA pro Tool
  ohne Testdruck.
- **Lade-/Entlade-Dialog:** `LOAD_FILAMENT` fragt nach Tool, Material und
  Spule, in Mainsail und KlipperScreen.
- **Spoolman, eine Spule pro Tool:** Die aktive Spule wechselt mit dem Tool,
  der Verbrauch landet auf der richtigen Spule.
- **OrcaSlicer:** Druckerprofil; Filamentprofile und Farben pro Tool aus
  Spoolman.
- **KlipperScreen-Add-on:** INDX-Panel mit allen Tools und ihren Spulen,
  aktives Tool in der Titelleiste.
- **Düsenkamera-Seite** für die XY-Tool-Offsets, dazu `CAL_VERIFY_XY` zum
  Gegenprüfen.
- **INDX-Overrides** (`indx/indx_overrides.cfg`): sicherer Z-Hop,
  Filamentwerte pro Tool, Spoolman-Hook, ohne Bondtechs Dateien zu ändern.

## Anleitungen

In dieser Reihenfolge abarbeiten:

| Anleitung | Inhalt | Pflicht? |
|---|---|---|
| [Installation](docs/INSTALLATION.de.md) | Voraussetzungen, Kopieren, Anpassen, erster Start, Updates | **ja** |
| [Kalibrierung](docs/CALIBRATION.de.md) | Reihenfolge mit Links zu Bondtech/Kalico; Teile dieses Repos: Eddy-Scanner, Düsenkamera, globaler Z-Offset, PA per Load-Cell | **ja** |
| [Spoolman](docs/SPOOLMAN.de.md) | eine Spule pro Tool, Verbrauch buchen | optional |
| [OrcaSlicer](docs/ORCASLICER.de.md) | Druckerprofil, Filamentprofile aus Spoolman; Profil-Skript für Windows, getestet mit OrcaSlicer 2.5.x | optional |
| [KlipperScreen](docs/KLIPPERSCREEN.de.md) | Lade-/Entlade-Dialog, INDX-Add-on | Dialog: Teil der Grundinstallation; Add-on optional |
| [Bootlogo](bootlogo/README.md#deutsch) | Plymouth-Logo auf dem Display | optional |
| [Fehlerbehebung](docs/TROUBLESHOOTING.de.md) | Symptome, Ursachen, Lösungen | – |

## Inhalt

```
klipper/                      Inhalt kommt nach ~/printer_data/config/
  printer.cfg                 Includes, ohne SAVE_CONFIG-Block
  config/                     M8P-Board, INDX-Toolhead, Bed Mesh, TMC-Autotune
  indx/indx_overrides.cfg     Anpassungen über den originalen Bondtech-INDX-Makros
  macros/                     START_PRINT/END_PRINT, Spoolman, Lade-Dialog, PA-Kalibrierung per Load-Cell, ...
  scripts/lc_pa/              Host-Skript für die PA-Kalibrierung
  scripts/orca_lanes/         schreibt die Tool->Spulen-Zuordnung für OrcaSlicer in Moonraker
  scripts/spool_picker/       Spulenliste aus Spoolman für den Lade-Dialog
moonraker/moonraker.example.conf   die benötigten Abschnitte für moonraker.conf
orca/                         OrcaSlicer-Druckerprofil + Skript Spoolman -> Orca-Filamentprofile
bootlogo/                     Plymouth-Bootlogo für das CM4-Display
klipperscreen/                KlipperScreen-Add-on und Beispiel-Config
tools/nozzle_cam.html         Browserseite für die XY-Tool-Offsets mit Düsenkamera
docs/                         die Anleitungen oben (englisch: *.md ohne .de)
```

**Nicht enthalten:**
- die originalen Bondtech-INDX-Dateien `indx/indx.cfg`, `indx/indx-tc-macros.cfg`,
  `indx/indx-cal.cfg`, `indx/homing.cfg` – die kommen aus
  [BondtechAB/INDX](https://github.com/BondtechAB/INDX). `printer.cfg` bindet
  sie ein; fehlen sie, startet Klipper nicht. Mehrere hier verwendete Befehle
  stammen aus diesen Dateien, z. B. `PARK_TOOL`, `CHANGE_TOOL` und das
  Start-Makro `INIT_STATE` (`indx-tc-macros.cfg`), `TOOL_POSITIONS`
  (`indx.cfg`), die Kalibrier-Makros `CAL_...`, `SYNC_GLOBAL_Z` und
  `CAL_CHECK_OFFSETS` (`indx-cal.cfg`). `INDX_LOAD_FILAMENT` ist ein Befehl des
  INDX-Moduls von Kalico;
- `mainsail.cfg` (aus [mainsail-config](https://github.com/mainsail-crew/mainsail-config),
  bei MainsailOS schon vorhanden) und `timelapse.cfg` (kommt mit
  [moonraker-timelapse](https://github.com/mainsail-crew/moonraker-timelapse));
- `indx_vars.cfg` (maschinenspezifische Tool-Offsets, legt INDX selbst an) und
  alles mit Netzwerkadressen oder API-Keys.

## Begriffe

In der Klipper-Welt sind englische Begriffe üblich; diese Anleitungen
verwenden sie durchgehend, etwa „Tool“ statt „Werkzeug“.

| Begriff | Bedeutung |
|---|---|
| Tool | einer der neun INDX-Druckköpfe (T0–T8), jeder mit eigener Düse und eigenem Extruder |
| Dock | Halter, in dem ein Tool geparkt wird |
| Pickup / Parken | der Kopf nimmt ein Tool aus seinem Dock auf / stellt es zurück |
| Latch (Verschluss) | hält das Tool am Kopf; wird vom Extrudermotor bewegt |
| Load-Cell | Kraftsensor im INDX-Kopf; Z-Taster (die Düse berührt das Bett) und Sensor für die PA-Kalibrierung |
| Thermalmodell | Kalicos Berechnung, wie sich die per Induktion beheizte Düse verhält; schützt vor Überhitzung und muss kalibriert werden |
| Bucket | Behälter, in den das Tool vor dem Druck und beim Laden Filament spült |
| Includes | `[include ...]`-Zeilen in `printer.cfg`, die die übrigen Config-Dateien einbinden |
| `SAVE_CONFIG` | schreibt Kalibrierergebnisse in den Block am Ende von `printer.cfg` und startet Klipper neu |
| `indx_vars.cfg` | Datei von `[save_variables]`: aktives Tool, Tool-Offsets, PA, Spule pro Tool; wird sofort geschrieben, kein `SAVE_CONFIG` nötig |
| Macro-Prompt | Dialog, den ein Makro in Mainsail und KlipperScreen öffnet (z. B. der Lade-Dialog) |
| Lane | ein Eintrag pro Tool in Moonrakers `lane_data` (`lane0` = T0); OrcaSlicer liest daraus Filament und Farbe |

## Erfahrungen / Stolperfallen

- **Globaler Z-Offset beim nächsten Druck weg?** Babystepping ändert nur den
  Live-Offset; mit `SYNC_GLOBAL_Z` speichern
  ([Kalibrierung, Schritt 6](docs/CALIBRATION.de.md#6-z-tool-offsets)).
- **Verschiedene Druckplatten** brauchen keinen eigenen Z-Offset: Z wird mit
  der Load-Cell direkt auf der Plattenoberfläche gemessen.
- **Bauteillüfter tauschen (4010-Blower ↔ CPAP):** das Thermalmodell neu
  messen, alte Werte `model_part_cooling_fan_a/k` passen oft nicht mehr.
- **Lüfterleistung:** `min_power` statt des veralteten `off_below` verwenden.
- **OrcaSlicer:** *Standard-Ruck* 0, kein adaptives PA
  ([OrcaSlicer, Abschnitt 1](docs/ORCASLICER.de.md#1-druckerprofil)).
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
