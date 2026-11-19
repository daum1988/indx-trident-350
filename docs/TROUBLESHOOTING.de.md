# Fehlerbehebung

[English version → TROUBLESHOOTING.md](TROUBLESHOOTING.md) ·
[README](../README.de.md)

Typische Probleme mit den Ergänzungen dieses Repos, ihre Ursache und die
Lösung. Probleme des INDX selbst (Load-Cell, Docks, Thermalmodell, `CAL_Z`):
siehe [BondtechAB/INDX](https://github.com/BondtechAB/INDX) und die
[Kalico-INDX-Doku](https://docs.kalico.gg/INDX.html). Logs auf dem
Pi: `~/printer_data/logs/` (`klippy.log`, `moonraker.log`, `KlipperScreen.log`,
`orca_lanes.log`, `spool_picker.log`); in Mainsail unter *Maschine*.

## Klipper-Start und Config

| Symptom | Ursache | Lösung |
|---|---|---|
| `Include file '.../indx/indx.cfg' does not exist` | Bondtechs INDX-Dateien fehlen | dieses Repo braucht eine funktionierende Bondtech-INDX-Installation ([INSTALLATION.de.md](INSTALLATION.de.md#für-wen-ist-diese-anleitung)) |
| Fehler in `autotune_tmc.cfg` oder `shaketune.cfg` | Modul nicht installiert | installieren oder Datei löschen ([INSTALLATION.de.md](INSTALLATION.de.md), Schritt 6) |
| `Unknown command:"PARK_TOOL"` (oder `CHANGE_TOOL`, `CAL_...`) | Bondtech-Datei nicht eingebunden | Includes prüfen ([INSTALLATION.de.md](INSTALLATION.de.md), Schritt 4) |
| Spoolman-Hook oder Z-Hop wirken nicht | `indx_overrides.cfg` vor `homing.cfg` eingebunden | als letzte einbinden ([INSTALLATION.de.md](INSTALLATION.de.md), Schritt 4) |
| `mcu ... Unable to connect` | falsche Serial-ID | `ls /dev/serial/by-id/` ([INSTALLATION.de.md](INSTALLATION.de.md), Schritt 5) |
| Kalibrierwerte nach dem Kopieren weg | `SAVE_CONFIG`-Block überschrieben | aus der Sicherung zurückkopieren ([INSTALLATION.de.md](INSTALLATION.de.md), Schritt 4) |

## Toolwechsel

| Symptom | Ursache | Lösung |
|---|---|---|
| Toolwechsel bricht ab mit *Remote method ... not registered* | `macros/spoolman.cfg` vorhanden, aber kein `[spoolman]` in Moonraker | Spoolman einrichten oder `spoolman.cfg` löschen und `variable_use_spoolman: 0` setzen ([INSTALLATION.de.md](INSTALLATION.de.md), Schritt 6) |
| Globaler Z-Offset beim nächsten Druck weg | Babystep nicht gespeichert | nach dem Babystepping `SYNC_GLOBAL_Z` ([CALIBRATION.de.md](CALIBRATION.de.md#6-z-tool-offsets)) |

## Kalibrierung

| Symptom | Ursache | Lösung |
|---|---|---|
| `Sample rate is not high enough` beim Mesh | Scan zu schnell | `speed` in `[bed_mesh]` senken oder `SCAN_SPEED=` |
| Mesh mit heißer Düse sieht falsch aus | Induktionsheizung stört den Scanner | mit kalter Düse scannen |
| `PA_CAL_LOADCELL` liefert keinen Wert, keine Meldung | falscher `/home/pi`-Pfad | [INSTALLATION.de.md](INSTALLATION.de.md), Schritt 7; Log `~/printer_data/config/lc_pa_data/last_run.log` |
| PA-Wert angezeigt, aber nicht gespeichert | Messung unsicher | mit `LC_EXTRUDE_TEST` prüfen, Filament geladen, Düse heiß, erneut messen |

## Spoolman und OrcaSlicer

| Symptom | Ursache | Lösung |
|---|---|---|
| Spoolman läuft, aber der Lade-Dialog zeigt keine Spulen | Skriptpfad falsch, Moonraker erreicht Spoolman nicht (`server:`), oder alle Spulen archiviert | `~/printer_data/logs/spool_picker.log`; [INSTALLATION.de.md](INSTALLATION.de.md), Schritt 7; `server:` in `[spoolman]`; archivierte Spulen werden nicht gelistet |
| Lade-Dialog zeigt nur Materialien, keine Spulen | `variable_use_spoolman: 0` oder eine alte `filament_menu.cfg` | auf `1` setzen / Datei erneut aus dem Repo kopieren |
| Aktive Spule wechselt beim Toolwechsel nicht | keine Spule zugeordnet oder Override nicht geladen | `SHOW_TOOL_SPOOLS`; Include-Reihenfolge ([SPOOLMAN.de.md](SPOOLMAN.de.md), Schritt 3) |
| Rote Meldung beim Pickup, Verbrauch wird nicht gebucht | Tool hat keine Spule | `SET_TOOL_SPOOL T=n ID=x` oder Mainsail-Dialog |
| `lane_data` bleibt leer | Skriptpfad falsch oder Skript scheitert | `~/printer_data/logs/orca_lanes.log`; `ORCA_LANES_SYNC` |
| Farbe in Orca veraltet | Spule in Spoolman selbst geändert | `ORCA_LANES_SYNC`, dann in Orca abgleichen |
| Timelapse ohne Bilder bzw. ohne Video | `TIMELAPSE_TAKE_FRAME` fehlt im G-Code: nicht im Druckerprofil, oder Orca nutzt bei angemeldetem Konto die Profile in `%APPDATA%\OrcaSlicer\user\<Konto-ID>\` statt `user\default\` | im aktiven Druckerprofil unter *Maschinen G-Code → Vor dem Schichtwechsel* `TIMELAPSE_TAKE_FRAME` eintragen ([ORCASLICER.de.md](ORCASLICER.de.md), Abschnitt 1), neu slicen; Kontrolle: Zeile kommt im G-Code vor |
| Orca zeigt keinen Sync-Knopf | `printer_agent_id` nicht `moonraker` oder `lane_data` leer | [ORCASLICER.de.md](ORCASLICER.de.md), Abschnitte 2 und 3 |
| Abgleich lässt ein Filament leer oder generisch | kein passendes Profil `PSM<id>`, oder alte Skript-Profile mit derselben ID | Reiter Spoolman Profiles → *Update profiles from Spoolman*; Statuszeile lesen; alte `PSM`-Profile in `filament\base` löschen ([ORCASLICER.de.md](ORCASLICER.de.md), Abschnitt 4) |
| Plugin erzeugt keine Profile | Spoolman-Adresse fehlt oder falsch, keine Vorlage `SM-Vorlage <Material>` oder Filament ohne aktive Spule | Statuszeile und `%APPDATA%\OrcaSlicer\spoolman_profiles\spoolman_profiles.log`; Vorlagen prüfen; Einstellung „auch Filamente ohne Spule“ (*Datei → Plugins → Config*) |
| Reiter Spoolman zeigt „500 Internal Error“ | ältere Plugin-Version bettet Spoolman in einen Rahmen ein | aktuelles `spoolman_profiles.py` installieren, Orca neu starten |
| Reiter Spoolman zeigt die alte Adresse | Reiter lädt die Adresse nur beim Start | Orca neu starten |
| SM-Profile nicht in der Filamentliste | Orca zeigt Bundle-Profile in einer eigenen Gruppe | Filamentliste → *Bundle presets → Spoolman Profiles* |
| Schrumpfung/Fluss usw. nicht übernommen | Zusatzfeld leer oder Schlüssel falsch | Schlüssel muss genau der Orca-Einstellung entsprechen; unbekannte Schlüssel meldet das Plugin |

## KlipperScreen und Dialog

| Symptom | Ursache | Lösung |
|---|---|---|
| Kein Menüeintrag *INDX*, kein Tool in der Titelleiste | Add-on nicht geladen | `enable_addons: True`, Link in `~/KlipperScreen/addons/`, Neustart; `KlipperScreen.log` |
| Titelleisten-Eintrag fehlt, Menü ist da | `spool` fehlt in `titlebar_items` oder falscher `[printer ...]`-Abschnitt | [KLIPPERSCREEN.de.md](KLIPPERSCREEN.de.md), Schritt 3 |
| *Loaded*/*Empty* falsch | von Hand geladen oder entladen | `SET_TOOL_LOADED T=n LOADED=0/1` |
| *Laden* in KlipperScreen lädt ohne Nachfrage | `LOAD_FILAMENT`-Override nicht geladen | `indx_overrides.cfg` und `filament_menu.cfg` eingebunden? |

## Düsenkamera

| Symptom | Ursache | Lösung |
|---|---|---|
| Seite wird heruntergeladen statt angezeigt | über `/server/files/...` geöffnet | nach `~/mainsail/` kopieren, `http://<DRUCKER-IP>/nozzle_cam.html` öffnen |
| Seite nach Mainsail-Update weg | nicht in `persistent_files` | [CALIBRATION.de.md](CALIBRATION.de.md#5-xy-tool-offsets-düsenkamera) |
| Kein Bild | falscher Stream-Pfad | Standard `/webcam2/?action=stream`; crowsnest-Kamera prüfen |
| Knöpfe tun nichts (Seite als Datei geöffnet) | Moonraker lehnt `file://` ab | über die Druckeradresse öffnen |

## Bootlogo

Siehe [bootlogo/README.md](../bootlogo/README.md#deutsch): Prüfung vor der
Installation, Rückgängig machen, gedrehtes Logo.
