# Spoolman on the INDX Trident (T0–T8)

[Deutsche Version → SPOOLMAN.de.md](SPOOLMAN.de.md)

One Spoolman spool per INDX tool. The active spool follows the tool on the head,
so filament usage is booked to the right spool, and OrcaSlicer can pick up the
colour and profile of every tool.

## 0. Check first: is Spoolman already running?

If your `moonraker.conf` already contains

```ini
[spoolman]
server: http://<SPOOLMAN-IP>:7912
```

open `http://<SPOOLMAN-IP>:7912` in a browser.
- **The Spoolman UI shows up:** Spoolman already runs somewhere (NAS, Docker host, …). Skip step 1, continue with step 2.
- **No page:** install Spoolman on the Pi as described below.

## 1. Install on the Pi / CM4 (via SSH as `pi`)

**Recommended: standalone.** The CM4 has little RAM, and Docker adds an extra daemon and memory use. Standalone runs as a systemd service and can be updated through the Mainsail update manager. Docker is only worth it if Docker already runs on the Pi.

```bash
cd ~ && sudo apt-get update && sudo apt-get install -y curl jq unzip
```

```bash
mkdir -p ~/Spoolman && cd ~ && source_url=$(curl -s https://api.github.com/repos/Donkie/Spoolman/releases/latest | jq -r '.assets[] | select(.name == "spoolman.zip").browser_download_url') && curl -sSL "$source_url" -o temp.zip && unzip temp.zip -d ./Spoolman && rm temp.zip
```

```bash
cd ~/Spoolman && bash ./scripts/install.sh
```

The script asks for the port (default 7912) and whether to create a systemd service: **yes**. Then check:

```bash
systemctl status Spoolman
```

Web UI: `http://<pi-ip>:7912`. The database lives in `~/.local/share/spoolman` and survives updates.

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

## 2. `moonraker.conf` – only these sections

If Spoolman runs on the Pi itself:

```ini
[spoolman]
server: http://localhost:7912
sync_rate: 5
```

If Spoolman runs on another device, point `server:` to that address.

Optional, only for standalone on the Pi, for updates through Mainsail:

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

So that Moonraker may restart the service, `Spoolman` must be on its own line in `~/printer_data/moonraker.asvc`:

```bash
grep -qx Spoolman ~/printer_data/moonraker.asvc || echo Spoolman >> ~/printer_data/moonraker.asvc
```

```bash
sudo systemctl restart moonraker
```

The Spoolman panel then appears on the Mainsail dashboard.

## 3. Macros

| File | Purpose |
|---|---|
| `macros/spoolman.cfg` | Assignment, sync, restore on startup, `spool_id` on T0–T8 |
| `indx/indx_overrides.cfg` | `_INDX_SET_ACTIVE_TOOL` with one extra line `_SPOOL_SYNC` at the end |

`macros/spoolman.cfg` is loaded via `[include macros/*.cfg]`. `[save_variables]` (INDX's `indx_vars.cfg`) must exist. Then `FIRMWARE_RESTART`.

### How it works

- Each tool's spool ID is stored in `indx_vars.cfg` as `t0__spool_id` … `t8__spool_id`. The Mainsail Spoolman dialog saves under the same names as long as `[save_variables]` exists, so both use the same values.
- **Pickup T3:** `_INDX_SET_ACTIVE_TOOL TOOL=3` calls `_SPOOL_SYNC`, which runs `SET_ACTIVE_SPOOL ID=<spool of T3>`.
- **Park:** `TOOL=-1` leads to `CLEAR_ACTIVE_SPOOL`.
- **Startup:** `INIT_STATE` reports the tool on the head, its spool becomes active again.
- Moonraker books usage continuously to the active spool, including purges and `LOAD_FILAMENT`.

### Commands

```
SET_TOOL_SPOOL T=3 ID=12    assign spool 12 to T3
SET_TOOL_SPOOL T=3 ID=0     clear the assignment of T3
                            (UNLOAD_FILAMENT does this automatically for the active tool)
SHOW_TOOL_SPOOLS            show all assignments
```

**Mainsail dialog:** T0–T8 appear in the Spoolman panel under *Change Spool*. If you pick a spool there for the tool currently on the head, a watcher (`_SPOOL_WATCH`, every 3 s) switches within 3 s. For a parked tool the spool becomes active on the next pickup.

If a tool has no spool, a red message appears in the console on pickup. The print continues, but usage is not tracked.

## 4. Test

1. Create two spools in Spoolman, e.g. ID 1 and 2.
2. `SET_TOOL_SPOOL T=0 ID=1` and `SET_TOOL_SPOOL T=1 ID=2`, then `SHOW_TOOL_SPOOLS`.
3. `T0` → console reports "Spoolman: T0 -> spool 1", the Spoolman panel shows spool 1.
4. Heat, `G1 E50 F300` → after about 5 s the remaining weight of spool 1 drops.
5. `T1` → spool 2 active, extrude again, only spool 2 decreases.
6. `PARK_TOOL` → no active spool.
7. `FIRMWARE_RESTART` with T1 on the head → `SHOW_TOOL_SPOOLS` shows the assignments again, spool 2 is active.

## 5. OrcaSlicer: colours and profiles from Spoolman

Flow: per tool, the printer writes the spool's material, colour and filament ID into Moonraker's `lane_data`. OrcaSlicer reads it when syncing filaments and picks the matching profile for filament 1–9 (= T0–T8). The profiles are generated on the PC from the filaments in Spoolman by a PowerShell script.

### 5.1 Once in OrcaSlicer (2.5.x)

- Preferences: developer mode on, *Developer → "Use printer agents instead of print hosts"* on.
- Printer profile: *Advanced* view, **Printer Agent = Moonraker**, address `<PRINTER-IP>` (without port; "Device (Web)" then shows Mainsail).
- In `%APPDATA%\OrcaSlicer\OrcaSlicer.conf` under `local_machines` the printer must have `"printer_agent_id": "moonraker"` (Orca creates new entries with `"orca"`).
- The sync button only appears once `lane_data` contains at least one slot.

### 5.2 Printer: write the slots automatically

| File | Purpose |
|---|---|
| `scripts/orca_lanes/orca_lanes.py` | Fetches the spools via Moonraker's Spoolman proxy, writes `lane0`–`lane8` |
| `scripts/orca_lanes/orca_lanes_launch.sh` | Starts the script in the background (never blocks a print) |
| `macros/spoolman.cfg` | `[gcode_shell_command orca_lanes]`, `_ORCA_LANES`, `ORCA_LANES_SYNC`; the watcher calls `_ORCA_LANES` |

Requires `gcode_shell_command` (built into Kalico). After `FIRMWARE_RESTART`, about 10 s after startup the console shows "Orca-Lanes: 9 tools sent, … with spool". The script runs again whenever an assignment changes (`SET_TOOL_SPOOL`, Mainsail dialog). After changing a spool in Spoolman itself (e.g. corrected colour): `ORCA_LANES_SYNC`. Log: `logs/orca_lanes.log`.

Check via SSH:

```bash
curl -s "http://localhost:7125/server/database/item?namespace=lane_data"
```

A slot looks like `{"lane": "0", "material": "PLA", "spool_id": 11, "filament_id": "PSM11", "color": "#F9FDFF"}`. Tools without a spool have `"material": ""` and are empty in Orca.

### 5.3 PC: generate profiles from Spoolman

1. **Create templates (once):** in Orca, create a *standalone* filament per material (Filament → *Create filament*, not "copy" of a system profile), compatible with your printer, with your proven settings. Name: `SM-Vorlage PLA`, `SM-Vorlage PETG`, … (the default prefix is `SM-Vorlage`; to use another one, e.g. `SM-Template PLA`, add `-TemplatePrefix "SM-Template"` to every call). **No** `SET_ACTIVE_SPOOL` in the filament start G-code. Save, close Orca.
2. **Dry run** (only shows what would happen):
   ```powershell
   powershell -ExecutionPolicy Bypass -File .\orca_spoolman_profiles.ps1 -SpoolmanUrl http://<SPOOLMAN-IP>:7912 -WhatIf
   ```
3. **Write:**
   ```powershell
   powershell -ExecutionPolicy Bypass -File .\orca_spoolman_profiles.ps1 -SpoolmanUrl http://<SPOOLMAN-IP>:7912
   ```
   Then start Orca. The profiles are named `<Vendor> <Name> (SM<id>)` and have filament ID `PSM<id>`.
4. **Sync:** select the printer, press the sync button → filament 1–9 get the profile and colour of the spools on T0–T8.

Taken from Spoolman: name, vendor, colour, density, diameter, nozzle and bed temperature (the first-layer offset stays as in the template), price per kg. Anything empty in Spoolman stays as in the template. Material matching: exact template, otherwise the longest matching one (`PLA+` → `SM-Vorlage PLA`).

Run it again whenever new filaments are added or values change in Spoolman; unchanged profiles are left alone. `-Prune` deletes `SM` profiles whose filament no longer exists in Spoolman (or has no active spool). `-All` also creates filaments without an active spool.

**Notes**
- Orca matches the filament ID only against standalone profiles (without "inherits"). That is why spoolman2slicer is not used here: its profiles inherit from "Voron Generic …".
- Ignore the "Device" tab (Bambu view); keep controlling the printer through Mainsail.
- Usage is tracked independently of the slicer; Orca only has to emit `T0`…`T8`.

### 5.4 Per-filament settings stored in Spoolman

Base settings live in the Orca template (one per nozzle size). Per-filament deviations go into the filament's extra fields in Spoolman; the script applies them to the profiles on the next run. Do not edit the SM profiles in Orca, they are regenerated on every run.

| Extra field | Orca setting |
|---|---|
| `filament_flow_ratio` | Flow ratio |
| `filament_max_volumetric_speed` (+ `_d025`, `_d04`, `_d06`) | Max volumetric speed |
| `filament_retraction_length`, `filament_retraction_speed` | Retraction |
| `fan_min_speed`, `fan_max_speed` | Cooling fan |

- Empty = template value.
- Suffix `_d025`/`_d04`/`_d06`: only applies to that nozzle size and takes precedence there over the field without suffix.
- More settings: create a field in Spoolman (Settings → Extra fields → Filament) whose key matches the Orca setting exactly. Unknown keys are reported by the script as a warning.
- `pressure_advance*` is written to Spoolman by the load cell calibration (`PA_CAL_LOADCELL`). The profile script copies it to Orca (`pressure_advance`, the nozzle field takes precedence) and turns on `enable_pressure_advance`. Orca then sets PA on every filament change in the G-code.

Afterwards: close Orca, run `orca_spoolman_profiles.ps1`, start Orca.
