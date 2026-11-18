# OrcaSlicer

[Deutsche Version → ORCASLICER.de.md](ORCASLICER.de.md) ·
[README](../README.md)

Printer profile for this machine, and filament profiles and colours from
Spoolman (OrcaSlicer 2.5.x on Windows).

**Requires:** for the printer profile only OrcaSlicer. For sections 2–5 also
Spoolman set up as in [SPOOLMAN.md](SPOOLMAN.md) and spools assigned to the
tools.

## 1. Printer profile

`orca/Voron Trident 350 INDX.json` has machine limits matching the Klipper
config (300 mm/s, 3000 mm/s², square corner velocity 5), so slicer time
estimates are realistic. Import it in Orca (*File → Import → Import
Configs*) and adjust:

- Nozzles: T0–T4 0.4, T5–T6 0.6, T7–T8 0.25 – set yours.
- Tool change time and start time are rough guesses; time your own machine.
- *Before layer change G-code* contains `TIMELAPSE_TAKE_FRAME` for
  moonraker-timelapse. Without timelapse remove that line, otherwise Klipper
  reports an unknown command on every layer.

Two settings that avoid trouble with Klipper:
- **Jerk:** with Klipper flavour, Orca treats `machine_max_jerk_x/y` as
  `square_corner_velocity` and warns. Set *Default jerk* in the process
  profile to 0; Orca then sends no jerk commands and Klipper's value applies.
- **Pressure advance:** plain PA per filament, no *adaptive PA* (floods
  Klipper with `SET_PRESSURE_ADVANCE`).

**Check:** slicing a small object with two tools shows `T0`/`T1` in the
G-code preview, and the estimated time is plausible.

## How the filament sync works

```mermaid
flowchart LR
    SM[(Spoolman<br/>spools, filaments)] -->|spool per tool| K[Klipper / Moonraker<br/>t0__spool_id … t8__spool_id]
    K -->|orca_lanes.py writes<br/>lane0 … lane8| L[(Moonraker<br/>lane_data)]
    L -->|sync button| O[OrcaSlicer<br/>filament 1–9 = T0–T8]
    SM -->|orca_spoolman_profiles.ps1<br/>on the PC| P[Orca filament profiles<br/>one per Spoolman filament]
    P --> O
```

Per tool, the printer writes the spool's material, colour and filament ID
into Moonraker's `lane_data`. A *lane* is one entry per tool: `lane0` = T0 …
`lane8` = T8, e.g. `lane3` = "PETG, red, filament ID PSM12". OrcaSlicer reads
the lanes when syncing filaments and picks the matching profile for filament
1–9. The profiles are generated on the PC from the filaments in Spoolman by a
PowerShell script.

## 2. Once in OrcaSlicer

1. Preferences → tab *Developer*: tick **Developer mode** and **Use printer
   agents instead of print hosts** (screenshot: German UI).

   ![Orca preferences, Developer tab: tick both options](images/orca_developer_settings.png)

2. Edit your printer profile (*Printer settings → Basic information*),
   *Advanced* view: **Printer agent = Moonraker**. Enter `<PRINTER-IP>` as
   address, without port ("Device (Web)" then shows Mainsail).

   ![Orca printer settings: printer agent set to Moonraker](images/orca_printer_agent.png)
3. Orca creates the printer entry with `"printer_agent_id": "orca"`; it must
   be `"moonraker"`. This is the only manual file edit:
   1. **Close OrcaSlicer** (it rewrites the file on exit).
   2. **Back up** `%APPDATA%\OrcaSlicer\OrcaSlicer.conf` (copy it).
   3. Open it in a text editor and search for `printer_agent_id` (Ctrl+F).
      Take the entry of your printer under `local_machines` (it contains its
      name or IP) and change exactly this one line:
      ```
      before:  "printer_agent_id": "orca",
      after:   "printer_agent_id": "moonraker",
      ```
      Leave everything else as it is.
   4. Save and start Orca. If Orca does not start or loses settings, put the
      backup back.

The sync button only appears once `lane_data` contains at least one lane
(section 3).

## 3. Printer: lanes are written automatically

Nothing extra to install: `macros/spoolman.cfg` (see [SPOOLMAN.md](SPOOLMAN.md),
step 3) already contains this part, together with the scripts from this repo:

| File | Purpose |
|---|---|
| `scripts/orca_lanes/orca_lanes.py` | Fetches the spools via Moonraker's Spoolman proxy, writes `lane0`–`lane8` |
| `scripts/orca_lanes/orca_lanes_launch.sh` | Starts the script in the background (never blocks a print) |
| `macros/spoolman.cfg` | `[gcode_shell_command orca_lanes]`, `_ORCA_LANES`, `ORCA_LANES_SYNC`; `_SPOOL_WATCH` calls `_ORCA_LANES` |

Requires `gcode_shell_command` (built into Kalico) and the correct user name
in the path (see [INSTALLATION.md](INSTALLATION.md), step 7).

The script runs again whenever an assignment changes (`SET_TOOL_SPOOL`,
Mainsail dialog). After changing a spool in Spoolman itself (e.g. corrected
colour): `ORCA_LANES_SYNC`. Log: `~/printer_data/logs/orca_lanes.log`.

**Check:** about 10 s after startup the console shows e.g.
"Orca-Lanes: 9 tools sent, 3 with spool". Via SSH:

```bash
curl -s "http://localhost:7125/server/database/item?namespace=lane_data"
```

A lane looks like `{"lane": "0", "material": "PLA", "spool_id": 11, "filament_id": "PSM11", "color": "#F9FDFF"}`.
Tools without a spool have `"material": ""` and are empty in Orca.

## 4. PC: generate profiles from Spoolman

The script is `orca/orca_spoolman_profiles.ps1` in this repo. It runs with
the Windows PowerShell 5.1 that ships with Windows 10/11 (no install needed)
and only needs network access to Spoolman. Copy it anywhere on the PC.
Spoolman's address is passed with `-SpoolmanUrl`; to avoid typing it every
time, change the default in the `param(...)` block at the top of the script
(`http://spoolman.local:7912`).

1. **Create templates (once):** in Orca, create a *standalone* filament per
   material (Filament → *Create filament*, not "copy" of a system profile),
   compatible with your printer, with your proven settings. Name:
   `SM-Vorlage PLA`, `SM-Vorlage PETG`, … (the default prefix is
   `SM-Vorlage`; to use another one, e.g. `SM-Template PLA`, add
   `-TemplatePrefix "SM-Template"` to every call). **No** `SET_ACTIVE_SPOOL`
   in the filament start G-code. Save, **close Orca**.
2. **Dry run** (only shows what would happen):
   ```powershell
   powershell -ExecutionPolicy Bypass -File .\orca_spoolman_profiles.ps1 -SpoolmanUrl http://<SPOOLMAN-IP>:7912 -WhatIf
   ```
3. **Write** (Orca must be closed; the script refuses to run otherwise):
   ```powershell
   powershell -ExecutionPolicy Bypass -File .\orca_spoolman_profiles.ps1 -SpoolmanUrl http://<SPOOLMAN-IP>:7912
   ```
   Then start Orca. The profiles are named `<Vendor> <Name> (SM<id>)` and
   have filament ID `PSM<id>`.
4. **Sync:** select the printer, press the sync button in the *Filament*
   area (right of the heading). Orca counts from 1: filament 1 = T0 …
   filament 9 = T8.

   ![Orca: Filament area with the sync button marked](images/orca_filament_sync.png)

**Check:** filament 1–9 get the profile and colour of the spools on T0–T8.

Taken from Spoolman: name, vendor, colour, density, diameter, nozzle and bed
temperature (the first-layer offset stays as in the template), price per kg.
Anything empty in Spoolman stays as in the template. Material matching: exact
template, otherwise the longest matching one (`PLA+` → `SM-Vorlage PLA`).

Run it again whenever new filaments are added or values change in Spoolman;
unchanged profiles are left alone. `-Prune` deletes `SM` profiles whose
filament no longer exists in Spoolman (or has no active spool). `-All` also
creates filaments without an active spool.

**Notes**
- Orca matches the filament ID only against standalone profiles (without
  "inherits"). That is why spoolman2slicer is not used here: its profiles
  inherit from "Voron Generic …".
- Ignore the "Device" tab (Bambu view); keep controlling the printer through Mainsail.
- Usage is tracked independently of the slicer; Orca only has to emit `T0`…`T8`.

## 5. Per-filament settings stored in Spoolman

Base settings live in the Orca template (one per nozzle size). Per-filament
deviations go into the filament's extra fields in Spoolman; the script
applies them to the profiles on the next run. Do not edit the SM profiles in
Orca, they are regenerated on every run.

| Extra field | Orca setting |
|---|---|
| `filament_flow_ratio` | Flow ratio |
| `filament_max_volumetric_speed` (+ `_d025`, `_d04`, `_d06`) | Max volumetric speed |
| `filament_retraction_length`, `filament_retraction_speed` | Retraction |
| `fan_min_speed`, `fan_max_speed` | Cooling fan |
| `filament_shrink`, `filament_shrinkage_compensation_z` | Shrinkage (XY), Shrinkage (Z), in % (e.g. `99.5`; 100 = no compensation) |

- Empty = template value.
- Suffix `_d025`/`_d04`/`_d06`: only applies to that nozzle size and takes
  precedence there over the field without suffix.
- More settings: create a field in Spoolman (Settings → Extra fields →
  Filament) whose key matches the Orca setting exactly. Unknown keys are
  reported by the script as a warning.
- `pressure_advance*` is written to Spoolman by the load cell calibration
  (`PA_CAL_LOADCELL`, see [CALIBRATION.md](CALIBRATION.md), step 8). The
  profile script copies it to Orca (`pressure_advance`, the nozzle field takes
  precedence) and turns on `enable_pressure_advance`. Orca then sets PA on
  every filament change in the G-code.

Afterwards: close Orca, run `orca_spoolman_profiles.ps1`, start Orca.

Problems: see [TROUBLESHOOTING.md](TROUBLESHOOTING.md#spoolman-and-orcaslicer).
