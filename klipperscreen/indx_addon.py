"""INDX add-on for KlipperScreen.

- Titlebar: the active tool ("T3") with the colour of its spool.
  Tap it to open the INDX panel.
- Panel "indx_tools" (menu item with "panel: indx_tools"): one button per
  tool with its state (spool name and colour, loaded / empty), the active
  tool highlighted. Tap a tool to pick it up. Park, load and unload below
  (load/unload open the dialog from macros/filament_menu.cfg).

Data comes from Klipper's save_variables:
    active_tool        tool on the head (-1 = none)
    t<n>__spool_id     Spoolman spool of tool n (macros/spoolman.cfg)
    t<n>__loaded       1/0, set by LOAD_FILAMENT / UNLOAD_FILAMENT
and the spool colours from Spoolman (through Moonraker).

Install (once, via SSH):
    mkdir -p ~/KlipperScreen/addons
    ln -sf ~/printer_data/config/klipperscreen/indx_addon.py ~/KlipperScreen/addons/indx.py
and in KlipperScreen.conf, section [main]:  enable_addons: True
The addons folder is ignored by KlipperScreen's git, so updates keep working.
Written against KlipperScreen v0.4.7-215. Everything is wrapped so that an
error here is logged and never breaks KlipperScreen itself.
"""
import logging
import re

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import GLib, Gtk, Pango  # noqa: E402

from ks_includes.screen_panel import ScreenPanel  # noqa: E402

try:
    from ks_includes.svg_gradient import filament_colors_from_dict
except Exception:  # older KlipperScreen
    def filament_colors_from_dict(fil):
        c = ((fil or {}).get("color_hex") or "").strip().lstrip("#")
        return [c] if c else []

PANEL = "indx_tools"
TOOL_RE = re.compile(r"^gcode_macro T(\d+)$", re.IGNORECASE)
LOG = "INDX add-on: "


def _rgb(hexval):
    h = (hexval or "").strip().lstrip("#")
    if len(h) < 6:
        return None
    try:
        return tuple(int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4))
    except ValueError:
        return None


class Swatch(Gtk.DrawingArea):
    """Colour patch for a spool (vertical stripes for multi-colour)."""

    def __init__(self, width, height):
        super().__init__()
        self.w, self.h = width, height
        self.colors = None  # None = no spool, [] = unknown colour
        self.set_size_request(width, height)
        self.connect("draw", self._draw)

    def set_colors(self, colors):
        if colors != self.colors:
            self.colors = colors
            self.queue_draw()

    def _draw(self, area, ctx):
        aw, ah = area.get_allocated_width(), area.get_allocated_height()
        w, h = min(self.w, aw), min(self.h, ah)
        x, y = (aw - w) / 2.0, (ah - h) / 2.0
        cols = [c for c in (_rgb(c) for c in (self.colors or [])) if c]
        if cols:
            step = w / len(cols)
            for i, c in enumerate(cols):
                ctx.set_source_rgb(*c)
                ctx.rectangle(x + i * step, y, step + 0.5, h)
                ctx.fill()
            ctx.set_dash([])
        else:
            ctx.set_dash([3.0, 3.0])
        ctx.set_source_rgb(0.55, 0.55, 0.55)
        ctx.set_line_width(1.0)
        ctx.rectangle(x + 0.5, y + 0.5, w - 1, h - 1)
        ctx.stroke()
        return False


class IndxState:
    """Tool data shared by the titlebar item and the panel."""

    def __init__(self, screen):
        self.screen = screen
        self.spools = {}      # spool id -> spool dict from Spoolman
        self.pending = set()
        self.listeners = []

    # -- Klipper data
    def variables(self):
        p = self.screen.printer
        if not p:
            return {}
        return (p.data.get("save_variables") or {}).get("variables") or {}

    def tools(self):
        nums = set()
        p = self.screen.printer
        if p and p.config:
            for sec in p.config:
                m = TOOL_RE.match(sec)
                if m:
                    nums.add(int(m.group(1)))
        return sorted(nums) or list(range(9))

    def active(self):
        try:
            return int(self.variables().get("active_tool", -1))
        except (TypeError, ValueError):
            return -1

    def spool_id(self, n):
        try:
            return int(self.variables().get("t%d__spool_id" % n) or 0)
        except (TypeError, ValueError):
            return 0

    def loaded(self, n):
        """True / False, or None when unknown (never loaded through the macros)."""
        v = self.variables().get("t%d__loaded" % n)
        if v is None:
            return True if self.spool_id(n) else None
        try:
            return bool(int(v))
        except (TypeError, ValueError):
            return None

    def printing(self):
        p = self.screen.printer
        return bool(p) and p.state in ("printing", "paused")

    # -- Spoolman data
    def spool(self, n):
        return self.spools.get(self.spool_id(n))

    def colors(self, n):
        sid = self.spool_id(n)
        if not sid:
            return None
        s = self.spools.get(sid)
        if not s:
            return []
        return filament_colors_from_dict(s.get("filament") or {})

    def fetch_spools(self, refresh=False):
        api = getattr(self.screen, "spoolman_api", None)
        p = self.screen.printer
        if api is None or not p or not getattr(p, "spoolman", False):
            return
        if refresh:
            self.spools.clear()
        for n in self.tools():
            sid = self.spool_id(n)
            if sid and sid not in self.spools and sid not in self.pending:
                self.pending.add(sid)
                api.get_spool_details(sid, lambda r, sid=sid: self._got_spool(sid, r))

    def _got_spool(self, sid, spool):
        self.pending.discard(sid)
        if isinstance(spool, dict):
            self.spools[sid] = spool
            self.notify()

    # -- change notification
    def notify(self):
        for cb in list(self.listeners):
            try:
                cb()
            except Exception:
                logging.exception(LOG + "listener failed")

    def changed(self):
        self.fetch_spools()
        self.notify()


STATE = None


class IndxToolsPanel(ScreenPanel):
    def __init__(self, screen, title, **kwargs):
        super().__init__(screen, title or "INDX")
        self.tool_widgets = {}
        tools = STATE.tools()
        cols = 3
        grid = Gtk.Grid(row_homogeneous=True, column_homogeneous=True, hexpand=True, vexpand=True)
        size = max(16, int(self._gtk.img_scale * self.bts * 1.2))
        for idx, n in enumerate(tools):
            b = Gtk.Button(hexpand=True, vexpand=True)
            b.set_can_focus(False)
            box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2,
                          valign=Gtk.Align.CENTER, halign=Gtk.Align.CENTER)
            name = Gtk.Label()
            name.set_markup("<big><b>T%d</b></big>" % n)
            sw = Swatch(size * 2, size)
            info = Gtk.Label(ellipsize=Pango.EllipsizeMode.END, max_width_chars=16)
            info2 = Gtk.Label(ellipsize=Pango.EllipsizeMode.END, max_width_chars=16)
            info2.get_style_context().add_class("dim-label")
            for w in (name, sw, info, info2):
                box.pack_start(w, False, False, 0)
            b.add(box)
            b.connect("clicked", self.pick_tool, n)
            b.connect("clicked", self._screen.screensaver.reset_timeout)
            grid.attach(b, idx % cols, idx // cols, 1, 1)
            self.tool_widgets[n] = (b, sw, info, info2)
        row = (len(tools) + cols - 1) // cols
        actions = (
            ("toolchanger", "Park", "PARK_TOOL", "color1"),
            ("load", "Load", "LOAD_FILAMENT", "color3"),
            ("filament", "Unload", "UNLOAD_FILAMENT", "color2"),
        )
        self.action_buttons = []
        for i, (icon, label, script, style) in enumerate(actions):
            b = self._gtk.Button(icon, label, style, self.bts, Gtk.PositionType.LEFT, 1)
            b.connect("clicked", self.run, script)
            grid.attach(b, i % cols, row + i // cols, 1, 1)
            self.action_buttons.append(b)
        self.content.add(grid)
        STATE.listeners.append(self.update)

    def run(self, widget, script):
        self._screen._send_action(widget, "printer.gcode.script", {"script": script})

    def pick_tool(self, widget, n):
        if STATE.printing():
            return
        self._screen._send_action(widget, "printer.gcode.script", {"script": "T%d" % n})

    def activate(self):
        STATE.fetch_spools(refresh=True)
        self.update()

    def process_update(self, action, data):
        if action == "notify_status_update" and (
            "save_variables" in data or "print_stats" in data or "webhooks" in data
        ):
            self.update()

    def update(self):
        try:
            active = STATE.active()
            busy = STATE.printing()
            for n, (b, sw, info, info2) in self.tool_widgets.items():
                ctx = b.get_style_context()
                if n == active:
                    ctx.add_class("button_active")
                else:
                    ctx.remove_class("button_active")
                b.set_sensitive(not busy)
                loaded = STATE.loaded(n)
                spool = STATE.spool(n)
                sw.set_colors(STATE.colors(n) if loaded is not False else None)
                if spool and loaded is not False:
                    fil = spool.get("filament") or {}
                    info.set_label(fil.get("name") or fil.get("material") or "#%d" % spool["id"])
                    w = spool.get("remaining_weight")
                    info2.set_label("%s%s" % (fil.get("material") or "",
                                              (" %d g" % round(w)) if w is not None else ""))
                elif STATE.spool_id(n) and loaded is not False:
                    info.set_label("Spool %d" % STATE.spool_id(n))
                    info2.set_label("")
                elif loaded:
                    info.set_label("Loaded")
                    info2.set_label("no spool assigned")
                elif loaded is False:
                    info.set_label("Empty")
                    info2.set_label("")
                else:
                    info.set_label("?")
                    info2.set_label("state unknown")
            for b in self.action_buttons:
                b.set_sensitive(not busy)
        except Exception:
            logging.exception(LOG + "panel update failed")


class TitlebarTool:
    """'T3' plus spool colour in the KlipperScreen titlebar."""

    def __init__(self, screen):
        self.screen = screen
        bp = screen.base_panel
        size = max(10, int(screen.gtk.img_scale * getattr(bp, "bts", 1) * 0.6))
        self.swatch = Swatch(size, size)
        self.label = Gtk.Label(label="T-")
        box = Gtk.Box(spacing=4)
        box.pack_start(self.swatch, False, False, 3)
        box.pack_start(self.label, False, False, 0)
        self.widget = Gtk.EventBox()
        self.widget.add(box)
        self.widget.connect("button-press-event", self.open_panel)
        STATE.listeners.append(self.update)

    def open_panel(self, *args):
        try:
            self.screen.show_panel(PANEL, "INDX")
        except Exception:
            logging.exception(LOG + "cannot open panel")
        return True

    def attach(self):
        item_box = self.screen.base_panel.control.get("item_box")
        if item_box is None:
            return
        if self.widget.get_parent() is None:
            item_box.add(self.widget)
            item_box.reorder_child(self.widget, 0)
        self.update()
        item_box.show_all()

    def update(self):
        a = STATE.active()
        if a >= 0:
            self.label.set_markup("<b>T%d</b>" % a)
            self.swatch.set_colors(STATE.colors(a))
            self.swatch.show()
        else:
            self.label.set_markup("<b>T-</b>")
            self.swatch.set_colors(None)
            self.swatch.hide()


def _install(screen):
    global STATE
    STATE = IndxState(screen)
    module = type("indx_tools_module", (), {"Panel": IndxToolsPanel})

    # 1. Make "indx_tools" loadable as a panel (KlipperScreen only looks in panels/)
    orig_load = screen._load_panel

    def load_panel(panel):
        if panel == PANEL:
            return module
        return orig_load(panel)

    screen._load_panel = load_panel

    # 2. Subscribe to save_variables and read its current value after (re)connect
    orig_subscribe = screen.ws_subscribe

    def ws_subscribe():
        api = screen._ws.api
        orig_sub = api.object_subscription

        def sub(req, *args, **kwargs):
            try:
                req.setdefault("objects", {})["save_variables"] = ["variables"]
            except Exception:
                logging.exception(LOG + "cannot extend subscription")
            return orig_sub(req, *args, **kwargs)

        api.object_subscription = sub
        try:
            orig_subscribe()
        finally:
            try:
                del api.object_subscription
            except AttributeError:
                api.object_subscription = orig_sub

        def got(response, *args):
            try:
                status = ((response or {}).get("result") or {}).get("status") or {}
                if "save_variables" in status and screen.printer:
                    screen.printer.process_update({"save_variables": status["save_variables"]})
                    STATE.changed()
            except Exception:
                logging.exception(LOG + "initial query failed")

        screen._ws.send_method("printer.objects.query",
                               {"objects": {"save_variables": ["variables"]}}, got)

    screen.ws_subscribe = ws_subscribe

    # 3. Titlebar item
    bp = screen.base_panel
    title = TitlebarTool(screen)
    orig_show = bp.show_titlebar_items

    def show_titlebar_items(*args, **kwargs):
        result = orig_show(*args, **kwargs)
        try:
            if bp.titlebar_populated:
                title.attach()
        except Exception:
            logging.exception(LOG + "titlebar item failed")
        return result

    bp.show_titlebar_items = show_titlebar_items

    # 4. Updates
    orig_update = bp.process_update

    def process_update(action, data, *args, **kwargs):
        result = orig_update(action, data, *args, **kwargs)
        try:
            if action == "notify_status_update" and "save_variables" in data:
                STATE.changed()
            elif action in ("notify_active_spool_set", "notify_spoolman_status_changed"):
                STATE.fetch_spools(refresh=True)
        except Exception:
            logging.exception(LOG + "update failed")
        return result

    bp.process_update = process_update


def init(screen):
    try:
        _install(screen)
        logging.info(LOG + "installed")
    except Exception:
        logging.exception(LOG + "install failed")
