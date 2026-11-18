#!/usr/bin/env python3
"""Spool selection dialog for LOAD_FILAMENT (KlipperScreen / Mainsail prompt).

Called by the _SPOOL_PICKER macro (macros/filament_menu.cfg) through
spool_picker_launch.sh:

    spool_picker.py --tool=3 --assigned=0=11,1=0,... --presets=PLA,PETG,...
                    --temp=250 [--material=PLA] [--page=0]

Reads the non-archived spools via Moonraker's Spoolman proxy and sends a
macro prompt back to Klipper:
  - several materials and no --material: one button per material
  - otherwise: a list with one row per spool (up to 40 per page), which runs
    LOAD_FILAMENT TOOL=<t> SPOOL=<id> [TYPE=<preset>] [TEMP=<filament temp>]
Spools already in another tool are marked with that tool. If Spoolman is not
reachable, the material preset dialog is shown instead.

Python standard library only.
"""
import argparse
import json
import re
import sys
import urllib.request

MOONRAKER = "http://127.0.0.1:7125"
TIMEOUT = 10
PER_PAGE = 40   # spool list (scrollable in KlipperScreen and Mainsail)
PER_ROW = 3     # material tiles


def call(method, path, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        MOONRAKER + path, data=data, method=method,
        headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        return json.loads(resp.read().decode() or "{}")


def gcode(lines):
    call("POST", "/printer/gcode/script", {"script": "\n".join(lines)})


def get_spools():
    res = call("POST", "/server/spoolman/proxy", {
        "request_method": "GET",
        "path": "/v1/spool?allow_archived=false",
        "use_v2_response": True,
    })
    res = res.get("result", res)
    if isinstance(res, dict) and "response" in res:
        if res.get("error"):
            raise RuntimeError(str(res["error"]))
        res = res["response"]
    return [s for s in res if not s.get("archived")]


def clean(text):
    """Text for a prompt label: no characters that break RESPOND/prompts."""
    text = re.sub(r'[|";{}\r\n]', " ", str(text))
    return re.sub(r"\s+", " ", text).strip()


def mat_key(material):
    """Material as a single G-code parameter word (no spaces)."""
    return re.sub(r"\s+", "_", material.strip().upper()) or "?"


def preset_for(material, presets):
    m = material.strip().upper()
    if m in presets:
        return m
    best = ""
    for p in presets:
        if m.startswith(p) and len(p) > len(best):
            best = p
    return best


def cmd(text):
    return 'RESPOND TYPE=command MSG="action:%s"' % text


def rows(buttons, per_row=PER_ROW):
    """buttons: list of (label, gcode, colour) -> prompt lines.
    per_row=None: no button groups, one full-width row per button (list)."""
    if not per_row:
        return [cmd("prompt_button %s|%s|%s" % b) for b in buttons]
    out = []
    for i in range(0, len(buttons), per_row):
        out.append(cmd("prompt_button_group_start"))
        for label, gc, colour in buttons[i:i + per_row]:
            out.append(cmd("prompt_button %s|%s|%s" % (label, gc, colour)))
        out.append(cmd("prompt_button_group_end"))
    return out


def material_of(spool):
    return ((spool.get("filament") or {}).get("material") or "").strip() or "?"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tool", type=int, required=True)
    ap.add_argument("--assigned", default="")
    ap.add_argument("--presets", default="")
    ap.add_argument("--temp", type=int, default=250)
    ap.add_argument("--material", default="")
    ap.add_argument("--page", type=int, default=0)
    a = ap.parse_args()

    t = a.tool
    presets = [p.strip().upper() for p in a.presets.split(",") if p.strip()]
    assigned = {}
    for pair in a.assigned.split(","):
        tool, _, sid = pair.partition("=")
        try:
            if int(sid or 0) > 0:
                assigned[int(sid)] = int(tool)
        except ValueError:
            pass
    head = [cmd("prompt_end"), cmd("prompt_begin Load filament")]
    cancel = cmd("prompt_footer_button Cancel|_FIL_PROMPT_CLOSE|error")
    presets_btn = cmd(
        "prompt_footer_button Without spool|_FIL_PROMPT MODE=LOAD TOOL=%d PRESETS=1|secondary" % t)

    try:
        spools = get_spools()
    except Exception as exc:
        print("Spoolman not reachable:", exc)
        gcode(['RESPOND TYPE=error MSG="Spoolman not reachable, showing material presets."',
               "_FIL_PROMPT MODE=LOAD TOOL=%d PRESETS=1" % t])
        return 1

    materials = sorted({material_of(s) for s in spools},
                       key=lambda m: (-sum(material_of(s) == m for s in spools), m))
    lines = list(head)

    if not spools:
        gcode(['RESPOND MSG="Spoolman: no active spools, showing material presets."',
               "_FIL_PROMPT MODE=LOAD TOOL=%d PRESETS=1" % t])
        return 0

    if len(materials) > 1 and not a.material:
        # Step: material
        lines.append(cmd("prompt_text T%d: choose the material of the spool." % t))
        buttons = []
        for m in materials:
            count = sum(material_of(s) == m for s in spools)
            buttons.append(("%s (%d)" % (clean(m), count),
                            "_SPOOL_PICKER TOOL=%d MATERIAL=%s" % (t, mat_key(m)), "primary"))
        lines += rows(buttons)
        lines.append(cmd("prompt_footer_button Back|_FIL_PROMPT MODE=LOAD|secondary"))
    else:
        # Step: spool
        sel = [s for s in spools
               if not a.material or mat_key(material_of(s)) == a.material.upper()]
        # spool of this tool first, then free spools, then those in other tools;
        # within that the most recently used first
        cur = [sid for sid, tool in assigned.items() if tool == t]
        sel.sort(key=lambda s: (s.get("last_used") or "", s["id"]), reverse=True)
        sel.sort(key=lambda s: (s["id"] not in cur,
                                s["id"] in assigned and s["id"] not in cur))
        pages = max(1, (len(sel) + PER_PAGE - 1) // PER_PAGE)
        page = min(max(a.page, 0), pages - 1)
        part = sel[page * PER_PAGE:(page + 1) * PER_PAGE]
        title = clean(a.material.replace("_", " ")) if a.material else "the spool"
        lines.append(cmd("prompt_text T%d: choose the spool (%s)%s." % (
            t, title, (", page %d/%d" % (page + 1, pages)) if pages > 1 else "")))
        buttons = []
        for s in part:
            fil = s.get("filament") or {}
            vendor = (fil.get("vendor") or {}).get("name") or ""
            name = fil.get("name") or material_of(s)
            weight = s.get("remaining_weight")
            parts = [name] + ([vendor] if vendor else [])
            if weight is not None:
                parts.append("%d g" % round(weight))
            label = " - ".join(parts)
            colour = "primary"
            if s["id"] in cur:
                label += " (in T%d)" % t
                colour = "info"
            elif s["id"] in assigned:
                label += " (in T%d)" % assigned[s["id"]]
                colour = "warning"
            gc = "LOAD_FILAMENT TOOL=%d SPOOL=%d" % (t, s["id"])
            preset = preset_for(material_of(s), presets)
            if preset:
                gc += " TYPE=%s" % preset
            ftemp = fil.get("settings_extruder_temp")
            if ftemp:
                gc += " TEMP=%d" % int(ftemp)
            elif not preset:
                gc += " TEMP=%d" % a.temp
            buttons.append(("ID%d  %s" % (s["id"], clean(label)), gc, colour))
        lines += rows(buttons, per_row=None)
        if pages > 1:
            nxt = (page + 1) % pages
            lines.append(cmd("prompt_footer_button More|_SPOOL_PICKER TOOL=%d MATERIAL=%s PAGE=%d|secondary"
                             % (t, a.material or "", nxt)))
        back = ("_SPOOL_PICKER TOOL=%d" % t) if len(materials) > 1 else "_FIL_PROMPT MODE=LOAD"
        lines.append(cmd("prompt_footer_button Back|%s|secondary" % back))
    lines += [presets_btn, cancel, cmd("prompt_show")]
    gcode(lines)
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main())
