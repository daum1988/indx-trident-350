# INDX Trident 350

Kalico/Klipper configuration, macros and tools for a **Voron Trident 350** with a
**Bondtech INDX** 9-tool changer (T0–T8).

[Deutsche Version → README.de.md](README.de.md)

CAD files of the printer (INDX conversion of the Trident):
[daum1988/Voron-Trident-INDX](https://github.com/daum1988/Voron-Trident-INDX)

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

## Features

- **Pressure advance with the load cell:** `PA_CAL_LOADCELL` measures PA per
  tool without a test print.
- **Load/unload dialog:** `LOAD_FILAMENT` asks for tool, material and spool,
  in Mainsail and KlipperScreen.
- **Spoolman, one spool per tool:** the active spool follows the tool, usage
  is booked to the right spool.
- **OrcaSlicer:** printer profile; filament profiles and colours per tool from
  Spoolman.
- **KlipperScreen add-on:** INDX panel with all tools and their spools, active
  tool in the titlebar.
- **Nozzle camera page** for the XY tool offsets, plus `CAL_VERIFY_XY` to
  cross-check them.
- **INDX overrides** (`indx/indx_overrides.cfg`): safe Z hop, per-tool
  filament values, Spoolman hook, without editing Bondtech's files.

## Documentation

Work through them in this order:

| Guide | Contents | Required? |
|---|---|---|
| [Installation](docs/INSTALLATION.md) | prerequisites, copying, adapting, first start, updates | **yes** |
| [Calibration](docs/CALIBRATION.md) | load cell, thermal model, docks, scanner, XY/Z offsets, input shaper, PA | **yes** |
| [Spoolman](docs/SPOOLMAN.md) | one spool per tool, usage tracking | optional |
| [OrcaSlicer](docs/ORCASLICER.md) | printer profile, filament profiles from Spoolman | optional |
| [KlipperScreen](docs/KLIPPERSCREEN.md) | load/unload dialog, INDX add-on | dialog: part of the base; add-on optional |
| [Boot logo](bootlogo/README.md) | Plymouth logo on the display | optional |
| [Troubleshooting](docs/TROUBLESHOOTING.md) | symptoms, causes, fixes | – |

## What is in here

```
klipper/                      content goes into ~/printer_data/config/
  printer.cfg                 includes, SAVE_CONFIG block removed
  config/                     M8P board config, INDX toolhead, bed mesh, TMC autotune
  indx/indx_overrides.cfg     overrides on top of the stock Bondtech INDX macros
  macros/                     START_PRINT/END_PRINT, Spoolman, load dialog, load-cell PA calibration, ...
  scripts/lc_pa/              host script for the load-cell PA calibration
  scripts/orca_lanes/         writes the tool->spool mapping to Moonraker for OrcaSlicer
  scripts/spool_picker/       Spoolman spool list for the load dialog
moonraker/moonraker.example.conf   the moonraker.conf sections this repo needs
orca/                         OrcaSlicer printer profile + Spoolman -> Orca filament profile script
bootlogo/                     Plymouth boot logo for the CM4 display
klipperscreen/                KlipperScreen add-on and example config
tools/nozzle_cam.html         browser page for the XY tool offsets with a nozzle camera
docs/                         the guides above (German: *.de.md)
```

**Not included:**
- the stock Bondtech INDX files `indx/indx.cfg`, `indx/indx-tc-macros.cfg`,
  `indx/indx-cal.cfg`, `indx/homing.cfg` – get them from
  [BondtechAB/INDX](https://github.com/BondtechAB/INDX). `printer.cfg`
  includes them; without them Klipper does not start. Several commands used
  here come from these files, e.g. `PARK_TOOL`, `CHANGE_TOOL` and the startup
  `INIT_STATE` (`indx-tc-macros.cfg`), `TOOL_POSITIONS` (`indx.cfg`), the
  `CAL_...` calibration macros, `SYNC_GLOBAL_Z` and `CAL_CHECK_OFFSETS`
  (`indx-cal.cfg`). `INDX_LOAD_FILAMENT` is a command of Kalico's INDX module;
- `mainsail.cfg` (from [mainsail-config](https://github.com/mainsail-crew/mainsail-config),
  already present on MainsailOS) and `timelapse.cfg` (installed by
  [moonraker-timelapse](https://github.com/mainsail-crew/moonraker-timelapse));
- `indx_vars.cfg` (per-machine tool offsets, created by INDX) and anything with
  network addresses or API keys.

## Terms

| Term | Meaning |
|---|---|
| Tool | one of the nine INDX print heads (T0–T8), each with its own nozzle and extruder |
| Dock | the holder a tool is parked in |
| Pickup / park | the head takes a tool out of its dock / puts it back |
| Latch | the lock that holds a tool on the head; driven by the extruder motor |
| Load cell | force sensor in the INDX head; Z probe (the nozzle touches the bed) and used for the PA calibration |
| Thermal model | Kalico's calculation of how the induction-heated nozzle behaves; protects against overheating and must be calibrated |
| Purge bucket | where the tool purges filament before printing and during loading |
| Includes | `[include ...]` lines in `printer.cfg` that load the other config files |
| `SAVE_CONFIG` | writes calibration results into the block at the end of `printer.cfg` and restarts Klipper |
| `indx_vars.cfg` | file of `[save_variables]`: active tool, tool offsets, PA, spool per tool; written immediately, no `SAVE_CONFIG` |
| Macro prompt | a dialog a macro opens in Mainsail and KlipperScreen (e.g. the load dialog) |
| Lane | one entry per tool in Moonraker's `lane_data` (`lane0` = T0); OrcaSlicer reads filament and colour from it |

## Lessons learned

- **Global Z offset lost at the next print?** Babystepping only changes the
  live offset; save it with `SYNC_GLOBAL_Z`
  ([Calibration, step 7](docs/CALIBRATION.md#7-z-tool-offsets)).
- **Different build plates** need no Z offset per plate: Z is homed with the
  load cell on the actual plate surface.
- **Part cooling fan swap (4010 blowers ↔ CPAP):** re-measure the thermal
  model, old `model_part_cooling_fan_a/k` values may not fit anymore.
- **Fan power:** use `min_power` instead of the deprecated `off_below`.
- **OrcaSlicer:** *Default jerk* 0, no adaptive PA
  ([OrcaSlicer, section 1](docs/ORCASLICER.md#1-printer-profile)).
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
