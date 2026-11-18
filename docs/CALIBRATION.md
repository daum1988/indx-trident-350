# Calibration

[Deutsche Version → CALIBRATION.de.md](CALIBRATION.de.md) ·
[README](../README.md)

Calibrating an INDX printer for the first time, in a suggested order. Each step
says what it is for, what has to be done before, which commands to run, what
moves, what you should see afterwards and what to do if it fails.

**Requires:** the base installation from [INSTALLATION.md](INSTALLATION.md)
is finished (Klipper starts, `G28 X Y` works).

**Sources:** most calibration macros come from Bondtech's `indx/indx-cal.cfg`;
its header comments are the reference and may be newer than this guide. The
thermal model and the load cell are part of Kalico's INDX module
([Kalico INDX docs](https://docs.kalico.gg/INDX.html)). Exact parameters
belong to those sources; this guide gives the order, the purpose and the
checks.

**Safety for every step:** stay at the printer, keep the emergency stop
(`M112`, or the button in Mainsail/KlipperScreen) within reach, and run the
first moves of a new step with the bed lowered.

**`SAVE_CONFIG`** writes calibration results into the block at the end of
`printer.cfg` and restarts Klipper. Values saved with `SAVE_VARIABLE` (tool
offsets, PA, spool assignments) go to `indx_vars.cfg` immediately and need no
`SAVE_CONFIG`.

| # | Step | Result is stored in |
|---|---|---|
| 1 | Load cell | `SAVE_CONFIG` block |
| 2 | First Z homing | – |
| 3 | Thermal model, bed PID | `SAVE_CONFIG` block |
| 4 | Dock positions | `indx/indx.cfg` (by hand) |
| 5 | Eddy scanner | `SAVE_CONFIG` block |
| 6 | XY tool offsets (nozzle camera) | `indx_vars.cfg` |
| 7 | Z tool offsets | `indx_vars.cfg` |
| 8 | Input shaper | `SAVE_CONFIG` block |
| 9 | Pressure advance per tool | `indx_vars.cfg` (+ Spoolman) |

### 1. Load cell

**Purpose:** the load cell in the INDX head measures force. It is the Z probe
(the nozzle touches the bed) and is also used by the PA calibration. It has to
know how many grams a reading means.

**Requires:** X and Y can be homed. **No tool on the head.** Z must not be
homed yet; this step comes before every Z homing.

**Commands:**
1. `CALIBRATE_LOAD_CELL` with an empty head. Homes X and Y, opens the latch and
   tares the empty head.
2. Seat a tool by hand (cold, no filament needed).
3. `CALIBRATE_LOAD_CELL_APPLY GRAMS=1600`. Locks the latch, calibrates,
   unlocks again.
4. `SAVE_CONFIG`.

**What moves:** X/Y homing, the latch (driven by the extruder motor).

**Expected result:** after the restart the load cell values are in the
`SAVE_CONFIG` block. The tool is still on the head, unlocked, and is not
registered as active tool.

**If it fails:**
- `CALIBRATE_LOAD_CELL` refuses because a tool may be seated: remove the tool.
  Only if an old calibration is so far off that an empty head reads as seated,
  run it with `HEAD_EMPTY=1`.
- If your firmware does not allow chaining the calibration commands from a
  macro, run the steps by hand as listed in Bondtech's wiki
  (`LOAD_CELL_CALIBRATE`, `TARE`, `CALIBRATE`, `ACCEPT`).

### 2. First Z homing

**Purpose:** Z homing needs a tool (the nozzle is the probe), and picking up a
tool from the dock needs a homed Z. A tool seated by hand breaks that circle.

**Requires:** step 1 done. Bed free, nozzle clean (no filament blob).

**Commands:**
1. Seat T0 by hand (if the tool from step 1 is T0, leave it on).
2. `MANUAL_TOOL_SEAT TOOL=0` locks the latch and registers T0 as active tool.
3. `G28`.

**What moves:** X/Y, then the bed comes up to the nozzle at the probe position
(`probe_x`/`probe_y` in `indx.cfg`, default bed centre).

**Expected result:** the nozzle touches the bed gently and Z is homed.

**If it fails:** if the bed presses on without stopping, emergency stop
immediately and check step 1. Wrong tool on the head: `MANUAL_TOOL_REMOVE`,
then start again.

### 3. Thermal model and bed PID

**Purpose:** the INDX heats the nozzle by induction and protects it with a
thermal model. The model must know how the heater, the hotend and the part
cooling fan behave; with wrong values Kalico stops with a thermal error.

**Requires:** step 2 done, a tool on the head.

**Commands:** the INDX calibration as described in the
[Kalico INDX docs](https://docs.kalico.gg/INDX.html) (`INDX_CALIBRATE`),
then `SAVE_CONFIG`. Bed: `PID_CALIBRATE HEATER=heater_bed TARGET=100`, then
`SAVE_CONFIG`.

**What moves:** nothing; the nozzle heats, the part cooling fan runs.

**Expected result:** the `SAVE_CONFIG` block contains an `[indx]` section with
`model_...` values (including `model_part_cooling_fan_a/k`).

**If it fails / later:** after changing the part cooling fan (e.g. 4010
blowers ↔ CPAP) or its `max_power`, measure again; old values may not fit
anymore.

### 4. Dock positions

**Purpose:** the tool change has to find every dock exactly. Y and X are
measured per tool and entered in `indx/indx.cfg` by hand.

**Requires:** steps 1–3 done.

**Y (`CAL_SET_DOCK_Y`):** with a tool on the head and the printer homed, jog
carefully to the dock position in Y and run `CAL_SET_DOCK_Y`. The console
shows `variable_t<n>_dock_y: ...`; paste it into `indx.cfg`.

**X (`CALIBRATE_DOCK_X`), per tool:**
1. `M84` (motors off).
2. Slide the toolhead by hand to the dock of tool n.
3. `CALIBRATE_DOCK_X TOOL=n`. It energises X/Y, homes Y and then X from the
   dock and reports the dock X.
4. Note the value, repeat for every tool.
5. Paste the values into `indx.cfg`, `RESTART`, then `G28`.

If the printer is already homed, you can jog to the dock and use
`READ_DOCK_POSITION TOOL=n` instead (no homing move).

**Expected result:** after the restart, pick up and park every tool once
(`T1`, `PARK_TOOL`, …) while watching: the tool slides into the dock without
catching and is picked up cleanly.

**If it fails:** if a tool catches on the dock, emergency stop, check the
values for that tool, repeat the measurement.

### 5. Eddy scanner (bed mesh)

**Purpose:** the eddy current scanner in the INDX Smart Head scans the bed
shape quickly (rapid scan). Z=0 still comes from the load cell.

**Requires:** step 2 done, T0 on the head, **nozzle cold** (the induction
heater disturbs the scanner).

**Commands** (from `config/bed_mesh.cfg`):
```
G28
LDC_CALIBRATE_DRIVE_CURRENT CHIP=scanner
SAVE_CONFIG
G28
PROBE_EDDY_CURRENT_CALIBRATE CHIP=scanner
SAVE_CONFIG
```
`PROBE_EDDY_CURRENT_CALIBRATE` asks you to lower the nozzle to the bed (paper
test) step by step; details in the Kalico docs for `probe_eddy_current`.

**Expected result:** `BED_MESH_CALIBRATE PROBE=scanner METHOD=rapid_scan`
creates a mesh in one pass over the bed.

**If it fails:** "Sample rate is not high enough": lower `speed` in
`[bed_mesh]` or pass `SCAN_SPEED=`. Without `PROBE=scanner` the load cell taps
every point one by one; that is not an error, only slow.

### 6. XY tool offsets (nozzle camera)

**Purpose:** each tool's nozzle sits at a slightly different XY position. The
offsets relative to T0 are measured with a camera that looks up at the nozzle.

**Requires:** steps 1–4 done. A camera under the nozzle, set up as second
camera in crowsnest (MJPEG stream). Clean nozzles.

**Nozzle camera page:** `tools/nozzle_cam.html` shows the camera image with
crosshair and zoom, jog buttons, the calibration steps as buttons and a
console.

1. Copy it via SSH into Mainsail's folder (from the clone, see
   [INSTALLATION.md](INSTALLATION.md), step 2) and open
   `http://<PRINTER-IP>/nozzle_cam.html`:
   ```bash
   cp ~/indx-trident-350/tools/nozzle_cam.html ~/mainsail/
   ```
   This is a copy: after changing the file, copy it again. The page comes from
   the same address as Moonraker, so no CORS settings are needed; leave
   *Printer* empty.
2. A Mainsail update replaces `~/mainsail/`. To keep the page, list it under
   `persistent_files` in your existing `[update_manager mainsail]` section of
   `moonraker.conf`. If `persistent_files` is already there (e.g. with
   `config.json`), keep its entries and add `nozzle_cam.html`; otherwise add
   it with only `nozzle_cam.html`:
   ```ini
   persistent_files:
       nozzle_cam.html
   ```
3. Settings on the page: stream path (default `/webcam2/?action=stream`, the
   second crowsnest camera), mirror, zoom, crosshair ring. The page stores them
   in the browser.

Not working: the link `/server/files/config/nozzle_cam.html` (Moonraker sends
files as a download) and opening the file locally (`file://`; Moonraker does
not answer requests from it with the usual `cors_domains`).

**Commands** (Bondtech's `indx-cal.cfg`, except the last one):
1. Pick up T0, jog the nozzle into the crosshair, `CAL_ONE_SET_CAMERA_REF`.
2. `CAL_TWO_PREP_TOOL_CAL TOOL=n` picks up tool n and moves it to the camera;
   jog it into the crosshair.
3. `CAL_THREE_SAVE_XY_OFFSET` saves the offset. Repeat 2–3 for every tool.
4. Cross-check: `CAL_VERIFY_XY TOOL=n` (this repo, `indx/indx_overrides.cfg`)
   picks up the tool with the normal tool change and moves to the reference
   with the stored offset. Changes nothing.

**What moves:** tool changes, travel to the camera, jogging.

**Expected result:** with `CAL_VERIFY_XY` the nozzle sits in the crosshair
without jogging. `CAL_CHECK_OFFSETS` lists the offsets.

**If it fails:** if the nozzle is off with `CAL_VERIFY_XY`, run 2–3 again for
that tool. Do not run `CAL_THREE_SAVE_XY_OFFSET` after `CAL_VERIFY_XY`.

### 7. Z tool offsets

**Purpose:** the nozzles differ in height. `CAL_Z` probes every tool with the
load cell and saves its Z offset relative to T0.

**Requires:** steps 1–4 done, clean nozzles (no filament on the tip), bed
clean.

**Commands:** `CAL_Z` (optional `NOZZLE_TEMP=150 SOAK=10` to probe warm).
Check with `CAL_CHECK_OFFSETS`.

**What moves:** every tool is picked up and probes the bed several times in a
small area (first on its own spot, then on a shared clean spot), then parked.

**Expected result:** the console lists per tool the median and
`t<n>_offset_z`; the values are saved immediately. Pick up a tool again to
apply the new offset.

**If it fails:** if a tool does not converge, it probes on a small circle and
slows down; scattering values usually mean a dirty nozzle or bed.

**Global Z offset (first layer):** fine-tune with babystepping during a print,
then `SYNC_GLOBAL_Z` to save it; `CAL_CHECK_OFFSETS` shows it. Without
`SYNC_GLOBAL_Z` it is lost at the next print start, because `START_PRINT`
homes Z and applies the saved offset. After a restart the live value shows 0
until `G28` or a T0 pickup; that is normal. Different build plates need no
offset per plate: Z is measured on the plate surface.

### 8. Input shaper

**Purpose:** reduce ringing. The INDX PCB has an accelerometer (`[lis2dw]`,
already configured in `config/INDX_toolhead.cfg`).

**Commands:** Klipper's `SHAPER_CALIBRATE` or Shake&Tune's commands (see the
[Shake&Tune docs](https://github.com/Frix-x/klippain-shaketune)), then
`SAVE_CONFIG`.

**What moves:** X and Y vibrate at increasing frequency (loud).

**Expected result:** `[input_shaper]` values in the `SAVE_CONFIG` block.

### 9. Pressure advance per tool (load cell)

**Purpose:** pressure advance per tool and filament, measured without a test
print. The tool extrudes into the purge bucket in speed steps while the load
cell records the nozzle pressure; the pressure time constant is fitted and is
the PA value.

**Requires:** steps 1–4 done, filament loaded in the tool, purge bucket in
place. Once per tool (and after every nozzle change) store the nozzle size:
`SET_TOOL_NOZZLE TOOL=3 D=0.6`. Optional check first: `LC_EXTRUDE_TEST`
shows whether the load cell sees the extrusion force at all.

**Commands:**
```
PA_CAL_LOADCELL TOOL=0 TEMP=230
PA_CAL_LOADCELL TOOLS=0,3,5 TEMP=230
PA_CAL_LOADCELL TOOLS=ALL TEMP=230
LC_PA_SHOW          list stored values
LC_PA_APPLY         apply the stored value of the active tool
```
Use the filament and temperature you print with. Do not send other commands
during a measurement.

**What moves:** tool change, travel to the bucket, extrusion (at most about 51 mm of
filament per tool, 1–2 minutes).

**Expected result:** a PA value per tool in the console, stored as `t<n>_pa`
in `indx_vars.cfg`. If a spool is assigned to the tool (Spoolman), also in the
spool's filament (`pressure_advance_d025/_d04/_d06`, one per nozzle size).
Uncertain values are shown but not saved.

**If it fails:** errors are in `~/printer_data/config/lc_pa_data/last_run.log`
(Mainsail: config files). No value at all: check the user name path (see
[INSTALLATION.md](INSTALLATION.md), step 6).

In OrcaSlicer use plain PA per filament (the profile script copies it from
Spoolman, see [ORCASLICER.md](ORCASLICER.md)); avoid Orca's *adaptive PA*, it
floods Klipper with `SET_PRESSURE_ADVANCE`.
