# INDX Trident 350

Kalico/Klipper configuration, macros and tools for a **Voron Trident 350** with a
**Bondtech INDX** 9-tool changer (T0–T8).

[Deutsche Version → README.de.md](README.de.md)

> This is a personal machine config shared as a reference. It is **not** a
> drop-in config: pins, serial IDs, positions and all calibration values must
> be checked and measured on your own printer. Use at your own risk.

## Hardware / software

| | |
|---|---|
| Printer | Voron Trident 350 |
| Tool changer | Bondtech INDX, 9 tools, docks at the front |
| Mainboard | BTT Manta M8P v2.0 + Raspberry Pi CM4 |
| Z probing | INDX load cell (default probe) |
| Bed mesh | Eddy current scanner (`[probe_eddy_current scanner]`, rapid scan) |
| Firmware | [Kalico](https://docs.kalico.gg/INDX.html) |
| UI | Mainsail, KlipperScreen |
| Slicer | OrcaSlicer 2.5.x |
| Filament management | Spoolman (one spool per tool) |

## What is in here

```
klipper/
  printer.cfg                 includes, SAVE_CONFIG block removed
  config/                     M8P board config, INDX toolhead, bed mesh, TMC autotune
  indx/indx_overrides.cfg     overrides on top of the stock Bondtech INDX macros
  macros/                     START_PRINT/END_PRINT, Spoolman, load-cell PA calibration, ...
  scripts/lc_pa/              host script for the load-cell PA calibration
  scripts/orca_lanes/         writes the tool->spool mapping to Moonraker for OrcaSlicer
  scripts/spool_picker/       Spoolman spool list for the load dialog
moonraker/moonraker.example.conf   the moonraker.conf sections this repo needs
orca/                         OrcaSlicer printer profile + Spoolman -> Orca filament profile script
bootlogo/                     Plymouth boot logo for the CM4 display
klipperscreen/                KlipperScreen add-on: INDX panel and active tool in the titlebar
tools/nozzle_cam.html         browser page for checking tool XY offsets with a nozzle camera
docs/SPOOLMAN.md              Spoolman setup guide (German: SPOOLMAN.de.md)
```

**Not included:** the stock Bondtech INDX files (`indx/indx.cfg`,
`indx-tc-macros.cfg`, `indx-cal.cfg`, `homing.cfg`) – get them from
[BondtechAB/INDX](https://github.com/BondtechAB/INDX) and configure `indx.cfg`
for your machine. Also not included: `mainsail.cfg`, `timelapse.cfg`,
`indx_vars.cfg` (per-machine tool offsets) and anything with network
addresses or API keys.

## Highlights

### Pressure advance with the INDX load cell
`PA_CAL_LOADCELL` measures pressure advance per tool without printing. The tool
extrudes into the purge bucket in speed steps while the load cell records the
nozzle pressure; the pressure time constant is fitted and is the PA value.

```
PA_CAL_LOADCELL TOOL=0 TEMP=230
PA_CAL_LOADCELL TOOLS=0,3,5 TEMP=230
PA_CAL_LOADCELL TOOLS=ALL TEMP=230
SET_TOOL_NOZZLE TOOL=3 D=0.6     # once per tool, after a nozzle change
LC_PA_SHOW / LC_PA_APPLY
```

Results are stored per tool in `save_variables` and, if a spool is assigned,
in the Spoolman filament (extra fields `pressure_advance_d025/_d04/_d06`, one per
nozzle size). Needs `gcode_shell_command` (built into Kalico) and
`scripts/lc_pa/` in the config folder. `LC_EXTRUDE_TEST` is a quick check that
your load cell sees the extrusion force at all.

### KlipperScreen: tool selection and load/unload
KlipperScreen only sees one `[extruder]`, so it shows no T0–T8 buttons, and its
Load/Unload buttons send a bare `LOAD_FILAMENT` / `UNLOAD_FILAMENT`.
The add-on `klipperscreen/indx_addon.py` adds an *INDX* panel (every tool with its
spool colour and name, loaded/empty, active tool highlighted; park, load, unload)
and shows the active tool with its spool colour in the titlebar. Install: copy it to
`~/printer_data/config/klipperscreen/`, then
`mkdir -p ~/KlipperScreen/addons && ln -sf ~/printer_data/config/klipperscreen/indx_addon.py ~/KlipperScreen/addons/indx.py`
and merge `klipperscreen/KlipperScreen.example.conf`. LOAD/UNLOAD_FILAMENT keep
`t<n>__loaded` up to date; `SET_TOOL_LOADED T=<n> LOADED=<0|1>` corrects it. A bare `LOAD_FILAMENT` or `UNLOAD_FILAMENT` opens a dialog
(`macros/filament_menu.cfg`, macro prompt) to pick the tool and, for loading, the
spool from Spoolman (material first, then spool; `scripts/spool_picker/`). The chosen
spool is assigned to the tool and its nozzle temperature is used. *Without spool*
falls back to the material presets. The dialog also appears in Mainsail.

### Spoolman, one spool per tool
`SET_TOOL_SPOOL T=3 ID=12` assigns a spool to a tool (same variables the
Mainsail Spoolman dialog uses). On every tool change the active spool in
Moonraker follows the tool, so usage is booked to the right spool.
`orca_lanes.py` publishes the tool → filament mapping as Moonraker
`lane_data`, so OrcaSlicer (printer agent *Moonraker*) can sync colours and
profiles. `orca/orca_spoolman_profiles.ps1` creates matching Orca filament
profiles from Spoolman on Windows. Full guide: [docs/SPOOLMAN.md](docs/SPOOLMAN.md).

### INDX overrides
`indx/indx_overrides.cfg` must be included **after** `indx/homing.cfg`. It adds
a safe Z hop when the bed is at the bottom, stores measured filament values
from `INDX_LOAD_FILAMENT` per tool, a nozzle-camera XY check (`CAL_VERIFY_XY`)
and the Spoolman hook on tool changes, without editing Bondtech's files.

### OrcaSlicer printer profile
`orca/Voron Trident 350 INDX.json` has machine limits matching the Klipper
config (300 mm/s, 3000 mm/s², square corner velocity 5), so slicer time
estimates are realistic. Nozzles: T0–T4 0.4, T5–T6 0.6, T7–T8 0.25 – adjust
to yours. Tool change time and start time in the profile are rough guesses;
time your own machine.

## Setup

1. Install Kalico and the Bondtech INDX module/configs per Bondtech's docs.
2. Copy `klipper/` into `~/printer_data/config/`.
3. Replace the serial IDs (`ls /dev/serial/by-id/`) and check every pin against
   your wiring.
4. Merge `moonraker/moonraker.example.conf` into your `moonraker.conf`.
5. Run all calibrations yourself and `SAVE_CONFIG`: bed PID, input shaper,
   INDX thermal model, load cell, eddy scanner, tool offsets.

## Lessons learned

- **Global Z offset is lost after a restart / print start?** Babystepping only
  changes the live offset. `START_PRINT` homes Z, which re-applies the *saved*
  global offset. Run `SYNC_GLOBAL_Z` after babystepping to save it, check with
  `CAL_CHECK_OFFSETS`. After a restart the live value shows 0 until `G28` or a
  T0 pickup – that is normal.
- **Different build plates (smooth/textured)** need no Z offset per plate: Z is
  homed with the load cell on the actual plate surface.
- **OrcaSlicer jerk warning:** with Klipper flavour, Orca treats
  `machine_max_jerk_x/y` as `square_corner_velocity`. Set *Default jerk* in the
  process profile to 0 so Orca sends no jerk commands and Klipper's value is used.
- **Pressure advance:** set plain PA per filament in Orca, avoid Orca's
  *adaptive PA* (floods Klipper with `SET_PRESSURE_ADVANCE`).
- **Part cooling fan swap (4010 blowers ↔ CPAP):** the INDX thermal model
  values `model_part_cooling_fan_a/k` depend on the fan and its `max_power`.
  Re-measure after changing fan hardware; old values may not fit anymore.
- **Fan power:** use `min_power` instead of the deprecated `off_below`.
- **Boot logo rotated by 90°:** rotate the PNG, not the Plymouth image.

## Credits

- [Bondtech INDX](https://github.com/BondtechAB/INDX) – tool changer and stock macros
- [Kalico](https://github.com/KalicoCrew/kalico), [Klipper](https://github.com/Klipper3d/klipper)
- [Spoolman](https://github.com/Donkie/Spoolman), [OrcaSlicer](https://github.com/SoftFever/OrcaSlicer)
- [klipper_tmc_autotune](https://github.com/andrewmcgr/klipper_tmc_autotune),
  [Shake&Tune](https://github.com/Frix-x/klippain-shaketune)
- Adaptive purge / print start ideas: see links in `macros/trident_macros.cfg`

## License

[GPL-3.0](LICENSE), like Klipper and Kalico. Parts derived from third-party
macros keep their original authors' terms.
