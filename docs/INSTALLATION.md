# Installation

[Deutsche Version → INSTALLATION.de.md](INSTALLATION.de.md) ·
[README](../README.md)

This guide covers the **base installation**: at the end Klipper starts without
errors with this repo's config, and X/Y can be homed. Calibration follows in
[CALIBRATION.md](CALIBRATION.md); extensions (Spoolman, OrcaSlicer,
KlipperScreen, nozzle camera, boot logo) have their own guides.

> This is a personal machine config. Pins, serial IDs, positions and all
> calibration values must be checked and measured on your own printer.

## Before you start

**Must already work:**
- The printer is mechanically finished and wired: Voron Trident with Bondtech
  INDX, docks, toolhead board, mainboard. This repo uses a BTT Manta M8P v2.0
  with CM4; with other boards you rewrite `config/Trident_M8P_v2.0_config.cfg`.
- MainsailOS (or Klipper/Kalico + Moonraker + Mainsail installed by hand),
  network access and SSH to the Pi, `git` installed.
- [Kalico](https://docs.kalico.gg/INDX.html) with its INDX module. No minimum
  version is known; use the one Bondtech's INDX guide asks for.
- Bondtech's INDX configs from [BondtechAB/INDX](https://github.com/BondtechAB/INDX),
  with `indx/indx.cfg` adapted to your machine (tool count, dock direction,
  probe position).

**Does not have to be done yet:** calibration. If your printer already runs
on Bondtech's stock config and is calibrated, the values are kept:
`indx/indx.cfg` and `indx_vars.cfg` are not touched by this repo, and the
`SAVE_CONFIG` block is copied back in step 2. You can then skip the
calibration steps that are already done.

**Who provides what:**

| Comes from | Contents |
|---|---|
| Kalico | firmware, INDX module (`[indx]`, `INDX_LOAD_FILAMENT`, thermal model, load cell) |
| Bondtech | `indx/indx.cfg`, `indx/indx-tc-macros.cfg` (tool change, `PARK_TOOL`, `CHANGE_TOOL`), `indx/indx-cal.cfg` (calibration macros), `indx/homing.cfg` |
| this repo | board and toolhead config, print macros, `indx/indx_overrides.cfg`, Spoolman/Orca/KlipperScreen integration, load-cell PA calibration |

## Base installation and extensions

| Part | Needed for | Guide |
|---|---|---|
| **Base installation** | printer starts, tool changes work | this guide |
| **Calibration** | printing | [CALIBRATION.md](CALIBRATION.md) |
| Spoolman | one spool per tool, usage tracking, spool list in the load dialog | [SPOOLMAN.md](SPOOLMAN.md) |
| OrcaSlicer integration | printer profile, filament profiles and colours from Spoolman | [ORCASLICER.md](ORCASLICER.md) |
| KlipperScreen add-on | INDX panel, active tool in the titlebar | [KLIPPERSCREEN.md](KLIPPERSCREEN.md) |
| Nozzle camera | XY tool offsets | [CALIBRATION.md, step 6](CALIBRATION.md#6-xy-tool-offsets-nozzle-camera) |
| Boot logo (optional) | logo on the display while booting | [bootlogo/README.md](../bootlogo/README.md) |

The load/unload dialog (`macros/filament_menu.cfg`) is part of the base
installation; it works with or without Spoolman.

## Steps

### 1. Kalico and INDX

Install Kalico and set up the INDX module and configs as described by
Bondtech, so that these files exist in `~/printer_data/config/indx/`:
`indx.cfg`, `indx-tc-macros.cfg`, `indx-cal.cfg`, `homing.cfg`.

**Expected result:** Klipper starts with Bondtech's stock config; the Mainsail
console shows the INDX status on startup.

### 2. Back up and copy the files (SSH)

The copy overwrites files with the same name, including `printer.cfg`, which
may already contain your `SAVE_CONFIG` block. Back up the whole config folder
first:

```bash
cp -r ~/printer_data/config ~/printer_data/config.bak-$(date +%F)
```
```bash
cd ~ && git clone https://github.com/daum1988/indx-trident-350
```
```bash
cp -r ~/indx-trident-350/klipper/. ~/printer_data/config/
```

This copies the *content* of `klipper/` (not the folder itself). The macros
expect the scripts in `~/printer_data/config/scripts/`.

If your old `printer.cfg` had a `SAVE_CONFIG` block (the lines starting with
`#*#` at the end; Klipper writes calibration results there), copy it from the
backup to the end of the new `printer.cfg`.

**Expected result:** `ls ~/printer_data/config` shows `printer.cfg`,
`config/`, `macros/`, `scripts/` and `indx/` (Bondtech's files plus
`indx_overrides.cfg`).

### 3. Includes

`printer.cfg` loads the other files with `[include ...]` lines. The order
matters:

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

`mainsail.cfg` comes with MainsailOS, `timelapse.cfg` with
[moonraker-timelapse](https://github.com/mainsail-crew/moonraker-timelapse).
Comment out the line of anything you do not use.

### 4. Other modules

- `config/autotune_tmc.cfg` needs
  [klipper_tmc_autotune](https://github.com/andrewmcgr/klipper_tmc_autotune),
- `macros/shaketune.cfg` needs [Shake&Tune](https://github.com/Frix-x/klippain-shaketune).

Install them or delete those files; otherwise Klipper does not start.

### 5. With or without Spoolman

`macros/spoolman.cfg` switches the active Spoolman spool on every tool change.
That needs a working `[spoolman]` section in `moonraker.conf`; without it
Kalico stops the tool change with an error (*Remote method ... not
registered*), during a print the print as well.

- **With Spoolman:** set it up as in [SPOOLMAN.md](SPOOLMAN.md) (it can be
  done after this guide; until then do not change tools).
- **Without Spoolman:** delete `macros/spoolman.cfg` and set
  `variable_use_spoolman: 0` in `macros/filament_menu.cfg`. The load dialog
  then offers material presets instead of spools.

### 6. User name

Three `[gcode_shell_command]` sections (`macros/lc_pa_cal.cfg`,
`macros/spoolman.cfg`, `macros/filament_menu.cfg`) call scripts via
`/home/pi/printer_data/...`. Check your user name with `whoami`. If it is not
`pi`, replace the paths:

```bash
cd ~/printer_data/config/macros && sed -i "s#/home/pi/#$HOME/#g" lc_pa_cal.cfg filament_menu.cfg spoolman.cfg
```

(Without Spoolman `sed` reports the missing `spoolman.cfg`; that is fine.)
Otherwise the PA calibration, the Orca lanes and the spool dialog fail
without a message. The scripts themselves find `printer_data` on their own.

**Expected result:** `grep -rn "/home/" ~/printer_data/config/macros/` only
shows your own home folder.

### 7. Hardware

- Serial IDs: `ls /dev/serial/by-id/` and replace the `serial:` lines in
  `config/`. If you use CAN, replace the `canbus_uuid`.
- Check every pin against your wiring (steppers, heaters, thermistors, fans,
  endstops).

### 8. Moonraker

Merge `moonraker/moonraker.example.conf` into your `moonraker.conf`, but only
the sections for what is installed: `[spoolman]` only with Spoolman (step 5),
`[timelapse]` only with moonraker-timelapse, each `[update_manager ...]` only
if that module is installed. Then:

```bash
sudo systemctl restart moonraker
```

**Expected result:** Mainsail shows no Moonraker warnings (bell icon /
notifications); with Spoolman the Spoolman panel appears on the dashboard.

### 9. First start

`FIRMWARE_RESTART` in the Mainsail console.

**Expected result:**
- Klipper is *ready*, no config error. An error names the file and section;
  see [TROUBLESHOOTING.md](TROUBLESHOOTING.md).
- `LC_PA_SHOW` answers (macros from this repo are loaded).
- `CAL_CHECK_OFFSETS` answers (Bondtech's calibration macros are loaded).
- `G28 X Y` homes X and Y.

**Do not home Z yet.** Z is homed with the load cell (the nozzle is the
probe), and it has to be calibrated first:
[CALIBRATION.md](CALIBRATION.md), step 1.

## Updates later

```bash
cd ~/indx-trident-350 && git pull
```

Then do **not** simply copy everything again as in step 2. That overwrites
your adaptations from the setup:
- `printer.cfg` loses its `SAVE_CONFIG` block,
- without Spoolman (step 5) `macros/spoolman.cfg` is back and
  `variable_use_spoolman` is `1` again, so every tool change aborts,
- the `/home/pi` paths (step 6) are reset,
- serial IDs, CAN UUID and pins in `config/` (step 7) are the originals again.

Compare first and take over only what you want. This lists only repo files
that changed or are new (files that exist only in your config folder, such as
`moonraker.conf` or Bondtech's `indx/` files, are filtered out):

```bash
diff -rq ~/indx-trident-350/klipper/ ~/printer_data/config/ | grep -v "^Only in $HOME/printer_data"
```

Then look at single files with `diff`, e.g.
`diff ~/indx-trident-350/klipper/macros/filament_menu.cfg ~/printer_data/config/macros/filament_menu.cfg`.

If you do copy everything: back up first, then restore the `SAVE_CONFIG`
block from the backup and repeat steps 5–7. The KlipperScreen add-on and the
nozzle camera page are copies too: copy them again as described in their
guides if they changed.
