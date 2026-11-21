#!/usr/bin/env python3
# LC-PA capture: INDX load cell force curve during extruder feed steps
#
# Runs on the Pi and talks to Kalico directly via the Klippy unix socket
# (no Moonraker token needed). Subscribes to:
#   load_cell/dump_force      (load_cell=load_cell_probe)  -> 500 Hz force
#   motion_report/dump_trapq  (name=extruder)              -> commanded E motion
# Both streams carry print_time as timestamp, so they can be
# overlaid directly.
#
# Called via the LC_PA_RAW / PA_CAL_LOADCELL macros or directly via SSH:
#   python3 ~/printer_data/config/scripts/lc_pa/lc_pa_capture.py
#   python3 ... --pa 0.035 --seq 1:5,4:3,1:4,0:6
#
# Python standard library only.

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

# printer_data folder, derived from this file's location
# (<printer_data>/config/scripts/lc_pa/), so any user name works
PRINTER_DATA = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
DEFAULT_SOCK = os.path.join(PRINTER_DATA, "comms", "klippy.sock")
DEFAULT_OUT = os.path.join(PRINTER_DATA, "config", "lc_pa_data")
# Feed sequence: (filament mm/s, duration s). 0 = pause (G4).
DEFAULT_SEQ = "1:5,4:3,1:4,0:6,2:4,0:6,4:2,0:8"
MOONRAKER = "http://127.0.0.1:7125"
MAX_TOTAL_E = 60.0  # mm, safety limit per run
FILAMENT_AREA = 2.405  # mm2 at 1.75 mm


class KlippyError(Exception):
    pass


class Klippy:
    """Minimal client for the Klippy API socket (JSON, separated by 0x03)."""

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
                    except Exception as e:  # never let the reader thread die
                        print("Handler error:", e, file=sys.stderr)

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
            raise KlippyError("Timeout on %s" % method)
        self.pending.pop(mid, None)
        msg = ev[1]
        if msg is None:
            raise KlippyError("Connection to Klippy lost")
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
        # Mainsail renders console text as HTML: < > would be swallowed
        text = (text.replace('"', "'").replace(";", ",").replace("#", "No.")
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
            raise ValueError("Segment %s outside 0-8 mm/s or 0-20 s" % part)
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
    """Waits until the mean over 1.5 s changes by less than tol g."""
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
    """Commanded extruder position/velocity at print_time t (without PA)."""
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
# Evaluation
# ---------------------------------------------------------------------------
# Model per feed step (measured on T0, PLA 230 C, 16 steps):
#   F(t) = F_pre + A * step(t - d) + B * (1 - exp(-(t - d) / tau))
#   A   = instant part (friction/drive, follows the feed without delay)
#   B   = nozzle pressure, follows the feed with time constant tau
# In the linear compression model the ideal Klipper/Kalico PA value = tau
# (PA pushes an extra K * v_e, exactly the volume stored in the
# pressure). Steps from standstill are not used, they
# behave differently (start-up, residual force after stopping).

FIT_WINDOW = 0.4  # s after the step
TAU_GRID = [0.008 * 1.03 ** i for i in range(0, 140)]  # 8 ms .. ~0.5 s, 3 % steps
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
    """Fits all steps between two constant-speed moves with v > 0."""
    rows_t = [r[0] for r in rows]
    rows_f = [r[1] for r in rows]
    cruise = [m for m in moves if m[3] == 0 and m[1] > 0.8 and m[2] > 0]
    fits = []
    prev_end = None
    for a, b in zip(cruise, cruise[1:]):
        # first constant move after a pause: pressure is still building -> skip
        first_in_block = prev_end is None or a[0] - prev_end > 0.05
        prev_end = a[0] + a[1]
        if first_in_block or b[0] - (a[0] + a[1]) > 0.05:
            continue  # pause before or in between -> start from standstill
        v1, v2 = a[2] * a[5][0], b[2] * b[5][0]
        if abs(v2 - v1) < 0.5:
            continue
        ts = a[0] + a[1]  # end of the previous constant move (decel/accel ~5 ms)
        f = fit_step(rows_t, rows_f, ts)
        if f is None:
            continue
        f["v1"], f["v2"] = v1, v2
        # Plausibility: the pressure part must point in the step direction and
        # be well above noise, tau not at the edge of the grid
        sign = -1.0 if v2 > v1 else 1.0  # more feed -> force drops
        f["ok"] = (f["delayed"] * sign > 60 and f["rms"] < 40
                   and TAU_GRID[1] < f["tau"] < TAU_GRID[-2])
        fits.append(f)
    return fits


def low_drift(rows, moves):
    """Spread of the force at the end of the slow segments (g).

    Nozzle pressure at the same speed is the same every time. If the level
    wanders, drag in the filament path builds up and releases (T3 2026-11-20:
    slow level -356 -> -1262 g, spool/path dragging)."""
    cruise = [m for m in moves if m[3] == 0 and m[1] > 0.8 and m[2] > 0]
    if len(cruise) < 4:
        return 0.0
    v_lo = min(m[2] for m in cruise[1:])
    lv = []
    for m in cruise[1:]:
        if abs(m[2] - v_lo) > 0.05:
            continue
        end = m[0] + m[1]
        f = [r[1] for r in rows if end - 0.5 <= r[0] < end]
        if f:
            lv.append(sum(f) / len(f))
    return max(lv) - min(lv) if len(lv) >= 2 else 0.0


def median(xs):
    s = sorted(xs)
    n = len(s)
    if not n:
        return float("nan")
    return s[n // 2] if n % 2 else 0.5 * (s[n // 2 - 1] + s[n // 2])


# ---------------------------------------------------------------------------
# Measurement
# ---------------------------------------------------------------------------
# Phase 1: pre-flush 12 mm (fills the nozzle, gives the force level at 2 mm/s)
PRIME_SEQ = "2:6"
V_MAX = 4.0  # mm/s filament, upper limit of the steps
V_MIN_HI = 1.0  # below this the signal is too small
LOW_RATIO = 0.375  # low feed = 0.375 * high (like 1.5 <-> 4)
DEFAULT_PRELOAD = 1100.0  # g, lowest seat preload according to INDX (1100-1900 g)
# print PA / measured time constant per nozzle diameter, from Orca PA patterns:
#   0.4 mm: Sunlu T0 0.024/0.038, T1 0.024/0.042, Overture T0 0.025/0.042 -> 0.6
#   0.6 mm: Overture T5 0.022/0.045, Sunlu T5 0.020/0.039 -> 0.5
#   0.25 mm: Sunlu Cyan T7, measured 0.052, pattern clean from 0.054 up to
#            0.082 (no upper limit seen) -> 1.1 (one filament so far)
# Between two entries it is interpolated; outside the table the nearest
# entry is used and the result is marked as not verified.
PA_SCALE_BY_NOZZLE = {0.25: 1.1, 0.4: 0.6, 0.6: 0.5}
AGREE_MAX = 1.6    # max ratio of the up and down medians
AGREE_SMALL = 2.0  # same for nozzles below 0.35 mm
PA_SCALE = PA_SCALE_BY_NOZZLE[0.4]  # nozzle unknown


def pa_scale(noz):
    """(factor, note) for the nozzle diameter."""
    pts = sorted(PA_SCALE_BY_NOZZLE.items())
    if noz <= 0:
        return PA_SCALE, " - nozzle unknown, factor for 0.4 mm"
    for d, s in pts:
        if abs(noz - d) < 0.01:
            return s, ""
    if noz < pts[0][0] or noz > pts[-1][0]:
        d, s = pts[0] if noz < pts[0][0] else pts[-1]
        return s, " - factor for %s mm nozzle not verified, %s mm value used" % (nozzle_str(noz), nozzle_str(d))
    for (d0, s0), (d1, s1) in zip(pts, pts[1:]):
        if d0 < noz < d1:
            return round(s0 + (s1 - s0) * (noz - d0) / (d1 - d0), 2), " - interpolated, not verified"
DRIFT_MAX = 400.0  # g, spread of the slow-speed force level (usable runs up to ~250 g, T3 with drag 905 g)
RESIDUAL_MAX = 0.3  # share of the preload that may stay after the stop (drag)


def seat_preload(kl):
    """Seat preload of the active tool from the last INDX seat check."""
    try:
        st = kl.call("objects/query", {"objects": {"gcode_macro _INDX_SEAT_CHECK": ["force_g"]}},
                     timeout=5)["status"]
        g = abs(float(st["gcode_macro _INDX_SEAT_CHECK"]["force_g"]))
    except (KlippyError, KeyError, TypeError, ValueError):
        g = 0.0
    # 0 after a restart or without a pickup in this session -> conservative default
    return g if g >= 680.0 else DEFAULT_PRELOAD


def make_plan(kl, preload, v_max=V_MAX):
    """Picks the step height so the force stays at about half the seat preload.

    Above the preload the nozzle pressure lifts the tool in its seat (T1/T2 at
    ~2000 g: time constant distorted, zero point shifted afterwards).
    """
    def plan(level, residual):
        # level = nozzle pressure at 2 mm/s (force while flushing minus force
        # 0.5 s after the stop), residual = force that stays after the stop.
        # Nozzle pressure decays within ~0.2 s (T0: -450 g -> -70 g). Force that
        # stays is friction or pull in the filament path (T1 2026-11-20: 600 g
        # stayed, only ~60 g per mm/s came from the nozzle).
        if residual > RESIDUAL_MAX * preload:
            kl.respond("Aborted - %.0f g stay on the tool after the pre-flush stops, nozzle pressure "
                       "only %.0f g. That is drag in the filament path, not nozzle pressure: spool "
                       "brakes or is tangled, PTFE tube or buffer stiff, extruder idler too tight. "
                       "Fix that first (feed by hand should be easy)." % (residual, level))
            return None
        if not level == level or level < 40:  # NaN or no pressure build-up
            kl.respond("Aborted - hardly any force while pre-flushing (%.0f g). Filament loaded, nozzle clear?" % level)
            return None
        limit = 0.6 * preload - residual
        v_seat = 2.0 * limit / level
        v_hi = math.floor(min(v_max, v_seat) * 10) / 10.0
        if v_hi < V_MIN_HI:
            kl.respond("Aborted - already %.0f g nozzle pressure at 2 mm/s (preload %.0f g). "
                       "Nozzle partly clogged, temperature too low or wrong filament?"
                       % (level, preload))
            return None
        v_lo = round(LOW_RATIO * v_hi, 2)
        kl.respond("Pre-flush: %.0f g nozzle pressure at 2 mm/s, %.0f g residual, preload %.0f g "
                   "-> steps %.2f <-> %.1f mm/s (%.1f <-> %.1f mm3/s)"
                   % (level, residual, preload, v_lo, v_hi,
                      v_lo * FILAMENT_AREA, v_hi * FILAMENT_AREA))
        if v_max > V_MAX and v_seat < v_max:
            kl.respond("Requested %.1f mm3/s, limited to %.1f mm3/s by the seat preload."
                       % (v_max * FILAMENT_AREA, v_hi * FILAMENT_AREA))
        # v_lo 4 s to rebuild pressure (not evaluated), then 4x up/down
        # above 4 mm/s shorter segments (still > 0.8 s cruise for the fit)
        d = 1.5 if v_hi <= V_MAX else 1.2
        return [(v_lo, 4.0)] + [(v_hi, d), (v_lo, d)] * 4
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


def measure(kl, rec, args, tool, seq_str, pa, label, plan=None, at_bucket=False):
    """One measurement on the active tool. Returns (rows, moves, meta) or None.

    With plan: seq_str is only the pre-flush. Then plan(force_g) is called with the
    force level at the end of the pre-flush and returns the actual
    step sequence (or None = abort).
    """
    seq = parse_seq(seq_str)
    total_e = sum(v * d for v, d in seq)
    if total_e > MAX_TOTAL_E:
        raise KlippyError("Sequence would extrude %.0f mm (max %.0f)" % (total_e, MAX_TOTAL_E))
    ex, act = query(kl)
    if act != tool:
        kl.respond("Aborted - expected T%d, T%d is on the head." % (tool, act))
        return None
    if ex["temperature"] < args.min_temp:
        kl.respond("Aborted - T%d is only at %.0f C, at least %.0f C needed (e.g. M109 S210)."
                   % (tool, ex["temperature"], args.min_temp))
        return None
    old_pa = ex.get("pressure_advance", 0.0)
    old_st = ex.get("smooth_time", 0.04)
    kl.respond("T%d, %.0f C, PA during measurement %.3f, %.0f mm filament, sequence %s"
               % (tool, ex["temperature"], pa, total_e, seq_str))

    lines = ["SAVE_GCODE_STATE NAME=_lc_pa_state"]
    if not args.no_bucket and not at_bucket:
        lines.append("MOVE_TO_BUCKET")
    lines.append("M400")
    kl.gcode("\n".join(lines), timeout=120)
    _, act = query(kl)
    if act != tool:  # e.g. homing inside MOVE_TO_BUCKET changed the tool
        kl.gcode("RESTORE_GCODE_STATE NAME=_lc_pa_state", timeout=10)
        kl.respond("Aborted - T%d is on the head now instead of T%d. Start again." % (act, tool))
        return None

    kl.respond("waiting for a quiet zero point (max %.0f s) ..." % args.settle_timeout)
    ok, _, waited = wait_settled(kl, rec, args.settle_tol, args.settle_timeout)
    if not ok:
        kl.respond("Warning - force still not quiet after %.0f s, measuring anyway." % waited)

    f_settled = mean(rec.last_force(1.5))
    with rec.lock:
        t_mark = rec.force[-1][0] if rec.force else 0.0
        err0, ovf0 = rec.lc_errors, rec.lc_overflows
    try:
        if plan is not None:
            # Phase 1: pre-flush with M400, measure the force level at the end
            kl.gcode("\n".join(["M83", "SET_PRESSURE_ADVANCE ADVANCE=%.4f" % pa, "G4 P3000"]
                               + seq_to_gcode(seq) + ["M400"]),
                     timeout=sum(d for _, d in seq) + 60)
            # end of the pre-flush from the trapq, then wait until the load cell
            # data covers 0.8 s after it (data lags slightly)
            t_end = None
            deadline = time.time() + 4.0
            while time.time() < deadline:
                with rec.lock:
                    ends = [m[0] + m[1] for m in rec.moves.values() if m[0] >= t_mark]
                    tl = rec.force[-1][0] if rec.force else 0.0
                if ends:
                    t_end = max(ends)
                    if tl >= t_end + 0.8:
                        break
                time.sleep(0.1)
            with rec.lock:
                if t_end is None:
                    t_end = tl - 0.9
                run = [f for t, f, _ in rec.force if t_end - 1.0 <= t < t_end - 0.1]
                rest = [f for t, f, _ in rec.force if t_end + 0.5 <= t < t_end + 0.8]
            if run and rest:
                level = abs(mean(run) - mean(rest))
                residual = abs(mean(rest) - f_settled)
            else:
                level, residual = float("nan"), 0.0
            # Phase 2: steps with adapted speed
            seq2 = plan(level, residual)
            if seq2 is None:
                return None
            total_e += sum(v * d for v, d in seq2)
            if total_e > MAX_TOTAL_E + 25:
                raise KlippyError("Sequence would extrude %.0f mm" % total_e)
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
            print("Could not restore PA:", e, file=sys.stderr)
    time.sleep(1.0)  # wait for the last batches

    with rec.lock:
        force = [r for r in rec.force if r[0] >= t_mark - 4.0]
        # only E moves of this measurement (trapq also returns older history)
        moves = sorted((m for m in rec.moves.values() if m[0] >= t_mark),
                       key=lambda m: m[0])
        lc_err, lc_ovf = rec.lc_errors - err0, rec.lc_overflows - ovf0
        rec.force = []  # free memory for the next tool
    if not moves or not force:
        kl.respond("Aborted - no data received (force %d, E moves %d)." % (len(force), len(moves)))
        return None
    ext = [m for m in moves if abs(m[3]) > 0 or m[2] > 0]
    t_e0 = ext[0][0] if ext else moves[0][0]
    rows = [r for r in force if r[0] >= t_e0 - 4.0]
    f_base = mean([f for t, f, _ in rows if t_e0 - 2.5 <= t < t_e0 - 0.2])

    os.makedirs(args.out, exist_ok=True)
    stamp = time.strftime("%Y%m%d_%H%M%S")
    base = os.path.join(args.out, "lcpa_%s_T%d_%s" % (label, tool, stamp))
    with open(base + ".csv", "w", newline="") as fh:
        fh.write("# LC-PA raw data, tool T%d, %s\n" % (tool, stamp))
        fh.write("# temp_C=%.1f pa_during=%.4f pa_before=%.4f smooth_time=%.4f seq=%s\n"
                 % (ex["temperature"], pa, old_pa, old_st, seq_str))
        fh.write("# t_s relative to the start of the first E move, force_rel_g = force_g - baseline (%.1f g)\n" % f_base)
        fh.write("# e_pos/e_vel = commanded extruder motion without PA (from trapq)\n")
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
        kl.respond("Note - load cell reported %d errors / %d overflows." % (lc_err, lc_ovf))
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


def clean_after(kl, args):
    """Wipe the strand off at the brush while the nozzle is still hot."""
    if args.no_bucket:
        return
    ex, _ = query(kl)
    if ex["temperature"] < args.min_temp:
        return
    try:
        kl.gcode("clean_nozzle\nM400", timeout=120)
    except KlippyError as e:
        kl.respond("clean_nozzle failed: %s" % e)


def run_raw(kl, rec, args):
    _, tool = query(kl)
    if tool < 0:
        kl.respond("Aborted - no tool on the head.")
        return 1
    res = measure(kl, rec, args, tool, args.seq, args.pa, "raw")
    clean_after(kl, args)
    if res is None:
        return 1
    rows, moves, meta = res
    rate = len(rows) / max(rows[-1][0] - rows[0][0], 1e-6)
    kl.respond("done, %d samples (%.0f Hz). Baseline %.0f g. Plateaus: %s"
               % (len(rows), rate, meta["f_base"],
                  ", ".join(plateau_summary(rows, moves, meta["f_base"])) or "-"))
    kl.respond("File: lc_pa_data/%s.csv" % os.path.basename(meta["base"]))
    return 0


def evaluate(kl, tool, rows, moves, meta):
    """Fit + rating for one tool. Returns PA or None."""
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
    drift = low_drift(rows, moves)
    drag_hint = ("The force drifted by %.0f g at the same speed: drag in the filament path "
                 "(spool, PTFE tube, buffer, idler). Check that the filament feeds freely by hand."
                 % drift) if drift > DRIFT_MAX else ""
    if len(good) < 5:
        kl.respond("T%d: only %d of %d steps usable - no result. Details: lc_pa_data/%s_fit.csv"
                   % (tool, len(good), len(fits), name))
        if drag_hint:
            kl.respond(drag_hint)
        return None, False
    taus = sorted(f["tau"] for f in good)
    up = [f["tau"] for f in good if f["v2"] > f["v1"]]
    dn = [f["tau"] for f in good if f["v2"] < f["v1"]]
    lo, hi = taus[len(taus) // 4], taus[(3 * len(taus)) // 4]
    # Pressure builds up more slowly than it drops (T1 2026-11-20: up 47-62 ms,
    # down 33-37 ms, each tight). Rate each direction on its own, PA = mean of both.
    if up and dn:
        pa = round((median(up) + median(dn)) / 2.0, 3)
        spread = False
        for g in (up, dn):
            if len(g) < 2:
                continue
            m = median(g)
            devs = sorted(abs(x - m) for x in g)
            if len(devs) >= 3:
                devs = devs[:-1]  # one outlier per direction is tolerated (T3 23:29: 31/50/50 ms)
            spread = spread or devs[-1] > 0.3 * m
    else:
        pa = round(median(taus), 3)
        spread = (hi - lo) > 0.35 * pa
    # Valid only with tight spread, enough steps, faster/slower
    # similar and a value plausible for direct drive
    reasons = []
    if len(good) < 6:
        reasons.append("only %d steps" % len(good))
    if spread:
        reasons.append("large spread")
    # Small nozzles build pressure clearly slower than they release it
    # (0.25 mm T7: up 0.065 / down 0.038).
    agree = AGREE_SMALL if 0 < meta.get("nozzle", 0) < 0.35 else AGREE_MAX
    if up and dn and max(median(up), median(dn)) > agree * min(median(up), median(dn)):
        reasons.append("faster/slower do not agree")
    if not 0.005 <= pa <= 0.15:
        reasons.append("implausible value")
    if drag_hint:
        reasons.append("force drifts %.0f g" % drift)
    preload = meta.get("preload")
    if preload and meta.get("max_dev", 0) > 0.8 * preload:
        reasons.append("force %.0f g close to the seat preload %.0f g" % (meta["max_dev"], preload))
    valid = not reasons
    quality = "good" if valid else "UNCERTAIN (%s) - not applied" % ", ".join(reasons)
    kl.respond("T%d: measured %.3f  (%d steps, pressure up %.3f / down %.3f) - %s"
               % (tool, pa, len(good), median(up) if up else float("nan"),
                  median(dn) if dn else float("nan"), quality))
    kl.respond("Details: lc_pa_data/%s_fit.csv" % name)
    return pa, valid


# --- Spoolman (via Moonraker's proxy, the Spoolman address is only in moonraker.conf)

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
    """Spool and nozzle diameter of the tool from save_variables."""
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
    """Write PA to the filament of the tool's spool, one extra field per nozzle size
    (pressure_advance_d025 / _d04 / _d06 ...; missing fields are created with the
    same scheme). Nothing is written without a stored nozzle size."""
    sid, _ = tool_vars(kl, tool)
    if sid <= 0:
        kl.respond("T%d has no spool assigned (SET_TOOL_SPOOL) - Spoolman not updated." % tool)
        return
    if noz <= 0:
        kl.respond("T%d nozzle diameter unknown (SET_TOOL_NOZZLE TOOL=%d D=0.4) - Spoolman not updated."
                   % (tool, tool))
        return
    ns = nozzle_str(noz)
    key = "pressure_advance_d" + ns.replace(".", "")
    try:
        fields = sm_call("GET", "/v1/field/filament") or []
        if not any(f.get("key") == key for f in fields):
            sm_call("POST", "/v1/field/filament/" + key,
                    {"name": "Pressure Advance %s mm nozzle" % ns, "field_type": "float", "unit": "s"})
        fil = (sm_call("GET", "/v1/spool/%d" % sid) or {}).get("filament") or {}
        if fil.get("id") is None:
            raise RuntimeError("spool %d has no filament" % sid)
        extra = dict(fil.get("extra") or {})
        old = extra.get(key)
        extra[key] = json.dumps(round(pa, 3))  # Spoolman: values are JSON strings
        sm_call("PATCH", "/v1/filament/%d" % int(fil["id"]), {"extra": extra})
        name = " ".join(x for x in ((fil.get("vendor") or {}).get("name"), fil.get("name")) if x)
        kl.respond("Spoolman: %s (spool %d) PA %s mm = %.3f%s" % (
            name or "Filament %d" % fil["id"], sid, ns, pa,
            (" (was %s)" % old) if old else ""))
    except Exception as e:  # Spoolman is optional, the measurement stays valid
        kl.respond("Spoolman not updated: %s" % e)


def run_cal(kl, rec, args):
    tools = [int(t) for t in args.tools.split(",") if t.strip() != ""]
    results = []
    # Home first: INDX homing needs a seated tool for Z and may pick up a
    # different one (2026-11-20: after FIRMWARE_RESTART MOVE_TO_BUCKET homed,
    # T0 ended up on the head and was measured instead of T1).
    st = kl.call("objects/query", {"objects": {"toolhead": ["homed_axes"]}}, timeout=5)["status"]
    if "".join(sorted(st["toolhead"].get("homed_axes", ""))) != "xyz":
        kl.respond("printer not homed - homing first ...")
        kl.gcode("G28", timeout=300)
    for tool in tools:
        ex, act = query(kl)
        # freshly picked up: INDX already heats on pickup, but the melt zone
        # is not heat-soaked yet
        cold = act != tool or ex["temperature"] < args.temp - 15
        if act != tool:
            kl.respond("switching to T%d ..." % tool)
            kl.gcode("CHANGE_TOOL TOOL=%d" % tool, timeout=300)
        if not args.no_bucket:
            # heat over the bucket, so oozing during heat-up and soak lands there
            kl.gcode("MOVE_TO_BUCKET\nM400", timeout=120)
        kl.respond("heating T%d to %.0f C ..." % (tool, args.temp))
        kl.gcode("M109 S%.0f" % args.temp, timeout=600)
        if cold and args.soak > 0:
            # Induction reaches the target at the sensor within seconds, the
            # melt zone takes longer (T1/T2 freshly heated: pressure
            # drifted during the whole measurement)
            kl.respond("T%d freshly heated - soaking for %.0f s ..." % (tool, args.soak))
            kl.gcode("G4 P%d" % int(args.soak * 1000), timeout=args.soak + 30)
        preload = seat_preload(kl)
        res = measure(kl, rec, args, tool, args.seq or PRIME_SEQ, 0.0, "cal",
                      plan=None if args.seq else make_plan(kl, preload, round(args.flow / FILAMENT_AREA, 1)),
                      at_bucket=True)
        clean_after(kl, args)
        _, noz = tool_vars(kl, tool)
        if res is not None:
            res[2]["preload"] = preload
            res[2]["nozzle"] = noz
        pa, valid = evaluate(kl, tool, *res) if res is not None else (None, False)
        if not valid:
            pa = None
        tau = pa
        if pa is not None:
            # The measured time constant is longer than the PA that prints best
            # (PA patterns, see PA_SCALE_BY_NOZZLE). The factor maps one to the other.
            if args.scale is not None:
                scale, note = args.scale, " (SCALE given)"
            else:
                scale, note = pa_scale(noz)
            pa = round(tau * scale, 3)
            kl.respond("T%d: print PA %.3f (measured %.3f x %.2f%s)" % (tool, pa, tau, scale, note))
        if pa is not None and args.save:
            kl.gcode("SAVE_VARIABLE VARIABLE=t%d_pa VALUE=%.3f\n"
                     "SAVE_VARIABLE VARIABLE=t%d_pa_raw VALUE=%.3f\n"
                     "SAVE_VARIABLE VARIABLE=t%d_pa_temp VALUE=%.0f"
                     % (tool, pa, tool, tau, tool, args.temp)
                     + ("\nSAVE_VARIABLE VARIABLE=t%d_pa_nozzle VALUE=%s" % (tool, nozzle_str(noz))
                        if noz > 0 else ""), timeout=10)
            if args.spoolman:
                spoolman_write(kl, tool, pa, noz)
        results.append((tool, pa))
    done = [(t, p) for t, p in results if p is not None]
    if done:
        kl.respond("Result: " + ", ".join("T%d %.3f" % tp for tp in done)
                   + (" - saved (LC_PA_SHOW lists all, LC_PA_APPLY applies the active tool's value)."
                      if args.save else " - not saved (SAVE=0)."))
        _, act = query(kl)
        for t, p in done:
            if t == act and args.save:
                kl.gcode("SET_PRESSURE_ADVANCE ADVANCE=%.3f" % p, timeout=10)
                kl.respond("PA %.3f for T%d is now active." % (p, t))
    return 0 if len(done) == len(results) else 1


def main():
    ap = argparse.ArgumentParser(description="Pressure advance via the INDX load cell")
    ap.add_argument("--mode", choices=["raw", "cal"], default="raw")
    ap.add_argument("--socket", default=DEFAULT_SOCK)
    ap.add_argument("--out", default=DEFAULT_OUT)
    ap.add_argument("--load-cell", default="load_cell_probe")
    ap.add_argument("--seq", default=None, help="v:duration,... (mm/s:s), v=0 is a pause")
    ap.add_argument("--pa", type=float, default=0.0, help="raw: PA during the measurement")
    ap.add_argument("--tools", default="", help="cal: tools, e.g. 0 or 0,1,2")
    ap.add_argument("--temp", type=float, default=0.0, help="cal: nozzle temperature")
    ap.add_argument("--save", type=int, default=1, help="cal: save the result via SAVE_VARIABLE")
    ap.add_argument("--spoolman", type=int, default=1, help="cal: write PA to the Spoolman filament (with --save)")
    ap.add_argument("--cool", type=int, default=1, help="turn the heater off at the end (M104 S0)")
    ap.add_argument("--scale", type=float, default=None,
                    help="cal: print PA = measured time constant x scale "
                         "(default: per nozzle diameter, see PA_SCALE_BY_NOZZLE)")
    ap.add_argument("--flow", type=float, default=V_MAX * FILAMENT_AREA,
                    help="cal: upper flow of the steps in mm3/s (default 9.6, max 19)")
    ap.add_argument("--soak", type=float, default=30.0, help="cal: soak time after heating from cold (s)")
    ap.add_argument("--min-temp", type=float, default=180.0)
    ap.add_argument("--settle-tol", type=float, default=15.0, help="g per 1.5 s")
    ap.add_argument("--settle-timeout", type=float, default=90.0)
    ap.add_argument("--no-bucket", action="store_true", help="do not move to the bucket")
    ap.add_argument("--analyze", nargs=2, metavar=("CSV", "MOVES_CSV"),
                    help="only evaluate an existing measurement (no printer)")
    args = ap.parse_args()
    args.flow = max(3.0, min(19.0, args.flow))
    if args.analyze:
        return offline(args.analyze[0], args.analyze[1])
    if args.mode == "raw" and not args.seq:
        args.seq = DEFAULT_SEQ
    if args.seq:
        parse_seq(args.seq)  # validate early

    kl = Klippy(args.socket)
    rec = Recorder()
    try:
        kl.subscribe("load_cell/dump_force", {"load_cell": args.load_cell}, "lc", rec.on_force)
    except KlippyError as e:
        kl.respond("Aborted - load_cell/dump_force not available (%s)." % e)
        return 1
    kl.subscribe("motion_report/dump_trapq", {"name": "extruder"}, "eq", rec.on_trapq)
    try:
        if args.mode == "cal":
            if not args.tools or args.temp < args.min_temp:
                kl.respond("Aborted - pass TOOL and TEMP (min. %.0f C)." % args.min_temp)
                return 1
            return run_cal(kl, rec, args)
        return run_raw(kl, rec, args)
    except KlippyError as e:
        kl.respond("Aborted - %s" % e)
        return 2
    finally:
        # Also after an abort: turn off the heater of the tool on the head (COOL=0 keeps it hot)
        if args.cool and not kl.closed:
            try:
                kl.gcode("M104 S0", timeout=10)
                kl.respond("Heater off, tool is cooling down.")
            except KlippyError as e:
                print("Could not turn off the heater:", e, file=sys.stderr)


class _Printer:
    def respond(self, text):
        print(text)


def offline(csv_path, moves_path):
    """Evaluates a saved measurement (CSV times are relative, that is enough)."""
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
        print("Error:", e, file=sys.stderr)
        sys.exit(2)
