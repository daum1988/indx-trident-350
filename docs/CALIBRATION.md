# Calibration

[Deutsche Version → CALIBRATION.de.md](CALIBRATION.de.md) ·
[README](../README.md)

The INDX calibration itself is documented by Bondtech and Kalico; this guide
does not replace it. It gives a suggested order, links to the sources and
describes in detail only what this repo adds.

**Requires:** the base installation from [INSTALLATION.md](INSTALLATION.md)
is finished (Klipper starts, `G28 X Y` works).

**Sources for the INDX steps:**
- Bondtech: [BondtechAB/INDX](https://github.com/BondtechAB/INDX) and the
  header comments of `indx/indx-cal.cfg` (they list every calibration
  workflow with its commands),
- Kalico: [INDX docs](https://docs.kalico.gg/INDX.html) (load cell, thermal
  model) and the docs for `probe_eddy_current`.

## Order

| # | Step | Source | What this repo adds |
|---|---|---|---|
| 1 | Load cell (before the first Z homing) | Bondtech `indx-cal.cfg`, Kalico | – |
| 2 | Thermal model, bed PID | Kalico INDX docs | – |
| 3 | Dock positions | Bondtech `indx-cal.cfg` | – |
| 4 | Eddy scanner | Kalico | [`config/bed_mesh.cfg`](#4-eddy-scanner), see below |
| 5 | XY tool offsets | Bondtech `indx-cal.cfg` (camera method) | [nozzle camera page and `CAL_VERIFY_XY`](#5-xy-tool-offsets-nozzle-camera) |
| 6 | Z tool offsets (`CAL_Z`) | Bondtech `indx-cal.cfg` | [note on the global Z offset](#6-z-tool-offsets-global-z-offset) |
| 7 | Input shaper | Klipper / Shake&Tune | `[lis2dw]` and `[resonance_tester]` already in `config/INDX_toolhead.cfg` |
| 8 | Pressure advance per tool | this repo | [`PA_CAL_LOADCELL`](#8-pressure-advance-with-the-load-cell) |

Notes for this machine:
- The part cooling fan is a CPAP on the M8P (`[fan]` in
  `config/Trident_M8P_v2.0_config.cfg`, `max_power 0.6`). The thermal model
  values `model_part_cooling_fan_a/k` depend on the fan and its `max_power`:
  after changing either, measure the thermal model again.
- `printer.cfg` contains no `SAVE_CONFIG` block; all measured values come from
  your own calibration.

## 4. Eddy scanner

The scanner is `[probe_eddy_current scanner]` in `config/INDX_toolhead.cfg`
and is **not** registered as the default probe: Z=0 comes from the load cell,
the scanner only provides the bed shape. Calibrate once, T0 on the head,
**nozzle cold** (the induction heater disturbs the scanner):

```
G28
LDC_CALIBRATE_DRIVE_CURRENT CHIP=scanner
SAVE_CONFIG
G28
PROBE_EDDY_CURRENT_CALIBRATE CHIP=scanner
SAVE_CONFIG
```

Every mesh call has to select the scanner:
`BED_MESH_CALIBRATE PROBE=scanner METHOD=rapid_scan` (`START_PRINT` does this, adaptive to the print area).
Without `PROBE=scanner` the load cell taps every point one by one.

**Check:** the command above creates a mesh in one pass over the bed.
"Sample rate is not high enough": lower `speed` in `[bed_mesh]` or pass
`SCAN_SPEED=`.

## 5. XY tool offsets (nozzle camera)

Bondtech's camera method (`CAL_ONE_SET_CAMERA_REF`,
`CAL_TWO_PREP_TOOL_CAL TOOL=n`, `CAL_THREE_SAVE_XY_OFFSET`, see
`indx-cal.cfg`) needs a camera that looks up at the nozzle. This repo adds a
browser page for it and a cross-check.

**Nozzle camera page** `tools/nozzle_cam.html`: camera image with crosshair
and zoom, jog buttons, the calibration steps as buttons and a console.

1. **Camera:** set up as second camera in crowsnest (MJPEG stream).
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
Bondtech's steps 2–3 for that tool.

## 6. Z tool offsets: global Z offset

`CAL_Z` (Bondtech) saves each tool's Z offset relative to T0. The first layer
is then fine-tuned with the global Z offset:

- Babystepping during a print only changes the live offset. Save it with
  `SYNC_GLOBAL_Z` (Bondtech); `CAL_CHECK_OFFSETS` shows it. Without it the
  value is lost at the next print start, because `START_PRINT` homes Z and
  applies the saved offset.
- After a restart the live value shows 0 until `G28` or a T0 pickup; that is
  normal.
- Different build plates need no offset per plate: Z is measured with the
  load cell on the plate surface.

## 8. Pressure advance with the load cell

`PA_CAL_LOADCELL` (`macros/lc_pa_cal.cfg`) measures pressure advance per tool
without a test print. The tool extrudes into the purge bucket in speed steps
while the load cell records the nozzle pressure; the pressure time constant is
fitted and is the PA value.

**Requires:** steps 1–3 done (load cell, thermal model, docks),
filament loaded, purge bucket in place, correct user name in the script path
([INSTALLATION.md](INSTALLATION.md), step 6). Once per tool, and after every
nozzle change, store the nozzle size: `SET_TOOL_NOZZLE TOOL=3 D=0.6`.

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

**Result:** a PA value per tool in the console, stored as `t<n>_pa` in
`indx_vars.cfg`. If a spool is assigned to the tool (Spoolman), also in the
spool's filament (`pressure_advance_d025/_d04/_d06`, one per nozzle size).
Uncertain values are shown but not saved. Errors:
`~/printer_data/config/lc_pa_data/last_run.log`.

In OrcaSlicer use plain PA per filament (the profile script copies it from
Spoolman, see [ORCASLICER.md](ORCASLICER.md)); avoid Orca's *adaptive PA*, it
floods Klipper with `SET_PRESSURE_ADVANCE`.
