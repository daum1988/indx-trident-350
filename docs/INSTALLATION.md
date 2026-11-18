# Installation

[Deutsche Version → INSTALLATION.de.md](INSTALLATION.de.md) ·
[README](../README.md)

## Who is this for?

For anyone who has already worked through Bondtech's INDX guide and has a
**working INDX installation**. Starting point:

- Kalico with its INDX module is installed. No minimum version is known;
  this machine runs Kalico `v2026.11.00-30-g991e1823`. Other versions are
  not tested; the INDX module must know the commands used here (e.g.
  `INDX_LOAD_FILAMENT`, `[load_cell_probe]`).
- Bondtech's files are in `~/printer_data/config/indx/` (`indx.cfg`,
  `indx-tc-macros.cfg`, `indx-cal.cfg`, `homing.cfg`).
- Klipper starts with that config without errors.
- Tools are picked up and parked, Z homes with the load cell.

If you are not there yet, work through
[BondtechAB/INDX](https://github.com/BondtechAB/INDX) and the
[Kalico INDX docs](https://docs.kalico.gg/INDX.html) first.

**What this guide does:** the files from this repo replace the board and
toolhead config, `printer.cfg` and the macros. Bondtech's files and your
calibration values are kept. At the end Klipper starts with this repo's
config and the INDX functions work as before.

> **Important:** this is not an add-on you simply copy over your existing
> config. The repo is the complete config of one machine (Voron Trident 350,
> BTT Manta M8P v2.0, 9 tools). The board config and the machine-specific
> values have to be adapted to your printer.

## Labels

| Label | Meaning |
|---|---|
| **[General]** | applies to every matching INDX installation, run as written |
| **[Machine-specific]** | values of this machine; adapt them to your printer |
| **[Optional]** | only if you use that feature |

## Decide first

Answer these before copying; they decide what you adapt afterwards:

| Question | If "no" | Step |
|---|---|---|
| Same hardware (Trident, Manta M8P v2.0)? | replace `config/Trident_M8P_v2.0_config.cfg` with your own board config | 5 |
| Spoolman installed or planned? | delete `macros/spoolman.cfg`, `variable_use_spoolman: 0` | 6 |
| moonraker-timelapse installed? | comment out the `timelapse.cfg` include | 6 |
| [Shake&Tune](https://github.com/Frix-x/klippain-shaketune) installed? | delete `macros/shaketune.cfg` | 6 |
| [klipper_tmc_autotune](https://github.com/andrewmcgr/klipper_tmc_autotune) installed? | delete `config/autotune_tmc.cfg` | 6 |
| Is the Linux user `pi` (`whoami`)? | change three paths | 7 |

## What copying changes

`cp` in step 3 overwrites files with the same name and adds new ones.
Everything else stays.

| File / folder | What happens | Afterwards |
|---|---|---|
| `printer.cfg` | **replaced** | restore your `SAVE_CONFIG` block (step 4) |
| `config/Trident_M8P_v2.0_config.cfg` | added or replaced | **[Machine-specific]** board, pins, serial ID |
| `config/INDX_toolhead.cfg` | added or replaced; contains `[mcu indxmcu]`, `[indx]`, `[extruder]`, `[load_cell_probe]`, `[save_variables]`, scanner | **[Machine-specific]** compare with your previous toolhead config |
| `config/bed_mesh.cfg`, `config/autotune_tmc.cfg` | added or replaced | check the mesh area |
| `indx/indx_overrides.cfg` | added | – |
| `macros/*.cfg` | added; your macro files with the same name are replaced | adapt the bucket positions |
| `scripts/` | added | – |
| `indx/indx.cfg`, `indx-tc-macros.cfg`, `indx-cal.cfg`, `homing.cfg` | **unchanged** | do not replace them with other versions |
| `indx_vars.cfg` (tool offsets, active tool) | **unchanged** | – |
| `moonraker.conf`, `mainsail.cfg`, `KlipperScreen.conf` | unchanged | – |
| your files with other names in `config/` and `macros/` | **stay and are still loaded** (`[include config/*.cfg]`) | check them, see step 4 |

## Steps

### 1. Back up [General]

```bash
B=~/printer_data/config.bak-$(date +%Y%m%d-%H%M%S) && cp -r ~/printer_data/config "$B" && echo "$B"
```

The command prints the path of the backup, e.g.
`/home/pi/printer_data/config.bak-20261118-231500`. Note it; step 4 uses it
as `<BACKUP>`: in the commands below replace `<BACKUP>` with this path
(without the angle brackets).

**Check:** `ls <BACKUP>` shows `printer.cfg`, `indx/` etc.

### 2. Clone the repo [General]

```bash
cd ~ && git clone https://github.com/daum1988/indx-trident-350
```

The clone in `~/indx-trident-350/` is only the source. Klipper keeps reading
from `~/printer_data/config/`; step 3 brings the files there.

### 3. Copy the files [General]

```bash
cp -r ~/indx-trident-350/klipper/. ~/printer_data/config/
```

This copies the *content* of `klipper/` (not the folder itself). The macros
expect the scripts in `~/printer_data/config/scripts/`.

**Check:** `ls ~/printer_data/config/indx/` shows Bondtech's four files plus
`indx_overrides.cfg`; `ls ~/printer_data/config/scripts/` shows `lc_pa`,
`orca_lanes`, `spool_picker`.

### 4. Carry over your previous config [Machine-specific]

1. **`SAVE_CONFIG` block:** the old `printer.cfg` ends with lines starting
   with `#*#`. That is where Klipper stored the calibration values (load cell,
   thermal model, PID, input shaper, scanner). Copy the whole block from the
   backup to the end of the new `printer.cfg`;
   ```bash
   sed -n '/^#\*# <---------------------- SAVE_CONFIG/,$p' <BACKUP>/printer.cfg
   ```
   shows it. **Without this block the load cell is not calibrated and Z
   homing is dangerous.** Check after copying:
   ```bash
   grep -n "^#\*# \[" ~/printer_data/config/printer.cfg
   ```
   lists the sections in the block; `[load_cell_probe]` and `[indx]` must be
   there. The block must be at the very end of the file. A comparison with
   the backup shows whether it is complete (no output except "same" =
   complete):
   ```bash
   diff <(sed -n '/^#\*# <---------------------- SAVE_CONFIG/,$p' <BACKUP>/printer.cfg) <(sed -n '/^#\*# <---------------------- SAVE_CONFIG/,$p' ~/printer_data/config/printer.cfg) && echo same
   ```
2. **Includes:** the new `printer.cfg` loads `mainsail.cfg`, `config/*.cfg`,
   `macros/*.cfg`, `timelapse.cfg` and Bondtech's files;
   `indx_overrides.cfg` must come after `indx/homing.cfg`. If your old
   `printer.cfg` included other files, check whether you still need them.
3. **Old files in `config/` and `macros/`:** files with names other than the
   repo's stay and are still loaded by the wildcard includes. If they contain
   sections that are now also in the repo files (e.g. your own board or
   toolhead config with `[mcu]`, `[indx]`, `[extruder]`, or your own
   `START_PRINT`), Klipper merges sections with the same name: the option
   loaded last wins, usually without an error. The result is a mix of old and
   new config. Move such files out of `config/` and `macros/` (they are in
   the backup) or merge them deliberately. So Klipper starting without errors is not
   enough as a check. This command lists every section that is in more than
   one loaded file, with the files:
   ```bash
   cd ~/printer_data/config && grep -Ho "^\[[^]]*\]" printer.cfg mainsail.cfg timelapse.cfg config/*.cfg macros/*.cfg indx/*.cfg 2>/dev/null | awk -F: '{f[$2]=f[$2]" "$1; n[$2]++} END {for (s in n) if (n[s]>1) print s f[s]}' | sort
   ```
   With this config these duplicates are intended: Bondtech macros replaced
   by `indx/indx_overrides.cfg` (`LOAD_FILAMENT`, `CAL_Z`, `_INDX_SAFE_Z_HOP`,
   `_INDX_SET_ACTIVE_TOOL`), `T0`–`T8` (`indx/indx.cfg` and
   `macros/spoolman.cfg`), `PAUSE`/`RESUME`/`CANCEL_PRINT` (`mainsail.cfg` and
   `macros/trident_macros.cfg`), `[respond]` and `[heater_bed]`. Check every
   other line, especially one with an old file of your own.

### 5. Adapt the hardware [Machine-specific]

- **Board:** `config/Trident_M8P_v2.0_config.cfg` only fits a Manta M8P v2.0
  in a Trident. With other hardware use your own board config.
- **Serial IDs:** `ls /dev/serial/by-id/` and replace the `serial:` lines in
  `config/Trident_M8P_v2.0_config.cfg` and `config/INDX_toolhead.cfg`. With
  CAN, the `canbus_uuid`.
- **Pins:** check against your wiring (steppers, bed heater, thermistors,
  fans, LEDs). This machine's part cooling fan is a CPAP on the M8P (`[fan]`,
  `max_power 0.6`); if you use the fans on the INDX head, enable the `[fan]`
  in `config/INDX_toolhead.cfg` instead.
- **Toolhead:** compare `config/INDX_toolhead.cfg` with your previous toolhead
  config and carry over your values.
- **Bucket and brush:** this machine uses the
  [Voron Trident purge bucket & nozzle brush, INDX remix](https://www.printables.com/model/1921254-voron-trident-purge-bucket-nozzle-brush-indx).
  Positions in `macros/bucket.cfg` (`_BUCKET_VARS`); used for loading,
  unloading, PA calibration and print start.
- **Park position, load temperature:** `_global_var` in `macros/common.cfg`.
- **Bed mesh:** `mesh_min`/`mesh_max` in `config/bed_mesh.cfg`.

### 6. Optional parts [Optional]

According to your answers in "Decide first":

- **Without Spoolman:** delete `macros/spoolman.cfg` and set
  `variable_use_spoolman: 0` in `macros/filament_menu.cfg`. Otherwise every
  tool change stops with *Remote method ... not registered*, because
  `spoolman.cfg` needs a `[spoolman]` section in `moonraker.conf`. With
  Spoolman: set it up as in [SPOOLMAN.md](SPOOLMAN.md); until then do not
  change tools.
- **Without moonraker-timelapse:** comment out `[include timelapse.cfg]` in
  `printer.cfg`.
- **Without Shake&Tune:** delete `macros/shaketune.cfg`.
- **Without TMC autotune:** delete `config/autotune_tmc.cfg`.

### 7. User name [Machine-specific]

Three `[gcode_shell_command]` sections (`macros/lc_pa_cal.cfg`,
`macros/spoolman.cfg`, `macros/filament_menu.cfg`) call scripts via
`/home/pi/printer_data/...`. If your user is not `pi`:

```bash
cd ~/printer_data/config/macros && sed -i "s#/home/pi/#$HOME/#g" lc_pa_cal.cfg filament_menu.cfg spoolman.cfg
```

(Without Spoolman `sed` reports the missing `spoolman.cfg`; that is fine.)
Otherwise the PA calibration, the Orca lanes and the spool dialog fail
without a message.

**Check:** `grep -rn "/home/" ~/printer_data/config/macros/` only shows your
own home folder.

### 8. Moonraker [Optional]

`moonraker/moonraker.example.conf` has sections for Spoolman, timelapse and
the update manager. Merge only the sections for what is installed into your
`moonraker.conf`, then:

```bash
sudo systemctl restart moonraker
```

**Check:** Mainsail shows no Moonraker warnings (bell icon).

### 9. First start [General]

**Before the first restart:** after copying, `config/` holds the board and
toolhead config of *this* machine, not yours. Only restart once steps 4 and 5
are done (serial IDs, pins, toolhead values, `SAVE_CONFIG` block). Wrong pins
can drive heaters or motors incorrectly.

`FIRMWARE_RESTART` in the Mainsail console, then check in this order.
Heaters and sensors first, then motion, the tool change last:

- [ ] Klipper is *ready*, no config error. An error names the file and
      section; see [TROUBLESHOOTING.md](TROUBLESHOOTING.md).
- [ ] `LC_PA_SHOW` answers: the macros from this repo are loaded.
- [ ] `CAL_CHECK_OFFSETS` shows your previous tool offsets: Bondtech's files
      and `indx_vars.cfg` are intact.
- [ ] The `SAVE_CONFIG` block at the end of `printer.cfg` contains
      `[load_cell_probe]` and `[indx]`.
- [ ] Temperatures in Mainsail are plausible: bed, tool and chamber show
      about room temperature, no sensor jumps or is missing.
- [ ] Heaters one at a time and under observation: bed to 60 °C
      (`SET_HEATER_TEMPERATURE HEATER=heater_bed TARGET=60`), then with a tool
      on the head the nozzle to 150 °C (`M104 S150`). The right temperature
      must rise each time. Then switch both off (`TURN_OFF_HEATERS`).
- [ ] `G28 X Y` homes X and Y. Before: nothing in the way, bed clear, hand
      on the emergency stop.
- [ ] Only then `G28` (with Z), hand on the emergency stop: the nozzle touches
      the bed gently, Z is homed.
- [ ] Tool change: **with Spoolman** only once [SPOOLMAN.md](SPOOLMAN.md) is
      done (otherwise the tool change aborts); skip this item until then.
      **Without Spoolman** (`spoolman.cfg` deleted) right away: `T1`, then
      `PARK_TOOL`. The tool is picked up and parked.
- [ ] `LOAD_FILAMENT` without parameters opens the tool dialog; *Cancel*
      closes it.

Continue with [CALIBRATION.md](CALIBRATION.md). The INDX calibration of your
previous installation stays valid; only this repo's parts need measuring
(eddy scanner if new, and pressure advance).

## Updates later

```bash
cd ~/indx-trident-350 && git pull
```

`git pull` updates **only the clone** in `~/indx-trident-350/`. The installed
files in `~/printer_data/config/` do not change.

Then do **not** simply copy everything again as in step 3. That overwrites
your adaptations from steps 4–7:
- `printer.cfg` loses its `SAVE_CONFIG` block,
- without Spoolman `macros/spoolman.cfg` is back and `variable_use_spoolman`
  is `1` again, so every tool change aborts,
- the `/home/pi` paths are reset,
- serial IDs, pins, bucket positions etc. are the originals again.

Compare first and take over only what you want. This lists only repo files
that changed or are new (files that exist only in your config folder are
filtered out):

```bash
diff -rq ~/indx-trident-350/klipper/ ~/printer_data/config/ | grep -v "^Only in $HOME/printer_data"
```

Then look at single files with `diff`, e.g.
`diff ~/indx-trident-350/klipper/macros/filament_menu.cfg ~/printer_data/config/macros/filament_menu.cfg`,
and carry over changes by hand.

If you do copy everything: back up first, then repeat steps 4–7. The
KlipperScreen add-on and the nozzle camera page are copies too: copy them
again as described in their guides if they changed.

## Using single extensions in your own config

If you want to keep your own config, you can take over single parts. This is
not the tested path; the dependencies:

| Extension | Files | Also needs |
|---|---|---|
| Load/unload dialog | `indx/indx_overrides.cfg`, `macros/filament_menu.cfg`, `macros/bucket.cfg`, `scripts/spool_picker/` | `macros/common.cfg`; `[respond]`, `[save_variables]` |
| Spoolman per tool | `macros/spoolman.cfg`, `indx/indx_overrides.cfg`, `scripts/orca_lanes/` | `[save_variables]`, `[spoolman]` in Moonraker |
| PA with the load cell | `macros/lc_pa_cal.cfg`, `scripts/lc_pa/` | `macros/bucket.cfg` (`MOVE_TO_BUCKET`), `macros/common.cfg` |
| `LC_EXTRUDE_TEST` | `macros/lc_extrude_test.cfg` | `macros/bucket.cfg`, `macros/common.cfg` |
| `CAL_VERIFY_XY`, safe Z hop | `indx/indx_overrides.cfg` | – |

`macros/common.cfg` holds the helper macros the extensions share with the
print macros (`_global_var`, `_ENSURE_HOMED`, `UNLOAD_FILAMENT`). The print
macros themselves (`START_PRINT`, `END_PRINT`, `PAUSE`, `RESUME`,
`CANCEL_PRINT`) are in `macros/trident_macros.cfg`; leave that file out if you
keep your own. If your config already has an `UNLOAD_FILAMENT`, remove it:
the one in `common.cfg` opens the tool dialog.
