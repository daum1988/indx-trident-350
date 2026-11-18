# Kalibrierung

[English version → CALIBRATION.md](CALIBRATION.md) ·
[README](../README.de.md)

Erstkalibrierung eines INDX-Druckers in einer vorgeschlagenen Reihenfolge. Zu
jedem Schritt steht, wofür er da ist, was vorher erledigt sein muss, welche
Befehle auszuführen sind, was sich bewegt, was man danach sehen sollte und was
bei einem Fehler zu tun ist.

**Voraussetzung:** Die Grundinstallation aus
[INSTALLATION.de.md](INSTALLATION.de.md) ist fertig (Klipper startet,
`G28 X Y` funktioniert).

**Quellen:** Die meisten Kalibrier-Makros stammen aus Bondtechs
`indx/indx-cal.cfg`; deren Kopfkommentare sind maßgeblich und können neuer
sein als diese Anleitung. Thermalmodell und Load-Cell gehören zum INDX-Modul
von Kalico ([Kalico-INDX-Doku](https://docs.kalico.gg/INDX.html)). Genaue
Parameter stehen dort; diese Anleitung liefert Reihenfolge, Zweck und
Kontrollen.

**Sicherheit bei jedem Schritt:** am Drucker bleiben, den Notaus (`M112` oder
der Knopf in Mainsail/KlipperScreen) in Reichweite halten und die ersten
Bewegungen eines neuen Schritts mit abgesenktem Bett ausführen.

**`SAVE_CONFIG`** schreibt Kalibrierergebnisse in den Block am Ende von
`printer.cfg` und startet Klipper neu. Werte, die mit `SAVE_VARIABLE`
gespeichert werden (Tool-Offsets, PA, Spulenzuordnung), landen sofort in
`indx_vars.cfg` und brauchen kein `SAVE_CONFIG`.

| # | Schritt | Ergebnis steht in |
|---|---|---|
| 1 | Load-Cell | `SAVE_CONFIG`-Block |
| 2 | Erstes Z-Homing | – |
| 3 | Thermalmodell, Bett-PID | `SAVE_CONFIG`-Block |
| 4 | Dock-Positionen | `indx/indx.cfg` (von Hand) |
| 5 | Eddy-Scanner | `SAVE_CONFIG`-Block |
| 6 | XY-Tool-Offsets (Düsenkamera) | `indx_vars.cfg` |
| 7 | Z-Tool-Offsets | `indx_vars.cfg` |
| 8 | Input Shaper | `SAVE_CONFIG`-Block |
| 9 | Pressure Advance pro Tool | `indx_vars.cfg` (+ Spoolman) |

### 1. Load-Cell

**Zweck:** Die Load-Cell (Kraftsensor) im INDX-Kopf misst Kraft. Sie ist der
Z-Taster (die Düse berührt das Bett) und wird auch für die PA-Kalibrierung
genutzt. Sie muss wissen, wie viel Gramm ein Messwert bedeutet.

**Voraussetzung:** X und Y lassen sich homen. **Kein Tool am Kopf.** Z darf
noch nicht gehomt sein; dieser Schritt kommt vor jedem Z-Homing.

**Befehle:**
1. `CALIBRATE_LOAD_CELL` mit leerem Kopf. Homt X und Y, öffnet den Verschluss
   (Latch) und tariert den leeren Kopf.
2. Ein Tool von Hand einsetzen (kalt, ohne Filament möglich).
3. `CALIBRATE_LOAD_CELL_APPLY GRAMS=1600`. Verriegelt, kalibriert und
   entriegelt wieder.
4. `SAVE_CONFIG`.

**Was sich bewegt:** X/Y-Homing, der Verschluss (wird vom Extrudermotor
angetrieben).

**Erwartetes Ergebnis:** Nach dem Neustart stehen die Load-Cell-Werte im
`SAVE_CONFIG`-Block. Das Tool sitzt noch am Kopf, entriegelt, und ist nicht
als aktives Tool eingetragen.

**Bei Fehlern:**
- `CALIBRATE_LOAD_CELL` verweigert, weil vielleicht ein Tool sitzt: Tool
  abnehmen. Nur wenn eine alte Kalibrierung so falsch ist, dass ein leerer Kopf
  als besetzt gilt, mit `HEAD_EMPTY=1` ausführen.
- Erlaubt die Firmware das Verketten der Kalibrierbefehle in einem Makro
  nicht, die Schritte von Hand ausführen, wie in Bondtechs Wiki beschrieben
  (`LOAD_CELL_CALIBRATE`, `TARE`, `CALIBRATE`, `ACCEPT`).

### 2. Erstes Z-Homing

**Zweck:** Z-Homing braucht ein Tool (die Düse ist der Taster), und ein Tool
aus dem Dock holen braucht ein gehomtes Z. Ein von Hand eingesetztes Tool
durchbricht diesen Kreis.

**Voraussetzung:** Schritt 1 erledigt. Bett frei, Düse sauber (kein
Filamentrest).

**Befehle:**
1. T0 von Hand einsetzen (ist das Tool aus Schritt 1 schon T0, einfach
   sitzen lassen).
2. `MANUAL_TOOL_SEAT TOOL=0` verriegelt und trägt T0 als aktives Tool ein.
3. `G28`.

**Was sich bewegt:** X/Y, dann fährt das Bett an der Probe-Position
(`probe_x`/`probe_y` in `indx.cfg`, Standard Bettmitte) zur Düse.

**Erwartetes Ergebnis:** Die Düse berührt das Bett sanft, Z ist gehomt.

**Bei Fehlern:** Drückt das Bett ohne anzuhalten weiter, sofort Notaus und
Schritt 1 prüfen. Falsches Tool am Kopf: `MANUAL_TOOL_REMOVE`, dann von vorn.

### 3. Thermalmodell und Bett-PID

**Zweck:** Der INDX heizt die Düse per Induktion und schützt sie mit einem
Thermalmodell, also einer Berechnung, wie warm die Düse bei welcher Leistung
werden darf. Das Modell muss wissen, wie sich Heizung, Hotend und
Bauteillüfter verhalten; mit falschen Werten bricht Kalico mit einem
Thermalfehler ab.

**Voraussetzung:** Schritt 2 erledigt, ein Tool am Kopf.

**Befehle:** die INDX-Kalibrierung wie in der
[Kalico-INDX-Doku](https://docs.kalico.gg/INDX.html) beschrieben
(`INDX_CALIBRATE`), danach `SAVE_CONFIG`. Bett:
`PID_CALIBRATE HEATER=heater_bed TARGET=100`, danach `SAVE_CONFIG`.

**Was sich bewegt:** nichts; die Düse heizt, der Bauteillüfter läuft.

**Erwartetes Ergebnis:** Der `SAVE_CONFIG`-Block enthält einen Abschnitt
`[indx]` mit `model_...`-Werten (auch `model_part_cooling_fan_a/k`).

**Bei Fehlern / später:** Nach einem Wechsel des Bauteillüfters (z. B.
4010-Blower ↔ CPAP) oder seines `max_power` neu messen; alte Werte passen oft
nicht mehr.

### 4. Dock-Positionen

**Zweck:** Der Toolwechsel muss jedes Dock genau treffen. Y und X werden pro
Tool gemessen und von Hand in `indx/indx.cfg` eingetragen.

**Voraussetzung:** Schritte 1–3 erledigt.

**Y (`CAL_SET_DOCK_Y`):** Mit einem Tool am Kopf und gehomtem Drucker
vorsichtig in Y zur Dock-Position fahren und `CAL_SET_DOCK_Y` ausführen. Die
Konsole zeigt `variable_t<n>_dock_y: ...`; in `indx.cfg` eintragen.

**X (`CALIBRATE_DOCK_X`), pro Tool:**
1. `M84` (Motoren aus).
2. Den Druckkopf von Hand zum Dock von Tool n schieben.
3. `CALIBRATE_DOCK_X TOOL=n`. Schaltet X/Y ein, homt vom Dock aus erst Y,
   dann X und meldet die Dock-X-Position.
4. Wert notieren, für jedes Tool wiederholen.
5. Die Werte in `indx.cfg` eintragen, `RESTART`, danach `G28`.

Ist der Drucker schon gehomt, kann man auch zum Dock fahren und
`READ_DOCK_POSITION TOOL=n` nutzen (ohne Homing-Bewegung).

**Erwartetes Ergebnis:** Nach dem Neustart jedes Tool einmal aufnehmen und
parken (`T1`, `PARK_TOOL`, …) und dabei zusehen: Das Tool gleitet ohne
Hängenbleiben ins Dock und wird sauber aufgenommen.

**Bei Fehlern:** Bleibt ein Tool am Dock hängen, Notaus, die Werte dieses
Tools prüfen, Messung wiederholen.

### 5. Eddy-Scanner (Bed Mesh)

**Zweck:** Der Eddy-Current-Scanner im INDX-Smart-Head tastet die Bettform
schnell ab (Rapid Scan). Z=0 kommt weiterhin von der Load-Cell.

**Voraussetzung:** Schritt 2 erledigt, T0 am Kopf, **Düse kalt** (die
Induktionsheizung stört den Scanner).

**Befehle** (aus `config/bed_mesh.cfg`):
```
G28
LDC_CALIBRATE_DRIVE_CURRENT CHIP=scanner
SAVE_CONFIG
G28
PROBE_EDDY_CURRENT_CALIBRATE CHIP=scanner
SAVE_CONFIG
```
`PROBE_EDDY_CURRENT_CALIBRATE` lässt die Düse schrittweise bis aufs Bett
absenken (Papiertest); Details in der Kalico-Doku zu `probe_eddy_current`.

**Erwartetes Ergebnis:** `BED_MESH_CALIBRATE PROBE=scanner METHOD=rapid_scan`
erzeugt ein Mesh in einer Fahrt über das Bett.

**Bei Fehlern:** „Sample rate is not high enough“: `speed` in `[bed_mesh]`
senken oder `SCAN_SPEED=` mitgeben. Ohne `PROBE=scanner` tippt die Load-Cell
jeden Punkt einzeln an; das ist kein Fehler, nur langsam.

### 6. XY-Tool-Offsets (Düsenkamera)

**Zweck:** Die Düse jedes Tools sitzt in XY etwas anders. Die Abstände zu T0
werden mit einer Kamera gemessen, die von unten auf die Düse schaut.

**Voraussetzung:** Schritte 1–4 erledigt. Eine Kamera unter der Düse, als
zweite Kamera in crowsnest eingerichtet (MJPEG-Stream). Saubere Düsen.

**Düsenkamera-Seite:** `tools/nozzle_cam.html` zeigt das Kamerabild mit
Fadenkreuz und Zoom, Verfahrknöpfe, die Kalibrierschritte als Knöpfe und eine
Konsole.

1. Per SSH in den Mainsail-Ordner kopieren (aus dem Klon, siehe
   [INSTALLATION.de.md](INSTALLATION.de.md), Schritt 2) und
   `http://<DRUCKER-IP>/nozzle_cam.html` öffnen:
   ```bash
   cp ~/indx-trident-350/tools/nozzle_cam.html ~/mainsail/
   ```
   Das ist eine Kopie: Nach Änderungen an der Datei erneut kopieren. Die Seite
   kommt von derselben Adresse wie Moonraker, CORS-Einstellungen sind nicht
   nötig; das Feld *Printer* bleibt leer.
2. Ein Mainsail-Update ersetzt `~/mainsail/`. Damit die Seite bleibt, sie
   unter `persistent_files` im vorhandenen Abschnitt
   `[update_manager mainsail]` der `moonraker.conf` eintragen. Steht dort schon
   `persistent_files` (z. B. mit `config.json`), die Einträge stehen lassen und
   `nozzle_cam.html` ergänzen; sonst die Option nur mit `nozzle_cam.html`
   anlegen:
   ```ini
   persistent_files:
       nozzle_cam.html
   ```
3. Einstellungen auf der Seite: Stream-Pfad (Standard
   `/webcam2/?action=stream`, die zweite crowsnest-Kamera), Spiegeln, Zoom,
   Fadenkreuz-Ring. Die Seite merkt sie sich im Browser.

Funktioniert nicht: der Link `/server/files/config/nozzle_cam.html`
(Moonraker schickt Dateien als Download) und die Datei lokal öffnen
(`file://`; mit den üblichen `cors_domains` beantwortet Moonraker solche
Anfragen nicht).

**Befehle** (Bondtechs `indx-cal.cfg`, außer dem letzten):
1. T0 aufnehmen, Düse ins Fadenkreuz fahren, `CAL_ONE_SET_CAMERA_REF`.
2. `CAL_TWO_PREP_TOOL_CAL TOOL=n` nimmt Tool n auf und fährt es zur Kamera;
   ins Fadenkreuz verfahren.
3. `CAL_THREE_SAVE_XY_OFFSET` speichert den Offset. Schritte 2–3 für jedes
   Tool wiederholen.
4. Gegencheck: `CAL_VERIFY_XY TOOL=n` (dieses Repo,
   `indx/indx_overrides.cfg`) nimmt das Tool mit dem normalen Toolwechsel auf
   und fährt mit gespeichertem Offset zur Referenz. Ändert nichts.

**Was sich bewegt:** Toolwechsel, Fahrt zur Kamera, Verfahren.

**Erwartetes Ergebnis:** Bei `CAL_VERIFY_XY` sitzt die Düse ohne Verfahren im
Fadenkreuz. `CAL_CHECK_OFFSETS` listet die Offsets.

**Bei Fehlern:** Liegt die Düse bei `CAL_VERIFY_XY` daneben, für dieses Tool
2–3 wiederholen. Nach `CAL_VERIFY_XY` kein `CAL_THREE_SAVE_XY_OFFSET`
ausführen.

### 7. Z-Tool-Offsets

**Zweck:** Die Düsen sind unterschiedlich hoch. `CAL_Z` tastet jedes Tool mit
der Load-Cell ab und speichert seinen Z-Offset relativ zu T0.

**Voraussetzung:** Schritte 1–4 erledigt, saubere Düsen (kein Filament an der
Spitze), sauberes Bett.

**Befehle:** `CAL_Z` (optional `NOZZLE_TEMP=150 SOAK=10`, um warm zu messen).
Prüfen mit `CAL_CHECK_OFFSETS`.

**Was sich bewegt:** Jedes Tool wird aufgenommen, tastet das Bett mehrmals in
einem kleinen Bereich ab (erst an einer eigenen Stelle, dann an einer
gemeinsamen sauberen Stelle) und wird geparkt.

**Erwartetes Ergebnis:** Die Konsole listet pro Tool den Median und
`t<n>_offset_z`; die Werte sind sofort gespeichert. Ein Tool neu aufnehmen,
damit der neue Offset gilt.

**Bei Fehlern:** Konvergiert ein Tool nicht, tastet es auf einem kleinen
Kreis weiter und wird langsamer; streuende Werte kommen meist von einer
verschmutzten Düse oder einem verschmutzten Bett.

**Globaler Z-Offset (erste Schicht):** im Druck per Babystepping feinjustieren,
dann mit `SYNC_GLOBAL_Z` speichern; `CAL_CHECK_OFFSETS` zeigt ihn. Ohne
`SYNC_GLOBAL_Z` ist er beim nächsten Druckstart weg, weil `START_PRINT` Z homt
und dabei den gespeicherten Offset setzt. Nach einem Neustart steht live 0,
bis `G28` oder T0 aufgenommen wird; das ist normal. Verschiedene Druckplatten
brauchen keinen eigenen Offset: Z wird auf der Plattenoberfläche gemessen.

### 8. Input Shaper

**Zweck:** Nachschwingen (Ringing) verringern. Die INDX-Platine hat einen
Beschleunigungssensor (`[lis2dw]`, schon in `config/INDX_toolhead.cfg`
eingerichtet).

**Befehle:** Klippers `SHAPER_CALIBRATE` oder die Befehle von Shake&Tune
(siehe [Shake&Tune-Doku](https://github.com/Frix-x/klippain-shaketune)),
danach `SAVE_CONFIG`.

**Was sich bewegt:** X und Y vibrieren mit steigender Frequenz (laut).

**Erwartetes Ergebnis:** `[input_shaper]`-Werte im `SAVE_CONFIG`-Block.

### 9. Pressure Advance pro Tool (Load-Cell)

**Zweck:** Pressure Advance pro Tool und Filament, ohne Testdruck gemessen.
Das Tool extrudiert in Geschwindigkeitsstufen in den Bucket, die Load-Cell
misst dabei den Düsendruck. Aus den Kraftsprüngen wird die
Druck-Zeitkonstante gefittet; das ist der PA-Wert.

**Voraussetzung:** Schritte 1–4 erledigt, Filament im Tool geladen, Bucket
eingebaut. Einmal pro Tool (und nach jedem Düsenwechsel) die Düsengröße
speichern: `SET_TOOL_NOZZLE TOOL=3 D=0.6`. Optional vorher prüfen:
`LC_EXTRUDE_TEST` zeigt, ob die Load-Cell den Extrusionsdruck überhaupt sieht.

**Befehle:**
```
PA_CAL_LOADCELL TOOL=0 TEMP=230
PA_CAL_LOADCELL TOOLS=0,3,5 TEMP=230
PA_CAL_LOADCELL TOOLS=ALL TEMP=230
LC_PA_SHOW          gespeicherte Werte anzeigen
LC_PA_APPLY         gespeicherten Wert des aktiven Tools anwenden
```
Mit dem Filament und der Temperatur messen, mit denen gedruckt wird. Während
einer Messung keine anderen Befehle senden.

**Was sich bewegt:** Toolwechsel, Fahrt zum Bucket, Extrusion (höchstens etwa
51 mm Filament pro Tool, 1–2 Minuten).

**Erwartetes Ergebnis:** ein PA-Wert pro Tool in der Konsole, gespeichert als
`t<n>_pa` in `indx_vars.cfg`. Ist dem Tool eine Spule zugeordnet (Spoolman),
auch im Filament der Spule (`pressure_advance_d025/_d04/_d06`, je
Düsengröße). Unsichere Werte werden angezeigt, aber nicht gespeichert.

**Bei Fehlern:** Fehler stehen in
`~/printer_data/config/lc_pa_data/last_run.log` (Mainsail: Config-Dateien).
Gar kein Wert: Pfad mit Benutzernamen prüfen (siehe
[INSTALLATION.de.md](INSTALLATION.de.md), Schritt 6).

In OrcaSlicer den normalen PA-Wert pro Filament nutzen (das Profil-Skript
übernimmt ihn aus Spoolman, siehe [ORCASLICER.de.md](ORCASLICER.de.md)); kein
*adaptives PA*, das schickt sehr viele `SET_PRESSURE_ADVANCE` an Klipper.
