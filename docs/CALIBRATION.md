# Calibration

[Deutsche Version → CALIBRATION.de.md](CALIBRATION.de.md) ·
[README](../README.md)

The INDX calibration itself is documented by Bondtech and Kalico; this guide
does not replace it. For each INDX step it says **where** the instructions
are, **what** to run and **how** to tell it worked. Only what this repo adds
is described in detail.

**Requires:** the installation from [INSTALLATION.md](INSTALLATION.md) is
finished.

**Coming from a calibrated INDX installation?** Your values are kept (the
`SAVE_CONFIG` block, `indx/indx.cfg`, `indx_vars.cfg`). Steps 1, 3, 5 and 6
are then already done; check them with the "Done when" lines. Measure again:
step 2 if the part cooling fan differs from your previous config, step 4 if
the scanner is new for you, and step 8 (this repo).

**Sources:**
- Bondtech: [BondtechAB/INDX](https://github.com/BondtechAB/INDX) and
  `~/printer_data/config/indx/indx-cal.cfg`. Its header lists every
  calibration workflow with its commands; each workflow has its own section
  further down with the exact steps.
- Kalico: [INDX docs](https://docs.kalico.gg/INDX.html) (load cell, thermal
  model), docs for `probe_eddy_current`.

| # | Step | Source | This repo adds |
|---|---|---|---|
| 1 | Load cell | Bondtech, Kalico | – |
| 2 | Thermal model, bed PID | Kalico | note on the fan |
| 3 | Dock positions | Bondtech | – |
| 4 | Eddy scanner | Kalico | `config/bed_mesh.cfg` |
| 5 | XY tool offsets | Bondtech | nozzle camera page, `CAL_VERIFY_XY` |
| 6 | Z tool offsets | Bondtech | note on the global Z offset |
| 7 | Input shaper | Klipper / Shake&Tune | accelerometer already configured |
| 8 | Pressure advance | this repo | `PA_CAL_LOADCELL` |

`SAVE_CONFIG` writes results into the block at the end of `printer.cfg` and
restarts Klipper. Values saved with `SAVE_VARIABLE` (tool offsets, PA) go to
`indx_vars.cfg` immediately.

## 1. Load cell

- **Where:** `indx-cal.cfg`, section *LOAD CELL CALIBRATION*; Kalico INDX
  docs.
- **What:** before the first Z homing, empty head: `CALIBRATE_LOAD_CELL`.
  Seat a tool by hand, `CALIBRATE_LOAD_CELL_APPLY GRAMS=1600`, `SAVE_CONFIG`.
  For the very first Z homing seat T0 by hand and register it with
  `MANUAL_TOOL_SEAT TOOL=0`, then `G28`.
- **Done when:** the `SAVE_CONFIG` block contains `[load_cell_probe]`, and
  `G28` lets the bed touch the nozzle gently and stop.

## 2. Thermal model and bed PID

- **Where:** [Kalico INDX docs](https://docs.kalico.gg/INDX.html) (thermal
  model, `INDX_CALIBRATE`).
- **What:** the INDX calibration as described there, `SAVE_CONFIG`. Bed:
  `PID_CALIBRATE HEATER=heater_bed TARGET=100`, `SAVE_CONFIG`.
- **Done when:** the `SAVE_CONFIG` block has an `[indx]` section with
  `model_...` values, and a tool heats to printing temperature without a
  thermal error.

**This machine:** the part cooling fan is a CPAP on the M8P (`[fan]` in
`config/Trident_M8P_v2.0_config.cfg`, `max_power 0.6`). The values
`model_part_cooling_fan_a/k` depend on the fan and its `max_power`. If your
fan or `max_power` differs from the config you calibrated with, measure the
thermal model again.

## 3. Dock positions

- **Where:** `indx-cal.cfg`, sections *1. DOCK POSITION CALIBRATION*
  (`CAL_SET_DOCK_Y`) and *DOCK X CALIBRATION* (`CALIBRATE_DOCK_X`,
  `READ_DOCK_POSITION`).
- **What:** per tool, measure Y and X as described there, paste the reported
  `variable_t<n>_...` lines into `indx/indx.cfg`, `RESTART`.
- **Done when:** every tool is picked up and parked once (`T1`,
  `PARK_TOOL`, …) without catching on the dock.

## 4. Eddy scanner

The scanner is `[probe_eddy_current scanner]` in `config/INDX_toolhead.cfg`
and is **not** registered as the default probe: Z=0 comes from the load cell,
the scanner only provides the bed shape.

- **Where:** Kalico docs for `probe_eddy_current`; the commands are also in
  the header of `config/bed_mesh.cfg`.
- **What:** once, T0 on the head, **nozzle cold** (the induction heater
  disturbs the scanner), the commands below in order.
  `PROBE_EDDY_CURRENT_CALIBRATE` asks you to lower the nozzle onto the bed
  step by step (paper test): you trigger every step yourself with
  `TESTZ Z=-0.1` etc. Go in small steps, watch the nozzle and send `ABORT` or
  press the emergency stop if anything unexpected happens.
- **Done when:** `BED_MESH_CALIBRATE PROBE=scanner METHOD=rapid_scan` creates a
  mesh in one pass over the bed.

```
G28
LDC_CALIBRATE_DRIVE_CURRENT CHIP=scanner
SAVE_CONFIG
G28
PROBE_EDDY_CURRENT_CALIBRATE CHIP=scanner
SAVE_CONFIG
```

Every mesh call has to select the scanner; `START_PRINT` does this, adaptive
to the print area. Without `PROBE=scanner` the load cell taps every point one
by one. "Sample rate is not high enough": lower `speed` in `[bed_mesh]` or
pass `SCAN_SPEED=`.

## 5. XY tool offsets (nozzle camera)

- **Where:** `indx-cal.cfg`, section *2. XY TOOL OFFSET CALIBRATION (CAMERA
  METHOD)*.
- **What:** pick up T0, jog the nozzle into the camera crosshair,
  `CAL_ONE_SET_CAMERA_REF`. Per tool: `CAL_TWO_PREP_TOOL_CAL TOOL=n`, jog into
  the crosshair, `CAL_THREE_SAVE_XY_OFFSET`.
- **Done when:** `CAL_VERIFY_XY TOOL=n` (below) puts every nozzle into the
  crosshair without jogging.

This repo adds a browser page for the camera and the cross-check.

**Nozzle camera page** `tools/nozzle_cam.html`: camera image with crosshair
and zoom, jog buttons, the calibration steps as buttons and a console.

1. **Camera:** a camera looking up at the nozzle, set up as second camera in
   crowsnest (MJPEG stream).
2. **Install:** copy the page via SSH into Mainsail's folder (from the clone,
   see [INSTALLATION.md](INSTALLATION.md), step 2) and open
   `http://<PRINTER-IP>/nozzle_cam.html`:
   ```bash
   cp ~/indx-trident-350/tools/nozzle_cam.html ~/mainsail/
   ```
   This is a copy: after changing the file, copy it again. The page comes from
   the same address as Moonraker, so no CORS settings are needed; leave
   *Printer* empty.
3. **Keep it across Mainsail updates:** an update replaces `~/mainsail/`. List
   the page under `persistent_files` in your existing
   `[update_manager mainsail]` section of `moonraker.conf`. If
   `persistent_files` is already there (e.g. with `config.json`), keep its
   entries and add `nozzle_cam.html`; otherwise add it with only
   `nozzle_cam.html`:
   ```ini
   persistent_files:
       nozzle_cam.html
   ```
4. **Settings on the page:** stream path (default `/webcam2/?action=stream`,
   the second crowsnest camera), mirror, zoom, crosshair ring. The page stores
   them in the browser.

Not working: the link `/server/files/config/nozzle_cam.html` (Moonraker sends
files as a download) and opening the file locally (`file://`; Moonraker does
not answer requests from it with the usual `cors_domains`).

**Cross-check `CAL_VERIFY_XY TOOL=n`** (`indx/indx_overrides.cfg`): picks up
the tool with the normal tool change (offsets active as when printing) and
moves to the camera reference from `CAL_ONE_SET_CAMERA_REF`. If the offset is
right, the nozzle sits in the crosshair without jogging. It changes nothing;
do not run `CAL_THREE_SAVE_XY_OFFSET` afterwards. If the nozzle is off, repeat
`CAL_TWO_PREP_TOOL_CAL` and `CAL_THREE_SAVE_XY_OFFSET` for that tool.

## 6. Z tool offsets

- **Where:** `indx-cal.cfg`, section *3. Z AUTO-CALIBRATION*.
- **What:** clean nozzles and bed, `CAL_Z`.
- **Done when:** the console lists `t<n>_offset_z` for every tool,
  `CAL_CHECK_OFFSETS` shows them, and the first layer of every tool has the
  same squish.

**Global Z offset (this repo's note):** fine-tune the first layer with
babystepping during a print, then save it with `SYNC_GLOBAL_Z` (Bondtech);
`CAL_CHECK_OFFSETS` shows it. Without it the value is lost at the next print
start, because `START_PRINT` homes Z and applies the saved offset. After a
restart the live value shows 0 until `G28` or a T0 pickup; that is normal.
Different build plates need no offset per plate: Z is measured with the load
cell on the plate surface.

## 7. Input shaper

- **Where:** Klipper's *Resonance compensation* docs or
  [Shake&Tune](https://github.com/Frix-x/klippain-shaketune).
- **What:** measure under printing conditions: a tool on the head, belts
  tensioned, nothing loose on the bed or head. Then `SHAPER_CALIBRATE` (or
  the Shake&Tune commands), `SAVE_CONFIG`.
  The accelerometer on the INDX PCB (`[lis2dw]`, `[resonance_tester]`) is
  already configured in `config/INDX_toolhead.cfg`.
- **Done when:** the `SAVE_CONFIG` block contains `[input_shaper]`.

## 8. Pressure advance with the load cell

`PA_CAL_LOADCELL` (`macros/lc_pa_cal.cfg`) measures pressure advance per tool
without a test print. The tool extrudes into the purge bucket in speed steps
while the load cell records the nozzle pressure; the pressure time constant is
fitted and is the PA value.

**Requires:** steps 1–3 done, filament loaded, purge bucket in place and its
position set in `macros/bucket.cfg`, correct user name in the script path
([INSTALLATION.md](INSTALLATION.md), step 7). **Once per tool, and after every
nozzle change before measuring,** store the nozzle size: `SET_TOOL_NOZZLE TOOL=3 D=0.6`.

**Optional first:** `LC_EXTRUDE_TEST SPEED=1` / `SPEED=3` / `SPEED=6` with a hot
tool shows whether the load cell sees the extrusion force at all (the
difference must rise clearly with speed).

```
PA_CAL_LOADCELL TOOL=0 TEMP=230
PA_CAL_LOADCELL TOOLS=0,3,5 TEMP=230
PA_CAL_LOADCELL TOOLS=ALL TEMP=230
LC_PA_SHOW          list stored values
LC_PA_APPLY         apply the stored value of the active tool
```

Measure with the filament and temperature you print with, and do not send
other commands during a measurement. Per tool: tool change, travel to the
bucket, at most about 51 mm of filament, 1–2 minutes.

**Done when:** the console shows a PA value per tool and `LC_PA_SHOW` lists
it (stored as `t<n>_pa` in `indx_vars.cfg`). If a spool is assigned to the
tool (Spoolman), the value is also in the spool's filament
(`pressure_advance_d025/_d04/_d06`, one per nozzle size). Uncertain values are
shown but not saved. Errors: `~/printer_data/config/lc_pa_data/last_run.log`.

In OrcaSlicer use plain PA per filament (the Orca plugin copies it from
Spoolman, see [ORCASLICER.md](ORCASLICER.md)); avoid Orca's *adaptive PA*, it
floods Klipper with `SET_PRESSURE_ADVANCE`.
