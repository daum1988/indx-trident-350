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

## What is in here

```
klipper/                      content goes into ~/printer_data/config/
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

**Not included:**
- the stock Bondtech INDX files `indx/indx.cfg`, `indx/indx-tc-macros.cfg`,
  `indx/indx-cal.cfg`, `indx/homing.cfg` – get them from
  [BondtechAB/INDX](https://github.com/BondtechAB/INDX) and configure
  `indx.cfg` for your machine. `printer.cfg` includes them; without them
  Klipper does not start. Several commands used here come from these files,
  e.g. `PARK_TOOL`, `CHANGE_TOOL` and the startup `INIT_STATE`
  (`indx-tc-macros.cfg`), `TOOL_POSITIONS` (`indx.cfg`), `SYNC_GLOBAL_Z`,
  `CAL_CHECK_OFFSETS`, `CAL_ONE_SET_CAMERA_REF`, `CAL_TWO_PREP_TOOL_CAL` and
  `CAL_THREE_SAVE_XY_OFFSET` (`indx-cal.cfg`). `INDX_LOAD_FILAMENT` is a
  command of Kalico's INDX module;
- `mainsail.cfg` (from [mainsail-config](https://github.com/mainsail-crew/mainsail-config),
  already present on MainsailOS) and `timelapse.cfg` (installed by
  [moonraker-timelapse](https://github.com/mainsail-crew/moonraker-timelapse)).
  `printer.cfg` includes both; comment the lines out if you do not use them;
- `indx_vars.cfg` (per-machine tool offsets, created by INDX) and anything with
  network addresses or API keys.

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

### KlipperScreen: INDX panel, tool selection and load/unload
KlipperScreen only sees one `[extruder]`, so it shows no T0–T8 buttons, and its
Load/Unload buttons send a bare `LOAD_FILAMENT` / `UNLOAD_FILAMENT`. This repo
adds:

- **Load/unload dialog** (`macros/filament_menu.cfg`, macro prompt, also shown
  in Mainsail): a bare `LOAD_FILAMENT` asks for the tool, the material and the
  spool from Spoolman (`scripts/spool_picker/`, scrollable list sorted by
  vendor and name). The spool is assigned to the tool and its nozzle
  temperature is used; *Without spool* falls back to the material presets.
  A bare `UNLOAD_FILAMENT` asks for the tool.
- **KlipperScreen add-on** `klipperscreen/indx_addon.py`: an *INDX* panel with
  every tool (spool colour and name, loaded/empty, active tool highlighted;
  park, load, unload) and the active tool with its spool colour in the
  titlebar. `LOAD_FILAMENT` / `UNLOAD_FILAMENT` keep the loaded state
  (`t<n>__loaded`) up to date; `SET_TOOL_LOADED T=<n> LOADED=<0|1>` corrects it.

Installing the add-on (needs a KlipperScreen version with add-on support,
setting `enable_addons`):

1. Copy the add-on into the config folder (from the clone, see Setup step 2):
   ```bash
   mkdir -p ~/printer_data/config/klipperscreen && cp ~/indx-trident-350/klipperscreen/indx_addon.py ~/printer_data/config/klipperscreen/
   ```
2. Via SSH, link it into KlipperScreen's add-on folder (ignored by
   KlipperScreen's git, so updates keep working):
   ```bash
   mkdir -p ~/KlipperScreen/addons && ln -sf ~/printer_data/config/klipperscreen/indx_addon.py ~/KlipperScreen/addons/indx.py
   ```
3. Merge `klipperscreen/KlipperScreen.example.conf` into your
   `KlipperScreen.conf` (`enable_addons: True`, the INDX menu entry, `spool` in
   the titlebar).
4. Restart KlipperScreen.

### Spoolman, one spool per tool
`SET_TOOL_SPOOL T=3 ID=12` assigns a spool to a tool (same variables the
Mainsail Spoolman dialog uses). On every tool change the active spool in
Moonraker follows the tool, so usage is booked to the right spool.
`orca_lanes.py` publishes the tool → filament mapping as Moonraker
`lane_data`, so OrcaSlicer (printer agent *Moonraker*) can sync colours and
profiles. `orca/orca_spoolman_profiles.ps1` creates matching Orca filament
profiles from Spoolman on Windows. Full guide: [docs/SPOOLMAN.md](docs/SPOOLMAN.md).

### INDX overrides
`indx/indx_overrides.cfg` must be included **after** `indx/homing.cfg`. It
adds a safe Z hop when the bed is at the bottom, stores measured filament
values from `INDX_LOAD_FILAMENT` (Kalico INDX module) per tool, a
nozzle-camera XY check (`CAL_VERIFY_XY`) and the Spoolman hook on tool
changes, without editing Bondtech's files.

### Nozzle camera for XY tool offsets
`tools/nozzle_cam.html` is a browser page for Bondtech's camera method of
calibrating the XY tool offsets: camera image with crosshair and zoom, jog
buttons, the calibration steps as buttons and a console.

1. **Camera:** a camera looking up at the nozzle, set up as a second camera
   in crowsnest. The page expects an MJPEG stream; the default path
   `/webcam2/?action=stream` is from this machine (second crowsnest camera).
2. **Open the page:** nginx has to serve it next to Mainsail. Copy it via
   SSH into Mainsail's folder (from the clone, see Setup step 2) and open
   `http://<PRINTER-IP>/nozzle_cam.html`:
   ```bash
   cp ~/indx-trident-350/tools/nozzle_cam.html ~/mainsail/
   ```
   This is a copy: after changing the file, copy it again. The page comes
   from the same address as Moonraker, so no CORS settings are needed; leave
   *Printer* empty. A Mainsail update replaces `~/mainsail/`. To keep the
   page, list it under `persistent_files` in your existing
   `[update_manager mainsail]` section. Keep entries that are already there
   (MainsailOS lists Mainsail's own `config.json`); if the option is missing,
   add it with only `nozzle_cam.html`:
   ```ini
   persistent_files:
       nozzle_cam.html
   ```
   Not working: the link `/server/files/config/nozzle_cam.html` (Moonraker
   sends files as a download), and opening the file locally (`file://`):
   with the usual `cors_domains` Moonraker does not answer requests from it.
3. **Settings:** check the stream path; mirror, zoom and the crosshair ring
   as needed. The page stores its settings in the browser.
4. **Calibrate** (macros from Bondtech's `indx-cal.cfg`, except the last one):
   1. *T0 as reference*: pick up T0, jog the nozzle into the crosshair, then
      `CAL_ONE_SET_CAMERA_REF`.
   2. *Fetch tool*: `CAL_TWO_PREP_TOOL_CAL TOOL=n` picks up the tool and moves
      it to the camera; jog it into the crosshair.
   3. *Save offset*: `CAL_THREE_SAVE_XY_OFFSET`. Repeat 2–3 for every tool.
   4. *Cross-check*: `CAL_VERIFY_XY TOOL=n` (this repo,
      `indx/indx_overrides.cfg`) moves the tool to the reference with its
      stored offset; the nozzle must sit in the crosshair without jogging.
      Do not run `CAL_THREE_SAVE_XY_OFFSET` afterwards.

### OrcaSlicer printer profile
`orca/Voron Trident 350 INDX.json` has machine limits matching the Klipper
config (300 mm/s, 3000 mm/s², square corner velocity 5), so slicer time
estimates are realistic. Nozzles: T0–T4 0.4, T5–T6 0.6, T7–T8 0.25 – adjust
to yours. Tool change time and start time in the profile are rough guesses;
time your own machine.

## Setup

1. **Kalico and INDX:** install [Kalico](https://docs.kalico.gg/INDX.html) and
   the Bondtech INDX module and configs as described in
   [BondtechAB/INDX](https://github.com/BondtechAB/INDX), so that
   `indx/indx.cfg`, `indx/indx-tc-macros.cfg`, `indx/indx-cal.cfg` and
   `indx/homing.cfg` exist in your config folder.
2. **Copy the files** (via SSH). First back up the whole config folder: the
   copy overwrites files with the same name, including `printer.cfg`, which
   may already contain your `SAVE_CONFIG` block.
   ```bash
   cp -r ~/printer_data/config ~/printer_data/config.bak-$(date +%F)
   ```
   ```bash
   cd ~ && git clone https://github.com/daum1988/indx-trident-350
   ```
   ```bash
   cp -r ~/indx-trident-350/klipper/. ~/printer_data/config/
   ```
   This copies the *content* of `klipper/` (not the folder itself), so you get
   `~/printer_data/config/printer.cfg`, `.../config/`, `.../macros/`,
   `.../scripts/`; the macros expect the scripts there. If your old
   `printer.cfg` had a `SAVE_CONFIG` block (lines starting with `#*#`), copy
   it from the backup to the end of the new `printer.cfg`. The other parts
   (`klipperscreen/`, `tools/`, `bootlogo/`, `orca/`) are copied from
   `~/indx-trident-350/` in their own sections below.
3. **Includes:** check `printer.cfg`. The order matters:
   ```ini
   [include mainsail.cfg]
   [include config/*.cfg]
   [include macros/*.cfg]
   [include timelapse.cfg]            # only with moonraker-timelapse
   [include indx/indx.cfg]
   [include indx/indx-tc-macros.cfg]
   [include indx/indx-cal.cfg]
   [include indx/homing.cfg]
   [include indx/indx_overrides.cfg]  # must come after indx/homing.cfg
   ```
4. **Other modules:** `config/autotune_tmc.cfg` needs
   [klipper_tmc_autotune](https://github.com/andrewmcgr/klipper_tmc_autotune),
   `macros/shaketune.cfg` needs [Shake&Tune](https://github.com/Frix-x/klippain-shaketune).
   Install them or delete those files; otherwise Klipper does not start.
5. **Spoolman or not:** `macros/spoolman.cfg` switches the active Spoolman
   spool on every tool change. That needs a working `[spoolman]` section in
   `moonraker.conf`; without it Kalico stops the tool change with an error
   (*Remote method ... not registered*), during a print the print as well.
   - With Spoolman: set it up as in [docs/SPOOLMAN.md](docs/SPOOLMAN.md).
   - Without Spoolman: delete `macros/spoolman.cfg` and set
     `variable_use_spoolman: 0` in `macros/filament_menu.cfg` (the load
     dialog then offers material presets instead of spools).
6. **User name:** the three `[gcode_shell_command]` sections
   (`macros/lc_pa_cal.cfg`, `macros/spoolman.cfg`, `macros/filament_menu.cfg`)
   call the scripts via `/home/pi/printer_data/...`. If your Linux user is
   not `pi`, change these three paths, otherwise the PA calibration, the Orca
   lanes and the spool dialog fail silently. The scripts themselves find
   `printer_data` on their own.
7. **Hardware:** replace the serial IDs (`ls /dev/serial/by-id/`) and, if
   used, the CAN UUID, and check every pin against your wiring.
8. **Moonraker:** merge `moonraker/moonraker.example.conf` into your
   `moonraker.conf`, but only the sections for what is installed:
   `[spoolman]` only with Spoolman (step 5), `[timelapse]` only with
   moonraker-timelapse, each `[update_manager ...]` only if that module is
   installed. Restart Moonraker afterwards.
9. **Calibrate**, then `SAVE_CONFIG` where the command asks for it. Suggested
   order; details in the [Kalico INDX docs](https://docs.kalico.gg/INDX.html)
   and the comments in Bondtech's `indx-cal.cfg`:
   1. load cell (`CALIBRATE_LOAD_CELL`, before the first Z homing),
   2. INDX thermal model (Kalico INDX docs) and bed PID
      (`PID_CALIBRATE HEATER=heater_bed TARGET=100`),
   3. dock positions (`indx-cal.cfg`, section 1),
   4. eddy scanner (Kalico docs for `probe_eddy_current`),
   5. XY tool offsets: see [Nozzle camera](#nozzle-camera-for-xy-tool-offsets),
   6. Z tool offsets (`CAL_Z`), check with `CAL_CHECK_OFFSETS`,
   7. input shaper (Shake&Tune),
   8. pressure advance per tool: see
      [Pressure advance](#pressure-advance-with-the-indx-load-cell).
10. **Optional:** Spoolman and OrcaSlicer: [docs/SPOOLMAN.md](docs/SPOOLMAN.md);
    KlipperScreen add-on, nozzle camera: see above; boot logo:
    [bootlogo/README.md](bootlogo/README.md).

## Lessons learned

- **Global Z offset is lost after a restart / print start?** Babystepping only
  changes the live offset. `START_PRINT` homes Z, which re-applies the *saved*
  global offset. Run `SYNC_GLOBAL_Z` after babystepping to save it, check with
  `CAL_CHECK_OFFSETS` (both from Bondtech's `indx-cal.cfg`). After a restart the
  live value shows 0 until `G28` or a T0 pickup – that is normal.
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
