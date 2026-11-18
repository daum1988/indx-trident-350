# Troubleshooting

[Deutsche Version → TROUBLESHOOTING.de.md](TROUBLESHOOTING.de.md) ·
[README](../README.md)

Typical problems with this repo's additions, their cause and the fix.
Problems of the INDX itself (load cell, docks, thermal model, `CAL_Z`):
see [BondtechAB/INDX](https://github.com/BondtechAB/INDX) and the
[Kalico INDX docs](https://docs.kalico.gg/INDX.html). Logs on the Pi:
`~/printer_data/logs/` (`klippy.log`, `moonraker.log`, `KlipperScreen.log`,
`orca_lanes.log`, `spool_picker.log`); in Mainsail under *Machine*.

## Klipper start and config

| Symptom | Cause | Fix |
|---|---|---|
| `Include file '.../indx/indx.cfg' does not exist` | Bondtech's INDX files missing | this repo needs a working Bondtech INDX installation ([INSTALLATION.md](INSTALLATION.md#who-is-this-for)) |
| Error in `autotune_tmc.cfg` or `shaketune.cfg` | module not installed | install it or delete the file ([INSTALLATION.md](INSTALLATION.md), step 6) |
| `Unknown command:"PARK_TOOL"` (or `CHANGE_TOOL`, `CAL_...`) | Bondtech file not included | check the includes ([INSTALLATION.md](INSTALLATION.md), step 4) |
| Spoolman hook or Z hop has no effect | `indx_overrides.cfg` included before `homing.cfg` | include it last ([INSTALLATION.md](INSTALLATION.md), step 4) |
| `mcu ... Unable to connect` | wrong serial ID | `ls /dev/serial/by-id/` ([INSTALLATION.md](INSTALLATION.md), step 5) |
| Calibration values gone after copying | `SAVE_CONFIG` block overwritten | copy it back from the backup ([INSTALLATION.md](INSTALLATION.md), step 4) |

## Tool change

| Symptom | Cause | Fix |
|---|---|---|
| Tool change stops with *Remote method ... not registered* | `macros/spoolman.cfg` present, but no `[spoolman]` in Moonraker | set up Spoolman, or delete `spoolman.cfg` and set `variable_use_spoolman: 0` ([INSTALLATION.md](INSTALLATION.md), step 6) |
| Global Z offset lost at the next print | babystep not saved | `SYNC_GLOBAL_Z` after babystepping ([CALIBRATION.md](CALIBRATION.md#6-z-tool-offsets)) |

## Calibration

| Symptom | Cause | Fix |
|---|---|---|
| `Sample rate is not high enough` during the mesh | scan too fast | lower `speed` in `[bed_mesh]` or `SCAN_SPEED=` |
| Mesh with a hot nozzle looks wrong | induction heater disturbs the scanner | scan with a cold nozzle |
| `PA_CAL_LOADCELL` gives no value, no message | wrong `/home/pi` path | [INSTALLATION.md](INSTALLATION.md), step 7; log `~/printer_data/config/lc_pa_data/last_run.log` |
| PA value shown but not saved | measurement uncertain | check with `LC_EXTRUDE_TEST`, filament loaded, nozzle hot, measure again |

## Spoolman and OrcaSlicer

| Symptom | Cause | Fix |
|---|---|---|
| Spoolman runs, but the load dialog shows no spools | script path wrong, Moonraker cannot reach Spoolman (`server:`), or all spools archived | `~/printer_data/logs/spool_picker.log`; [INSTALLATION.md](INSTALLATION.md), step 7; `server:` in `[spoolman]`; archived spools are not listed |
| Load dialog only shows materials, no spools | `variable_use_spoolman: 0`, or an old `filament_menu.cfg` | set it to `1` / copy the file from the repo again |
| Active spool does not change on tool change | no spool assigned, or override not loaded | `SHOW_TOOL_SPOOLS`; include order ([SPOOLMAN.md](SPOOLMAN.md), step 3) |
| Red message on pickup, usage not booked | tool has no spool | `SET_TOOL_SPOOL T=n ID=x` or the Mainsail dialog |
| `lane_data` stays empty | script path wrong or script fails | `~/printer_data/logs/orca_lanes.log`; `ORCA_LANES_SYNC` |
| Colour in Orca is outdated | spool changed in Spoolman itself | `ORCA_LANES_SYNC`, then sync in Orca |
| Timelapse has no frames or no video | `TIMELAPSE_TAKE_FRAME` missing from the G-code: not in the printer profile, or Orca (logged in to an account) uses the profiles in `%APPDATA%\OrcaSlicer\user\<account-id>\` instead of `user\default\` | add `TIMELAPSE_TAKE_FRAME` under *Machine G-code → Before layer change* in the active printer profile ([ORCASLICER.md](ORCASLICER.md), section 1), slice again; check: the line appears in the G-code |
| Orca shows no sync button | `printer_agent_id` not `moonraker`, or `lane_data` empty | [ORCASLICER.md](ORCASLICER.md), sections 2 and 3 |
| Sync leaves a filament empty or generic | no matching profile `PSM<id>` | run the profile script again; profiles must be standalone |
| Profile script writes nothing | Orca open, no template `SM-Vorlage <material>`, or filament without active spool | close Orca; check templates; `-WhatIf` shows the plan; `-All` for filaments without spool |
| Shrinkage/flow etc. not applied | extra field empty or key wrong | field key must match the Orca setting exactly; script warns about unknown keys |

## KlipperScreen and dialog

| Symptom | Cause | Fix |
|---|---|---|
| No *INDX* menu entry, no tool in the titlebar | add-on not loaded | `enable_addons: True`, link in `~/KlipperScreen/addons/`, restart; `KlipperScreen.log` |
| Titlebar entry missing, menu present | `spool` missing in `titlebar_items`, or wrong `[printer ...]` section | [KLIPPERSCREEN.md](KLIPPERSCREEN.md), step 3 |
| *Loaded*/*Empty* wrong | loaded or unloaded by hand | `SET_TOOL_LOADED T=n LOADED=0/1` |
| *Load* on KlipperScreen loads without asking | `LOAD_FILAMENT` override not loaded | `indx_overrides.cfg` and `filament_menu.cfg` included? |

## Nozzle camera

| Symptom | Cause | Fix |
|---|---|---|
| Page is downloaded instead of shown | opened via `/server/files/...` | copy to `~/mainsail/`, open `http://<PRINTER-IP>/nozzle_cam.html` |
| Page gone after a Mainsail update | not in `persistent_files` | [CALIBRATION.md](CALIBRATION.md#5-xy-tool-offsets-nozzle-camera) |
| No image | wrong stream path | default `/webcam2/?action=stream`; check the crowsnest camera |
| Buttons do nothing (page opened as a file) | Moonraker rejects `file://` | open it from the printer address |

## Boot logo

See [bootlogo/README.md](../bootlogo/README.md): check before installing,
undo, rotated logo.
