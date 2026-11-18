# KlipperScreen and the load/unload dialog

[Deutsche Version → KLIPPERSCREEN.de.md](KLIPPERSCREEN.de.md) ·
[README](../README.md)

KlipperScreen only sees one `[extruder]`, so it shows no T0–T8 buttons, and its
Load/Unload buttons send a bare `LOAD_FILAMENT` / `UNLOAD_FILAMENT`. This repo
adds two parts:

| Part | File | Needs |
|---|---|---|
| Load/unload dialog | `macros/filament_menu.cfg` | base installation only; works in KlipperScreen **and** Mainsail |
| KlipperScreen add-on | `klipperscreen/indx_addon.py` | KlipperScreen with add-on support (`enable_addons`), written against v0.4.7-215 |

## Load/unload dialog

A *macro prompt* is a dialog that a macro opens in Mainsail and KlipperScreen.
Labels in the dialog and the add-on:

| Label | Meaning |
|---|---|
| *Without spool* | choose a material preset instead of a Spoolman spool |
| *Back* / *Cancel* | back / cancel |
| *Loaded* / *Empty* | tool has filament / is empty |
| *Park* | put the active tool back into its dock |
| *Load* / *Unload* | load / unload filament (opens the dialog) |

- **`LOAD_FILAMENT` without parameters** (also KlipperScreen's *Load* button):
  1. choose the tool (the active tool is highlighted),
  2. with Spoolman: choose the material, then the spool. The list is sorted by
     vendor and name and scrolls; spools already in another tool are marked.
     The spool is assigned to the tool and its nozzle temperature is used.
     The button *Without spool* shows the material presets instead,
  3. without Spoolman (`variable_use_spoolman: 0`): choose the material
     preset.

  The tool is picked up, heated over the purge bucket and loaded.
- **`UNLOAD_FILAMENT` without parameters:** choose the tool; it is unloaded
  and its spool assignment cleared.
- With parameters the macros run directly, e.g.
  `LOAD_FILAMENT TOOL=3 TYPE=PETG` or `UNLOAD_FILAMENT TOOL=3`.

The spool list comes from `scripts/spool_picker/spool_picker.py` via
Moonraker's Spoolman proxy. If Spoolman cannot be reached, the dialog falls
back to the material presets.

**Check:** type `LOAD_FILAMENT` in the Mainsail console: the tool dialog
opens. *Cancel* closes it without doing anything.

## KlipperScreen add-on (optional)

The dialog above works without it. Install the add-on only if you want the
INDX panel and the active tool in the titlebar.

- **Titlebar:** the active tool ("T3") with the colour of its spool. Tap it to
  open the INDX panel.
- **INDX panel** (main menu → *INDX*): one button per tool with spool colour
  and name, *Loaded* / *Empty*, the active tool highlighted. Tap a tool to
  pick it up. Below: *Park*, *Load*, *Unload* (load/unload open the dialog
  above). The panel is only in the main menu, not while printing.

The loaded state (`t<n>__loaded`) is set by `LOAD_FILAMENT` /
`UNLOAD_FILAMENT`. After loading or unloading by hand, correct it with
`SET_TOOL_LOADED T=<n> LOADED=<0|1>`.

### Install

1. Copy the add-on into the config folder (from the clone, see
   [INSTALLATION.md](INSTALLATION.md), step 2):
   ```bash
   mkdir -p ~/printer_data/config/klipperscreen && cp ~/indx-trident-350/klipperscreen/indx_addon.py ~/printer_data/config/klipperscreen/
   ```
2. Link it into KlipperScreen's add-on folder (ignored by KlipperScreen's
   git, so updates keep working):
   ```bash
   mkdir -p ~/KlipperScreen/addons && ln -sf ~/printer_data/config/klipperscreen/indx_addon.py ~/KlipperScreen/addons/indx.py
   ```
3. Merge `klipperscreen/KlipperScreen.example.conf` into
   `~/printer_data/config/KlipperScreen.conf`, above the auto-generated block:
   `enable_addons: True` in `[main]`, the `[menu __main indx]` entry, and
   `spool` in `titlebar_items`. The example uses the section
   `[printer INDX-Trident]`; use the name of your own `[printer ...]` section.
4. Restart KlipperScreen:
   ```bash
   sudo systemctl restart KlipperScreen
   ```

**Check:** the titlebar shows "T" plus the active tool, the main menu has an
*INDX* entry. `grep -i indx ~/printer_data/logs/KlipperScreen.log` shows
"INDX add-on: installed".

**Updates:** the add-on in the config folder is a copy. After `git pull` in
the clone, copy it again (step 1) and restart KlipperScreen. The link from
step 2 stays.

Problems: see [TROUBLESHOOTING.md](TROUBLESHOOTING.md#klipperscreen-and-dialog).
