#!/usr/bin/env python3
"""Spoolman spools of the INDX tools as Moonraker lane_data for OrcaSlicer.

Usage (via orca_lanes_launch.sh from the _ORCA_LANES macro):
    orca_lanes.py 0=11 1=10 2=8 3=0 ...     <tool>=<spool_id>, 0 = no spool

For each tool n the entry lane_data/lane<n> is written:
    {"lane": "n", "material": "PLA", "color": "#RRGGBB",
     "filament_id": "PSM<filament_id>", "nozzle_temp": 215, "bed_temp": 60,
     "spool_id": 11}
A tool without a spool gets material "" and counts as empty in Orca.
filament_id matches the profiles created by orca_spoolman_profiles.ps1.

Spoolman is queried via Moonraker's proxy, so the Spoolman address
is only in moonraker.conf. Python standard library only.
"""
import json
import sys
import urllib.request

MOONRAKER = "http://127.0.0.1:7125"
NAMESPACE = "lane_data"
TIMEOUT = 10


def call(method, path, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        MOONRAKER + path, data=data, method=method,
        headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        return json.loads(resp.read().decode() or "{}")


def respond(msg):
    """Short message to the Klipper console (Mainsail)."""
    msg = msg.replace('"', "'")
    try:
        call("POST", "/printer/gcode/script",
             {"script": 'RESPOND MSG="Orca-Lanes: %s"' % msg})
    except Exception as exc:  # console output is only a convenience
        print("RESPOND failed:", exc)


def get_spool(spool_id):
    res = call("POST", "/server/spoolman/proxy", {
        "request_method": "GET",
        "path": "/v1/spool/%d" % spool_id,
        "use_v2_response": True,
    })
    res = res.get("result", res)
    if isinstance(res, dict) and "response" in res:
        if res.get("error"):
            raise RuntimeError(str(res["error"]))
        return res["response"]
    return res


def first_color(fil):
    hexval = fil.get("color_hex") or ""
    if not hexval and fil.get("multi_color_hexes"):
        hexval = fil["multi_color_hexes"].split(",")[0]
    hexval = hexval.strip().lstrip("#")
    return ("#" + hexval.upper()[:6]) if len(hexval) >= 6 else ""


def lane_for(tool, spool_id):
    lane = {"lane": str(tool), "material": ""}
    if spool_id <= 0:
        return lane, "-"
    spool = get_spool(spool_id)
    fil = spool.get("filament") or {}
    lane["material"] = (fil.get("material") or "").strip() or "PLA"
    lane["spool_id"] = spool_id
    if fil.get("id") is not None:
        lane["filament_id"] = "PSM%d" % int(fil["id"])
    color = first_color(fil)
    if color:
        lane["color"] = color
    for src, dst in (("settings_extruder_temp", "nozzle_temp"),
                     ("settings_bed_temp", "bed_temp")):
        if fil.get(src):
            lane[dst] = int(fil[src])
    vendor = (fil.get("vendor") or {}).get("name") or ""
    label = " ".join(x for x in (vendor, fil.get("name") or "") if x)
    return lane, "%s %s" % (lane["material"], label or "#%d" % spool_id)


def main(argv):
    pairs = []
    for arg in argv:
        tool, _, sid = arg.partition("=")
        try:
            pairs.append((int(tool), int(sid or 0)))
        except ValueError:
            print("Ignoring argument:", arg)
    if not pairs:
        print(__doc__)
        return 2

    errors = 0
    for tool, sid in sorted(pairs):
        try:
            lane, text = lane_for(tool, sid)
        except Exception as exc:
            # Spool not found or Spoolman unreachable: clear the lane
            # so Orca does not pick up an outdated colour.
            errors += 1
            lane, text = {"lane": str(tool), "material": ""}, "ERROR (%s)" % exc
            respond("T%d spool %d not readable: %s" % (tool, sid, exc))
        call("POST", "/server/database/item",
             {"namespace": NAMESPACE, "key": "lane%d" % tool, "value": lane})
        print("T%d -> lane%d: %s %s" % (tool, tool, text, json.dumps(lane)))

    used = sum(1 for _, s in pairs if s > 0)
    respond("%d tools sent, %d with spool%s" % (
        len(pairs), used, (", %d errors (log: orca_lanes.log)" % errors) if errors else ""))
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
