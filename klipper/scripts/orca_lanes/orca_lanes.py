#!/usr/bin/env python3
"""Spoolman-Spulen der INDX-Tools als Moonraker lane_data fuer OrcaSlicer.

Aufruf (ueber orca_lanes_launch.sh aus dem Makro _ORCA_LANES):
    orca_lanes.py 0=11 1=10 2=8 3=0 ...     <tool>=<spool_id>, 0 = keine Spule

Pro Tool n wird der Eintrag lane_data/lane<n> geschrieben:
    {"lane": "n", "material": "PLA", "color": "#RRGGBB",
     "filament_id": "PSM<filament_id>", "nozzle_temp": 215, "bed_temp": 60,
     "spool_id": 11}
Ein Tool ohne Spule bekommt material "" und gilt in Orca als leer.
filament_id passt zu den Profilen, die orca_spoolman_profiles.ps1 anlegt.

Spoolman wird ueber den Proxy von Moonraker abgefragt, die Adresse des
NAS steht also nur in moonraker.conf. Nur Python-Standardbibliothek.
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
    """Kurze Meldung in die Klipper-Konsole (Mainsail)."""
    msg = msg.replace('"', "'")
    try:
        call("POST", "/printer/gcode/script",
             {"script": 'RESPOND MSG="Orca-Lanes: %s"' % msg})
    except Exception as exc:  # Konsole ist nur Komfort
        print("RESPOND fehlgeschlagen:", exc)


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
            print("Ignoriere Argument:", arg)
    if not pairs:
        print(__doc__)
        return 2

    errors = 0
    for tool, sid in sorted(pairs):
        try:
            lane, text = lane_for(tool, sid)
        except Exception as exc:
            # Spule nicht gefunden oder Spoolman nicht erreichbar: Lane leeren,
            # damit Orca keine veraltete Farbe uebernimmt.
            errors += 1
            lane, text = {"lane": str(tool), "material": ""}, "FEHLER (%s)" % exc
            respond("T%d Spule %d nicht lesbar: %s" % (tool, sid, exc))
        call("POST", "/server/database/item",
             {"namespace": NAMESPACE, "key": "lane%d" % tool, "value": lane})
        print("T%d -> lane%d: %s %s" % (tool, tool, text, json.dumps(lane)))

    used = sum(1 for _, s in pairs if s > 0)
    respond("%d Tools uebertragen, %d mit Spule%s" % (
        len(pairs), used, (", %d Fehler (Log: orca_lanes.log)" % errors) if errors else ""))
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
