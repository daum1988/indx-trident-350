#!/usr/bin/env python3
# LC-PA Rohdaten-Aufnahme: Kraftverlauf der INDX-Load-Cell bei Vorschubspruengen
#
# Laeuft auf dem Pi, spricht direkt mit Kalico ueber den Klippy-Unix-Socket
# (kein Moonraker-Token noetig). Abonniert:
#   load_cell/dump_force      (load_cell=load_cell_probe)  -> 500 Hz Kraft
#   motion_report/dump_trapq  (name=extruder)              -> Soll-Bewegung E
# Beide Datenstroeme tragen print_time als Zeitstempel und lassen sich daher
# direkt uebereinanderlegen.
#
# Aufruf ueber das Makro LC_PA_RAW oder direkt per SSH:
#   python3 ~/printer_data/config/scripts/lc_pa/lc_pa_capture.py
#   python3 ... --pa 0.035 --seq 1:5,4:3,1:4,0:6
#
# Nur Python-Standardbibliothek.

import argparse
import bisect
import csv
import json
import math
import os
import socket
import sys
import threading
import time
import urllib.request

DEFAULT_SOCK = "/home/pi/printer_data/comms/klippy.sock"
DEFAULT_OUT = "/home/pi/printer_data/config/lc_pa_data"
# Vorschub-Sequenz: (Filament mm/s, Dauer s). 0 = Pause (G4).
DEFAULT_SEQ = "1:5,4:3,1:4,0:6,2:4,0:6,4:2,0:8"
MOONRAKER = "http://127.0.0.1:7125"
MAX_TOTAL_E = 60.0  # mm, Sicherheitsgrenze pro Lauf
FILAMENT_AREA = 2.405  # mm2 bei 1.75 mm


class KlippyError(Exception):
    pass


class Klippy:
    """Minimaler Client fuer den Klippy-API-Socket (JSON, mit 0x03 getrennt)."""

    def __init__(self, path):
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.connect(path)
        self.send_lock = threading.Lock()
        self.next_id = 1
        self.pending = {}
        self.handlers = {}
        self.closed = False
        threading.Thread(target=self._reader, daemon=True).start()

    def _reader(self):
        buf = b""
        while True:
            try:
                data = self.sock.recv(65536)
            except OSError:
                data = b""
            if not data:
                self.closed = True
                for ev in list(self.pending.values()):
                    ev[0].set()
                return
            buf += data
            parts = buf.split(b"\x03")
            buf = parts.pop()
            for p in parts:
                if not p:
                    continue
                try:
                    msg = json.loads(p)
                except ValueError:
                    continue
                mid = msg.get("id")
                if mid is not None and mid in self.pending:
                    ev = self.pending[mid]
                    ev[1] = msg
                    ev[0].set()
                    continue
                key = msg.get("stream")
                cb = self.handlers.get(key)
                if cb is not None:
                    try:
                        cb(msg.get("params", {}))
                    except Exception as e:  # nie den Reader-Thread sterben lassen
                        print("Handler-Fehler:", e, file=sys.stderr)

    def call(self, method, params=None, timeout=None):
        with self.send_lock:
            mid = self.next_id
            self.next_id += 1
            ev = [threading.Event(), None]
            self.pending[mid] = ev
            req = {"id": mid, "method": method, "params": params or {}}
            self.sock.sendall(json.dumps(req).encode() + b"\x03")
        if not ev[0].wait(timeout):
            self.pending.pop(mid, None)
            raise KlippyError("Timeout bei %s" % method)
        self.pending.pop(mid, None)
        msg = ev[1]
        if msg is None:
            raise KlippyError("Verbindung zu Klippy getrennt")
        if "error" in msg:
            err = msg["error"]
            raise KlippyError(err.get("message", str(err)) if isinstance(err, dict) else str(err))
        return msg.get("result", {})

    def subscribe(self, method, params, key, cb):
        self.handlers[key] = cb
        p = dict(params)
        p["response_template"] = {"stream": key}
        return self.call(method, p, timeout=5)

    def gcode(self, script, timeout=None):
        return self.call("gcode/script", {"script": script}, timeout)

    def respond(self, text):
        # Mainsail zeigt Konsolentext als HTML: < > wuerden verschluckt
        text = (text.replace('"', "'").replace(";", ",").replace("#", "Nr.")
                .replace("<", "(").replace(">", ")"))
        try:
            self.gcode('RESPOND MSG="LC_PA: %s"' % text, timeout=10)
        except KlippyError:
            pass
        print(text, flush=True)


def parse_seq(s):
    seq = []
    for part in s.split(","):
        v, d = part.split(":")
        v, d = float(v), float(d)
        if v < 0 or v > 8 or d <= 0 or d > 20:
            raise ValueError("Segment %s ausserhalb 0-8 mm/s bzw. 0-20 s" % part)
        seq.append((v, d))
    return seq


class Recorder:
    def __init__(self):
        self.lock = threading.Lock()
        self.force = []  # (print_time, force_g, counts)
        self.moves = {}  # start_time -> move tuple
        self.lc_errors = 0
        self.lc_overflows = 0

    def on_force(self, params):
        rows = params.get("data") or []
        with self.lock:
            self.lc_errors += params.get("errors") or 0
            self.lc_overflows += params.get("overflows") or 0
            for r in rows:
                if r[1] is None:
                    continue
                self.force.append((r[0], r[1], r[2]))

    def on_trapq(self, params):
        with self.lock:
            for m in params.get("data") or []:
                self.moves[m[0]] = m

    def last_force(self, seconds):
        with self.lock:
            if not self.force:
                return []
            tend = self.force[-1][0]
            i = len(self.force) - 1
            while i > 0 and self.force[i - 1][0] >= tend - seconds:
                i -= 1
            return [f for _, f, _ in self.force[i:]]


def mean(xs):
    return sum(xs) / len(xs) if xs else float("nan")


def wait_settled(kl, rec, tol, timeout):
    """Wartet, bis sich der Mittelwert ueber 1,5 s um weniger als tol g aendert."""
    t0 = time.time()
    prev = None
    while time.time() - t0 < timeout:
        time.sleep(1.5)
        cur = rec.last_force(1.5)
        if len(cur) < 100:
            continue
        m = mean(cur)
        if prev is not None and abs(m - prev) < tol:
            return True, m, time.time() - t0
        prev = m
    return False, prev, time.time() - t0


def eval_moves(moves, t):
    """Sollposition/-geschwindigkeit des Extruders zu print_time t (ohne PA)."""
    starts = [m[0] for m in moves]
    i = bisect.bisect_right(starts, t) - 1
    if i < 0:
        m = moves[0]
        return m[4][0], 0.0
    m = moves[i]
    st, dur, sv, acc, sp, dr = m
    dt = min(t - st, dur)
    pos = sp[0] + (sv * dt + 0.5 * acc * dt * dt) * dr[0]
    vel = (sv + acc * dt) * dr[0] if t - st <= dur else 0.0
    return pos, vel


# ---------------------------------------------------------------------------
# Auswertung
# ---------------------------------------------------------------------------
# Modell pro Vorschubsprung (gemessen an T0, PLA 230 C, 16 Spruenge):
#   F(t) = F_vor + A * Sprung(t - d) + B * (1 - exp(-(t - d) / tau))
#   A   = sofortiger Anteil (Reibung/Antrieb, folgt dem Vorschub ohne Verzug)
#   B   = Duesendruck, folgt dem Vorschub mit der Zeitkonstante tau
# Im linearen Kompressionsmodell ist der ideale Klipper/Kalico-PA-Wert = tau
# (PA schiebt K * v_e zusaetzlich nach, genau das Volumen, das im Druck
# gespeichert ist). Spruenge aus dem Stillstand werden nicht verwendet, sie
# verhalten sich anders (Anfahren, Restkraft nach dem Stopp).

FIT_WINDOW = 0.4  # s nach dem Sprung
TAU_GRID = [0.008 * 1.03 ** i for i in range(0, 140)]  # 8 ms .. ~0.5 s, Schritt 3 %
DELAY_GRID = [i * 0.002 for i in range(0, 8)]  # 0 .. 14 ms


def fit_step(rows_t, rows_f, ts, window=FIT_WINDOW):
    i0 = bisect.bisect_left(rows_t, ts - 0.4)
    i1 = bisect.bisect_left(rows_t, ts - 0.01)
    i2 = bisect.bisect_left(rows_t, ts + window)
    if i1 - i0 < 50 or i2 - i1 < 50:
        return None
    pre = mean(rows_f[i0:i1])
    tt = [t - ts for t in rows_t[i1:i2]]
    yy = [f - pre for f in rows_f[i1:i2]]
    n = len(yy)
    best = None
    for d in DELAY_GRID:
        for tau in TAU_GRID:
            s11 = s12 = s22 = y1 = y2 = 0.0
            for u, y in zip(tt, yy):
                u -= d
                if u < 0:
                    continue
                e = 1.0 - math.exp(-u / tau)
                s11 += 1.0
                s12 += e
                s22 += e * e
                y1 += y
                y2 += e * y
            den = s11 * s22 - s12 * s12
            if abs(den) < 1e-9:
                continue
            a = (y1 * s22 - y2 * s12) / den
            b = (s11 * y2 - s12 * y1) / den
            err = 0.0
            for u, y in zip(tt, yy):
                u -= d
                if u < 0:
                    r = y
                else:
                    r = a + b * (1.0 - math.exp(-u / tau)) - y
                err += r * r
            err /= n
            if best is None or err < best[0]:
                best = (err, d, tau, a, b)
    if best is None:
        return None
    err, d, tau, a, b = best
    return {"ts": ts, "pre": pre, "tau": tau, "delay": d, "instant": a,
            "delayed": b, "rms": math.sqrt(err)}


def analyze(rows, moves):
    """Fittet alle Spruenge zwischen zwei Konstantfahrten mit v > 0."""
    rows_t = [r[0] for r in rows]
    rows_f = [r[1] for r in rows]
    cruise = [m for m in moves if m[3] == 0 and m[1] > 0.8 and m[2] > 0]
    fits = []
    prev_end = None
    for a, b in zip(cruise, cruise[1:]):
        # erste Konstantfahrt nach einer Pause: Druck baut sich noch auf -> nicht auswerten
        first_in_block = prev_end is None or a[0] - prev_end > 0.05
        prev_end = a[0] + a[1]
        if first_in_block or b[0] - (a[0] + a[1]) > 0.05:
            continue  # Pause davor oder dazwischen -> Anfahren aus dem Stillstand
        v1, v2 = a[2] * a[5][0], b[2] * b[5][0]
        if abs(v2 - v1) < 0.5:
            continue
        ts = a[0] + a[1]  # Ende der alten Konstantfahrt (Bremsen/Beschleunigen ~5 ms)
        f = fit_step(rows_t, rows_f, ts)
        if f is None:
            continue
        f["v1"], f["v2"] = v1, v2
        # Plausibilitaet: Druckanteil muss in Richtung des Sprungs zeigen und
        # deutlich ueber dem Rauschen liegen, tau nicht am Rand des Rasters
        sign = -1.0 if v2 > v1 else 1.0  # mehr Vorschub -> Kraft sinkt
        f["ok"] = (f["delayed"] * sign > 60 and f["rms"] < 40
                   and TAU_GRID[1] < f["tau"] < TAU_GRID[-2])
        fits.append(f)
    return fits


def median(xs):
    s = sorted(xs)
    n = len(s)
    if not n:
        return float("nan")
    return s[n // 2] if n % 2 else 0.5 * (s[n // 2 - 1] + s[n // 2])


# ---------------------------------------------------------------------------
# Messung
# ---------------------------------------------------------------------------
# Phase 1: Vorspuelen 12 mm (fuellt die Duese, liefert das Kraftniveau bei 2 mm/s)
PRIME_SEQ = "2:6"
V_MAX = 4.0  # mm/s Filament, obere Grenze der Spruenge
V_MIN_HI = 1.0  # darunter ist das Signal zu klein
LOW_RATIO = 0.375  # niedriger Vorschub = 0.375 * hoher (wie 1.5 <-> 4)
DEFAULT_PRELOAD = 1100.0  # g, kleinste Vorspannung laut INDX (1100-1900 g)


def seat_preload(kl):
    """Sitz-Vorspannung des aktiven Tools aus der letzten INDX-Sitzkontrolle."""
    try:
        st = kl.call("objects/query", {"objects": {"gcode_macro _INDX_SEAT_CHECK": ["force_g"]}},
                     timeout=5)["status"]
        g = abs(float(st["gcode_macro _INDX_SEAT_CHECK"]["force_g"]))
    except (KlippyError, KeyError, TypeError, ValueError):
        g = 0.0
    # 0 nach einem Neustart oder ohne Pickup in dieser Sitzung -> vorsichtiger Standard
    return g if g >= 680.0 else DEFAULT_PRELOAD


def make_plan(kl, preload):
    """Waehlt die Sprunghoehe so, dass die Kraft bei etwa der halben Vorspannung bleibt.

    Ueber der Vorspannung hebt der Duesendruck das Tool im Sitz an (T1/T2 bei
    ~2000 g: Zeitkonstante verfaelscht, Nullpunkt danach verschoben).
    """
    def plan(level):
        limit = 0.5 * preload
        if not level == level or level < 40:  # NaN oder kein Druckaufbau
            kl.respond("Abbruch - beim Vorspuelen kaum Kraft (%.0f g). Filament geladen, Duese frei?" % level)
            return None
        v_hi = min(V_MAX, 2.0 * limit / level)
        v_hi = math.floor(v_hi * 10) / 10.0
        if v_hi < V_MIN_HI:
            kl.respond("Abbruch - schon bei 2 mm/s %.0f g Duesendruck (Vorspannung %.0f g). "
                       "Duese teilweise verstopft, Temperatur zu niedrig oder falsches Filament?"
                       % (level, preload))
            return None
        v_lo = round(LOW_RATIO * v_hi, 2)
        kl.respond("Vorspuelen: %.0f g bei 2 mm/s, Vorspannung %.0f g -> Spruenge %.2f <-> %.1f mm/s"
                   % (level, preload, v_lo, v_hi))
        # v_lo 4 s zum Wiederaufbau des Drucks (wird nicht ausgewertet), dann 4x hoch/runter
        return [(v_lo, 4.0)] + [(v_hi, 1.5), (v_lo, 1.5)] * 4
    return plan


def query(kl):
    st = kl.call("objects/query", {"objects": {
        "extruder": ["temperature", "target", "pressure_advance", "smooth_time"],
        "save_variables": ["variables"],
        "toolhead": ["homed_axes"],
    }}, timeout=5)["status"]
    tool = (st.get("save_variables", {}).get("variables", {}) or {}).get("active_tool", -1)
    try:
        tool = int(tool)
    except (TypeError, ValueError):
        tool = -1
    return st["extruder"], tool


def seq_to_gcode(seq):
    g = []
    for v, d in seq:
        if v <= 0:
            g.append("G4 P%d" % int(d * 1000))
        else:
            g.append("G1 E%.3f F%.1f" % (v * d, v * 60.0))
    return g


def measure(kl, rec, args, tool, seq_str, pa, label, plan=None):
    """Eine Messung am aktiven Tool. Gibt (rows, moves, meta) zurueck oder None.

    Mit plan: seq_str ist nur das Vorspuelen. Danach wird plan(kraft_g) mit dem
    Kraftniveau am Ende des Vorspuelens aufgerufen und liefert die eigentliche
    Sprungsequenz (oder None = abbrechen).
    """
    seq = parse_seq(seq_str)
    total_e = sum(v * d for v, d in seq)
    if total_e > MAX_TOTAL_E:
        raise KlippyError("Sequenz wuerde %.0f mm extrudieren (max %.0f)" % (total_e, MAX_TOTAL_E))
    ex, act = query(kl)
    if act != tool:
        kl.respond("Abbruch - T%d erwartet, im Kopf ist T%d." % (tool, act))
        return None
    if ex["temperature"] < args.min_temp:
        kl.respond("Abbruch - T%d hat nur %.0f C, mindestens %.0f C noetig (z.B. M109 S210)."
                   % (tool, ex["temperature"], args.min_temp))
        return None
    old_pa = ex.get("pressure_advance", 0.0)
    old_st = ex.get("smooth_time", 0.04)
    kl.respond("T%d, %.0f C, PA waehrend Messung %.3f, %.0f mm Filament, Sequenz %s"
               % (tool, ex["temperature"], pa, total_e, seq_str))

    lines = ["SAVE_GCODE_STATE NAME=_lc_pa_state"]
    if not args.no_bucket:
        lines.append("MOVE_TO_BUCKET")
    lines.append("M400")
    kl.gcode("\n".join(lines), timeout=120)

    kl.respond("warte auf ruhigen Nullpunkt (max %.0f s) ..." % args.settle_timeout)
    ok, _, waited = wait_settled(kl, rec, args.settle_tol, args.settle_timeout)
    if not ok:
        kl.respond("Warnung - Kraft nach %.0f s noch nicht ruhig, messe trotzdem." % waited)

    f_settled = mean(rec.last_force(1.5))
    with rec.lock:
        t_mark = rec.force[-1][0] if rec.force else 0.0
        err0, ovf0 = rec.lc_errors, rec.lc_overflows
    try:
        if plan is not None:
            # Phase 1: Vorspuelen mit M400, Kraftniveau am Ende messen
            kl.gcode("\n".join(["M83", "SET_PRESSURE_ADVANCE ADVANCE=%.4f" % pa, "G4 P3000"]
                               + seq_to_gcode(seq) + ["M400"]),
                     timeout=sum(d for _, d in seq) + 60)
            time.sleep(0.4)  # Load-Cell-Daten laufen etwas nach
            with rec.lock:
                tl = rec.force[-1][0] if rec.force else 0.0
                lvl = [f for t, f, _ in rec.force if tl - 1.6 <= t < tl - 0.5]
            level = abs(mean(lvl) - f_settled) if lvl else float("nan")
            # Phase 2: Spruenge mit angepasster Geschwindigkeit
            seq2 = plan(level)
            if seq2 is None:
                return None
            total_e += sum(v * d for v, d in seq2)
            if total_e > MAX_TOTAL_E + 15:
                raise KlippyError("Sequenz wuerde %.0f mm extrudieren" % total_e)
            seq_str += " + " + ",".join("%g:%g" % s for s in seq2)
            seq = seq2
            g = []
        else:
            g = ["M83", "SET_PRESSURE_ADVANCE ADVANCE=%.4f" % pa, "G4 P3000"]
        g += seq_to_gcode(seq) + ["G4 P2000", "M400"]
        kl.gcode("\n".join(g), timeout=sum(d for _, d in seq) + 60)
    finally:
        try:
            kl.gcode("SET_PRESSURE_ADVANCE ADVANCE=%.4f SMOOTH_TIME=%.4f\n"
                     "RESTORE_GCODE_STATE NAME=_lc_pa_state" % (old_pa, old_st), timeout=10)
        except KlippyError as e:
            print("PA konnte nicht zurueckgesetzt werden:", e, file=sys.stderr)
    time.sleep(1.0)  # letzte Batches abwarten

    with rec.lock:
        force = [r for r in rec.force if r[0] >= t_mark - 4.0]
        # nur E-Bewegungen dieser Messung (trapq liefert auch aeltere Historie)
        moves = sorted((m for m in rec.moves.values() if m[0] >= t_mark),
                       key=lambda m: m[0])
        lc_err, lc_ovf = rec.lc_errors - err0, rec.lc_overflows - ovf0
        rec.force = []  # Speicher fuer das naechste Tool freigeben
    if not moves or not force:
        kl.respond("Abbruch - keine Daten empfangen (Kraft %d, E-Moves %d)." % (len(force), len(moves)))
        return None
    ext = [m for m in moves if abs(m[3]) > 0 or m[2] > 0]
    t_e0 = ext[0][0] if ext else moves[0][0]
    rows = [r for r in force if r[0] >= t_e0 - 4.0]
    f_base = mean([f for t, f, _ in rows if t_e0 - 2.5 <= t < t_e0 - 0.2])

    os.makedirs(args.out, exist_ok=True)
    stamp = time.strftime("%Y%m%d_%H%M%S")
    base = os.path.join(args.out, "lcpa_%s_T%d_%s" % (label, tool, stamp))
    with open(base + ".csv", "w", newline="") as fh:
        fh.write("# LC-PA Rohdaten, Tool T%d, %s\n" % (tool, stamp))
        fh.write("# temp_C=%.1f pa_during=%.4f pa_before=%.4f smooth_time=%.4f seq=%s\n"
                 % (ex["temperature"], pa, old_pa, old_st, seq_str))
        fh.write("# t_s relativ zum Start der ersten E-Bewegung, force_rel_g = force_g - Grundwert (%.1f g)\n" % f_base)
        fh.write("# e_pos/e_vel = Soll-Extruderbewegung ohne PA (aus trapq)\n")
        fh.write("# lc_errors=%d lc_overflows=%d settle_ok=%s settle_wait_s=%.1f\n"
                 % (lc_err, lc_ovf, ok, waited))
        w = csv.writer(fh)
        w.writerow(["t_s", "print_time", "force_g", "force_rel_g", "counts", "e_pos_mm", "e_vel_mm_s"])
        for t, f, c in rows:
            pos, vel = eval_moves(moves, t)
            w.writerow(["%.5f" % (t - t_e0), "%.5f" % t, "%.2f" % f, "%.2f" % (f - f_base),
                        c, "%.4f" % pos, "%.3f" % vel])
    with open(base + "_moves.csv", "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["t_s", "print_time", "duration", "start_velocity", "acceleration",
                    "start_e", "direction_e"])
        for m in moves:
            w.writerow(["%.5f" % (m[0] - t_e0), "%.5f" % m[0], "%.5f" % m[1], "%.4f" % m[2],
                        "%.2f" % m[3], "%.4f" % m[4][0], "%.0f" % m[5][0]])
    if lc_ovf or lc_err:
        kl.respond("Hinweis - Load Cell meldete %d Fehler / %d Overflows." % (lc_err, lc_ovf))
    max_dev = max(abs(f - f_base) for t, f, _ in rows if t >= t_e0)
    meta = {"base": base, "f_base": f_base, "temp": ex["temperature"], "t_e0": t_e0,
            "max_dev": max_dev}
    return rows, moves, meta


def plateau_summary(rows, moves, f_base):
    summary = []
    for m in moves:
        if m[3] == 0 and m[1] >= 1.2 and m[2] > 0:
            te = m[0] + m[1]
            vals = [f for t, f, _ in rows if te - 1.0 <= t < te]
            summary.append("%.1f mm/s: %+.0f g" % (m[2] * m[5][0], mean(vals) - f_base))
    return summary


def run_raw(kl, rec, args):
    _, tool = query(kl)
    if tool < 0:
        kl.respond("Abbruch - kein Tool im Kopf.")
        return 1
    res = measure(kl, rec, args, tool, args.seq, args.pa, "raw")
    if res is None:
        return 1
    rows, moves, meta = res
    rate = len(rows) / max(rows[-1][0] - rows[0][0], 1e-6)
    kl.respond("fertig, %d Samples (%.0f Hz). Grundwert %.0f g. Plateaus: %s"
               % (len(rows), rate, meta["f_base"],
                  ", ".join(plateau_summary(rows, moves, meta["f_base"])) or "-"))
    kl.respond("Datei: lc_pa_data/%s.csv" % os.path.basename(meta["base"]))
    return 0


def evaluate(kl, tool, rows, moves, meta):
    """Fit + Bewertung fuer ein Tool. Gibt PA oder None zurueck."""
    fits = analyze(rows, moves)
    good = [f for f in fits if f["ok"]]
    with open(meta["base"] + "_fit.csv", "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["t_s", "v1", "v2", "tau_ms", "delay_ms", "instant_g", "delayed_g", "rms_g", "ok"])
        for f in fits:
            w.writerow(["%.3f" % (f["ts"] - meta["t_e0"]), "%.1f" % f["v1"], "%.1f" % f["v2"],
                        "%.1f" % (f["tau"] * 1000), "%.0f" % (f["delay"] * 1000),
                        "%.0f" % f["instant"], "%.0f" % f["delayed"], "%.1f" % f["rms"], int(f["ok"])])
    name = os.path.basename(meta["base"])
    if len(good) < 5:
        kl.respond("T%d: nur %d von %d Spruengen auswertbar - kein Ergebnis. Details: lc_pa_data/%s_fit.csv"
                   % (tool, len(good), len(fits), name))
        return None, False
    taus = sorted(f["tau"] for f in good)
    up = [f["tau"] for f in good if f["v2"] > f["v1"]]
    dn = [f["tau"] for f in good if f["v2"] < f["v1"]]
    pa = round(median(taus), 3)
    lo, hi = taus[len(taus) // 4], taus[(3 * len(taus)) // 4]
    # Gueltig nur bei enger Streuung, genug Spruengen, schneller/langsamer
    # aehnlich und einem fuer Direktantrieb plausiblen Wert
    reasons = []
    if len(good) < 6:
        reasons.append("nur %d Spruenge" % len(good))
    if (hi - lo) > 0.35 * pa:
        reasons.append("Streuung gross")
    if up and dn and max(median(up), median(dn)) > 1.6 * min(median(up), median(dn)):
        reasons.append("schneller/langsamer passen nicht zusammen")
    if not 0.005 <= pa <= 0.15:
        reasons.append("Wert unplausibel")
    preload = meta.get("preload")
    if preload and meta.get("max_dev", 0) > 0.8 * preload:
        reasons.append("Kraft %.0f g nahe an der Sitz-Vorspannung %.0f g" % (meta["max_dev"], preload))
    valid = not reasons
    quality = "gut" if valid else "UNSICHER (%s) - nicht uebernommen" % ", ".join(reasons)
    kl.respond("T%d: PA = %.3f  (Median aus %d Spruengen, mittlere Haelfte %.3f-%.3f, "
               "schneller %.3f / langsamer %.3f) - %s"
               % (tool, pa, len(good), lo, hi, median(up), median(dn), quality))
    kl.respond("Details: lc_pa_data/%s_fit.csv" % name)
    return pa, valid


# --- Spoolman (ueber den Proxy von Moonraker, NAS-Adresse steht nur in moonraker.conf)

def sm_call(method, path, body=None):
    req = {"request_method": method, "path": path, "use_v2_response": True}
    if body is not None:
        req["body"] = body
    r = urllib.request.Request(MOONRAKER + "/server/spoolman/proxy",
                               data=json.dumps(req).encode(), method="POST",
                               headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(r, timeout=10) as resp:
        res = json.loads(resp.read().decode() or "{}")
    res = res.get("result", res)
    if isinstance(res, dict) and "response" in res:
        if res.get("error"):
            raise RuntimeError(str(res["error"]))
        return res["response"]
    return res


def tool_vars(kl, tool):
    """Spule und Duesendurchmesser des Tools aus save_variables."""
    st = kl.call("objects/query", {"objects": {"save_variables": ["variables"]}}, timeout=5)
    var = (st["status"].get("save_variables", {}) or {}).get("variables", {}) or {}
    try:
        sid = int(var.get("t%d__spool_id" % tool) or 0)
    except (TypeError, ValueError):
        sid = 0
    try:
        noz = float(var.get("t%d_nozzle" % tool) or 0)
    except (TypeError, ValueError):
        noz = 0.0
    return sid, noz


def nozzle_str(d):
    return ("%.2f" % d).rstrip("0").rstrip(".")


def spoolman_write(kl, tool, pa, noz):
    """PA ins Filament der Spule im Tool schreiben, ein Zusatzfeld je Duesengroesse
    in Spoolman schon vorhanden: pressure_advance_d025 / _d04 / _d06 ("Pressure
    Advance 0.4er Duese"), weitere Groessen werden im selben Schema angelegt.
    Ohne hinterlegte Duese wird nichts geschrieben."""
    sid, _ = tool_vars(kl, tool)
    if sid <= 0:
        kl.respond("T%d hat keine Spule zugeordnet (SET_TOOL_SPOOL) - Spoolman nicht aktualisiert." % tool)
        return
    if noz <= 0:
        kl.respond("T%d Duesendurchmesser unbekannt (SET_TOOL_NOZZLE TOOL=%d D=0.4) - Spoolman nicht aktualisiert."
                   % (tool, tool))
        return
    ns = nozzle_str(noz)
    key = "pressure_advance_d" + ns.replace(".", "")
    try:
        fields = sm_call("GET", "/v1/field/filament") or []
        if not any(f.get("key") == key for f in fields):
            sm_call("POST", "/v1/field/filament/" + key,
                    {"name": "Pressure Advance %ser Duese" % ns, "field_type": "float", "unit": "s"})
        fil = (sm_call("GET", "/v1/spool/%d" % sid) or {}).get("filament") or {}
        if fil.get("id") is None:
            raise RuntimeError("Spule %d ohne Filament" % sid)
        extra = dict(fil.get("extra") or {})
        old = extra.get(key)
        extra[key] = json.dumps(round(pa, 3))  # Spoolman: Werte sind JSON-Strings
        sm_call("PATCH", "/v1/filament/%d" % int(fil["id"]), {"extra": extra})
        name = " ".join(x for x in ((fil.get("vendor") or {}).get("name"), fil.get("name")) if x)
        kl.respond("Spoolman: %s (Spule %d) PA %s mm = %.3f%s" % (
            name or "Filament %d" % fil["id"], sid, ns, pa,
            (" (vorher %s)" % old) if old else ""))
    except Exception as e:  # Spoolman ist Zusatz, die Messung bleibt gueltig
        kl.respond("Spoolman nicht aktualisiert: %s" % e)


def run_cal(kl, rec, args):
    tools = [int(t) for t in args.tools.split(",") if t.strip() != ""]
    results = []
    for tool in tools:
        ex, act = query(kl)
        # frisch aufgenommen: INDX heizt beim Pickup schon auf, die Schmelzzone
        # ist trotzdem noch nicht durchgewaermt
        cold = act != tool or ex["temperature"] < args.temp - 15
        if act != tool:
            kl.respond("wechsle zu T%d ..." % tool)
            kl.gcode("CHANGE_TOOL TOOL=%d" % tool, timeout=300)
        kl.respond("heize T%d auf %.0f C ..." % (tool, args.temp))
        kl.gcode("M109 S%.0f" % args.temp, timeout=600)
        if cold and args.soak > 0:
            # Induktion erreicht die Solltemperatur am Sensor in Sekunden, die
            # Schmelzzone braucht laenger (T1/T2 frisch aufgeheizt: Druck
            # driftete waehrend der ganzen Messung)
            kl.respond("T%d frisch aufgeheizt - %.0f s durchwaermen ..." % (tool, args.soak))
            kl.gcode("G4 P%d" % int(args.soak * 1000), timeout=args.soak + 30)
        preload = seat_preload(kl)
        res = measure(kl, rec, args, tool, args.seq or PRIME_SEQ, 0.0, "cal",
                      plan=None if args.seq else make_plan(kl, preload))
        if res is not None:
            res[2]["preload"] = preload
        pa, valid = evaluate(kl, tool, *res) if res is not None else (None, False)
        if not valid:
            pa = None
        if pa is not None and args.save:
            _, noz = tool_vars(kl, tool)
            kl.gcode("SAVE_VARIABLE VARIABLE=t%d_pa VALUE=%.3f\n"
                     "SAVE_VARIABLE VARIABLE=t%d_pa_temp VALUE=%.0f"
                     % (tool, pa, tool, args.temp)
                     + ("\nSAVE_VARIABLE VARIABLE=t%d_pa_nozzle VALUE=%s" % (tool, nozzle_str(noz))
                        if noz > 0 else ""), timeout=10)
            if args.spoolman:
                spoolman_write(kl, tool, pa, noz)
        results.append((tool, pa))
    done = [(t, p) for t, p in results if p is not None]
    if done:
        kl.respond("Ergebnis: " + ", ".join("T%d %.3f" % tp for tp in done)
                   + (" - gespeichert (LC_PA_SHOW zeigt alle, LC_PA_APPLY setzt den Wert des aktiven Tools)."
                      if args.save else " - nicht gespeichert (SAVE=0)."))
        _, act = query(kl)
        for t, p in done:
            if t == act and args.save:
                kl.gcode("SET_PRESSURE_ADVANCE ADVANCE=%.3f" % p, timeout=10)
                kl.respond("PA %.3f fuer T%d ist jetzt aktiv." % (p, t))
    return 0 if len(done) == len(results) else 1


def main():
    ap = argparse.ArgumentParser(description="Pressure Advance per INDX-Load-Cell")
    ap.add_argument("--mode", choices=["raw", "cal"], default="raw")
    ap.add_argument("--socket", default=DEFAULT_SOCK)
    ap.add_argument("--out", default=DEFAULT_OUT)
    ap.add_argument("--load-cell", default="load_cell_probe")
    ap.add_argument("--seq", default=None, help="v:dauer,... (mm/s:s), v=0 ist Pause")
    ap.add_argument("--pa", type=float, default=0.0, help="raw: PA waehrend der Messung")
    ap.add_argument("--tools", default="", help="cal: Tools, z.B. 0 oder 0,1,2")
    ap.add_argument("--temp", type=float, default=0.0, help="cal: Duesentemperatur")
    ap.add_argument("--save", type=int, default=1, help="cal: Ergebnis per SAVE_VARIABLE speichern")
    ap.add_argument("--spoolman", type=int, default=1, help="cal: PA ins Spoolman-Filament schreiben (mit --save)")
    ap.add_argument("--cool", type=int, default=1, help="am Ende Heizung aus (M104 S0)")
    ap.add_argument("--soak", type=float, default=60.0, help="cal: Durchwaermzeit nach Aufheizen aus kalt (s)")
    ap.add_argument("--min-temp", type=float, default=180.0)
    ap.add_argument("--settle-tol", type=float, default=15.0, help="g pro 1,5 s")
    ap.add_argument("--settle-timeout", type=float, default=90.0)
    ap.add_argument("--no-bucket", action="store_true", help="nicht zum Bucket fahren")
    ap.add_argument("--analyze", nargs=2, metavar=("CSV", "MOVES_CSV"),
                    help="nur vorhandene Messung auswerten (ohne Drucker)")
    args = ap.parse_args()
    if args.analyze:
        return offline(args.analyze[0], args.analyze[1])
    if args.mode == "raw" and not args.seq:
        args.seq = DEFAULT_SEQ
    if args.seq:
        parse_seq(args.seq)  # frueh pruefen

    kl = Klippy(args.socket)
    rec = Recorder()
    try:
        kl.subscribe("load_cell/dump_force", {"load_cell": args.load_cell}, "lc", rec.on_force)
    except KlippyError as e:
        kl.respond("Abbruch - load_cell/dump_force nicht verfuegbar (%s)." % e)
        return 1
    kl.subscribe("motion_report/dump_trapq", {"name": "extruder"}, "eq", rec.on_trapq)
    try:
        if args.mode == "cal":
            if not args.tools or args.temp < args.min_temp:
                kl.respond("Abbruch - TOOL und TEMP (mind. %.0f C) angeben." % args.min_temp)
                return 1
            return run_cal(kl, rec, args)
        return run_raw(kl, rec, args)
    except KlippyError as e:
        kl.respond("Abbruch - %s" % e)
        return 2
    finally:
        # Auch nach Abbruch: Heizung des Tools im Kopf aus (COOL=0 laesst es heiss)
        if args.cool and not kl.closed:
            try:
                kl.gcode("M104 S0", timeout=10)
                kl.respond("Heizung aus, Tool kuehlt ab.")
            except KlippyError as e:
                print("Heizung konnte nicht ausgeschaltet werden:", e, file=sys.stderr)


class _Printer:
    def respond(self, text):
        print(text)


def offline(csv_path, moves_path):
    """Wertet eine gespeicherte Messung aus (CSV-Zeiten sind relativ, das reicht)."""
    rows, moves = [], []
    for line in open(csv_path):
        if line[0] in "#t":
            continue
        p = line.split(",")
        rows.append((float(p[0]), float(p[2]), int(p[4])))
    for line in open(moves_path):
        if line[0] == "t":
            continue
        p = line.split(",")
        moves.append((float(p[0]), float(p[2]), float(p[3]), float(p[4]),
                      (float(p[5]), 0.0, 0.0), (float(p[6]), 0.0, 0.0)))
    base = os.path.splitext(csv_path)[0]
    meta = {"base": base, "t_e0": 0.0}
    _, valid = evaluate(_Printer(), -1, rows, moves, meta)
    return 0 if valid else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (KlippyError, OSError, ValueError) as e:
        print("Fehler:", e, file=sys.stderr)
        sys.exit(2)
