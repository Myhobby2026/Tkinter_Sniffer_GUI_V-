"""Mock tkinter for headless GUI *surface* tests.

Why this exists: real tkinter silently forwards any unknown method name to
Tcl (``Widget.__getattr__``), so an import-based test can never catch

  * an invalid subcommand (e.g. ``ttk.PanedWindow.paneconfigure`` does not
    exist — ttk::panedwindow speaks ``configure/cget/add/panes/...``), or
  * an invalid *value* (e.g. ``Treeview.heading("device")`` for a column that
    was never declared → TclError 'Invalid column index').

This mock replicates those two failure semantics (strict subcommand sets per
widget class + column/pane option validation), so the full GUI construction
and command flow can be exercised in sandboxes without a display.

It complements — not replaces — the real-display tests in
``test_main_window.py``.
"""
from __future__ import annotations

import sys
import types

# ---------------------------------------------------------------------------
# Constants (mirroring tkinter's)
# ---------------------------------------------------------------------------
VERTICAL = "vertical"
HORIZONTAL = "horizontal"
LEFT, RIGHT, TOP, BOTTOM = "left", "right", "top", "bottom"
BOTH, X, Y = "both", "x", "y"
W, E, N, S = "w", "e", "n", "s"
CENTER, END, START = "center", "end", "start"
NORMAL, DISABLED, ACTIVE = "normal", "disabled", "active"


class TclError(Exception):
    pass


class _Result:
    """Stand-in for a Tcl result value."""


class _Recorder:
    def __init__(self, owner, name, args, kwargs) -> None:
        self.owner = owner
        self.name = name
        self.args = args
        self.kwargs = kwargs

    def __call__(self, *args, **kwargs) -> _Result:
        CALLS.append(_Recorder(self.owner, self.name, args, kwargs))
        return _Result()


CALLS: list[_Recorder] = []


def reset_calls() -> None:
    CALLS.clear()


# Subcommands allowed on plain widgets (permissive union; the strict,
# bug-prone classes below override with their own sets).
_WIDGET_METHODS = frozenset({
    "pack", "grid", "place", "pack_forget", "grid_forget", "place_forget",
    "bind", "bind_all", "bindtags", "unbind", "unbind_all",
    "focus", "focus_force", "focus_set", "focus_get", "focus_displayof",
    "grab_set", "grab_release", "lift", "lower",
    "wait_window", "wait_variable", "wait_visibility",
    "update", "update_idletasks",
    "select_set", "select_clear", "select_adjust", "select_range",
    "selection_get", "selection_clear", "selection_set",
    "winfo_id", "winfo_children", "winfo_reqwidth", "winfo_reqheight",
    "winfo_width", "winfo_height", "winfo_viewable", "winfo_geometry",
    "winfo_manager", "winfo_parent", "winfo_screenwidth", "winfo_screenheight",
    "compare", "event", "focus_next", "focus_prev",
})


class _Widget:
    _subcommands: frozenset[str] = frozenset()

    def __init__(self, master=None, **kw) -> None:
        self._master = master
        self._destroyed = False
        self._constructor_kw = kw
        self._options: dict = dict(kw)

    # -- real methods (logic-bearing) --------------------------------------
    def winfo_toplevel(self):
        w = self
        while getattr(w, "_master", None) is not None:
            w = w._master
        return w

    def winfo_exists(self) -> int:
        return 0 if self._destroyed else 1

    def destroy(self) -> None:
        self._destroyed = True

    def configure(self, *args, **kw) -> None:
        # ttk-style: configure(option=value...), configure({"opt": v}) — the
        # pane-overloads (PanedWindow/Treeview) override this.
        if args and len(args) == 1 and isinstance(args[0], dict):
            self._options.update(args[0])
        self._options.update(kw)

    config = configure

    def cget(self, option: str) -> str:
        return self._options.get(option, "")

    def __getattr__(self, name: str):
        # Only invoked when normal attribute lookup fails. Real tkinter
        # forwards unknown names to Tcl, which rejects invalid subcommands —
        # we do the same, so surface bugs fail the same way they do in Tk.
        if name.startswith("_"):
            raise AttributeError(name)
        allowed = _WIDGET_METHODS | self._subcommands
        if name not in allowed:
            raise AttributeError(
                f"mock tkinter: '{name}' is not a valid method/subcommand on "
                f"{type(self).__name__} (Tcl would raise TclError). "
                f"Allowed: {sorted(allowed)}"
            )

        def method(*call_args, **call_kw):
            CALLS.append(_Recorder(self, name, call_args, call_kw))
            return _Result()

        return method


class Tk(_Widget):
    def __init__(self, **kw) -> None:
        super().__init__(None, **kw)
        self._protocols: dict[str, object] = {}
        self._after_jobs: list[tuple[int, object]] = []

    def title(self, value: str | None = None) -> None:
        pass

    def minsize(self, width: int, height: int) -> None:
        pass

    def after(self, ms: int, callback=None, *args):
        self._after_jobs.append((ms, callback))
        return len(self._after_jobs)

    def after_cancel(self, job_id: int) -> None:
        pass

    def protocol(self, name: str, callback=None) -> None:
        self._protocols[name] = callback

    def bind(self, *args, **kw) -> None:
        pass

    def bind_all(self, *args, **kw) -> None:
        pass

    def bindtags(self, *args, **kw) -> None:
        pass

    def tk_call(self, *args, **kw):
        return _Result()


class Frame(_Widget):
    pass


class Canvas(_Widget):
    _subcommands = frozenset({
        "create_line", "create_text", "create_rectangle", "create_oval",
        "create_polygon", "create_arc", "create_bitmap", "create_image",
        "create_window", "coords", "itemconfig", "itemcget", "bbox",
        "find_overlapping", "find_withtag", "gettags", "addtag", "dtag",
        "delete", "move", "scale", "type", "xview", "yview",
    })


class Menu(_Widget):
    _subcommands = frozenset({
        "add", "add_command", "add_separator", "add_radiobutton",
        "add_checkbutton", "add_cascade", "delete", "index", "post",
        "unpost", "entryconfig", "entrycget", "invoke", "tearoff",
    })


class _Var:
    def __init__(self, master=None, value=None, **kw) -> None:
        self._value = value

    def get(self):
        return self._value

    def set(self, value) -> None:
        self._value = value

    def trace(self, *args) -> None:
        pass

    def trace_add(self, *args) -> None:
        pass

    def trace_remove(self, *args) -> None:
        pass

    def delete(self) -> None:
        self._value = None


class StringVar(_Var):
    pass


class IntVar(_Var):
    pass


class DoubleVar(_Var):
    pass


class BooleanVar(_Var):
    pass


# ---------------------------------------------------------------------------
# ttk
# ---------------------------------------------------------------------------
_TTK_PANE_OPTIONS = {"width", "height", "minsize", "maxsize", "weight",
                     "padding", "stretch", "side", "show", "hide"}


class PanedWindow(_Widget):
    """Mirrors ttk::panedwindow's Tcl subcommand vocabulary exactly:
    add, configure, cget, forget, identify, insert, instate, pane, panes,
    sashpos, state — and NO 'paneconfigure'."""

    _subcommands = frozenset({
        "add", "configure", "cget", "forget", "identify", "insert",
        "instate", "pane", "panes", "sashpos", "state",
    })

    def __init__(self, master=None, **kw) -> None:
        super().__init__(master, **kw)
        self._panes: dict[int, object] = {}

    def add(self, pane, **kw) -> None:
        unknown = set(kw) - _TTK_PANE_OPTIONS
        if unknown:
            raise TclError(f"bad option {sorted(unknown)[0]} in 'add'")
        self._panes[id(pane)] = pane

    def configure(self, pane=None, **kw) -> None:
        if isinstance(pane, _Widget):
            # Real Tk (all versions): PanedWindow.configure() does NOT take a
            # pane positionally — the inherited tk configure consumes it as an
            # options source and Tcl fails with "unknown option -...".
            # Use pane(pane, **opts) instead.
            raise TclError(
                "unknown option (a pane was passed to configure; "
                "use .pane(pane, width=..., minsize=...) instead)"
            )

    def pane(self, pane, option=None, **kw) -> None:
        """Documented ttk API: per-pane options (integer index or subwindow)."""
        if id(pane) not in self._panes:
            raise TclError(f"bad pane (not added): {pane!r}")
        if option is not None:
            kw[option] = None
        unknown = set(kw) - _TTK_PANE_OPTIONS
        if unknown:
            raise TclError(f"bad option {sorted(unknown)[0]} in 'pane'")

    def panes(self) -> tuple:
        return tuple(self._panes.values())


_HEADING_OPTIONS = {"text", "image", "underline", "anchor", "command"}
_COLUMN_OPTIONS = {"width", "minwidth", "stretch", "anchor", "align"}


class Treeview(_Widget):
    _subcommands = frozenset({
        "heading", "column", "insert", "delete", "get_children", "children",
        "parent", "index", "item", "set", "move", "selection_set",
        "selection_remove", "selection_clear", "selection_get", "focus",
        "displaycolumn", "show", "tag", "xview", "yview", "bbox",
        "detach", "forget", "get",
    })

    def __init__(self, master=None, columns=(), **kw) -> None:
        super().__init__(master, **kw)
        self._columns: tuple = tuple(columns)
        self._items: dict[str, tuple] = {}

    def __getitem__(self, key: str):
        if key == "columns":
            return self._columns
        raise TclError(f"bad option {key}")

    def heading(self, column, **kw) -> None:
        # Real Tcl semantics: unknown column → TclError, exactly like
        # "Invalid column index device".
        if column not in self._columns:
            raise TclError(f"Invalid column index {column}")
        unknown = set(kw) - _HEADING_OPTIONS
        if unknown:
            raise TclError(f"bad option {sorted(unknown)[0]} in 'heading'")

    def column(self, column, **kw) -> None:
        if column not in self._columns:
            raise TclError(f"Invalid column index {column}")
        unknown = set(kw) - _COLUMN_OPTIONS
        if unknown:
            raise TclError(f"bad option {sorted(unknown)[0]} in 'column'")

    def insert(self, parent: str, index: str, iid=None, values=(), **kw) -> str:
        if iid is None:
            iid = f"item{len(self._items)}"
        self._items[iid] = tuple(values)
        return iid

    def get_children(self, parent: str = "") -> tuple:
        return tuple(self._items)

    def delete(self, *iids) -> None:
        if not iids:
            self._items.clear()
        else:
            for iid in iids:
                self._items.pop(iid, None)

    def selection_set(self, *iids) -> None:
        pass


class Label(_Widget):
    pass


class Button(_Widget):
    pass


class Separator(_Widget):
    pass


class Labelframe(_Widget):
    pass


class Notebook(_Widget):
    _subcommands = frozenset({"add", "forget", "tab", "tabs", "select", "index"})


class Style:
    def __init__(self, master=None, **kw) -> None:
        self._master = master

    def theme_use(self, name: str | None = None) -> None:
        pass

    def theme_names(self) -> tuple:
        return ("clam", "default", "alt", "ttk")

    def theme_settings(self, *args, **kw):
        return _Result()

    def configure(self, *args, **kw) -> None:
        pass

    def map(self, *args, **kw) -> None:
        pass

    def lookup(self, *args, **kw) -> str:
        return ""

    def create(self, *args, **kw) -> None:
        pass

    def destroy(self, *args, **kw) -> None:
        pass

    def layout(self, *args, **kw):
        return _Result()

    def range(self, *args, **kw):
        return _Result()

    def __getattr__(self, name: str):
        if name.startswith("_"):
            raise AttributeError(name)
        return _Recorder(self, name, (), {})()


# ---------------------------------------------------------------------------
# messagebox
# ---------------------------------------------------------------------------
class _Messagebox:
    calls: list[tuple[str, tuple, dict]] = []

    def _record(self, kind, *args, **kw):
        _Messagebox.calls.append((kind, args, kw))
        return "ok"

    def showinfo(self, *a, **k):
        return self._record("showinfo", *a, **k)

    def showerror(self, *a, **k):
        return self._record("showerror", *a, **k)

    def showwarning(self, *a, **k):
        return self._record("showwarning", *a, **k)

    def showquestion(self, *a, **k):
        return self._record("showquestion", *a, **k)


messagebox = _Messagebox()


# ---------------------------------------------------------------------------
# install / restore
# ---------------------------------------------------------------------------
def _build_modules():
    tk_mod = types.ModuleType("tkinter")
    for name in ("VERTICAL", "HORIZONTAL", "LEFT", "RIGHT", "TOP", "BOTTOM",
                 "BOTH", "X", "Y", "W", "E", "N", "S", "CENTER", "END",
                 "START", "NORMAL", "DISABLED", "ACTIVE"):
        setattr(tk_mod, name, globals()[name])
    for name in ("Tk", "Frame", "Canvas", "Menu", "TclError", "StringVar",
                 "IntVar", "DoubleVar", "BooleanVar"):
        setattr(tk_mod, name, globals()[name])

    ttk_mod = types.ModuleType("tkinter.ttk")
    for name in ("Frame", "Label", "Button", "Separator", "PanedWindow",
                 "Treeview", "Notebook", "Labelframe", "Style"):
        setattr(ttk_mod, name, globals()[name])
    for name in ("VERTICAL", "HORIZONTAL", "LEFT", "RIGHT", "TOP", "BOTTOM",
                 "BOTH", "X", "Y", "W", "E", "N", "S"):
        setattr(ttk_mod, name, globals()[name])

    mb_mod = types.ModuleType("tkinter.messagebox")
    for name in ("showinfo", "showerror", "showwarning", "showquestion"):
        setattr(mb_mod, name, getattr(messagebox, name))

    tk_mod.ttk = ttk_mod
    tk_mod.messagebox = mb_mod
    return tk_mod, ttk_mod, mb_mod


def install() -> dict[str, object]:
    """Put the mock into sys.modules; return the displaced real modules."""
    tk_mod, ttk_mod, mb_mod = _build_modules()
    removed = {}
    for name in [n for n in sys.modules
                 if n == "tkinter" or n.startswith("tkinter.") or n.startswith("app")]:
        removed[name] = sys.modules.pop(name)
    sys.modules["tkinter"] = tk_mod
    sys.modules["tkinter.ttk"] = ttk_mod
    sys.modules["tkinter.messagebox"] = mb_mod
    _Messagebox.calls.clear()
    reset_calls()
    return removed


def restore(removed: dict[str, object]) -> None:
    for name in [n for n in sys.modules
                 if n == "tkinter" or n.startswith("tkinter.") or n.startswith("app")]:
        sys.modules.pop(name, None)
    sys.modules.update(removed)


# Convenience handle for tests
tkinter = None  # set by install() consumers via sys.modules["tkinter"]
