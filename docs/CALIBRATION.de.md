# Kalibrierung

[English version → CALIBRATION.md](CALIBRATION.md) ·
[README](../README.de.md)

Die INDX-Kalibrierung selbst dokumentieren Bondtech und Kalico; diese
Anleitung ersetzt das nicht. Sie gibt eine vorgeschlagene Reihenfolge,
verlinkt die Quellen und beschreibt ausführlich nur das, was dieses Repo
ergänzt.

**Voraussetzung:** Die Grundinstallation aus
[INSTALLATION.de.md](INSTALLATION.de.md) ist fertig (Klipper startet,
`G28 X Y` funktioniert).

**Quellen für die INDX-Schritte:**
- Bondtech: [BondtechAB/INDX](https://github.com/BondtechAB/INDX) und die
  Kopfkommentare von `indx/indx-cal.cfg` (dort steht jeder
  Kalibrierablauf mit seinen Befehlen),
- Kalico: [INDX-Doku](https://docs.kalico.gg/INDX.html) (Load-Cell,
  Thermalmodell) und die Doku zu `probe_eddy_current`.

## Reihenfolge

| # | Schritt | Quelle | Was dieses Repo ergänzt |
|---|---|---|---|
| 1 | Load-Cell (vor dem ersten Z-Homing) | Bondtech `indx-cal.cfg`, Kalico | – |
| 2 | Thermalmodell, Bett-PID | Kalico-INDX-Doku | – |
| 3 | Dock-Positionen | Bondtech `indx-cal.cfg` | – |
| 4 | Eddy-Scanner | Kalico | [`config/bed_mesh.cfg`](#4-eddy-scanner), siehe unten |
| 5 | XY-Tool-Offsets | Bondtech `indx-cal.cfg` (Kamera-Methode) | [Düsenkamera-Seite und `CAL_VERIFY_XY`](#5-xy-tool-offsets-düsenkamera) |
| 6 | Z-Tool-Offsets (`CAL_Z`) | Bondtech `indx-cal.cfg` | [Hinweis zum globalen Z-Offset](#6-z-tool-offsets-globaler-z-offset) |
| 7 | Input Shaper | Klipper / Shake&Tune | `[lis2dw]` und `[resonance_tester]` schon in `config/INDX_toolhead.cfg` |
| 8 | Pressure Advance pro Tool | dieses Repo | [`PA_CAL_LOADCELL`](#8-pressure-advance-mit-der-load-cell) |

Hinweise zu dieser Maschine:
- Der Bauteillüfter ist ein CPAP am M8P (`[fan]` in
  `config/Trident_M8P_v2.0_config.cfg`, `max_power 0.6`). Die
  Thermalmodell-Werte `model_part_cooling_fan_a/k` hängen vom Lüfter und
  seinem `max_power` ab: nach einer Änderung an einem von beiden das
  Thermalmodell neu messen.
- `printer.cfg` enthält keinen `SAVE_CONFIG`-Block; alle Messwerte kommen aus
  der eigenen Kalibrierung.

## 4. Eddy-Scanner

Der Scanner ist `[probe_eddy_current scanner]` in `config/INDX_toolhead.cfg`
und ist **nicht** als Standard-Probe eingetragen: Z=0 kommt von der
Load-Cell, der Scanner liefert nur die Bettform. Einmalig kalibrieren, T0 am
Kopf, **Düse kalt** (die Induktionsheizung stört den Scanner):

```
G28
LDC_CALIBRATE_DRIVE_CURRENT CHIP=scanner
SAVE_CONFIG
G28
PROBE_EDDY_CURRENT_CALIBRATE CHIP=scanner
SAVE_CONFIG
```

Jeder Mesh-Aufruf muss den Scanner wählen:
`BED_MESH_CALIBRATE PROBE=scanner METHOD=rapid_scan` (`START_PRINT` macht das,
angepasst an die Druckfläche). Ohne `PROBE=scanner` tippt die Load-Cell jeden
Punkt einzeln an.

**Kontrolle:** Der Befehl oben erzeugt ein Mesh in einer Fahrt über das Bett.
„Sample rate is not high enough“: `speed` in `[bed_mesh]` senken oder
`SCAN_SPEED=` mitgeben.

## 5. XY-Tool-Offsets (Düsenkamera)

Bondtechs Kamera-Methode (`CAL_ONE_SET_CAMERA_REF`,
`CAL_TWO_PREP_TOOL_CAL TOOL=n`, `CAL_THREE_SAVE_XY_OFFSET`, siehe
`indx-cal.cfg`) braucht eine Kamera, die von unten auf die Düse schaut. Dieses
Repo ergänzt eine Browserseite dafür und eine Gegenprüfung.

**Düsenkamera-Seite** `tools/nozzle_cam.html`: Kamerabild mit Fadenkreuz und
Zoom, Verfahrknöpfe, die Kalibrierschritte als Knöpfe und eine Konsole.

1. **Kamera:** als zweite Kamera in crowsnest eingerichtet (MJPEG-Stream).
2. **Installieren:** die Seite per SSH in den Mainsail-Ordner kopieren (aus
   dem Klon, siehe [INSTALLATION.de.md](INSTALLATION.de.md), Schritt 2) und
   `http://<DRUCKER-IP>/nozzle_cam.html` öffnen:
   ```bash
   cp ~/indx-trident-350/tools/nozzle_cam.html ~/mainsail/
   ```
   Das ist eine Kopie: Nach Änderungen an der Datei erneut kopieren. Die Seite
   kommt von derselben Adresse wie Moonraker, CORS-Einstellungen sind nicht
   nötig; das Feld *Printer* bleibt leer.
3. **Bei Mainsail-Updates behalten:** Ein Update ersetzt `~/mainsail/`. Die
   Seite unter `persistent_files` im vorhandenen Abschnitt
   `[update_manager mainsail]` der `moonraker.conf` eintragen. Steht dort schon
   `persistent_files` (z. B. mit `config.json`), die Einträge stehen lassen und
   `nozzle_cam.html` ergänzen; sonst die Option nur mit `nozzle_cam.html`
   anlegen:
   ```ini
   persistent_files:
       nozzle_cam.html
   ```
4. **Einstellungen auf der Seite:** Stream-Pfad (Standard
   `/webcam2/?action=stream`, die zweite crowsnest-Kamera), Spiegeln, Zoom,
   Fadenkreuz-Ring. Die Seite merkt sie sich im Browser.

Funktioniert nicht: der Link `/server/files/config/nozzle_cam.html`
(Moonraker schickt Dateien als Download) und die Datei lokal öffnen
(`file://`; mit den üblichen `cors_domains` beantwortet Moonraker solche
Anfragen nicht).

**Gegenprüfung `CAL_VERIFY_XY TOOL=n`** (`indx/indx_overrides.cfg`): nimmt
das Tool mit dem normalen Toolwechsel auf (Offsets aktiv wie beim Drucken) und
fährt zur Kamera-Referenz aus `CAL_ONE_SET_CAMERA_REF`. Stimmt der Offset,
sitzt die Düse ohne Verfahren im Fadenkreuz. Ändert nichts; danach kein
`CAL_THREE_SAVE_XY_OFFSET` ausführen. Liegt die Düse daneben, für dieses Tool
Bondtechs Schritte 2–3 wiederholen.

## 6. Z-Tool-Offsets: globaler Z-Offset

`CAL_Z` (Bondtech) speichert den Z-Offset jedes Tools relativ zu T0. Die erste
Schicht wird danach mit dem globalen Z-Offset feinjustiert:

- Babystepping im Druck ändert nur den Live-Offset. Mit `SYNC_GLOBAL_Z`
  (Bondtech) speichern; `CAL_CHECK_OFFSETS` zeigt ihn. Ohne das ist der Wert
  beim nächsten Druckstart weg, weil `START_PRINT` Z homt und dabei den
  gespeicherten Offset setzt.
- Nach einem Neustart steht live 0, bis `G28` oder T0 aufgenommen wird; das
  ist normal.
- Verschiedene Druckplatten brauchen keinen eigenen Offset: Z wird mit der
  Load-Cell auf der Plattenoberfläche gemessen.

## 8. Pressure Advance mit der Load-Cell

`PA_CAL_LOADCELL` (`macros/lc_pa_cal.cfg`) misst Pressure Advance pro Tool
ohne Testdruck. Das Tool extrudiert in Geschwindigkeitsstufen in den Bucket,
die Load-Cell misst dabei den Düsendruck. Aus den Kraftsprüngen wird die
Druck-Zeitkonstante gefittet; das ist der PA-Wert.

**Voraussetzung:** Schritte 1–3 erledigt (Load-Cell, Thermalmodell, Docks),
Filament geladen, Bucket eingebaut, richtiger Benutzername im Skriptpfad
([INSTALLATION.de.md](INSTALLATION.de.md), Schritt 6). Einmal pro Tool und
nach jedem Düsenwechsel die Düsengröße speichern:
`SET_TOOL_NOZZLE TOOL=3 D=0.6`.

**Optional vorher:** `LC_EXTRUDE_TEST SPEED=1` / `SPEED=3` / `SPEED=6` mit
heißem Tool zeigt, ob die Load-Cell den Extrusionsdruck überhaupt sieht (die
Differenz muss mit der Geschwindigkeit deutlich steigen).

```
PA_CAL_LOADCELL TOOL=0 TEMP=230
PA_CAL_LOADCELL TOOLS=0,3,5 TEMP=230
PA_CAL_LOADCELL TOOLS=ALL TEMP=230
LC_PA_SHOW          gespeicherte Werte anzeigen
LC_PA_APPLY         gespeicherten Wert des aktiven Tools anwenden
```

Mit dem Filament und der Temperatur messen, mit denen gedruckt wird, und
während einer Messung keine anderen Befehle senden. Pro Tool: Toolwechsel,
Fahrt zum Bucket, höchstens etwa 51 mm Filament, 1–2 Minuten.

**Ergebnis:** ein PA-Wert pro Tool in der Konsole, gespeichert als `t<n>_pa`
in `indx_vars.cfg`. Ist dem Tool eine Spule zugeordnet (Spoolman), auch im
Filament der Spule (`pressure_advance_d025/_d04/_d06`, je Düsengröße).
Unsichere Werte werden angezeigt, aber nicht gespeichert. Fehler:
`~/printer_data/config/lc_pa_data/last_run.log`.

In OrcaSlicer den normalen PA-Wert pro Filament nutzen (das Profil-Skript
übernimmt ihn aus Spoolman, siehe [ORCASLICER.de.md](ORCASLICER.de.md)); kein
*adaptives PA*, das schickt sehr viele `SET_PRESSURE_ADVANCE` an Klipper.
