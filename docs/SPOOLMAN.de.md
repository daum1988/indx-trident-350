# Spoolman am Trident (INDX, T0-T8)

[English version → SPOOLMAN.md](SPOOLMAN.md)

## 0. Vorher prüfen: läuft Spoolman schon?

In `moonraker.conf` steht schon:

```ini
[spoolman]
server: http://<SPOOLMAN-IP>:7912
```

Öffne `http://<SPOOLMAN-IP>:7912` im Browser.
- **Spoolman-Oberfläche erscheint:** Spoolman läuft schon auf einem anderen Gerät. Schritt 1 entfällt, weiter mit Schritt 3.
- **Keine Seite:** Spoolman wie unten auf dem Pi installieren. Mit `hostname -I` auf dem Pi prüfen, ob .250 die Adresse des Pi ist.

## 1. Installation auf dem CM4 (per SSH als `pi`)

**Empfehlung: Standalone.** Der CM4 hat wenig RAM, und Docker bringt einen zusätzlichen Daemon und mehr Speicherbedarf mit. Standalone läuft als systemd-Dienst und kann über den Update-Manager in Mainsail aktualisiert werden. Docker lohnt sich nur, wenn auf dem Pi ohnehin schon Docker läuft.

```bash
cd ~ && sudo apt-get update && sudo apt-get install -y curl jq unzip
```

```bash
mkdir -p ~/Spoolman && cd ~ && source_url=$(curl -s https://api.github.com/repos/Donkie/Spoolman/releases/latest | jq -r '.assets[] | select(.name == "spoolman.zip").browser_download_url') && curl -sSL "$source_url" -o temp.zip && unzip temp.zip -d ./Spoolman && rm temp.zip
```

```bash
cd ~/Spoolman && bash ./scripts/install.sh
```

Das Skript fragt nach Port (Standard 7912) und ob ein systemd-Dienst angelegt werden soll: **ja**. Danach prüfen:

```bash
systemctl status Spoolman
```

Weboberfläche: `http://<pi-ip>:7912`. Die Datenbank liegt in `~/.local/share/spoolman` und bleibt bei Updates erhalten.

<details><summary>Alternative: Docker</summary>

```yaml
# ~/spoolman/docker-compose.yml
services:
  spoolman:
    image: ghcr.io/donkie/spoolman:latest
    restart: unless-stopped
    volumes:
      - ./data:/home/app/.local/share/spoolman
    ports:
      - "7912:8000"
    environment:
      - TZ=Europe/Berlin
```

```bash
cd ~/spoolman && docker compose up -d
```
</details>

## 2. `moonraker.conf` – nur diese Abschnitte

`[spoolman]` **ersetzen** (läuft Spoolman auf dem Pi selbst):

```ini
[spoolman]
server: http://localhost:7912
sync_rate: 5
```

Läuft Spoolman auf einem anderen Gerät, bleibt die Zeile `server:` auf dessen Adresse.

Optional, nur bei Standalone auf dem Pi, für Updates über Mainsail:

```ini
[update_manager spoolman]
type: zip
channel: stable
repo: Donkie/Spoolman
path: ~/Spoolman
virtualenv: .venv
requirements: requirements.txt
persistent_files:
    .venv
    .env
managed_services: Spoolman
```

Damit Moonraker den Dienst neu starten darf, muss `Spoolman` als eigene Zeile in `~/printer_data/moonraker.asvc` stehen. Nachsehen und gegebenenfalls ergänzen:

```bash
grep -qx Spoolman ~/printer_data/moonraker.asvc || echo Spoolman >> ~/printer_data/moonraker.asvc
```

```bash
sudo systemctl restart moonraker
```

Danach erscheint in Mainsail im Dashboard das Spoolman-Panel.

## 3. Makros hochladen

Zwei Dateien in Mainsail unter *Machine* ersetzen:

| Datei | Was |
|---|---|
| `macros/spoolman.cfg` | Neu geschrieben: Zuweisung, Abgleich, Wiederherstellung beim Start, `spool_id` an T0-T8 |
| `indx/indx_overrides.cfg` | Am Ende ergänzt: `_INDX_SET_ACTIVE_TOOL` mit einer zusätzlichen Zeile `_SPOOL_SYNC` |

`printer.cfg` und `indx_vars.cfg` bleiben unverändert. `macros/spoolman.cfg` wird über `[include macros/*.cfg]` geladen. Danach `FIRMWARE_RESTART`.

### Wie es funktioniert

- Die Spool-ID jedes Tools steht in `indx_vars.cfg` als `t0__spool_id` … `t8__spool_id`. Unter diesen Namen speichert auch der Spoolman-Dialog von Mainsail, solange `[save_variables]` vorhanden ist. Beide benutzen also dieselben Werte.
- **Pickup T3:** `_INDX_SET_ACTIVE_TOOL TOOL=3` ruft `_SPOOL_SYNC` auf, das `SET_ACTIVE_SPOOL ID=<Spule von T3>` ausführt.
- **Parken:** `TOOL=-1` führt zu `CLEAR_ACTIVE_SPOOL`.
- **Start:** `INIT_STATE` meldet das Tool auf dem Kopf. Dessen Spule wird wieder aktiv.
- Moonraker bucht den Verbrauch laufend auf die aktive Spule, auch Purge und `LOAD_FILAMENT`.

### Makros

```
SET_TOOL_SPOOL T=3 ID=12    Spule 12 an T3 zuweisen
SET_TOOL_SPOOL T=3 ID=0     Zuweisung von T3 löschen
                            (macht UNLOAD_FILAMENT automatisch für das aktive Tool)
SHOW_TOOL_SPOOLS            alle Zuweisungen anzeigen
```

**Mainsail-Dialog:** Im Spoolman-Panel *Change Spool* erscheinen T0-T8 zur Auswahl. Wählst du dort eine Spule für das Tool, das gerade auf dem Kopf sitzt, schaltet ein Wächter (`_SPOOL_WATCH`, alle 3 s) innerhalb von 3 s um. Bei einem geparkten Tool wird die Spule beim nächsten Pickup aktiv.

Hat ein Tool keine Spule, steht beim Pickup eine rote Meldung in der Konsole. Der Druck läuft weiter, der Verbrauch wird aber nicht gebucht.

## 4. Test

1. In Spoolman zwei Spulen anlegen, zum Beispiel ID 1 und 2.
2. `SET_TOOL_SPOOL T=0 ID=1` und `SET_TOOL_SPOOL T=1 ID=2`, dann `SHOW_TOOL_SPOOLS`.
3. `T0` → Konsole meldet „Spoolman: T0 -> spool 1“, das Spoolman-Panel zeigt Spule 1.
4. Heizen, `G1 E50 F300` → nach etwa 5 s sinkt das Restgewicht von Spule 1.
5. `T1` → Spule 2 aktiv, wieder extrudieren, nur Spule 2 nimmt ab.
6. `PARK_TOOL` → keine aktive Spule.
7. `FIRMWARE_RESTART` mit T1 auf dem Kopf → `SHOW_TOOL_SPOOLS` zeigt die Zuweisungen wieder, Spule 2 ist aktiv.

## 5. OrcaSlicer: Farben und Profile aus Spoolman

Ablauf: Der Drucker schreibt pro Tool Material, Farbe und Filament-ID der Spule in Moonrakers `lane_data`. OrcaSlicer liest das beim Filamentabgleich und wählt pro Filament 1–9 (= T0–T8) das passende Profil. Die Profile erzeugt ein PowerShell-Skript auf dem PC aus den Filamenten in Spoolman.

### 5.1 Einmalig in OrcaSlicer (2.5.1)

- Einstellungen: Entwicklermodus an, *Entwickler → „Use printer agents instead of print hosts“* an.
- Druckerprofil „Voron Trident 350 INDX“: Ansicht *Erweitert*, **Printer Agent = Moonraker**, Adresse `<DRUCKER-IP>` (ohne Port, dann zeigt „Gerät (Web)“ Mainsail).
- In `%APPDATA%\OrcaSlicer\OrcaSlicer.conf` unter `local_machines` muss der Trident `"printer_agent_id": "moonraker"` haben (Orca legt neue Einträge mit `"orca"` an).
- Der Knopf zum Abgleichen erscheint erst, wenn in `lane_data` mindestens ein Steckplatz steht.

### 5.2 Drucker: Steckplätze automatisch schreiben

Hochladen (Mainsail → *Machine*):

| Datei | Was |
|---|---|
| `scripts/orca_lanes/orca_lanes.py` | Holt die Spulen über Moonrakers Spoolman-Proxy, schreibt `lane0`–`lane8` |
| `scripts/orca_lanes/orca_lanes_launch.sh` | Startet das Skript im Hintergrund (blockiert keinen Druck) |
| `macros/spoolman.cfg` | Neu: `[gcode_shell_command orca_lanes]`, `_ORCA_LANES`, `ORCA_LANES_SYNC`; der Wächter ruft `_ORCA_LANES` auf |

Danach `FIRMWARE_RESTART`. Etwa 10 s nach dem Start kommt in der Konsole „Orca-Lanes: 9 tools sent, … with spool“. Das Skript läuft wieder, sobald sich eine Zuweisung ändert (`SET_TOOL_SPOOL`, Mainsail-Dialog). Nach Änderungen an einer Spule in Spoolman selbst (z. B. Farbe korrigiert): `ORCA_LANES_SYNC`. Log: `logs/orca_lanes.log`.

Kontrolle per SSH:

```bash
curl -s "http://localhost:7125/server/database/item?namespace=lane_data"
```

Ein Steckplatz sieht so aus: `{"lane": "0", "material": "PLA", "spool_id": 11, "filament_id": "PSM11", "color": "#F9FDFF"}`. Tools ohne Spule haben `"material": ""` und sind in Orca leer.

### 5.3 PC: Profile aus Spoolman erzeugen

1. **Vorlagen anlegen (einmalig):** In Orca pro Material ein *eigenes* Filament anlegen (Filament → *Filament erstellen*, nicht „Kopieren“ eines System-Profils), kompatibel mit dem Trident, mit deinen bewährten Einstellungen. Name: `SM-Vorlage PLA`, `SM-Vorlage PETG`, … Im Filament-Startcode **kein** `SET_ACTIVE_SPOOL`. Speichern, Orca schließen.
2. **Probelauf** (zeigt nur an):
   ```powershell
   powershell -ExecutionPolicy Bypass -File .\orca_spoolman_profiles.ps1 -WhatIf
   ```
3. **Schreiben:**
   ```powershell
   powershell -ExecutionPolicy Bypass -File .\orca_spoolman_profiles.ps1
   ```
   Danach Orca starten. Die Profile heißen `<Hersteller> <Name> (SM<id>)`, z. B. „Sunlu High Speed Matte Pri-White (SM11)“, und haben die Filament-ID `PSM<id>`.
4. **Abgleich:** Trident wählen, Sync-Knopf → Filament 1–9 bekommen Profil und Farbe der Spulen auf T0–T8.

Aus Spoolman übernommen: Name, Hersteller, Farbe, Dichte, Durchmesser, Düsen- und Betttemperatur (Abstand zur ersten Schicht bleibt wie in der Vorlage), Preis pro kg. Was in Spoolman leer ist, bleibt wie in der Vorlage. Material-Zuordnung: genaue Vorlage, sonst die längste passende (`PLA+` → `SM-Vorlage PLA`).

Erneut ausführen, wenn in Spoolman neue Filamente dazukommen oder sich Werte ändern; unveränderte Profile werden nicht angefasst. `-Prune` löscht `SM`-Profile, deren Filament es in Spoolman nicht mehr gibt (oder das keine aktive Spule mehr hat). `-All` legt auch Filamente ohne aktive Spule an.

**Hinweise**
- Orca vergleicht die Filament-ID nur mit eigenständigen Profilen (ohne „erbt von“). Deshalb nicht spoolman2slicer nehmen: dessen Profile erben von „Voron Generic …“.
- Den Reiter „Gerät“ (Bambu-Ansicht) ignorieren; Steuerung weiter über Mainsail.
- Der Verbrauch wird unabhängig vom Slicer gebucht; Orca muss nur `T0`…`T8` ausgeben.

### 5.4 Einstellungen pro Filament zentral in Spoolman

Grundeinstellungen stehen in der Orca-Vorlage (`SM-Vorlage PLA Basis @… nozzle`, eine pro Düse). Abweichungen pro Filament trägst du in Spoolman beim Filament in die Zusatzfelder ein; das Skript übernimmt sie beim nächsten Lauf in die Profile. Die SM-Profile selbst nicht in Orca bearbeiten, sie werden bei jedem Lauf neu erzeugt.

| Zusatzfeld | Orca-Einstellung |
|---|---|
| `filament_flow_ratio` | Flussrate |
| `filament_max_volumetric_speed` (+ `_d025`, `_d04`, `_d06`) | Max. Volumenstrom |
| `filament_retraction_length`, `filament_retraction_speed` | Retract |
| `fan_min_speed`, `fan_max_speed` | Lüfter |

- Leer = Wert der Vorlage.
- Endung `_d025`/`_d04`/`_d06`: gilt nur für diese Düse und hat dort Vorrang vor dem Feld ohne Endung.
- Weitere Einstellungen: in Spoolman (Einstellungen → Zusatzfelder → Filament) ein Feld anlegen, dessen Schlüssel genau der Orca-Einstellung entspricht. Unbekannte Schlüssel meldet das Skript als Warnung.
- `pressure_advance*` schreibt die Load-Cell-Kalibrierung (PA_CAL_LOADCELL) in Spoolman. Das Profil-Skript übernimmt den Wert nach Orca (`pressure_advance`, Düsenfeld hat Vorrang) und schaltet `enable_pressure_advance` ein. Orca setzt PA dann beim Filamentwechsel im G-Code.

Danach: Orca schließen, `orca_spoolman_profiles.ps1` ausführen, Orca starten.
