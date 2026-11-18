# Spoolman mit Bondtech INDX (T0–T8)

[English version → SPOOLMAN.md](SPOOLMAN.md)

Eine Spoolman-Spule pro INDX-Tool. Die aktive Spule wechselt mit dem Tool auf
dem Kopf, der Verbrauch landet also auf der richtigen Spule, und OrcaSlicer
kann Farbe und Profil jedes Tools übernehmen.

> Geschrieben für die Maschine aus diesem Repo (Voron Trident 350, INDX mit
> 9 Tools, Kalico, Mainsail, OrcaSlicer 2.5.x unter Windows). Namen wie das
> Orca-Druckerprofil „Voron Trident 350 INDX“, der Benutzer `pi` und die
> Anzahl der Tools stammen von dieser Maschine; an die eigene anpassen.

**Voraussetzungen:** die INDX-Config von Bondtech, `[save_variables]` mit
`indx_vars.cfg` (in diesem Repo in `config/INDX_toolhead.cfg`), der Inhalt von
`klipper/` aus diesem Repo im eigenen Config-Ordner (siehe
[README](../README.de.md#einrichtung)), Moonraker mit Netzwerkzugriff auf
Spoolman.

## 0. Vorher prüfen: läuft Spoolman schon?

Steht in `moonraker.conf` schon ein Abschnitt `[spoolman]`, die Adresse aus
dessen Zeile `server:` im Browser öffnen.

- **Spoolman-Oberfläche erscheint:** Spoolman läuft schon (auf dem Pi oder auf
  einem anderen Gerät, z. B. einem NAS). Schritt 1 entfällt.
- **Keine Seite:** Spoolman installieren, z. B. auf dem Pi wie in Schritt 1.
  Ob die Adresse aus `server:` der Pi selbst ist, zeigt `hostname -I` auf
  dem Pi.

Ohne Abschnitt `[spoolman]`: Spoolman installieren (Schritt 1) und den
Abschnitt in Schritt 2 ergänzen.

## 1. Installation auf dem Pi (per SSH)

**Empfehlung: Standalone.** Ein CM4 hat wenig RAM, und Docker bringt einen
zusätzlichen Daemon und mehr Speicherbedarf mit. Standalone läuft als
systemd-Dienst und kann über den Update-Manager in Mainsail aktualisiert
werden. Docker lohnt sich nur, wenn auf dem Pi ohnehin schon Docker läuft.

```bash
cd ~ && sudo apt-get update && sudo apt-get install -y curl jq unzip
```

```bash
mkdir -p ~/Spoolman && cd ~ && source_url=$(curl -s https://api.github.com/repos/Donkie/Spoolman/releases/latest | jq -r '.assets[] | select(.name == "spoolman.zip").browser_download_url') && curl -sSL "$source_url" -o temp.zip && unzip temp.zip -d ./Spoolman && rm temp.zip
```

```bash
cd ~/Spoolman && bash ./scripts/install.sh
```

Das Skript fragt nach Port (Standard 7912) und ob ein systemd-Dienst angelegt
werden soll: **ja**. Danach prüfen:

```bash
systemctl status Spoolman
```

Weboberfläche: `http://<PI-IP>:7912`. Die Datenbank liegt in
`~/.local/share/spoolman` und bleibt bei Updates erhalten.

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

## 2. `moonraker.conf`

```ini
[spoolman]
server: http://localhost:7912
sync_rate: 5
```

`server:` ist `http://localhost:7912`, wenn Spoolman auf dem Pi läuft, sonst
die Adresse des anderen Geräts, z. B. `http://<SPOOLMAN-IP>:7912`.

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

Damit Moonraker den Dienst neu starten darf, muss `Spoolman` als eigene Zeile
in `~/printer_data/moonraker.asvc` stehen:

```bash
grep -qx Spoolman ~/printer_data/moonraker.asvc || echo Spoolman >> ~/printer_data/moonraker.asvc
```

```bash
sudo systemctl restart moonraker
```

Danach erscheint in Mainsail im Dashboard das Spoolman-Panel.

## 3. Makros

Die Spoolman-Logik steckt in diesen Dateien des Repos. Wer den Inhalt von
`klipper/` in den Config-Ordner kopiert hat (README, Einrichtung), hat sie
schon:

| Datei | Was |
|---|---|
| `macros/spoolman.cfg` | Zuweisung, Abgleich, Wiederherstellung beim Start, `spool_id` an T0–T8, Orca-Lanes (Schritt 5.2) |
| `indx/indx_overrides.cfg` | Überschreibt Bondtechs `_INDX_SET_ACTIVE_TOOL` mit einer zusätzlichen Zeile `_SPOOL_SYNC` am Ende |

In `printer.cfg` prüfen:
- `[include macros/*.cfg]` ist vorhanden (lädt `spoolman.cfg`),
- `[include indx/indx_overrides.cfg]` steht **nach** `[include indx/homing.cfg]`,
- `[save_variables]` existiert (in diesem Repo in `config/INDX_toolhead.cfg`, Datei `indx_vars.cfg`).

Danach `FIRMWARE_RESTART`.

### Wie es funktioniert

- Die Spool-ID jedes Tools steht in `indx_vars.cfg` als `t0__spool_id` …
  `t8__spool_id`. Unter diesen Namen speichert auch der Spoolman-Dialog von
  Mainsail, solange `[save_variables]` vorhanden ist. Beide benutzen also
  dieselben Werte.
- **Pickup T3:** `_INDX_SET_ACTIVE_TOOL TOOL=3` ruft `_SPOOL_SYNC` auf, das
  `SET_ACTIVE_SPOOL ID=<Spule von T3>` ausführt.
- **Parken:** `TOOL=-1` führt zu `CLEAR_ACTIVE_SPOOL`.
- **Start:** `INIT_STATE` (Bondtech, `indx-tc-macros.cfg`) meldet das Tool auf dem Kopf. Dessen
  Spule wird wieder aktiv.
- Moonraker bucht den Verbrauch laufend auf die aktive Spule, auch Purge und
  `LOAD_FILAMENT`.

### Befehle

```
SET_TOOL_SPOOL T=3 ID=12    Spule 12 an T3 zuweisen
SET_TOOL_SPOOL T=3 ID=0     Zuweisung von T3 löschen
                            (erledigt UNLOAD_FILAMENT automatisch)
SHOW_TOOL_SPOOLS            alle Zuweisungen anzeigen
LOAD_FILAMENT               Dialog: Tool -> Material -> Spule (wird zugewiesen)
```

**Mainsail-Dialog:** Im Spoolman-Panel *Change Spool* erscheinen T0–T8 zur
Auswahl. Das Makro `_SPOOL_WATCH` prüft alle 3 s, ob sich dort eine Zuweisung
geändert hat (der „Wächter“). Wählst du eine Spule für das Tool, das gerade
auf dem Kopf sitzt, wird sie innerhalb von 3 s aktiv. Bei einem geparkten Tool
wird die Spule beim nächsten Pickup aktiv.

Hat ein Tool keine Spule, steht beim Pickup eine rote Meldung in der Konsole.
Der Druck läuft weiter, der Verbrauch wird aber nicht gebucht.

## 4. Test

1. In Spoolman zwei Spulen anlegen, zum Beispiel ID 1 und 2.
2. `SET_TOOL_SPOOL T=0 ID=1` und `SET_TOOL_SPOOL T=1 ID=2`, dann `SHOW_TOOL_SPOOLS`.
3. `T0` → Konsole meldet „Spoolman: T0 -> spool 1“, das Spoolman-Panel zeigt Spule 1.
4. Heizen, `G1 E50 F300` → nach etwa 5 s sinkt das Restgewicht von Spule 1.
5. `T1` → Spule 2 aktiv, wieder extrudieren, nur Spule 2 nimmt ab.
6. `PARK_TOOL` (Bondtech-Makro) → keine aktive Spule.
7. `FIRMWARE_RESTART` mit T1 auf dem Kopf → `SHOW_TOOL_SPOOLS` zeigt die Zuweisungen wieder, Spule 2 ist aktiv.

## 5. OrcaSlicer: Farben und Profile aus Spoolman

Ablauf: Der Drucker schreibt pro Tool Material, Farbe und Filament-ID der
Spule in Moonrakers `lane_data` (ein Eintrag pro Tool, *Lane* genannt:
`lane0` = T0 … `lane8` = T8). OrcaSlicer liest das beim Filamentabgleich und
wählt pro Filament 1–9 (= T0–T8) das passende Profil. Die Profile erzeugt ein
PowerShell-Skript auf dem PC aus den Filamenten in Spoolman.

### 5.1 Einmalig in OrcaSlicer (2.5.x)

1. Einstellungen: Entwicklermodus an, *Entwickler → „Use printer agents
   instead of print hosts“* an.
2. Eigenes Druckerprofil (in diesem Repo: `orca/Voron Trident 350 INDX.json`):
   Ansicht *Erweitert*, **Printer Agent = Moonraker**, Adresse `<DRUCKER-IP>`
   (ohne Port; „Gerät (Web)“ zeigt dann Mainsail).
3. Orca legt den Drucker mit `"printer_agent_id": "orca"` an; es muss
   `"moonraker"` sein. Das ist die einzige Handarbeit in einer Datei:
   1. **OrcaSlicer schließen** (Orca schreibt die Datei beim Beenden neu).
   2. **Sicherung** von `%APPDATA%\OrcaSlicer\OrcaSlicer.conf` anlegen (Datei kopieren).
   3. In einem Texteditor öffnen, unter `local_machines` den eigenen Drucker
      suchen und `"printer_agent_id": "orca"` in
      `"printer_agent_id": "moonraker"` ändern. Sonst nichts ändern.
   4. Speichern, Orca starten. Startet Orca nicht oder fehlen Einstellungen,
      die Sicherung zurückkopieren.

Der Knopf zum Abgleichen erscheint erst, wenn in `lane_data` mindestens eine
Lane steht (Schritt 5.2).

### 5.2 Drucker: Lanes automatisch schreiben

Nichts zusätzlich hochzuladen: `macros/spoolman.cfg` aus Schritt 3 enthält
diesen Teil schon, zusammen mit den Skripten aus dem Repo:

| Datei | Was |
|---|---|
| `scripts/orca_lanes/orca_lanes.py` | Holt die Spulen über Moonrakers Spoolman-Proxy, schreibt `lane0`–`lane8` |
| `scripts/orca_lanes/orca_lanes_launch.sh` | Startet das Skript im Hintergrund (blockiert keinen Druck) |
| `macros/spoolman.cfg` | `[gcode_shell_command orca_lanes]`, `_ORCA_LANES`, `ORCA_LANES_SYNC`; `_SPOOL_WATCH` ruft `_ORCA_LANES` auf |

Benötigt `gcode_shell_command` (in Kalico enthalten). Der Pfad in
`[gcode_shell_command orca_lanes]` enthält den Benutzernamen `pi`; bei einem
anderen Benutzer anpassen.

Etwa 10 s nach dem Start kommt in der Konsole z. B.
„Orca-Lanes: 9 tools sent, 3 with spool“. Das Skript läuft wieder, sobald sich
eine Zuweisung ändert (`SET_TOOL_SPOOL`, Mainsail-Dialog). Nach Änderungen an
einer Spule in Spoolman selbst (z. B. Farbe korrigiert): `ORCA_LANES_SYNC`.
Log: `logs/orca_lanes.log`.

Kontrolle per SSH:

```bash
curl -s "http://localhost:7125/server/database/item?namespace=lane_data"
```

Eine Lane sieht so aus: `{"lane": "0", "material": "PLA", "spool_id": 11, "filament_id": "PSM11", "color": "#F9FDFF"}`.
Tools ohne Spule haben `"material": ""` und sind in Orca leer.

### 5.3 PC: Profile aus Spoolman erzeugen

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
4. **Abgleich:** Drucker wählen, Sync-Knopf → Filament 1–9 bekommen Profil und
   Farbe der Spulen auf T0–T8.

Aus Spoolman übernommen: Name, Hersteller, Farbe, Dichte, Durchmesser, Düsen-
und Betttemperatur (Abstand zur ersten Schicht bleibt wie in der Vorlage),
Preis pro kg. Was in Spoolman leer ist, bleibt wie in der Vorlage.
Material-Zuordnung: genaue Vorlage, sonst die längste passende
(`PLA+` → `SM-Vorlage PLA`).

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

### 5.4 Einstellungen pro Filament zentral in Spoolman

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
- `pressure_advance*` schreibt die Load-Cell-Kalibrierung (`PA_CAL_LOADCELL`)
  in Spoolman. Das Profil-Skript übernimmt den Wert nach Orca
  (`pressure_advance`, Düsenfeld hat Vorrang) und schaltet
  `enable_pressure_advance` ein. Orca setzt PA dann beim Filamentwechsel im G-Code.

Danach: Orca schließen, `orca_spoolman_profiles.ps1` ausführen, Orca starten.
