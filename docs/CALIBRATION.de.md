# Kalibrierung

[English version → CALIBRATION.md](CALIBRATION.md) ·
[README](../README.de.md)

Die INDX-Kalibrierung selbst dokumentieren Bondtech und Kalico; diese
Anleitung ersetzt das nicht. Zu jedem INDX-Schritt steht hier, **wo** die
Anleitung steht, **was** auszuführen ist und **woran** man den Erfolg
erkennt. Ausführlich beschrieben ist nur, was dieses Repo ergänzt.

**Voraussetzung:** Die Installation aus [INSTALLATION.de.md](INSTALLATION.de.md)
ist abgeschlossen.

**Von einer kalibrierten INDX-Installation kommend?** Die Werte bleiben
erhalten (`SAVE_CONFIG`-Block, `indx/indx.cfg`, `indx_vars.cfg`). Die Schritte
1, 3, 5 und 6 sind dann schon erledigt; mit den Zeilen „Erledigt, wenn“
prüfen. Neu messen: Schritt 2, wenn der Bauteillüfter von der bisherigen
Config abweicht, Schritt 4, wenn der Scanner neu ist, und Schritt 8 (dieses
Repo).

**Quellen:**
- Bondtech: [BondtechAB/INDX](https://github.com/BondtechAB/INDX) und
  `~/printer_data/config/indx/indx-cal.cfg`. Der Kopf der Datei listet jeden
  Kalibrierablauf mit seinen Befehlen; weiter unten hat jeder Ablauf einen
  eigenen Abschnitt mit den genauen Schritten.
- Kalico: [INDX-Doku](https://docs.kalico.gg/INDX.html) (Load-Cell,
  Thermalmodell), Doku zu `probe_eddy_current`.

| # | Schritt | Quelle | Dieses Repo ergänzt |
|---|---|---|---|
| 1 | Load-Cell | Bondtech, Kalico | – |
| 2 | Thermalmodell, Bett-PID | Kalico | Hinweis zum Lüfter |
| 3 | Dock-Positionen | Bondtech | – |
| 4 | Eddy-Scanner | Kalico | `config/bed_mesh.cfg` |
| 5 | XY-Tool-Offsets | Bondtech | Düsenkamera-Seite, `CAL_VERIFY_XY` |
| 6 | Z-Tool-Offsets | Bondtech | Hinweis zum globalen Z-Offset |
| 7 | Input Shaper | Klipper / Shake&Tune | Beschleunigungssensor schon eingerichtet |
| 8 | Pressure Advance | dieses Repo | `PA_CAL_LOADCELL` |

`SAVE_CONFIG` schreibt Ergebnisse in den Block am Ende von `printer.cfg` und
startet Klipper neu. Werte, die mit `SAVE_VARIABLE` gespeichert werden
(Tool-Offsets, PA), landen sofort in `indx_vars.cfg`.

## 1. Load-Cell

- **Wo:** `indx-cal.cfg`, Abschnitt *LOAD CELL CALIBRATION*;
  Kalico-INDX-Doku.
- **Was:** vor dem ersten Z-Homing, mit leerem Kopf: `CALIBRATE_LOAD_CELL`.
  Ein Tool von Hand einsetzen, `CALIBRATE_LOAD_CELL_APPLY GRAMS=1600`,
  `SAVE_CONFIG`. Für das allererste Z-Homing T0 von Hand einsetzen, mit
  `MANUAL_TOOL_SEAT TOOL=0` eintragen, dann `G28`.
- **Erledigt, wenn:** der `SAVE_CONFIG`-Block `[load_cell_probe]` enthält und
  bei `G28` das Bett die Düse sanft berührt und anhält.

## 2. Thermalmodell und Bett-PID

- **Wo:** [Kalico-INDX-Doku](https://docs.kalico.gg/INDX.html)
  (Thermalmodell, `INDX_CALIBRATE`).
- **Was:** die INDX-Kalibrierung wie dort beschrieben, `SAVE_CONFIG`. Bett:
  `PID_CALIBRATE HEATER=heater_bed TARGET=100`, `SAVE_CONFIG`.
- **Erledigt, wenn:** der `SAVE_CONFIG`-Block einen Abschnitt `[indx]` mit
  `model_...`-Werten hat und ein Tool ohne Thermalfehler auf Drucktemperatur
  heizt.

**Diese Maschine:** Der Bauteillüfter ist ein CPAP am M8P (`[fan]` in
`config/Trident_M8P_v2.0_config.cfg`, `max_power 0.6`). Die Werte
`model_part_cooling_fan_a/k` hängen vom Lüfter und seinem `max_power` ab.
Weicht beides von der Config ab, mit der kalibriert wurde, das Thermalmodell
neu messen.

## 3. Dock-Positionen

- **Wo:** `indx-cal.cfg`, Abschnitte *1. DOCK POSITION CALIBRATION*
  (`CAL_SET_DOCK_Y`) und *DOCK X CALIBRATION* (`CALIBRATE_DOCK_X`,
  `READ_DOCK_POSITION`).
- **Was:** pro Tool Y und X wie dort beschrieben messen, die gemeldeten Zeilen
  `variable_t<n>_...` in `indx/indx.cfg` eintragen, `RESTART`.
- **Erledigt, wenn:** jedes Tool einmal aufgenommen und geparkt wird (`T1`,
  `PARK_TOOL`, …), ohne am Dock hängen zu bleiben.

## 4. Eddy-Scanner

Der Scanner ist `[probe_eddy_current scanner]` in `config/INDX_toolhead.cfg`
und ist **nicht** als Standard-Probe eingetragen: Z=0 kommt von der
Load-Cell, der Scanner liefert nur die Bettform.

- **Wo:** Kalico-Doku zu `probe_eddy_current`; die Befehle stehen auch im Kopf
  von `config/bed_mesh.cfg`.
- **Was:** einmalig, T0 am Kopf, **Düse kalt** (die Induktionsheizung stört
  den Scanner), die Befehle unten der Reihe nach.
  `PROBE_EDDY_CURRENT_CALIBRATE` lässt die Düse schrittweise bis aufs Bett
  absenken (Papiertest): Jeder Schritt wird selbst mit `TESTZ Z=-0.1` usw.
  ausgelöst. In kleinen Schritten gehen, die Düse beobachten und bei
  unerwartetem Verhalten `ABORT` senden oder den Notaus drücken.
- **Erledigt, wenn:** `BED_MESH_CALIBRATE PROBE=scanner METHOD=rapid_scan` ein
  Mesh in einer Fahrt über das Bett erzeugt.

```
G28
LDC_CALIBRATE_DRIVE_CURRENT CHIP=scanner
SAVE_CONFIG
G28
PROBE_EDDY_CURRENT_CALIBRATE CHIP=scanner
SAVE_CONFIG
```

Jeder Mesh-Aufruf muss den Scanner wählen; `START_PRINT` macht das, angepasst
an die Druckfläche. Ohne `PROBE=scanner` tippt die Load-Cell jeden Punkt
einzeln an. „Sample rate is not high enough“: `speed` in `[bed_mesh]` senken
oder `SCAN_SPEED=` mitgeben.

## 5. XY-Tool-Offsets (Düsenkamera)

- **Wo:** `indx-cal.cfg`, Abschnitt *2. XY TOOL OFFSET CALIBRATION (CAMERA
  METHOD)*.
- **Was:** T0 aufnehmen, Düse ins Fadenkreuz der Kamera fahren,
  `CAL_ONE_SET_CAMERA_REF`. Pro Tool: `CAL_TWO_PREP_TOOL_CAL TOOL=n`, ins
  Fadenkreuz verfahren, `CAL_THREE_SAVE_XY_OFFSET`.
- **Erledigt, wenn:** `CAL_VERIFY_XY TOOL=n` (siehe unten) jede Düse ohne
  Verfahren ins Fadenkreuz bringt.

Dieses Repo ergänzt eine Browserseite für die Kamera und die Gegenprüfung.

**Düsenkamera-Seite** `tools/nozzle_cam.html`: Kamerabild mit Fadenkreuz und
Zoom, Verfahrknöpfe, die Kalibrierschritte als Knöpfe und eine Konsole.

1. **Kamera:** eine Kamera, die von unten auf die Düse schaut, als zweite
   Kamera in crowsnest eingerichtet (MJPEG-Stream).
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
`CAL_TWO_PREP_TOOL_CAL` und `CAL_THREE_SAVE_XY_OFFSET` wiederholen.

## 6. Z-Tool-Offsets

- **Wo:** `indx-cal.cfg`, Abschnitt *3. Z AUTO-CALIBRATION*.
- **Was:** Düsen und Bett säubern, `CAL_Z`.
- **Erledigt, wenn:** die Konsole für jedes Tool `t<n>_offset_z` meldet,
  `CAL_CHECK_OFFSETS` sie zeigt und die erste Schicht bei allen Tools gleich
  stark angedrückt ist.

**Globaler Z-Offset (Hinweis dieses Repos):** Die erste Schicht im Druck per
Babystepping feinjustieren, dann mit `SYNC_GLOBAL_Z` (Bondtech) speichern;
`CAL_CHECK_OFFSETS` zeigt ihn. Ohne das ist der Wert beim nächsten Druckstart
weg, weil `START_PRINT` Z homt und dabei den gespeicherten Offset setzt. Nach
einem Neustart steht live 0, bis `G28` oder T0 aufgenommen wird; das ist
normal. Verschiedene Druckplatten brauchen keinen eigenen Offset: Z wird mit
der Load-Cell auf der Plattenoberfläche gemessen.

## 7. Input Shaper

- **Wo:** Klipper-Doku *Resonance compensation* oder
  [Shake&Tune](https://github.com/Frix-x/klippain-shaketune).
- **Was:** unter Druckbedingungen messen: ein Tool am Kopf, Riemen
  gespannt, nichts Loses auf Bett oder Kopf. Dann `SHAPER_CALIBRATE` (oder
  die Befehle von Shake&Tune),
  `SAVE_CONFIG`. Der Beschleunigungssensor der INDX-Platine (`[lis2dw]`,
  `[resonance_tester]`) ist in `config/INDX_toolhead.cfg` schon eingerichtet.
- **Erledigt, wenn:** der `SAVE_CONFIG`-Block `[input_shaper]` enthält.

## 8. Pressure Advance mit der Load-Cell

`PA_CAL_LOADCELL` (`macros/lc_pa_cal.cfg`) misst Pressure Advance pro Tool
ohne Testdruck. Das Tool extrudiert in Geschwindigkeitsstufen in den Bucket,
die Load-Cell misst dabei den Düsendruck. Aus den Kraftsprüngen wird die
Druck-Zeitkonstante gefittet und mit einem Faktor je Düsengröße
multipliziert; das ergibt den PA-Wert.

**Voraussetzung:** Schritte 1–3 erledigt, Filament geladen, Bucket eingebaut
und seine Position in `macros/bucket.cfg` eingetragen, richtiger
Benutzername im Skriptpfad ([INSTALLATION.de.md](INSTALLATION.de.md),
Schritt 7). **Einmal pro Tool und nach jedem Düsenwechsel, vor der Messung,**
die Düsengröße speichern: `SET_TOOL_NOZZLE TOOL=3 D=0.6`.

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

**Faktor je Düsengröße** (gemessene Zeitkonstante -> Druck-PA), geprüft mit
OrcaSlicer-PA-Mustern:

| Düse | Faktor | Geprüft mit |
|---|---|---|
| 0,25 mm | 1,1 | 1 PLA |
| 0,4 mm | 0,6 | 2 PLA, 3 Tools |
| 0,6 mm | 0,5 | 2 PLA |

Andere Größen werden interpoliert oder bekommen den nächstliegenden Wert; die
Konsole meldet dann „not verified“. Ohne `SET_TOOL_NOZZLE` gilt der Faktor für
0,4 mm. Bei anderen Materialien (PETG, ABS …) das Ergebnis einmal mit einem
Orca-PA-Muster prüfen. `FLOW=15 SAVE=1` macht die Stufen größer (hilft bei
0,6-mm-Düsen, wenn das Ergebnis „UNCERTAIN“ ist); bei kleinen Düsen den Fluss
nicht senken, sonst wird das Signal zu schwach.

**Filamentweg:** Kraft, die nach dem Vorspülen auf dem Tool bleibt (in der
Konsole „residual“), ist Zug im Filamentweg, kein Düsendruck. Lange
PTFE-Schläuche mit Bögen, eine schwergängige Kupplung oder eine bremsende
Spule machen Messungen unsicher oder brechen sie ab. Dann mit kurz vor dem
Drucker getrenntem Schlauch messen.

Mit dem Filament und der Temperatur messen, mit denen gedruckt wird, und
während einer Messung keine anderen Befehle senden. Pro Tool: Toolwechsel,
Fahrt zum Bucket, höchstens etwa 51 mm Filament, 1–2 Minuten.

**Erledigt, wenn:** die Konsole pro Tool einen PA-Wert zeigt und `LC_PA_SHOW`
ihn auflistet (gespeichert als `t<n>_pa` in `indx_vars.cfg`). Ist dem Tool
eine Spule zugeordnet (Spoolman), steht der Wert auch im Filament der Spule
(`pressure_advance_d025/_d04/_d06`, je Düsengröße). Unsichere Werte werden
angezeigt, aber nicht gespeichert. Fehler:
`~/printer_data/config/lc_pa_data/last_run.log`.

In OrcaSlicer den normalen PA-Wert pro Filament nutzen (das Orca-Plugin
übernimmt ihn aus Spoolman, siehe [ORCASLICER.de.md](ORCASLICER.de.md)); kein
*adaptives PA*, das schickt sehr viele `SET_PRESSURE_ADVANCE` an Klipper.
