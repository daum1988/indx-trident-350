# Installation

[English version → INSTALLATION.md](INSTALLATION.md) ·
[README](../README.de.md)

## Für wen ist diese Anleitung?

Für alle, die Bondtechs INDX-Anleitung schon durchgearbeitet haben und eine
**funktionierende INDX-Installation** besitzen. Ausgangszustand:

- Kalico mit INDX-Modul ist installiert. Eine Mindestversion ist nicht
  bekannt; diese Maschine läuft mit Kalico `v2026.11.00-30-g991e1823`.
  Andere Versionen sind nicht getestet; das INDX-Modul muss die hier
  verwendeten Befehle kennen (z. B. `INDX_LOAD_FILAMENT`, `[load_cell_probe]`).
- Bondtechs Dateien liegen in `~/printer_data/config/indx/` (`indx.cfg`,
  `indx-tc-macros.cfg`, `indx-cal.cfg`, `homing.cfg`).
- Klipper startet mit dieser Config ohne Fehler.
- Tools werden aufgenommen und geparkt, Z homt mit der Load-Cell.

Wer noch nicht so weit ist: zuerst [BondtechAB/INDX](https://github.com/BondtechAB/INDX)
und die [Kalico-INDX-Doku](https://docs.kalico.gg/INDX.html) abarbeiten.

**Was diese Anleitung macht:** Die Dateien aus diesem Repo ersetzen die
Board- und Toolhead-Config, `printer.cfg` und die Makros. Bondtechs Dateien
und die eigenen Kalibrierwerte bleiben erhalten. Am Ende startet Klipper mit
der Config aus diesem Repo, und die INDX-Funktionen laufen wie vorher.

> **Wichtig:** Das ist keine Ergänzung, die man einfach über die bestehende
> Config kopiert. Das Repo ist die komplette Config einer bestimmten Maschine
> (Voron Trident 350, BTT Manta M8P v2.0, 9 Tools). Die Board-Config und die
> maschinenspezifischen Werte müssen an den eigenen Drucker angepasst werden.

## Kennzeichnung

| Kennzeichen | Bedeutung |
|---|---|
| **[Allgemein]** | gilt für jede passende INDX-Installation, so ausführen |
| **[Maschinenspezifisch]** | Werte dieser Maschine; an den eigenen Drucker anpassen |
| **[Optional]** | nur, wenn die Funktion genutzt wird |

## Vorab entscheiden

Diese Fragen vor dem Kopieren beantworten; davon hängt ab, was nach dem
Kopieren angepasst wird:

| Frage | Bei „nein“ | Schritt |
|---|---|---|
| Gleiche Hardware (Trident, Manta M8P v2.0)? | `config/Trident_M8P_v2.0_config.cfg` durch die eigene Board-Config ersetzen | 5 |
| Spoolman vorhanden oder geplant? | `macros/spoolman.cfg` löschen, `variable_use_spoolman: 0` | 6 |
| moonraker-timelapse installiert? | Include `timelapse.cfg` auskommentieren | 6 |
| [Shake&Tune](https://github.com/Frix-x/klippain-shaketune) installiert? | `macros/shaketune.cfg` löschen | 6 |
| [klipper_tmc_autotune](https://github.com/andrewmcgr/klipper_tmc_autotune) installiert? | `config/autotune_tmc.cfg` löschen | 6 |
| Heißt der Linux-Benutzer `pi` (`whoami`)? | drei Pfade anpassen | 7 |

## Was das Kopieren ändert

`cp` in Schritt 3 überschreibt gleichnamige Dateien und legt neue an. Alles
andere bleibt liegen.

| Datei / Ordner | Was passiert | Danach |
|---|---|---|
| `printer.cfg` | **ersetzt** | eigenen `SAVE_CONFIG`-Block zurückholen (Schritt 4) |
| `config/Trident_M8P_v2.0_config.cfg` | neu bzw. ersetzt | **[Maschinenspezifisch]** Board, Pins, Serial-ID |
| `config/INDX_toolhead.cfg` | neu bzw. ersetzt; enthält `[mcu indxmcu]`, `[indx]`, `[extruder]`, `[load_cell_probe]`, `[save_variables]`, Scanner | **[Maschinenspezifisch]** mit der bisherigen Toolhead-Config abgleichen |
| `config/bed_mesh.cfg`, `config/autotune_tmc.cfg` | neu bzw. ersetzt | Mesh-Bereich prüfen |
| `indx/indx_overrides.cfg` | neu | – |
| `macros/*.cfg` | neu; gleichnamige eigene Makro-Dateien werden ersetzt | Bucket-Positionen anpassen |
| `scripts/` | neu | – |
| `indx/indx.cfg`, `indx-tc-macros.cfg`, `indx-cal.cfg`, `homing.cfg` | **bleiben unverändert** | nicht durch andere Versionen ersetzen |
| `indx_vars.cfg` (Tool-Offsets, aktives Tool) | **bleibt unverändert** | – |
| `moonraker.conf`, `mainsail.cfg`, `KlipperScreen.conf` | bleiben unverändert | – |
| eigene Dateien mit anderen Namen in `config/` und `macros/` | **bleiben liegen und werden weiter geladen** (`[include config/*.cfg]`) | prüfen, siehe Schritt 4 |

## Schritte

### 1. Sichern [Allgemein]

```bash
B=~/printer_data/config.bak-$(date +%Y%m%d-%H%M%S) && cp -r ~/printer_data/config "$B" && echo "$B"
```

Der Befehl gibt den Pfad der Sicherung aus, z. B.
`/home/pi/printer_data/config.bak-20261118-231500`. Diesen Pfad notieren; er
wird in Schritt 4 als `<SICHERUNG>` gebraucht: In den Befehlen unten
`<SICHERUNG>` jeweils durch diesen Pfad ersetzen (ohne spitze Klammern).

**Kontrolle:** `ls <SICHERUNG>` zeigt `printer.cfg`, `indx/` usw.

### 2. Repo klonen [Allgemein]

```bash
cd ~ && git clone https://github.com/daum1988/indx-trident-350
```

Der Klon in `~/indx-trident-350/` ist nur die Quelle. Klipper liest weiter
aus `~/printer_data/config/`; erst Schritt 3 bringt die Dateien dorthin.

### 3. Dateien kopieren [Allgemein]

```bash
cp -r ~/indx-trident-350/klipper/. ~/printer_data/config/
```

Das kopiert den *Inhalt* von `klipper/` (nicht den Ordner selbst). Die Makros
erwarten die Skripte in `~/printer_data/config/scripts/`.

**Kontrolle:** `ls ~/printer_data/config/indx/` zeigt Bondtechs vier Dateien
plus `indx_overrides.cfg`; `ls ~/printer_data/config/scripts/` zeigt
`lc_pa`, `orca_lanes`, `spool_picker`.

### 4. Bisherige Config übernehmen [Maschinenspezifisch]

1. **`SAVE_CONFIG`-Block:** Die alte `printer.cfg` endet mit Zeilen, die mit
   `#*#` beginnen. Dort hat Klipper die Kalibrierwerte gespeichert
   (Load-Cell, Thermalmodell, PID, Input Shaper, Scanner). Den ganzen Block
   aus der Sicherung ans Ende der neuen `printer.cfg` kopieren:
   ```bash
   sed -n '/^#\*# <---------------------- SAVE_CONFIG/,$p' <SICHERUNG>/printer.cfg
   ```
   zeigt den Block. **Ohne diesen Block ist die Load-Cell nicht kalibriert,
   Z-Homing ist dann gefährlich.** Kontrolle nach dem Kopieren:
   ```bash
   grep -n "^#\*# \[" ~/printer_data/config/printer.cfg
   ```
   listet die Abschnitte im Block; `[load_cell_probe]` und `[indx]` müssen
   dabei sein. Der Block muss ganz am Ende der Datei stehen. Ob er
   vollständig übernommen ist, zeigt ein Vergleich mit der Sicherung (keine
   Ausgabe außer „gleich“ = vollständig):
   ```bash
   diff <(sed -n '/^#\*# <---------------------- SAVE_CONFIG/,$p' <SICHERUNG>/printer.cfg) <(sed -n '/^#\*# <---------------------- SAVE_CONFIG/,$p' ~/printer_data/config/printer.cfg) && echo gleich
   ```
2. **Includes:** Die neue `printer.cfg` lädt `mainsail.cfg`, `config/*.cfg`,
   `macros/*.cfg`, `timelapse.cfg` und Bondtechs Dateien; `indx_overrides.cfg`
   muss nach `indx/homing.cfg` stehen. Hat die alte `printer.cfg` weitere
   Dateien eingebunden, prüfen, ob sie noch gebraucht werden.
3. **Alte Dateien in `config/` und `macros/`:** Dateien mit anderen Namen als
   im Repo bleiben liegen und werden über die Wildcard-Includes weiter
   geladen. Enthalten sie Abschnitte, die jetzt auch in den Repo-Dateien
   stehen (z. B. eine eigene Board- oder Toolhead-Config mit `[mcu]`,
   `[indx]`, `[extruder]`, oder eigene `START_PRINT`-Makros), führt Klipper
   gleichnamige Abschnitte zusammen: Die zuletzt geladene Option gewinnt,
   meist ohne Fehlermeldung. Das Ergebnis ist dann eine Mischung aus alter
   und neuer Config. Solche Dateien aus `config/` und `macros/`
   herausnehmen (sie liegen ja in der Sicherung) oder gezielt
   zusammenführen. Dass Klipper danach ohne Fehler startet, reicht deshalb
   als Kontrolle nicht. Dieser Befehl listet jeden Abschnitt, der in mehr als
   einer geladenen Datei steht, mit den Dateien dazu:
   ```bash
   cd ~/printer_data/config && grep -Ho "^\[[^]]*\]" printer.cfg mainsail.cfg timelapse.cfg config/*.cfg macros/*.cfg indx/*.cfg 2>/dev/null | awk -F: '{f[$2]=f[$2]" "$1; n[$2]++} END {for (s in n) if (n[s]>1) print s f[s]}' | sort
   ```
   Bei dieser Config sind diese Doppelungen gewollt: Bondtech-Makros, die
   `indx/indx_overrides.cfg` ersetzt (`LOAD_FILAMENT`, `CAL_Z`,
   `_INDX_SAFE_Z_HOP`, `_INDX_SET_ACTIVE_TOOL`), `T0`–`T8` (`indx/indx.cfg`
   und `macros/spoolman.cfg`), `PAUSE`/`RESUME`/`CANCEL_PRINT` (`mainsail.cfg`
   und `macros/trident_macros.cfg`), `[respond]` und `[heater_bed]`. Jede
   andere Zeile, vor allem mit einer eigenen alten Datei, prüfen. Die Ausgabe
   ist eine Prüfliste, keine vollständige Analyse der geladenen Config: Der
   Befehl durchsucht die genannten Dateien, auch solche, die gar nicht
   eingebunden sind (z. B. `timelapse.cfg` bei auskommentiertem Include).

### 5. Hardware anpassen [Maschinenspezifisch]

- **Board:** `config/Trident_M8P_v2.0_config.cfg` gilt nur für ein Manta M8P
  v2.0 im Trident. Bei anderer Hardware die eigene Board-Config verwenden.
- **Serial-IDs:** `ls /dev/serial/by-id/` und die `serial:`-Zeilen in
  `config/Trident_M8P_v2.0_config.cfg` und `config/INDX_toolhead.cfg`
  ersetzen. Bei CAN die `canbus_uuid`.
- **Pins:** mit der eigenen Verkabelung abgleichen (Motoren, Heizbett,
  Thermistoren, Lüfter, LEDs). Der Bauteillüfter dieser Maschine ist ein CPAP
  am M8P (`[fan]`, `max_power 0.6`); wer die Lüfter am INDX-Kopf nutzt,
  schaltet stattdessen den `[fan]` in `config/INDX_toolhead.cfg` ein.
- **Toolhead:** `config/INDX_toolhead.cfg` mit der bisherigen
  Toolhead-Config vergleichen, eigene Werte übernehmen.
- **Bucket und Bürste:** Diese Maschine nutzt
  [Voron Trident Purge Bucket & Nozzle Brush, INDX-Remix](https://www.printables.com/model/1921254-voron-trident-purge-bucket-nozzle-brush-indx).
  Positionen in `macros/bucket.cfg` (`_BUCKET_VARS`); werden für Laden,
  Entladen, PA-Kalibrierung und Druckstart gebraucht.
- **Parkposition, Ladetemperatur:** `_global_var` in `macros/common.cfg`.
- **Bed Mesh:** `mesh_min`/`mesh_max` in `config/bed_mesh.cfg`.

### 6. Optionale Teile [Optional]

Nach den Antworten aus „Vorab entscheiden“:

- **Ohne Spoolman:** `macros/spoolman.cfg` löschen und in
  `macros/filament_menu.cfg` `variable_use_spoolman: 0` setzen. Sonst bricht
  jeder Toolwechsel mit *Remote method ... not registered* ab, weil
  `spoolman.cfg` einen `[spoolman]`-Abschnitt in `moonraker.conf` braucht.
  Mit Spoolman: Einrichtung in [SPOOLMAN.de.md](SPOOLMAN.de.md); bis dahin
  keinen Toolwechsel ausführen.
- **Ohne moonraker-timelapse:** in `printer.cfg` die Zeile
  `[include timelapse.cfg]` auskommentieren.
- **Ohne Shake&Tune:** `macros/shaketune.cfg` löschen.
- **Ohne TMC Autotune:** `config/autotune_tmc.cfg` löschen.

### 7. Benutzername [Maschinenspezifisch]

Drei Abschnitte `[gcode_shell_command]` (`macros/lc_pa_cal.cfg`,
`macros/spoolman.cfg`, `macros/filament_menu.cfg`) rufen Skripte über
`/home/pi/printer_data/...` auf. Ist der Benutzer nicht `pi`:

```bash
cd ~/printer_data/config/macros && sed -i "s#/home/pi/#$HOME/#g" lc_pa_cal.cfg filament_menu.cfg spoolman.cfg
```

(Ohne Spoolman meldet `sed` die fehlende `spoolman.cfg`; das ist in Ordnung.)
Sonst schlagen PA-Kalibrierung, Orca-Lanes und Spulen-Dialog ohne Meldung
fehl.

**Kontrolle:** `grep -rn "/home/" ~/printer_data/config/macros/` zeigt nur
noch den eigenen Home-Ordner.

### 8. Moonraker [Optional]

`moonraker/moonraker.example.conf` enthält Abschnitte für Spoolman,
Timelapse und Update-Manager. Nur die Abschnitte für Installiertes in die
eigene `moonraker.conf` übernehmen, dann:

```bash
sudo systemctl restart moonraker
```

**Kontrolle:** Mainsail zeigt keine Moonraker-Warnungen (Glocke).

### 9. Erster Start [Allgemein]

**Vor dem ersten Neustart:** Nach dem Kopieren enthält `config/` die
Board- und Toolhead-Config *dieser* Maschine, nicht mehr die eigene. Erst
neu starten, wenn die Schritte 4 und 5 erledigt sind (Serial-IDs, Pins,
Toolhead-Werte, `SAVE_CONFIG`-Block). Falsche Pins können Heizungen oder
Motoren falsch ansteuern.

`FIRMWARE_RESTART` in der Mainsail-Konsole, dann der Reihe nach prüfen.
Erst Heizungen und Sensoren, dann Bewegung, zuletzt der Toolwechsel:

- [ ] Klipper ist *ready*, kein Config-Fehler. Ein Fehler nennt Datei und
      Abschnitt; siehe [TROUBLESHOOTING.de.md](TROUBLESHOOTING.de.md).
- [ ] `LC_PA_SHOW` antwortet: Die Makros aus diesem Repo sind geladen.
- [ ] `CAL_CHECK_OFFSETS` zeigt die bisherigen Tool-Offsets: Bondtechs Dateien
      und `indx_vars.cfg` sind erhalten.
- [ ] Der `SAVE_CONFIG`-Block am Ende von `printer.cfg` enthält
      `[load_cell_probe]` und `[indx]`.
- [ ] Temperaturen in Mainsail plausibel: Bett, Tool und Kammer zeigen
      etwa Raumtemperatur, kein Sensor springt oder fehlt.
- [ ] Heizungen einzeln und unter Beobachtung: Bett auf 60 °C
      (`SET_HEATER_TEMPERATURE HEATER=heater_bed TARGET=60`), dann mit Tool
      am Kopf die Düse auf 150 °C (`M104 S150`). Es muss jeweils die richtige
      Temperatur steigen. Danach beide wieder aus (`TURN_OFF_HEATERS`).
- [ ] `G28 X Y` homt X und Y. Vorher: nichts im Fahrweg, Bett frei, Hand
      am Notaus.
- [ ] Erst danach `G28` (mit Z), die Hand am Notaus: Die Düse berührt das Bett
      sanft, Z ist gehomt.
- [ ] Toolwechsel: **Mit Spoolman** erst, wenn [SPOOLMAN.de.md](SPOOLMAN.de.md)
      erledigt ist (sonst bricht der Toolwechsel ab); bis dahin diesen Punkt
      überspringen. **Ohne Spoolman** (`spoolman.cfg` gelöscht) sofort:
      `T1`, danach `PARK_TOOL`. Das Tool wird aufgenommen und geparkt.
- [ ] `LOAD_FILAMENT` ohne Parameter öffnet den Tool-Dialog; *Cancel*
      schließt ihn.

Weiter mit [CALIBRATION.de.md](CALIBRATION.de.md). Die INDX-Kalibrierung aus
der bisherigen Installation bleibt gültig; neu zu messen sind nur die Teile
dieses Repos (Eddy-Scanner, falls neu, und Pressure Advance).

## Spätere Updates

```bash
cd ~/indx-trident-350 && git pull
```

`git pull` aktualisiert **nur den Klon** in `~/indx-trident-350/`. Die
installierten Dateien in `~/printer_data/config/` ändern sich dadurch nicht.

Danach **nicht** einfach wie in Schritt 3 alles erneut kopieren. Das
überschreibt die Anpassungen aus den Schritten 4–7:
- `printer.cfg` verliert ihren `SAVE_CONFIG`-Block,
- ohne Spoolman ist `macros/spoolman.cfg` wieder da und
  `variable_use_spoolman` wieder `1`, dann bricht jeder Toolwechsel ab,
- die `/home/pi`-Pfade stehen wieder auf `pi`,
- Serial-IDs, Pins, Bucket-Positionen usw. sind wieder die vom Original.

Vorher vergleichen und nur übernehmen, was man will. Dieser Befehl listet nur
geänderte oder neue Repo-Dateien (Dateien, die nur im eigenen Config-Ordner
liegen, werden ausgefiltert):

```bash
diff -rq ~/indx-trident-350/klipper/ ~/printer_data/config/ | grep -v "^Only in $HOME/printer_data"
```

Danach einzelne Dateien mit `diff` ansehen, z. B.
`diff ~/indx-trident-350/klipper/macros/filament_menu.cfg ~/printer_data/config/macros/filament_menu.cfg`,
und Änderungen von Hand übernehmen.

Wer doch alles kopiert: vorher sichern, danach Schritte 4–7 wiederholen. Das
KlipperScreen-Add-on und die Düsenkamera-Seite sind ebenfalls Kopien: bei
Änderungen wie in ihren Anleitungen neu kopieren.

## Nur einzelne Erweiterungen in die eigene Config übernehmen

Wer die eigene Config behalten will, kann einzelne Teile übernehmen. Das ist
nicht der getestete Weg; die Abhängigkeiten:

| Erweiterung | Dateien | braucht außerdem |
|---|---|---|
| Lade-/Entlade-Dialog | `indx/indx_overrides.cfg`, `macros/filament_menu.cfg`, `macros/bucket.cfg`, `scripts/spool_picker/` | `macros/common.cfg`; `[respond]`, `[save_variables]` |
| Spoolman pro Tool | `macros/spoolman.cfg`, `indx/indx_overrides.cfg`, `scripts/orca_lanes/` | `[save_variables]`, `[spoolman]` in Moonraker |
| PA per Load-Cell | `macros/lc_pa_cal.cfg`, `scripts/lc_pa/` | `macros/bucket.cfg` (`MOVE_TO_BUCKET`), `macros/common.cfg` |
| `LC_EXTRUDE_TEST` | `macros/lc_extrude_test.cfg` | `macros/bucket.cfg`, `macros/common.cfg` |
| `CAL_VERIFY_XY`, sicherer Z-Hop | `indx/indx_overrides.cfg` | – |

`macros/common.cfg` enthält die Hilfsmakros, die die Erweiterungen mit den
Druck-Makros teilen (`_global_var`, `_ENSURE_HOMED`, `UNLOAD_FILAMENT`). Die
Druck-Makros selbst (`START_PRINT`, `END_PRINT`, `PAUSE`, `RESUME`,
`CANCEL_PRINT`) stehen in `macros/trident_macros.cfg`; wer eigene behält,
lässt diese Datei weg. Hat die eigene Config schon ein `UNLOAD_FILAMENT`, das
entfernen: das aus `common.cfg` öffnet den Tool-Dialog.
