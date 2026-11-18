# OrcaSlicer

[English version → ORCASLICER.md](ORCASLICER.md) ·
[README](../README.de.md)

Druckerprofil für diese Maschine sowie Filamentprofile und Farben aus Spoolman
(OrcaSlicer 2.5.x unter Windows).

**Voraussetzung:** Für das Druckerprofil nur OrcaSlicer. Für die Abschnitte
2–5 außerdem Spoolman, eingerichtet wie in [SPOOLMAN.de.md](SPOOLMAN.de.md),
und den Tools zugeordnete Spulen.

## 1. Druckerprofil

`orca/Voron Trident 350 INDX.json` hat Maschinenlimits passend zur
Klipper-Config (300 mm/s, 3000 mm/s², Square Corner Velocity 5), damit die
Zeitschätzung stimmt. In Orca importieren (Menü *File → Import →
Import Configs*, in der deutschen Oberfläche entsprechend) und anpassen:

- Düsen: T0–T4 0.4, T5–T6 0.6, T7–T8 0.25 – die eigenen eintragen.
- Toolwechselzeit und Startzeit sind Schätzwerte; an der eigenen Maschine
  stoppen.
- Der G-Code *Vor dem Schichtwechsel* enthält `TIMELAPSE_TAKE_FRAME` für
  moonraker-timelapse. Ohne Timelapse die Zeile löschen, sonst meldet Klipper
  bei jeder Schicht einen unbekannten Befehl.

Zwei Einstellungen, die Ärger mit Klipper vermeiden:
- **Ruck:** Bei Klipper behandelt Orca `machine_max_jerk_x/y` als
  `square_corner_velocity` und warnt. Im Prozessprofil *Standard-Ruck* auf 0
  setzen; dann sendet Orca keine Ruck-Befehle und es gilt der Wert aus
  Klipper.
- **Pressure Advance:** normaler PA-Wert pro Filament, kein *adaptives PA*
  (schickt sehr viele `SET_PRESSURE_ADVANCE` an Klipper).

**Kontrolle:** Ein kleines Objekt mit zwei Tools slicen: Die G-Code-Vorschau
zeigt `T0`/`T1`, die geschätzte Zeit ist plausibel.

## So funktioniert der Filamentabgleich

```mermaid
flowchart LR
    SM[(Spoolman<br/>Spulen, Filamente)] -->|Spule pro Tool| K[Klipper / Moonraker<br/>t0__spool_id … t8__spool_id]
    K -->|orca_lanes.py schreibt<br/>lane0 … lane8| L[(Moonraker<br/>lane_data)]
    L -->|Sync-Knopf| O[OrcaSlicer<br/>Filament 1–9 = T0–T8]
    SM -->|orca_spoolman_profiles.ps1<br/>auf dem PC| P[Orca-Filamentprofile<br/>eins pro Spoolman-Filament]
    P --> O
```

Der Drucker schreibt pro Tool Material, Farbe und Filament-ID der Spule in
Moonrakers `lane_data`. Eine *Lane* ist ein Eintrag pro Tool: `lane0` = T0 …
`lane8` = T8, z. B. `lane3` = „PETG, rot, Filament-ID PSM12“. OrcaSlicer liest
die Lanes beim Filamentabgleich und wählt pro Filament 1–9 das passende
Profil. Die Profile erzeugt ein PowerShell-Skript auf dem PC aus den
Filamenten in Spoolman.

## 2. Einmalig in OrcaSlicer

1. Einstellungen → Reiter *Entwickler*: **Entwicklermodus** anhaken
   (englisch: *Developer mode*). Die übrigen Optionen dort bleiben, wie sie
   sind.

   ![Orca-Einstellungen, Reiter Entwickler: Entwicklermodus anhaken](images/orca_developer_settings.png)

2. Eigenes Druckerprofil bearbeiten (*Drucker-Einstellungen → Grundlegende
   Informationen*), Ansicht *Erweitert*: **Drucker-Agent = Moonraker**. Als
   Adresse `<DRUCKER-IP>` ohne Port eintragen. **Kontrolle:** Der Reiter
   „Gerät (Web)“ zeigt Mainsail mit dem aktuellen Druckerstatus.

   ![Orca-Drucker-Einstellungen: Drucker-Agent auf Moonraker](images/orca_printer_agent.png)
3. Orca legt den Drucker mit `"printer_agent_id": "orca"` an; es muss
   `"moonraker"` sein. Das ist die einzige Handarbeit in einer Datei:
   1. **OrcaSlicer schließen** (Orca schreibt die Datei beim Beenden neu).
   2. **Sicherung** von `%APPDATA%\OrcaSlicer\OrcaSlicer.conf` anlegen (Datei kopieren).
   3. In einem Texteditor öffnen und nach `printer_agent_id` suchen (Strg+F).
      Unter `local_machines` den Eintrag des eigenen Druckers nehmen (er
      enthält dessen Namen bzw. IP) und genau diese eine Zeile ändern:
      ```
      vorher:   "printer_agent_id": "orca",
      nachher:  "printer_agent_id": "moonraker",
      ```
      Sonst nichts ändern.
   4. Speichern, Orca starten. Startet Orca nicht oder fehlen Einstellungen,
      die Sicherung zurückkopieren.

Der Knopf zum Abgleichen erscheint erst, wenn in `lane_data` mindestens eine
Lane steht (Abschnitt 3).

## 3. Drucker: Lanes werden automatisch geschrieben

Nichts zusätzlich zu installieren: `macros/spoolman.cfg` (siehe
[SPOOLMAN.de.md](SPOOLMAN.de.md), Schritt 3) enthält diesen Teil schon,
zusammen mit den Skripten aus dem Repo:

| Datei | Was |
|---|---|
| `scripts/orca_lanes/orca_lanes.py` | Holt die Spulen über Moonrakers Spoolman-Proxy, schreibt `lane0`–`lane8` |
| `scripts/orca_lanes/orca_lanes_launch.sh` | Startet das Skript im Hintergrund (blockiert keinen Druck) |
| `macros/spoolman.cfg` | `[gcode_shell_command orca_lanes]`, `_ORCA_LANES`, `ORCA_LANES_SYNC`; `_SPOOL_WATCH` ruft `_ORCA_LANES` auf |

Benötigt `gcode_shell_command` (in Kalico enthalten) und den richtigen
Benutzernamen im Pfad (siehe [INSTALLATION.de.md](INSTALLATION.de.md),
Schritt 7).

Das Skript läuft wieder, sobald sich eine Zuweisung ändert (`SET_TOOL_SPOOL`,
Mainsail-Dialog). Nach Änderungen an einer Spule in Spoolman selbst (z. B.
Farbe korrigiert): `ORCA_LANES_SYNC`. Log: `~/printer_data/logs/orca_lanes.log`.

**Kontrolle:** Etwa 10 s nach dem Start kommt in der Konsole z. B.
„Orca-Lanes: 9 tools sent, 3 with spool“. Per SSH:

```bash
curl -s "http://localhost:7125/server/database/item?namespace=lane_data"
```

Eine Lane sieht so aus: `{"lane": "0", "material": "PLA", "spool_id": 11, "filament_id": "PSM11", "color": "#F9FDFF"}`.
Tools ohne Spule haben `"material": ""` und sind in Orca leer.

## 4. PC: Profile aus Spoolman erzeugen

Das Skript ist `orca/orca_spoolman_profiles.ps1` aus diesem Repo. Es läuft
mit der Windows PowerShell 5.1, die bei Windows 10/11 dabei ist (keine
Installation nötig), und braucht nur Netzwerkzugriff auf Spoolman. Irgendwo
auf dem PC ablegen. Die Spoolman-Adresse wird mit `-SpoolmanUrl` übergeben;
wer sie nicht jedes Mal tippen will, ändert oben im Skript im Block
`param(...)` den Standardwert (`http://spoolman.local:7912`).

1. **Vorlagen anlegen (einmalig):** In Orca pro Material ein *eigenständiges*
   Filament anlegen (Filament → *Filament erstellen*, nicht „Kopieren“ eines
   System-Profils), kompatibel mit dem eigenen Drucker, mit den bewährten
   Einstellungen. Name: `SM-Vorlage PLA`, `SM-Vorlage PETG`, … (anderes
   Präfix, z. B. `SM-Template PLA`: bei jedem Aufruf
   `-TemplatePrefix "SM-Template"` anhängen). Im Filament-Startcode **kein**
   `SET_ACTIVE_SPOOL`. Speichern, **Orca schließen**.
2. **Probelauf** (zeigt nur an):
   ```powershell
   powershell -ExecutionPolicy Bypass -File .\orca_spoolman_profiles.ps1 -SpoolmanUrl http://<SPOOLMAN-IP>:7912 -WhatIf
   ```
3. **Schreiben** (Orca muss geschlossen sein, sonst bricht das Skript ab):
   ```powershell
   powershell -ExecutionPolicy Bypass -File .\orca_spoolman_profiles.ps1 -SpoolmanUrl http://<SPOOLMAN-IP>:7912
   ```
   Danach Orca starten. Die Profile heißen `<Hersteller> <Name> (SM<id>)`,
   z. B. „Sunlu High Speed Matte Pri-White (SM11)“, und haben die Filament-ID
   `PSM<id>`.
4. **Abgleich:** Drucker wählen, im Bereich *Filament* den Sync-Knopf (rechts
   neben der Überschrift) drücken. Orca zählt ab 1: Filament 1 = T0 …
   Filament 9 = T8.

   ![Orca: Bereich Filament mit markiertem Sync-Knopf](images/orca_filament_sync.png)

**Kontrolle:** Filament 1–9 bekommen Profil und Farbe der Spulen auf T0–T8.

Aus Spoolman übernommen: Name, Hersteller, Farbe, Dichte, Durchmesser, Düsen-
und Betttemperatur (Abstand zur ersten Schicht bleibt wie in der Vorlage),
Preis pro kg. Was in Spoolman leer ist, bleibt wie in der Vorlage.
Material-Zuordnung: genaue Vorlage, sonst die längste passende
(`PLA+` → `SM-Vorlage PLA`).

Nach einem OrcaSlicer-Update zuerst einen Probelauf (`-WhatIf`) machen und
danach ein erzeugtes Profil in Orca öffnen: Das Skript ist mit dem
Profilformat von 2.5.x getestet.

Erneut ausführen, wenn in Spoolman neue Filamente dazukommen oder sich Werte
ändern; unveränderte Profile werden nicht angefasst. `-Prune` löscht
`SM`-Profile, deren Filament es in Spoolman nicht mehr gibt (oder das keine
aktive Spule mehr hat). `-All` legt auch Filamente ohne aktive Spule an.

**Hinweise**
- Orca vergleicht die Filament-ID nur mit eigenständigen Profilen (ohne „erbt
  von“). Deshalb nicht spoolman2slicer nehmen: dessen Profile erben von
  „Voron Generic …“.
- Den Reiter „Gerät“ (Bambu-Ansicht) ignorieren; Steuerung weiter über Mainsail.
- Der Verbrauch wird unabhängig vom Slicer gebucht; Orca muss nur `T0`…`T8` ausgeben.

## 5. Einstellungen pro Filament zentral in Spoolman

Grundeinstellungen stehen in der Orca-Vorlage (eine pro Düsengröße).
Abweichungen pro Filament trägst du in Spoolman beim Filament in die
Zusatzfelder ein; das Skript übernimmt sie beim nächsten Lauf in die Profile.
Die SM-Profile selbst nicht in Orca bearbeiten, sie werden bei jedem Lauf neu
erzeugt.

| Zusatzfeld | Orca-Einstellung |
|---|---|
| `filament_flow_ratio` | Flussrate |
| `filament_max_volumetric_speed` (+ `_d025`, `_d04`, `_d06`) | Max. Volumenstrom |
| `filament_retraction_length`, `filament_retraction_speed` | Retract |
| `fan_min_speed`, `fan_max_speed` | Lüfter |
| `filament_shrink`, `filament_shrinkage_compensation_z` | Schrumpfung (XY), Schrumpfung (Z), in % (z. B. `99.5`; 100 = keine Korrektur) |

- Leer = Wert der Vorlage.
- Endung `_d025`/`_d04`/`_d06`: gilt nur für diese Düse und hat dort Vorrang
  vor dem Feld ohne Endung.
- Weitere Einstellungen: in Spoolman (Einstellungen → Zusatzfelder →
  Filament) ein Feld anlegen, dessen Schlüssel genau der Orca-Einstellung
  entspricht. Unbekannte Schlüssel meldet das Skript als Warnung.
- `pressure_advance*` schreibt die Load-Cell-Kalibrierung (`PA_CAL_LOADCELL`,
  siehe [CALIBRATION.de.md](CALIBRATION.de.md), Schritt 8) in Spoolman. Das
  Profil-Skript übernimmt den Wert nach Orca (`pressure_advance`, Düsenfeld hat
  Vorrang) und schaltet `enable_pressure_advance` ein. Orca setzt PA dann beim
  Filamentwechsel im G-Code.

Danach: Orca schließen, `orca_spoolman_profiles.ps1` ausführen, Orca starten.

Probleme: siehe [TROUBLESHOOTING.de.md](TROUBLESHOOTING.de.md#spoolman-und-orcaslicer).
