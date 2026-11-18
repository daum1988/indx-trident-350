# KlipperScreen und der Lade-/Entlade-Dialog

[English version → KLIPPERSCREEN.md](KLIPPERSCREEN.md) ·
[README](../README.de.md)

KlipperScreen sieht nur einen `[extruder]` und zeigt daher keine
T0–T8-Knöpfe; seine Laden/Entladen-Knöpfe senden ein nacktes `LOAD_FILAMENT` /
`UNLOAD_FILAMENT`. Dieses Repo ergänzt zwei Teile:

| Teil | Datei | Braucht |
|---|---|---|
| Lade-/Entlade-Dialog | `macros/filament_menu.cfg` | nur die Grundinstallation; funktioniert in KlipperScreen **und** Mainsail |
| KlipperScreen-Add-on | `klipperscreen/indx_addon.py` | KlipperScreen mit Add-on-Unterstützung (`enable_addons`), geschrieben für v0.4.7-215 |

## Lade-/Entlade-Dialog

Ein *Macro-Prompt* ist ein Dialog, den ein Makro in Mainsail und KlipperScreen
öffnet. Die Knöpfe darin sind englisch beschriftet.

- **`LOAD_FILAMENT` ohne Parameter** (auch KlipperScreens Knopf *Laden*):
  1. Tool wählen (das aktive Tool ist hervorgehoben),
  2. mit Spoolman: Material wählen, dann die Spule. Die Liste ist nach
     Hersteller und Name sortiert und scrollbar; Spulen, die schon in einem
     anderen Tool stecken, sind markiert. Die Spule wird dem Tool zugeordnet
     und ihre Düsentemperatur verwendet. Der Knopf *Without spool* („ohne
     Spule“) zeigt stattdessen die Material-Presets,
  3. ohne Spoolman (`variable_use_spoolman: 0`): Material-Preset wählen.

  Das Tool wird aufgenommen, über dem Bucket aufgeheizt und geladen.
- **`UNLOAD_FILAMENT` ohne Parameter:** Tool wählen; es wird entladen und
  seine Spulenzuordnung gelöscht.
- Mit Parametern laufen die Makros direkt, z. B.
  `LOAD_FILAMENT TOOL=3 TYPE=PETG` oder `UNLOAD_FILAMENT TOOL=3`.

Die Spulenliste kommt von `scripts/spool_picker/spool_picker.py` über
Moonrakers Spoolman-Proxy. Ist Spoolman nicht erreichbar, zeigt der Dialog
die Material-Presets.

**Kontrolle:** `LOAD_FILAMENT` in die Mainsail-Konsole tippen: Der Tool-Dialog
öffnet sich. *Cancel* („Abbrechen“) schließt ihn, ohne etwas zu tun.

## KlipperScreen-Add-on

- **Titelleiste:** das aktive Tool („T3“) mit der Farbe seiner Spule. Antippen
  öffnet das INDX-Panel.
- **INDX-Panel** (Hauptmenü → *INDX*): ein Knopf pro Tool mit Spulenfarbe und
  -name, *Loaded* / *Empty* (geladen / leer), das aktive Tool hervorgehoben.
  Ein Tool antippen nimmt es auf. Darunter *Park*, *Load*, *Unload* (Parken,
  Laden, Entladen; Laden und Entladen öffnen den Dialog oben). Das Panel gibt
  es nur im Hauptmenü, nicht während eines Drucks.

Den Ladezustand (`t<n>__loaded`) setzen `LOAD_FILAMENT` / `UNLOAD_FILAMENT`.
Nach Laden oder Entladen von Hand mit `SET_TOOL_LOADED T=<n> LOADED=<0|1>`
korrigieren.

### Installation

1. Das Add-on in den Config-Ordner kopieren (aus dem Klon, siehe
   [INSTALLATION.de.md](INSTALLATION.de.md), Schritt 2):
   ```bash
   mkdir -p ~/printer_data/config/klipperscreen && cp ~/indx-trident-350/klipperscreen/indx_addon.py ~/printer_data/config/klipperscreen/
   ```
2. In den Add-on-Ordner von KlipperScreen verlinken (wird von KlipperScreens
   Git ignoriert, Updates funktionieren also weiter):
   ```bash
   mkdir -p ~/KlipperScreen/addons && ln -sf ~/printer_data/config/klipperscreen/indx_addon.py ~/KlipperScreen/addons/indx.py
   ```
3. `klipperscreen/KlipperScreen.example.conf` in
   `~/printer_data/config/KlipperScreen.conf` übernehmen, oberhalb des
   automatisch erzeugten Blocks: `enable_addons: True` in `[main]`, den
   Eintrag `[menu __main indx]` und `spool` in `titlebar_items`. Das Beispiel
   nutzt den Abschnitt `[printer INDX-Trident]`; den Namen des eigenen
   `[printer ...]`-Abschnitts verwenden.
4. KlipperScreen neu starten:
   ```bash
   sudo systemctl restart KlipperScreen
   ```

**Kontrolle:** Die Titelleiste zeigt „T“ und das aktive Tool, das Hauptmenü
hat einen Eintrag *INDX*. `grep -i indx ~/printer_data/logs/KlipperScreen.log`
zeigt „INDX add-on: installed“.

**Updates:** Das Add-on im Config-Ordner ist eine Kopie. Nach `git pull` im
Klon erneut kopieren (Schritt 1) und KlipperScreen neu starten. Der Link aus
Schritt 2 bleibt.

Probleme: siehe [TROUBLESHOOTING.de.md](TROUBLESHOOTING.de.md#klipperscreen-und-dialog).
