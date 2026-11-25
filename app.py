"""Turtle · Network Explorer — masaüstü arayüzü.

Tasarım notları
- Tüm bileşenler (buton, anahtar, ilerleme, ikon) Canvas/Frame ile çizilir; bu sayede
  macOS, Windows ve Linux'ta aynı görünür (macOS'ta tk.Button renkleri yok sayılır).
- Ağ işleri arka plan thread'lerinde çalışır, arayüze güvenli bir kuyruk üzerinden döner.
- Sonuçlar sayfalar arası gezinirken korunur.
"""
from __future__ import annotations

import ctypes
import queue
import sys
import threading
import tkinter as tk
import traceback
import webbrowser
from collections import Counter, deque
from datetime import datetime
from tkinter import font as tkfont
from tkinter import messagebox, ttk

import network

if sys.platform == "win32":  # Keskin metin için DPI farkındalığı
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass

MAC = sys.platform == "darwin"
SCALE = 1.0


def S(n: float) -> int:
    """Piksel değerini ekran ölçeğine göre büyüt."""
    return int(round(n * SCALE))


def mix(a: str, b: str, t: float) -> str:
    """a rengini b rengine t oranında karıştır."""
    pa = [int(a[i:i + 2], 16) for i in (1, 3, 5)]
    pb = [int(b[i:i + 2], 16) for i in (1, 3, 5)]
    return "#%02x%02x%02x" % tuple(round(y + (x - y) * t) for x, y in zip(pa, pb))


class C:
    BG = "#0a0e16"
    SIDEBAR = "#0d121b"
    SURFACE = "#121926"
    SURFACE2 = "#172033"
    SURFACE3 = "#1e2a41"
    BORDER = "#1f2b40"
    BORDER_STRONG = "#2c3c58"
    TEXT = "#e7ecf4"
    TEXT2 = "#a8b5c9"
    MUTED = "#70819b"
    ACCENT = "#34d399"
    ACCENT_HOVER = "#6ee7b7"
    ACCENT_PRESS = "#10b981"
    ON_ACCENT = "#04261b"
    BLUE = "#60a5fa"
    AMBER = "#fbbf24"
    RED = "#f87171"
    VIOLET = "#a78bfa"


PROTO = {"TCP": "#7cb7ff", "UDP": "#5eead4", "DNS": "#c4b5fd", "ICMP": "#fcd34d",
         "ARP": "#f9a8d4", "IPv6": C.TEXT2, "OTHER": C.MUTED}

FONT: dict[str, tkfont.Font] = {}


def init_fonts(root: tk.Tk) -> None:
    fams = set(tkfont.families(root))
    pick = lambda names, default: next((n for n in names if n in fams), default)
    if MAC:
        base = tkfont.nametofont("TkDefaultFont").actual("family")
        mono = pick(["SF Mono", "Menlo", "Monaco"], "Courier")
        m = 2
    elif sys.platform == "win32":
        base = pick(["Segoe UI Variable Text", "Segoe UI"], "Segoe UI")
        mono = pick(["Cascadia Mono", "Consolas"], "Courier New")
        m = 0
    else:
        base = pick(["Inter", "Cantarell", "Ubuntu", "Noto Sans", "DejaVu Sans"],
                    tkfont.nametofont("TkDefaultFont").actual("family"))
        mono = pick(["JetBrains Mono", "DejaVu Sans Mono", "Liberation Mono", "Noto Sans Mono"], "Courier")
        m = 0

    def f(size, weight="normal", family=None):
        return tkfont.Font(root=root, family=family or base, size=size + m, weight=weight)

    FONT.update(body=f(10), body_b=f(10, "bold"), small=f(9), small_b=f(9, "bold"),
                cap=f(8, "bold"), h1=f(20, "bold"), h2=f(12, "bold"), metric=f(21, "bold"),
                btn=f(10, "bold"), btn_s=f(9, "bold"), nav=f(10, "bold"), brand=f(14, "bold"),
                mono=f(9, family=mono))


# ───────────────────────────── çizim yardımcıları ─────────────────────────────

def rrect(cv: tk.Canvas, x1, y1, x2, y2, r, **kw):
    pts = [x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r, x2, y2 - r, x2, y2,
           x2 - r, y2, x1 + r, y2, x1, y2, x1, y2 - r, x1, y1 + r, x1, y1]
    return cv.create_polygon(pts, smooth=True, **kw)


def draw_icon(cv: tk.Canvas, name: str, color: str, size: float = 16, x: float = 0, y: float = 0):
    """16x16 ızgarada tanımlı çizgi ikonları."""
    k = size / 16.0
    w = max(1.3, 1.5 * k)

    def P(*pts):
        return [(x + v * k) if i % 2 == 0 else (y + v * k) for i, v in enumerate(pts)]

    line = dict(fill=color, width=w, capstyle="round", joinstyle="round")
    box = dict(outline=color, width=w)
    if name == "dashboard":
        for r in ((1.5, 1.5, 7, 7), (9, 1.5, 14.5, 7), (1.5, 9, 7, 14.5), (9, 9, 14.5, 14.5)):
            cv.create_rectangle(*P(*r), **box)
    elif name == "interfaces":
        cv.create_rectangle(*P(2, 3, 14, 10), **box)
        for px in (5, 8, 11):
            cv.create_line(*P(px, 10, px, 13), **line)
    elif name == "wifi":
        for r in (3, 6, 9):
            cv.create_arc(*P(8 - r, 12.5 - r, 8 + r, 12.5 + r), start=45, extent=90, style="arc", **box)
        cv.create_oval(*P(6.9, 11.4, 9.1, 13.6), fill=color, outline=color)
    elif name == "lan":
        for sx, sy in ((8, 2.5), (2.5, 12.5), (13.5, 12.5)):
            cv.create_line(*P(8, 8, sx, sy), **line)
            cv.create_oval(*P(sx - 1.7, sy - 1.7, sx + 1.7, sy + 1.7), fill=cv.cget("bg"), outline=color, width=w)
        cv.create_oval(*P(5.8, 5.8, 10.2, 10.2), fill=color, outline=color)
    elif name == "capture":
        cv.create_line(*P(1, 8, 4.5, 8, 6.5, 3, 9.5, 13, 11.5, 8, 15, 8), **line)
    elif name == "ports":
        cv.create_line(*P(2, 5, 13, 5), arrow="last", arrowshape=(S(5) * k, S(6) * k, S(3) * k), **line)
        cv.create_line(*P(14, 11, 3, 11), arrow="last", arrowshape=(S(5) * k, S(6) * k, S(3) * k), **line)
    elif name == "info":
        cv.create_oval(*P(1.5, 1.5, 14.5, 14.5), **box)
        cv.create_line(*P(8, 7, 8, 11.5), **line)
        cv.create_oval(*P(7.1, 4.1, 8.9, 5.9), fill=color, outline=color)
    elif name == "refresh":
        cv.create_arc(*P(2.5, 2.5, 13.5, 13.5), start=30, extent=290, style="arc", **box)
        cv.create_polygon(*P(13.8, 1.8, 13.8, 6.6, 9.2, 5.2), fill=color, outline=color)
    elif name == "search":
        cv.create_oval(*P(2, 2, 10.5, 10.5), **box)
        cv.create_line(*P(9.5, 9.5, 14, 14), **line)
    elif name == "play":
        cv.create_polygon(*P(4.5, 2.5, 13, 8, 4.5, 13.5), fill=color, outline=color, joinstyle="round")
    elif name == "stop":
        cv.create_rectangle(*P(3.5, 3.5, 12.5, 12.5), fill=color, outline=color)
    elif name == "trash":
        cv.create_line(*P(2, 4, 14, 4), **line)
        cv.create_line(*P(6, 4, 6, 2.5, 10, 2.5, 10, 4), **line)
        cv.create_rectangle(*P(3.5, 4.5, 12.5, 14), **box)
        cv.create_line(*P(6.5, 7, 6.5, 11.5), **line)
        cv.create_line(*P(9.5, 7, 9.5, 11.5), **line)
    elif name == "external":
        cv.create_line(*P(7, 2.5, 3, 2.5, 3, 13.5, 13.5, 13.5, 13.5, 9.5), **line)
        cv.create_line(*P(9.5, 2, 14, 2, 14, 6.5), **line)
        cv.create_line(*P(14, 2, 7, 9), **line)
    elif name == "check":
        cv.create_line(*P(3, 8.5, 6.5, 12, 13, 4.5), **line)
    elif name == "shield":
        cv.create_polygon(*P(8, 1.5, 13.5, 3.5, 13.5, 8, 8, 14.5, 2.5, 8, 2.5, 3.5),
                          fill="", outline=color, width=w, joinstyle="round")
    elif name == "globe":
        cv.create_oval(*P(1.5, 1.5, 14.5, 14.5), **box)
        cv.create_oval(*P(5.2, 1.5, 10.8, 14.5), **box)
        cv.create_line(*P(1.5, 8, 14.5, 8), **line)
    elif name == "chevron":
        cv.create_line(*P(6, 3.5, 10.5, 8, 6, 12.5), **line)


class Icon(tk.Canvas):
    def __init__(self, parent, name, color, size=16, bg=None):
        self.name, self.color, self.size = name, color, S(size)
        super().__init__(parent, width=self.size, height=self.size, bg=bg or parent.cget("bg"),
                         highlightthickness=0, bd=0)
        self._draw()

    def _draw(self):
        self.delete("all")
        draw_icon(self, self.name, self.color, self.size)

    def recolor(self, color=None, bg=None):
        if color:
            self.color = color
        if bg:
            self.configure(bg=bg)
        self._draw()

    def set_bg(self, bg):
        self.recolor(bg=bg)


class IconChip(tk.Canvas):
    """Yumuşak renkli zemin üzerinde ikon."""

    def __init__(self, parent, name, color, size=36, bg=None):
        self.name, self.color, self.box = name, color, S(size)
        super().__init__(parent, width=self.box, height=self.box, bg=bg or parent.cget("bg"),
                         highlightthickness=0, bd=0)
        self._draw()

    def _draw(self):
        self.delete("all")
        bg = self.cget("bg")
        rrect(self, 1, 1, self.box - 1, self.box - 1, S(9),
              fill=mix(self.color, bg, 0.13), outline=mix(self.color, bg, 0.26))
        isz = self.box * 0.48
        draw_icon(self, self.name, self.color, isz, (self.box - isz) / 2, (self.box - isz) / 2)

    def set_bg(self, bg):
        self.configure(bg=bg)
        self._draw()


class Logo(tk.Canvas):
    def __init__(self, parent, size=36, bg=C.SIDEBAR):
        s = S(size)
        super().__init__(parent, width=s, height=s, bg=bg, highlightthickness=0, bd=0)
        import math
        rrect(self, 1, 1, s - 1, s - 1, S(10), fill=mix(C.ACCENT, bg, 0.14), outline=mix(C.ACCENT, bg, 0.45))
        cx = cy = s / 2

        def hexagon(r):
            return [c for i in range(6) for c in (cx + r * math.cos(math.pi / 3 * i + math.pi / 6),
                                                   cy + r * math.sin(math.pi / 3 * i + math.pi / 6))]
        self.create_polygon(hexagon(s * 0.29), fill="", outline=C.ACCENT, width=max(2, S(1.8)), joinstyle="round")
        self.create_polygon(hexagon(s * 0.12), fill=C.ACCENT, outline=C.ACCENT)


def paint(widget, bg):
    """Alt widget'ların zeminini toplu değiştir."""
    if getattr(widget, "_nopaint", False):
        return
    if hasattr(widget, "set_bg"):
        widget.set_bg(bg)
        return
    try:
        widget.configure(bg=bg)
    except tk.TclError:
        pass
    for child in widget.winfo_children():
        paint(child, bg)


def hover_click(root_w, hover_cb, click_cb=None):
    """Çocuk widget'lara girişte titremeyen hover + tıklama bağlama."""
    def inside():
        x, y = root_w.winfo_pointerxy()
        w = root_w.winfo_containing(x, y)
        while w is not None:
            if w is root_w:
                return True
            w = w.master
        return False

    def walk(w):
        w.bind("<Enter>", lambda e: hover_cb(True), add="+")
        w.bind("<Leave>", lambda e: hover_cb(inside()), add="+")
        if click_cb:
            w.bind("<Button-1>", lambda e: click_cb(), add="+")
            try:
                w.configure(cursor="hand2")
            except tk.TclError:
                pass
        for c in w.winfo_children():
            walk(c)
    walk(root_w)


# ───────────────────────────── bileşenler ─────────────────────────────

class Btn(tk.Canvas):
    VARIANTS = {
        "primary": dict(bg=C.ACCENT, fg=C.ON_ACCENT, hover=C.ACCENT_HOVER, press=C.ACCENT_PRESS, border=C.ACCENT),
        "secondary": dict(bg=C.SURFACE2, fg=C.TEXT, hover=C.SURFACE3, press=C.BORDER, border=C.BORDER_STRONG),
        "danger": dict(bg="#35191f", fg="#fda4af", hover="#47212a", press="#2a1217", border="#5f2a34"),
        "ghost": dict(bg=None, fg=C.TEXT2, hover=C.SURFACE2, press=C.SURFACE3, border=None),
    }

    def __init__(self, parent, text, command=None, variant="secondary", icon=None, small=False, bg=None, width=0):
        self._pbg = bg or parent.cget("bg")
        super().__init__(parent, bg=self._pbg, highlightthickness=0, bd=0, cursor="hand2")
        self.text, self.command, self.variant, self.icon = text, command, variant, icon
        self.small, self.enabled, self.hovered, self.pressed, self.min_w = small, True, False, False, width
        self._layout()
        self.bind("<Enter>", lambda e: self._set(hovered=True))
        self.bind("<Leave>", lambda e: self._set(hovered=False, pressed=False))
        self.bind("<ButtonPress-1>", lambda e: self._set(pressed=True))
        self.bind("<ButtonRelease-1>", self._release)
        self.bind("<Configure>", self._resize)

    def _resize(self, e):
        if e.width > 1 and e.width != self.w:
            self.w = e.width
            self._draw()

    def _set(self, **kw):
        for k, v in kw.items():
            setattr(self, k, v)
        self._draw()

    def _release(self, e):
        was = self.pressed
        self._set(pressed=False)
        if was and self.enabled and 0 <= e.x <= self.w and 0 <= e.y <= self.h and self.command:
            self.command()

    def _layout(self):
        font = FONT["btn_s"] if self.small else FONT["btn"]
        self.h = S(28 if self.small else 36)
        self.pad = S(11 if self.small else 16)
        self.isz = S(12 if self.small else 14)
        self.tw = font.measure(self.text) if self.text else 0
        self.iw = (self.isz + (S(7) if self.text else 0)) if self.icon else 0
        self.w = max(self.min_w, self.pad * 2 + self.iw + self.tw)
        self.configure(width=self.w, height=self.h)
        self._draw()

    def _draw(self):
        self.delete("all")
        v = self.VARIANTS[self.variant]
        fg, fill, border = v["fg"], v["bg"], v["border"]
        if not self.enabled:
            fg, fill, border = C.MUTED, (None if self.variant == "ghost" else C.SURFACE2), (None if self.variant == "ghost" else C.BORDER)
        elif self.pressed:
            fill = v["press"]
        elif self.hovered:
            fill = v["hover"]
            fg = C.TEXT if self.variant == "ghost" else fg
        if fill:
            rrect(self, 1, 1, self.w - 1, self.h - 1, S(8), fill=fill, outline=border or fill)
        x0 = (self.w - self.iw - self.tw) / 2
        if self.icon:
            draw_icon(self, self.icon, fg, self.isz, x0, (self.h - self.isz) / 2)
        if self.text:
            self.create_text(x0 + self.iw, self.h / 2, text=self.text, anchor="w", fill=fg,
                             font=FONT["btn_s"] if self.small else FONT["btn"])

    def update_style(self, text=None, variant=None, icon=None):
        if text is not None:
            self.text = text
        if variant:
            self.variant = variant
        if icon is not None:
            self.icon = icon
        self._layout()

    def set_enabled(self, flag: bool):
        self.enabled = flag
        self.configure(cursor="hand2" if flag else "arrow")
        self._draw()


class Switch(tk.Canvas):
    def __init__(self, parent, variable: tk.BooleanVar, bg=None):
        self.var = variable
        self.w, self.h = S(40), S(22)
        super().__init__(parent, width=self.w, height=self.h, bg=bg or parent.cget("bg"),
                         highlightthickness=0, bd=0, cursor="hand2")
        self.bind("<Button-1>", lambda e: self.var.set(not self.var.get()))
        self._trace = self.var.trace_add("write", lambda *a: self._draw())
        self.bind("<Destroy>", lambda e: self._cleanup(), add="+")
        self._draw()

    def _cleanup(self):
        try:
            self.var.trace_remove("write", self._trace)
        except Exception:
            pass

    def _draw(self):
        if not self.winfo_exists():
            return
        self.delete("all")
        on = self.var.get()
        rrect(self, 1, 1, self.w - 1, self.h - 1, self.h / 2 - 1, fill=C.ACCENT if on else C.BORDER_STRONG,
              outline=C.ACCENT if on else C.BORDER_STRONG)
        d = self.h - S(8)
        x = self.w - S(4) - d if on else S(4)
        self.create_oval(x, S(4), x + d, S(4) + d, fill="#ffffff" if on else C.TEXT2, outline="")


class Progress(tk.Canvas):
    def __init__(self, parent, bg=None):
        super().__init__(parent, height=S(6), bg=bg or parent.cget("bg"), highlightthickness=0, bd=0)
        self.frac = 0.0
        self.bind("<Configure>", lambda e: self._draw())

    def set(self, frac: float):
        self.frac = max(0.0, min(1.0, frac))
        self._draw()

    def _draw(self):
        self.delete("all")
        w, h = self.winfo_width(), self.winfo_height()
        if w < 4:
            return
        rrect(self, 0, 0, w, h, h / 2, fill=C.SURFACE3, outline=C.SURFACE3)
        if self.frac > 0:
            rrect(self, 0, 0, max(h, w * self.frac), h, h / 2, fill=C.ACCENT, outline=C.ACCENT)


class Chip(tk.Frame):
    def __init__(self, parent, text="", color=C.TEXT2, bg=None):
        bg = bg or parent.cget("bg")
        super().__init__(parent, bg=mix(color, bg, 0.12), highlightbackground=mix(color, bg, 0.3),
                         highlightthickness=1)
        self.label = tk.Label(self, text=text, bg=mix(color, bg, 0.12), fg=color, font=FONT["small_b"],
                              padx=S(9), pady=S(3))
        self.label.pack()

    def set(self, text):
        self.label.configure(text=text)


class Card(tk.Frame):
    def __init__(self, parent, pad=(18, 16), bg=C.SURFACE):
        super().__init__(parent, bg=bg, highlightbackground=C.BORDER, highlightthickness=1)
        self.body = tk.Frame(self, bg=bg)
        self.body.pack(fill="both", expand=True, padx=S(pad[0]), pady=S(pad[1]))


def caption(parent, text, bg=C.SURFACE, fg=C.MUTED):
    return tk.Label(parent, text=text.upper(), bg=bg, fg=fg, font=FONT["cap"], anchor="w")


def make_entry(parent, var, mono=False):
    return tk.Entry(parent, textvariable=var, relief="flat", bd=0, bg=C.SURFACE2, fg=C.TEXT,
                    insertbackground=C.TEXT, selectbackground=mix(C.ACCENT, C.SURFACE2, 0.4),
                    selectforeground=C.TEXT, font=FONT["mono"] if mono else FONT["body"],
                    highlightthickness=1, highlightbackground=C.BORDER_STRONG, highlightcolor=C.ACCENT)


class DataTable(tk.Frame):
    """Tema uyumlu tablo: zebra, boş durum, otomatik gizlenen kaydırma çubuğu."""

    def __init__(self, parent, columns, empty_icon, empty_title, empty_hint, mono=False, zebra=True):
        super().__init__(parent, bg=C.SURFACE, highlightbackground=C.BORDER, highlightthickness=1)
        self.zebra, self._n = zebra, 0
        ids = [c[0] for c in columns]
        self.tree = ttk.Treeview(self, columns=ids, show="headings", selectmode="browse",
                                 style="Turtle.Mono.Treeview" if mono else "Turtle.Treeview")
        for cid, heading, width, anchor, stretch in columns:
            self.tree.heading(cid, text=heading.upper(), anchor="w")
            self.tree.column(cid, width=S(width), minwidth=S(60), anchor=anchor, stretch=stretch)
        self.sb = ttk.Scrollbar(self, orient="vertical", style="Turtle.Vertical.TScrollbar", command=self.tree.yview)
        self.tree.configure(yscrollcommand=self._on_scroll)
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self.tree.grid(row=0, column=0, sticky="nsew")
        self.tree.tag_configure("odd", background=C.SURFACE)
        self.tree.tag_configure("even", background=mix(C.SURFACE2, C.SURFACE, 0.5))
        for name, color in PROTO.items():
            self.tree.tag_configure(name, foreground=color)
        self.tree.tag_configure("dim", foreground=C.MUTED)

        self.empty = tk.Frame(self, bg=C.SURFACE)
        IconChip(self.empty, empty_icon, C.MUTED, 44, C.SURFACE).pack()
        tk.Label(self.empty, text=empty_title, bg=C.SURFACE, fg=C.TEXT, font=FONT["body_b"]).pack(pady=(S(12), S(3)))
        tk.Label(self.empty, text=empty_hint, bg=C.SURFACE, fg=C.MUTED, font=FONT["small"],
                 justify="center", wraplength=S(360)).pack()
        self._sync()

    def _on_scroll(self, first, last):
        self.sb.set(first, last)
        if float(first) <= 0 and float(last) >= 1:
            self.sb.grid_remove()
        else:
            self.sb.grid(row=0, column=1, sticky="ns")

    def _sync(self):
        if self._n == 0:
            self.empty.place(relx=0.5, rely=0.56, anchor="center")
            self.empty.lift()
        else:
            self.empty.place_forget()

    def clear(self):
        self.tree.delete(*self.tree.get_children())
        self._n = 0
        self._sync()

    def add(self, values, tags=(), see=False):
        z = (("even" if self._n % 2 else "odd"),) if self.zebra else ()
        iid = self.tree.insert("", "end", values=values, tags=z + tuple(tags))
        self._n += 1
        if see:
            self.tree.see(iid)
        self._sync()

    def set_rows(self, rows):
        self.tree.delete(*self.tree.get_children())
        self._n = 0
        for values, tags in rows:
            self.add(values, tags)
        self._sync()

    def trim(self, limit):
        kids = self.tree.get_children()
        for iid in kids[:max(0, len(kids) - limit)]:
            self.tree.delete(iid)
        self._n = len(self.tree.get_children())


class NavItem(tk.Frame):
    def __init__(self, parent, icon, text, command):
        super().__init__(parent, bg=C.SIDEBAR)
        self.active = self.hovered = False
        self.bar = tk.Frame(self, width=S(3), bg=C.SIDEBAR)
        self.bar.pack(side="left", fill="y")
        self.icon = Icon(self, icon, C.MUTED, 18, C.SIDEBAR)
        self.icon.pack(side="left", padx=(S(18), S(12)), pady=S(10))
        self.label = tk.Label(self, text=text, bg=C.SIDEBAR, fg=C.TEXT2, font=FONT["nav"], anchor="w")
        self.label.pack(side="left", fill="x", expand=True)
        hover_click(self, self._hover, command)

    def _hover(self, flag):
        self.hovered = flag
        self._apply()

    def set_active(self, flag):
        self.active = flag
        self._apply()

    def _apply(self):
        if self.active:
            bg, fg, ic = mix(C.ACCENT, C.SIDEBAR, 0.10), C.TEXT, C.ACCENT
        elif self.hovered:
            bg, fg, ic = C.SURFACE, C.TEXT, C.TEXT2
        else:
            bg, fg, ic = C.SIDEBAR, C.TEXT2, C.MUTED
        self.configure(bg=bg)
        self.label.configure(bg=bg, fg=fg)
        self.icon.recolor(ic, bg)
        self.bar.configure(bg=C.ACCENT if self.active else bg)


# ───────────────────────────── uygulama ─────────────────────────────

NAV = [
    (None, [("dashboard", "dashboard", "Genel Bakış")]),
    ("Keşif", [("interfaces", "interfaces", "Ağ Arayüzleri"), ("wifi", "wifi", "Wi-Fi Ağları"),
               ("lan", "lan", "Yerel Ağ Keşfi")]),
    ("Analiz", [("capture", "capture", "Paket İzleme"), ("ports", "ports", "Port Analizi")]),
]
PAGE_ORDER = ["dashboard", "interfaces", "wifi", "lan", "capture", "ports", "about"]


class TurtleApp(tk.Tk):
    def __init__(self):
        super().__init__()
        global SCALE
        SCALE = max(1.0, self.winfo_fpixels("1i") / 96.0)
        init_fonts(self)
        self.title("Turtle · Network Explorer")
        self.configure(bg=C.BG)

        # durum (sayfalar arası korunur)
        self.current_page = ""
        self.view: dict = {}
        self.busy: set = set()
        self.iface_rows: list[dict] = []
        self.wifi_rows: list[dict] = []
        self.lan_rows: list[dict] = []
        self.port_rows: list[dict] = []
        self.lan_time = self.port_info = None
        self.cap_rows: deque = deque(maxlen=500)
        self.cap_counts: Counter = Counter()
        self.capture: network.PacketCapture | None = None
        self.capture_active = False
        self.activity: deque = deque(maxlen=40)
        self.lan_iface = tk.StringVar()
        self.cap_iface = tk.StringVar()
        self.cap_filter = tk.StringVar(value="Tümü")
        self.cap_autoscroll = tk.BooleanVar(value=True)
        self.port_target = tk.StringVar(value="192.168.1.1")
        self.port_spec = tk.StringVar(value="22,80,443,8080")
        self.port_auth = tk.BooleanVar(value=False)
        self.metrics = {k: (tk.StringVar(value="—"), tk.StringVar(value=n)) for k, n in (
            ("iface", "Yükleniyor…"), ("ip", "Yükleniyor…"), ("lan", "Henüz tarama yapılmadı"),
            ("ports", "Henüz analiz yapılmadı"))}
        self._q: queue.Queue = queue.Queue()
        self._cap_job = None

        self._configure_style()
        self._build_shell()
        self._place_window()
        self._bind_shortcuts()
        self._pump()
        self.show_page("dashboard")
        self.after(150, lambda: self.load_interfaces(quiet=True))

    # ── pencere / stil ──
    def _place_window(self):
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        w, h = min(S(1280), sw - 80), min(S(820), sh - 100)
        self.geometry(f"{w}x{h}+{(sw - w) // 2}+{max(20, (sh - h) // 3)}")
        self.minsize(min(S(1080), sw - 40), min(S(700), sh - 60))

    def _bind_shortcuts(self):
        mod = "Command" if MAC else "Control"
        for i, key in enumerate(PAGE_ORDER, 1):
            self.bind(f"<{mod}-Key-{i}>", lambda e, k=key: self.show_page(k))

    def _configure_style(self):
        st = ttk.Style(self)
        try:
            st.theme_use("clam")
        except tk.TclError:
            pass
        sel = mix(C.ACCENT, C.SURFACE, 0.16)
        for name, font in (("Turtle.Treeview", FONT["body"]), ("Turtle.Mono.Treeview", FONT["mono"])):
            st.configure(name, background=C.SURFACE, fieldbackground=C.SURFACE, foreground=C.TEXT,
                         rowheight=S(36), borderwidth=0, relief="flat", font=font)
            st.layout(name, [("Treeview.treearea", {"sticky": "nswe"})])
            st.configure(f"{name}.Cell", padding=(S(10), 0))
            st.map(name, background=[("selected", sel)], foreground=[("selected", C.TEXT)])
            st.configure(f"{name}.Heading", background=C.SURFACE2, foreground=C.MUTED, relief="flat",
                         borderwidth=0, padding=(S(14), S(10)), font=FONT["cap"],
                         bordercolor=C.SURFACE2, lightcolor=C.SURFACE2, darkcolor=C.SURFACE2)
            st.map(f"{name}.Heading", background=[("active", C.SURFACE3)])
        st.layout("Turtle.Vertical.TScrollbar", [("Vertical.Scrollbar.trough", {
            "sticky": "ns", "children": [("Vertical.Scrollbar.thumb", {"expand": "1", "sticky": "nswe"})]})])
        st.configure("Turtle.Vertical.TScrollbar", background=C.BORDER_STRONG, troughcolor=C.SURFACE,
                     bordercolor=C.SURFACE, lightcolor=C.BORDER_STRONG, darkcolor=C.BORDER_STRONG,
                     gripcount=0, width=S(10))
        st.map("Turtle.Vertical.TScrollbar", background=[("active", C.MUTED), ("pressed", C.MUTED)],
               lightcolor=[("active", C.MUTED)], darkcolor=[("active", C.MUTED)])
        st.configure("Turtle.TCombobox", fieldbackground=C.SURFACE2, background=C.SURFACE2, foreground=C.TEXT,
                     arrowcolor=C.TEXT2, bordercolor=C.BORDER_STRONG, lightcolor=C.BORDER_STRONG,
                     darkcolor=C.BORDER_STRONG, padding=(S(10), S(7)), arrowsize=S(14),
                     selectbackground=C.SURFACE2, selectforeground=C.TEXT)
        st.map("Turtle.TCombobox", fieldbackground=[("readonly", C.SURFACE2)], foreground=[("readonly", C.TEXT)],
               selectbackground=[("readonly", C.SURFACE2)], selectforeground=[("readonly", C.TEXT)],
               bordercolor=[("focus", C.ACCENT)], lightcolor=[("focus", C.ACCENT)],
               darkcolor=[("focus", C.ACCENT)], arrowcolor=[("hover", C.TEXT)])
        for opt, val in (("background", C.SURFACE2), ("foreground", C.TEXT),
                         ("selectBackground", mix(C.ACCENT, C.SURFACE2, 0.3)), ("selectForeground", C.TEXT),
                         ("font", FONT["body"]), ("borderWidth", 0)):
            self.option_add(f"*TCombobox*Listbox.{opt}", val)

    def _build_shell(self):
        shell = tk.Frame(self, bg=C.BG)
        shell.pack(fill="both", expand=True)
        side = tk.Frame(shell, bg=C.SIDEBAR, width=S(240))
        side.pack(side="left", fill="y")
        side.pack_propagate(False)
        tk.Frame(shell, bg=C.BORDER, width=1).pack(side="left", fill="y")

        brand = tk.Frame(side, bg=C.SIDEBAR)
        brand.pack(fill="x", padx=S(20), pady=(S(26), S(24)))
        Logo(brand).pack(side="left")
        names = tk.Frame(brand, bg=C.SIDEBAR)
        names.pack(side="left", padx=(S(12), 0))
        tk.Label(names, text="Turtle", bg=C.SIDEBAR, fg=C.TEXT, font=FONT["brand"]).pack(anchor="w")
        tk.Label(names, text="Network Explorer", bg=C.SIDEBAR, fg=C.MUTED, font=FONT["small"]).pack(anchor="w")

        self.nav: dict[str, NavItem] = {}
        for section, items in NAV:
            if section:
                tk.Label(side, text=section.upper(), bg=C.SIDEBAR, fg=C.MUTED, font=FONT["cap"],
                         anchor="w").pack(fill="x", padx=S(22), pady=(S(18), S(6)))
            for key, icon, label in items:
                item = NavItem(side, icon, label, lambda k=key: self.show_page(k))
                item.pack(fill="x", pady=1)
                self.nav[key] = item

        foot = tk.Frame(side, bg=C.SIDEBAR)
        foot.pack(side="bottom", fill="x", pady=(0, S(14)))
        item = NavItem(foot, "info", "Hakkında", lambda: self.show_page("about"))
        item.pack(fill="x", pady=(0, S(10)))
        self.nav["about"] = item
        tk.Frame(foot, bg=C.BORDER, height=1).pack(fill="x", padx=S(20), pady=(0, S(12)))
        tk.Label(foot, text=f"Sürüm {network.APP_VERSION}", bg=C.SIDEBAR, fg=C.TEXT2,
                 font=FONT["small_b"]).pack(anchor="w", padx=S(22))
        tk.Label(foot, text="Eğitim ve yetkili kullanım için", bg=C.SIDEBAR, fg=C.MUTED,
                 font=FONT["small"]).pack(anchor="w", padx=S(22), pady=(2, 0))

        main = tk.Frame(shell, bg=C.BG)
        main.pack(side="left", fill="both", expand=True)
        bar = tk.Frame(main, bg=C.SIDEBAR, height=S(32))
        bar.pack(side="bottom", fill="x")
        bar.pack_propagate(False)
        tk.Frame(main, bg=C.BORDER, height=1).pack(side="bottom", fill="x")
        self.status_dot = tk.Label(bar, text="●", bg=C.SIDEBAR, fg=C.ACCENT, font=FONT["small"])
        self.status_dot.pack(side="left", padx=(S(24), S(8)))
        self.status_text = tk.Label(bar, text="Hazır", bg=C.SIDEBAR, fg=C.TEXT2, font=FONT["small"])
        self.status_text.pack(side="left")
        Icon(bar, "shield", C.MUTED, 13, C.SIDEBAR).pack(side="right", padx=(S(6), S(24)))
        tk.Label(bar, text="Yalnızca izinli ağlarda kullanın", bg=C.SIDEBAR, fg=C.MUTED,
                 font=FONT["small"]).pack(side="right")
        self.content = tk.Frame(main, bg=C.BG)
        self.content.pack(fill="both", expand=True, padx=S(32), pady=(S(28), S(20)))

    # ── iş parçacığı köprüsü / durum ──
    def ui(self, fn):
        self._q.put(fn)

    def _pump(self):
        for _ in range(400):
            try:
                fn = self._q.get_nowait()
            except queue.Empty:
                break
            try:
                fn()
            except tk.TclError:
                pass
            except Exception:
                traceback.print_exc()
        self._pump_id = self.after(40, self._pump)

    def set_status(self, message, color=C.ACCENT, log=True):
        def apply():
            self.status_dot.configure(fg=color)
            self.status_text.configure(text=message)
            if log:
                self.activity.append((datetime.now().strftime("%H:%M"), message, color))
                self._render_activity()
        self.ui(apply)

    def worker(self, label, fn, ok, err=None, key=None, quiet=False):
        if key:
            if key in self.busy:
                return
            self.busy.add(key)
        if not quiet:
            self.set_status(f"{label} çalışıyor…", C.BLUE, log=False)

        def run():
            try:
                result = fn()
            except Exception as exc:
                msg = str(exc) or exc.__class__.__name__

                def fail():
                    self.busy.discard(key)
                    if quiet:
                        return
                    self.set_status("İşlem tamamlanamadı", C.RED)
                    (err or (lambda m: messagebox.showerror("Turtle · İşlem hatası", m)))(msg)
                self.ui(fail)
                return

            def done():
                self.busy.discard(key)
                ok(result)
            self.ui(done)
        threading.Thread(target=run, daemon=True).start()

    # ── gezinme ──
    def show_page(self, page):
        if page == self.current_page:
            return
        self.current_page = page
        self.view = {}
        for key, item in self.nav.items():
            item.set_active(key == page)
        for child in self.content.winfo_children():
            child.destroy()
        getattr(self, f"_page_{page}")()

    def _header(self, title, subtitle):
        head = tk.Frame(self.content, bg=C.BG)
        head.pack(fill="x", pady=(0, S(20)))
        left = tk.Frame(head, bg=C.BG)
        left.pack(side="left")
        tk.Label(left, text=title, bg=C.BG, fg=C.TEXT, font=FONT["h1"]).pack(anchor="w")
        tk.Label(left, text=subtitle, bg=C.BG, fg=C.MUTED, font=FONT["body"], justify="left",
                 wraplength=S(640)).pack(anchor="w", pady=(4, 0))
        right = tk.Frame(head, bg=C.BG)
        right.pack(side="right", anchor="s")
        return right

    def _visible(self, page):
        return self.current_page == page

    # ── Genel bakış ──
    def _page_dashboard(self):
        self._header("Genel Bakış", "Ağ ortamının özeti ve araçlara hızlı erişim.")
        grid = tk.Frame(self.content, bg=C.BG)
        grid.pack(fill="x", pady=(0, S(16)))
        specs = [("Arayüzler", "iface", C.ACCENT, "interfaces"), ("Birincil IPv4", "ip", C.BLUE, "globe"),
                 ("LAN cihazları", "lan", C.VIOLET, "lan"), ("Açık portlar", "ports", C.AMBER, "ports")]
        for i, (cap, key, color, icon) in enumerate(specs):
            grid.grid_columnconfigure(i, weight=1, uniform="m")
            card = Card(grid, (18, 16))
            card.grid(row=0, column=i, sticky="nsew", padx=(0, S(14) if i < 3 else 0))
            top = tk.Frame(card.body, bg=C.SURFACE)
            top.pack(fill="x")
            caption(top, cap).pack(side="left")
            IconChip(top, icon, color, 30, C.SURFACE).pack(side="right")
            val, note = self.metrics[key]
            tk.Label(card.body, textvariable=val, bg=C.SURFACE, fg=C.TEXT, font=FONT["metric"],
                     anchor="w").pack(fill="x", pady=(S(8), S(2)))
            tk.Label(card.body, textvariable=note, bg=C.SURFACE, fg=C.MUTED, font=FONT["small"],
                     anchor="w").pack(fill="x")

        body = tk.Frame(self.content, bg=C.BG)
        body.pack(fill="both", expand=True)
        body.grid_columnconfigure(0, weight=1)
        body.grid_columnconfigure(1, weight=0, minsize=S(340))
        body.grid_rowconfigure(0, weight=1)

        left = Card(body, (0, 0))
        left.grid(row=0, column=0, sticky="nsew", padx=(0, S(14)))
        tk.Label(left.body, text="Hızlı erişim", bg=C.SURFACE, fg=C.TEXT, font=FONT["h2"],
                 anchor="w").pack(fill="x", padx=S(20), pady=(S(16), S(8)))
        actions = [("interfaces", "interfaces", C.ACCENT, "Ağ arayüzlerini görüntüle", "Bağdaştırıcılar, IPv4 ve MAC adresleri"),
                   ("wifi", "wifi", C.BLUE, "Yakındaki Wi-Fi ağları", "SSID, BSSID, kanal, sinyal ve güvenlik"),
                   ("lan", "lan", C.VIOLET, "Yerel ağ cihazlarını keşfet", "Bağlı olduğun özel LAN üzerinde"),
                   ("capture", "capture", C.BLUE, "Paket başlıklarını izle", "Yalnızca başlık metaverisi, payload gösterilmez"),
                   ("ports", "ports", C.AMBER, "TCP portlarını analiz et", "Yetki kontrollü hedef taraması")]
        for key, icon, color, title, desc in actions:
            tk.Frame(left.body, bg=C.BORDER, height=1).pack(fill="x")
            row = tk.Frame(left.body, bg=C.SURFACE)
            row.pack(fill="x")
            IconChip(row, icon, color, 38, C.SURFACE).pack(side="left", padx=(S(20), S(14)), pady=S(11))
            txt = tk.Frame(row, bg=C.SURFACE)
            txt.pack(side="left", fill="x", expand=True)
            tk.Label(txt, text=title, bg=C.SURFACE, fg=C.TEXT, font=FONT["body_b"], anchor="w").pack(fill="x")
            tk.Label(txt, text=desc, bg=C.SURFACE, fg=C.MUTED, font=FONT["small"], anchor="w").pack(fill="x", pady=(2, 0))
            Icon(row, "chevron", C.MUTED, 14, C.SURFACE).pack(side="right", padx=S(20))
            hover_click(row, lambda f, r=row: paint(r, C.SURFACE2 if f else C.SURFACE), lambda k=key: self.show_page(k))

        right = tk.Frame(body, bg=C.BG)
        right.grid(row=0, column=1, sticky="nsew")
        act = Card(right, (20, 16))
        act.pack(fill="both", expand=True, pady=(0, S(14)))
        tk.Label(act.body, text="Son etkinlik", bg=C.SURFACE, fg=C.TEXT, font=FONT["h2"], anchor="w").pack(fill="x")
        host = tk.Frame(act.body, bg=C.SURFACE)
        host.pack(fill="both", expand=True, pady=(S(8), 0))
        self.view["activity"] = host
        self._render_activity()
        note = Card(right, (20, 16))
        note.pack(fill="x")
        head = tk.Frame(note.body, bg=C.SURFACE)
        head.pack(fill="x")
        Icon(head, "shield", C.AMBER, 15, C.SURFACE).pack(side="left")
        tk.Label(head, text="Kullanım notu", bg=C.SURFACE, fg=C.AMBER, font=FONT["body_b"]).pack(side="left", padx=8)
        tk.Label(note.body, text="Yalnızca kendi ağında veya yazılı izin aldığın sistemlerde kullan. "
                 "LAN keşfi en fazla /22 ile sınırlıdır; harici hedeflerde yetki onayı gerekir.",
                 bg=C.SURFACE, fg=C.TEXT2, font=FONT["small"], justify="left",
                 wraplength=S(290)).pack(anchor="w", pady=(S(8), 0))

    def _render_activity(self):
        host = self.view.get("activity")
        if host is None or not host.winfo_exists():
            return
        for w in host.winfo_children():
            w.destroy()
        items = list(self.activity)[-6:][::-1]
        if not items:
            tk.Label(host, text="Henüz etkinlik yok. Bir araç çalıştırdığında burada görünür.", bg=C.SURFACE,
                     fg=C.MUTED, font=FONT["small"], justify="left", wraplength=S(280)).pack(anchor="w", pady=S(6))
        for t, msg, color in items:
            row = tk.Frame(host, bg=C.SURFACE)
            row.pack(fill="x", pady=S(5))
            tk.Label(row, text="●", bg=C.SURFACE, fg=color, font=FONT["small"]).pack(side="left")
            tk.Label(row, text=msg, bg=C.SURFACE, fg=C.TEXT2, font=FONT["small"], anchor="w").pack(side="left", padx=8)
            tk.Label(row, text=t, bg=C.SURFACE, fg=C.MUTED, font=FONT["small"]).pack(side="right")

    # ── Arayüzler ──
    def _page_interfaces(self):
        right = self._header("Ağ Arayüzleri", "Sistemdeki ağ bağdaştırıcıları, adresler ve bağlantı durumları.")
        Btn(right, "Yenile", self.load_interfaces, "primary", icon="refresh").pack()
        bar = tk.Frame(self.content, bg=C.BG)
        bar.pack(fill="x", pady=(0, S(12)))
        chips = {"all": Chip(bar, "", C.TEXT2), "up": Chip(bar, "", C.ACCENT), "down": Chip(bar, "", C.MUTED)}
        for chip in chips.values():
            chip.pack(side="left", padx=(0, S(8)))
        table = DataTable(self.content, [("name", "Arayüz", 260, "w", False), ("state", "Durum", 130, "w", False),
                                         ("ipv4", "IPv4 adresi", 220, "w", False), ("mac", "MAC adresi", 260, "w", True)],
                          "interfaces", "Arayüz bulunamadı", "Listeyi güncellemek için Yenile'ye bas.")
        table.pack(fill="both", expand=True)
        self.view.update(table=table, chips=chips)
        self._fill_interfaces()

    def _fill_interfaces(self):
        v = self.view
        if not self._visible("interfaces") or "table" not in v:
            return
        rows = self.iface_rows
        up = sum(r["state"] == "AÇIK" for r in rows)
        v["chips"]["all"].set(f"{len(rows)} arayüz")
        v["chips"]["up"].set(f"{up} etkin")
        v["chips"]["down"].set(f"{len(rows) - up} pasif")
        v["table"].set_rows([((r["name"], "●  Açık" if r["state"] == "AÇIK" else "○  Kapalı", r["ipv4"], r["mac"]),
                              () if r["state"] == "AÇIK" else ("dim",)) for r in rows])

    def load_interfaces(self, quiet=False):
        def ok(rows):
            self.iface_rows = rows
            names = [r["name"] for r in rows]
            for var in (self.lan_iface, self.cap_iface):
                if not var.get() or var.get() not in names:
                    var.set(self._default_iface())
            for key in ("lan_combo", "cap_combo"):
                combo = self.view.get(key)
                if combo is not None and combo.winfo_exists():
                    combo["values"] = names
            self._update_metrics()
            self._fill_interfaces()
            if not quiet:
                self.set_status(f"Ağ arayüzleri güncellendi · {len(rows)} arayüz")
        self.worker("Arayüz listesi", network.get_interfaces, ok, key="ifaces", quiet=quiet)

    def _default_iface(self):
        for r in self.iface_rows:
            if r["state"] == "AÇIK" and r["ipv4"] not in ("-", "") and not r["ipv4"].startswith("127."):
                return r["name"]
        return self.iface_rows[0]["name"] if self.iface_rows else ""

    def _update_metrics(self):
        rows = self.iface_rows
        up = [r for r in rows if r["state"] == "AÇIK"]
        main = next((r for r in up if r["ipv4"] not in ("-", "") and not r["ipv4"].startswith("127.")), None)
        self.metrics["iface"][0].set(str(len(rows)))
        self.metrics["iface"][1].set(f"{len(up)} etkin · {len(rows) - len(up)} pasif")
        self.metrics["ip"][0].set(main["ipv4"] if main else "—")
        self.metrics["ip"][1].set(main["name"] if main else "Etkin IPv4 bağlantısı yok")

    def _iface_names(self):
        return [r["name"] for r in self.iface_rows]

    # ── Wi-Fi ──
    def _page_wifi(self):
        right = self._header("Wi-Fi Ağları", "İşletim sisteminin Wi-Fi taramasıyla yakındaki ağları pasif biçimde listele.")
        Btn(right, "Ağları tara", self.load_wifi, "primary", icon="search").pack()
        bar = tk.Frame(self.content, bg=C.BG)
        bar.pack(fill="x", pady=(0, S(12)))
        count = Chip(bar, "", C.TEXT2)
        count.pack(side="left", padx=(0, S(8)))
        Chip(bar, "Pasif tarama", C.ACCENT).pack(side="left", padx=(0, S(10)))
        tk.Label(bar, text="Paket enjeksiyonu veya bağlantı kesme işlemi yapılmaz.", bg=C.BG, fg=C.MUTED,
                 font=FONT["small"]).pack(side="left")
        table = DataTable(self.content, [("ssid", "SSID", 250, "w", True), ("bssid", "BSSID", 190, "w", False),
                                         ("channel", "Kanal", 80, "w", False), ("signal", "Sinyal", 150, "w", False),
                                         ("security", "Güvenlik", 190, "w", False)],
                          "wifi", "Henüz tarama yapılmadı", "Yakındaki ağları görmek için “Ağları tara” butonuna bas.")
        table.pack(fill="both", expand=True)
        tk.Label(self.content, text="Not: Bazı macOS sürümlerinde Wi-Fi/konum izni veya yönetici onayı gerekebilir.",
                 bg=C.BG, fg=C.MUTED, font=FONT["small"]).pack(anchor="w", pady=(S(10), 0))
        self.view.update(table=table, count=count)
        self._fill_wifi()

    @staticmethod
    def _signal(sig):
        try:
            pct = int(sig.replace("%", "").strip()) if "%" in sig else \
                max(0, min(100, 2 * (int(sig.split()[0]) + 100)))
        except (ValueError, IndexError):
            return sig
        bars = 1 + (pct >= 25) + (pct >= 50) + (pct >= 75)
        return f"{'●' * bars}{'○' * (4 - bars)}   {sig}"

    def _fill_wifi(self):
        v = self.view
        if not self._visible("wifi") or "table" not in v:
            return
        v["count"].set(f"{len(self.wifi_rows)} ağ")
        v["table"].set_rows([((r["ssid"], r["bssid"], r["channel"], self._signal(r["signal"]),
                               "Açık ağ (korumasız)" if r["security"].upper() in ("AÇIK", "OPEN") else r["security"]), ())
                             for r in self.wifi_rows])

    def load_wifi(self):
        def ok(rows):
            self.wifi_rows = rows
            self._fill_wifi()
            self.set_status(f"{len(rows)} Wi-Fi ağı listelendi")
        self.worker("Wi-Fi taraması", network.scan_wifi, ok, key="wifi")

    # ── Yerel ağ ──
    def _iface_combo(self, parent, var, width=24):
        combo = ttk.Combobox(parent, textvariable=var, state="readonly", width=width, values=self._iface_names(),
                             style="Turtle.TCombobox", font=FONT["body"])
        combo.bind("<<ComboboxSelected>>", lambda e: combo.selection_clear())
        return combo

    def _page_lan(self):
        right = self._header("Yerel Ağ Keşfi", "Yalnızca bağlı olduğun özel IPv4 LAN üzerinde erişilebilir cihazları bul.")
        card = Card(self.content, (18, 16))
        card.pack(fill="x", pady=(0, S(14)))
        row = tk.Frame(card.body, bg=C.SURFACE)
        row.pack(fill="x")
        caption(row, "Ağ arayüzü").pack(side="left", padx=(0, S(12)))
        combo = self._iface_combo(row, self.lan_iface)
        combo.pack(side="left")
        Btn(row, "", self.load_interfaces, "ghost", icon="refresh", small=True, bg=C.SURFACE, width=S(32)).pack(side="left", padx=S(6))
        start = Btn(row, "LAN keşfini başlat", self.start_lan_scan, "primary", icon="search", bg=C.SURFACE)
        start.pack(side="right")
        info = tk.Frame(card.body, bg=C.SURFACE)
        info.pack(fill="x", pady=(S(14), S(8)))
        label = tk.Label(info, text="Tarama /22 sınırı içinde tutulur.", bg=C.SURFACE, fg=C.MUTED, font=FONT["small"])
        label.pack(side="left")
        count = Chip(info, "", C.TEXT2, C.SURFACE)
        count.pack(side="right")
        progress = Progress(card.body, C.SURFACE)
        progress.pack(fill="x")
        table = DataTable(self.content, [("ip", "IP adresi", 180, "w", False), ("mac", "MAC adresi", 210, "w", False),
                                         ("vendor", "Üretici", 200, "w", False), ("host", "Ana bilgisayar", 280, "w", True)],
                          "lan", "Henüz cihaz keşfedilmedi", "Keşfi başlatınca ağındaki cihazlar burada listelenir.")
        table.pack(fill="both", expand=True)
        self.view.update(lan_combo=combo, table=table, progress=progress, label=label, count=count, start=start)
        if "lan" in self.busy:
            start.set_enabled(False)
        self._fill_lan()

    def _fill_lan(self):
        v = self.view
        if not self._visible("lan") or "table" not in v:
            return
        v["table"].set_rows([((r["ip"], r["mac"], r["vendor"], r["hostname"]), ()) for r in self.lan_rows])
        if self.lan_time:
            v["count"].set(f"{len(self.lan_rows)} cihaz · {self.lan_time}")
            v["progress"].set(1)
            v["label"].configure(text="Tarama tamamlandı.")
        else:
            v["count"].set("0 cihaz")

    def start_lan_scan(self):
        iface = self.lan_iface.get().strip() or None
        if "lan" in self.busy:
            return
        v = self.view
        v["start"].set_enabled(False)
        v["progress"].set(0)
        v["label"].configure(text="Ağ taranıyor…")

        def progress(done, total):
            def apply():
                if self._visible("lan") and "progress" in self.view:
                    self.view["progress"].set(done / max(total, 1))
                    self.view["label"].configure(text=f"{done}/{total} adres kontrol edildi")
            self.ui(apply)

        def finish():
            if self._visible("lan") and "start" in self.view:
                self.view["start"].set_enabled(True)

        def ok(rows):
            self.lan_rows, self.lan_time = rows, datetime.now().strftime("%H:%M")
            self.metrics["lan"][0].set(str(len(rows)))
            self.metrics["lan"][1].set(f"Son keşif {self.lan_time}")
            finish()
            self._fill_lan()
            self.set_status(f"LAN keşfi tamamlandı · {len(rows)} cihaz")

        def err(msg):
            finish()
            if self._visible("lan") and "label" in self.view:
                self.view["label"].configure(text="Tarama tamamlanamadı.")
            messagebox.showerror("Turtle · LAN keşfi", msg)
        self.worker("LAN keşfi", lambda: network.discover_lan(iface, progress), ok, err, key="lan")

    # ── Paket izleme ──
    def _page_capture(self):
        self._header("Paket İzleme", "Seçili arayüzdeki paketlerin yalnızca başlık metaverisini canlı görüntüle.")
        card = Card(self.content, (18, 14))
        card.pack(fill="x", pady=(0, S(12)))
        row = tk.Frame(card.body, bg=C.SURFACE)
        row.pack(fill="x")
        caption(row, "Arayüz").pack(side="left", padx=(0, S(10)))
        combo = self._iface_combo(row, self.cap_iface, 20)
        combo.pack(side="left", padx=(0, S(18)))
        caption(row, "Filtre").pack(side="left", padx=(0, S(10)))
        fcombo = ttk.Combobox(row, textvariable=self.cap_filter, state="readonly", width=12, style="Turtle.TCombobox",
                              font=FONT["body"], values=("Tümü", "TCP", "UDP", "ICMP", "ARP", "DNS", "Port:443"))
        fcombo.bind("<<ComboboxSelected>>", lambda e: fcombo.selection_clear())
        fcombo.pack(side="left")
        button = Btn(row, "İzlemeyi başlat", self.toggle_capture, "primary", icon="play", bg=C.SURFACE, width=S(170))
        button.pack(side="right")
        tk.Label(card.body, text="Paket gövdesi (payload) kaydedilmez veya gösterilmez. Scapy ve yönetici izni gerekebilir.",
                 bg=C.SURFACE, fg=C.MUTED, font=FONT["small"]).pack(anchor="w", pady=(S(10), 0))

        bar = tk.Frame(self.content, bg=C.BG)
        bar.pack(fill="x", pady=(0, S(10)))
        chips = {"total": Chip(bar, "", C.TEXT)}
        chips["total"].pack(side="left", padx=(0, S(8)))
        for proto in ("TCP", "UDP", "DNS", "ICMP", "ARP"):
            chips[proto] = Chip(bar, "", PROTO[proto])
            chips[proto].pack(side="left", padx=(0, S(8)))
        Btn(bar, "Temizle", self.clear_capture, "ghost", icon="trash", small=True).pack(side="right")
        tk.Label(bar, text="Otomatik kaydır", bg=C.BG, fg=C.TEXT2, font=FONT["small"]).pack(side="right", padx=(0, S(8)))
        Switch(bar, self.cap_autoscroll, C.BG).pack(side="right", padx=(0, S(8)))

        table = DataTable(self.content, [("time", "Saat", 90, "w", False), ("proto", "Protokol", 90, "w", False),
                                         ("src", "Kaynak", 190, "w", False), ("dst", "Hedef", 190, "w", False),
                                         ("info", "Başlık bilgisi", 320, "w", True)],
                          "capture", "Paket bekleniyor", "İzlemeyi başlattığında yakalanan paket başlıkları burada akar.",
                          mono=True, zebra=False)
        table.pack(fill="both", expand=True)
        self.view.update(cap_table=table, cap_button=button, cap_chips=chips, cap_combo=combo)
        for r in self.cap_rows:
            table.add((r["time"], r["protocol"], r["source"], r["dest"], r["info"]), (self._ptag(r["protocol"]),))
        table.tree.yview_moveto(1)
        self._sync_capture_button()
        self._refresh_cap_stats()

    @staticmethod
    def _ptag(proto):
        return proto if proto in PROTO else "OTHER"

    def _sync_capture_button(self):
        b = self.view.get("cap_button")
        if b is None:
            return
        if self.capture_active:
            b.update_style("İzlemeyi durdur", "danger", "stop")
        else:
            b.update_style("İzlemeyi başlat", "primary", "play")

    def _refresh_cap_stats(self):
        self._cap_job = None
        chips = self.view.get("cap_chips")
        if not chips or not self._visible("capture"):
            return
        chips["total"].set(f"{sum(self.cap_counts.values())} paket")
        for proto in ("TCP", "UDP", "DNS", "ICMP", "ARP"):
            chips[proto].set(f"{proto} {self.cap_counts[proto]}")

    def toggle_capture(self):
        if self.capture_active:
            if self.capture:
                self.capture.stop()
            self.capture_active = False
            self._sync_capture_button()
            self.set_status("Paket izleme durduruldu")
            return
        iface = self.cap_iface.get().strip()
        if not iface:
            messagebox.showwarning("Arayüz seç", "Önce izlenecek ağ arayüzünü seç.")
            return
        self.capture = network.PacketCapture(iface, self.cap_filter.get(),
                                             lambda row: self.ui(lambda: self._on_packet(row)),
                                             lambda msg: self.ui(lambda: self._capture_error(msg)))
        self.capture_active = True
        self._sync_capture_button()
        self.set_status(f"Paket başlıkları izleniyor · {iface}", C.BLUE)
        self.capture.start()

    def _on_packet(self, row):
        if not self.capture_active:
            return
        self.cap_rows.append(row)
        self.cap_counts[row["protocol"]] += 1
        table = self.view.get("cap_table") if self._visible("capture") else None
        if table is not None:
            table.add((row["time"], row["protocol"], row["source"], row["dest"], row["info"]),
                      (self._ptag(row["protocol"]),), see=self.cap_autoscroll.get())
            table.trim(500)
            if self._cap_job is None:
                self._cap_job = self.after(250, self._refresh_cap_stats)

    def _capture_error(self, msg):
        self.capture_active = False
        self._sync_capture_button()
        self.set_status("Paket izleme hatası", C.RED)
        messagebox.showerror("Turtle · Paket izleme", msg)

    def clear_capture(self):
        self.cap_rows.clear()
        self.cap_counts.clear()
        if self.view.get("cap_table") is not None:
            self.view["cap_table"].clear()
        self._refresh_cap_stats()

    # ── Port analizi ──
    def _page_ports(self):
        self._header("Port Analizi", "TCP bağlantı denemesiyle hedefteki açık servis portlarını belirle.")
        body = tk.Frame(self.content, bg=C.BG)
        body.pack(fill="both", expand=True)
        body.grid_columnconfigure(0, weight=0, minsize=S(360))
        body.grid_columnconfigure(1, weight=1)
        body.grid_rowconfigure(0, weight=1)

        form = Card(body, (20, 18))
        form.grid(row=0, column=0, sticky="new", padx=(0, S(14)))
        f = form.body
        tk.Label(f, text="Tarama ayarları", bg=C.SURFACE, fg=C.TEXT, font=FONT["h2"], anchor="w").pack(fill="x", pady=(0, S(14)))
        caption(f, "Hedef IP").pack(fill="x", pady=(0, S(6)))
        make_entry(f, self.port_target, True).pack(fill="x", ipady=S(7))
        caption(f, "Portlar").pack(fill="x", pady=(S(14), S(6)))
        make_entry(f, self.port_spec, True).pack(fill="x", ipady=S(7))
        presets = tk.Frame(f, bg=C.SURFACE)
        presets.pack(fill="x", pady=(S(8), 0))
        for text, spec in (("Web", "80,443,8080,8443"), ("Uzak erişim", "22,3389,5900"), ("1–1024", "1-1024")):
            Btn(presets, text, lambda s=spec: self.port_spec.set(s), "secondary", small=True, bg=C.SURFACE).pack(side="left", padx=(0, S(6)))
        auth = tk.Frame(f, bg=mix(C.AMBER, C.SURFACE, 0.08), highlightbackground=mix(C.AMBER, C.SURFACE, 0.28), highlightthickness=1)
        auth.pack(fill="x", pady=(S(18), S(16)))
        inner = tk.Frame(auth, bg=auth.cget("bg"))
        inner.pack(fill="x", padx=S(12), pady=S(10))
        Switch(inner, self.port_auth, auth.cget("bg")).pack(side="right", padx=(S(10), 0))
        tk.Label(inner, text="Özel LAN dışındaki hedef için yazılı tarama yetkim var.", bg=auth.cget("bg"),
                 fg=C.AMBER, font=FONT["small"], justify="left", wraplength=S(220), anchor="w").pack(side="left", fill="x", expand=True)
        start = Btn(f, "Portları tara", self.start_port_scan, "primary", icon="search", bg=C.SURFACE)
        start.pack(fill="x")
        start.min_w = 0
        label = tk.Label(f, text="En fazla 4096 port / tarama", bg=C.SURFACE, fg=C.MUTED, font=FONT["small"], anchor="w")
        label.pack(fill="x", pady=(S(14), S(8)))
        progress = Progress(f, C.SURFACE)
        progress.pack(fill="x")

        res = tk.Frame(body, bg=C.BG)
        res.grid(row=0, column=1, sticky="nsew")
        bar = tk.Frame(res, bg=C.BG)
        bar.pack(fill="x", pady=(0, S(10)))
        tk.Label(bar, text="Sonuçlar", bg=C.BG, fg=C.TEXT, font=FONT["h2"]).pack(side="left")
        count = Chip(bar, "", C.TEXT2)
        count.pack(side="right")
        table = DataTable(res, [("port", "Port", 120, "w", False), ("service", "Olası servis", 240, "w", True),
                                ("state", "Durum", 140, "w", False)],
                          "ports", "Sonuç yok", "Bir hedef ve port aralığı seçip taramayı başlat. Yalnızca açık portlar listelenir.")
        table.pack(fill="both", expand=True)
        self.view.update(table=table, progress=progress, label=label, count=count, start=start)
        if "ports" in self.busy:
            start.set_enabled(False)
        self._fill_ports()

    def _fill_ports(self):
        v = self.view
        if not self._visible("ports") or "table" not in v:
            return
        v["table"].set_rows([((r["port"], r["service"], "●  Açık"), ()) for r in self.port_rows])
        if self.port_info:
            v["count"].set(f"{len(self.port_rows)} açık port · {self.port_info}")
            v["progress"].set(1)
            v["label"].configure(text="Analiz tamamlandı.")
        else:
            v["count"].set("0 açık port")

    def start_port_scan(self):
        target, spec, auth = self.port_target.get().strip(), self.port_spec.get().strip(), self.port_auth.get()
        if "ports" in self.busy:
            return
        try:
            network.parse_ports(spec)
        except Exception as exc:
            messagebox.showerror("Port aralığı", str(exc))
            return
        v = self.view
        v["start"].set_enabled(False)
        v["table"].clear()
        v["progress"].set(0)
        v["label"].configure(text="Portlar kontrol ediliyor…")

        def progress(done, total):
            def apply():
                if self._visible("ports") and "progress" in self.view:
                    self.view["progress"].set(done / max(total, 1))
                    self.view["label"].configure(text=f"{done}/{total} port kontrol edildi")
            self.ui(apply)

        def finish():
            if self._visible("ports") and "start" in self.view:
                self.view["start"].set_enabled(True)

        def ok(rows):
            self.port_rows, self.port_info = rows, target
            self.metrics["ports"][0].set(str(len(rows)))
            self.metrics["ports"][1].set(f"Hedef {target}")
            finish()
            self._fill_ports()
            self.set_status(f"Port analizi tamamlandı · {target} · {len(rows)} açık port")

        def err(msg):
            finish()
            if self._visible("ports") and "label" in self.view:
                self.view["label"].configure(text="Analiz tamamlanamadı.")
            messagebox.showerror("Turtle · Port analizi", msg)
        self.worker("TCP port analizi", lambda: network.scan_ports(target, spec, auth, progress=progress), ok, err, key="ports")

    # ── Hakkında ──
    def _page_about(self):
        self._header("Hakkında", "Türkçe ağ keşif ve analiz aracı · Masaüstü sürümü")
        body = tk.Frame(self.content, bg=C.BG)
        body.pack(fill="both", expand=True)
        body.grid_columnconfigure(0, weight=3, uniform="a")
        body.grid_columnconfigure(1, weight=2, uniform="a")
        body.grid_rowconfigure(0, weight=1)

        main = Card(body, (28, 26))
        main.grid(row=0, column=0, sticky="nsew", padx=(0, S(14)))
        top = tk.Frame(main.body, bg=C.SURFACE)
        top.pack(fill="x")
        Logo(top, 52, C.SURFACE).pack(side="left")
        names = tk.Frame(top, bg=C.SURFACE)
        names.pack(side="left", padx=S(16))
        tk.Label(names, text="Turtle · Network Explorer", bg=C.SURFACE, fg=C.TEXT, font=FONT["h2"]).pack(anchor="w")
        Chip(names, f"Sürüm {network.APP_VERSION}", C.ACCENT, C.SURFACE).pack(anchor="w", pady=(S(6), 0))
        desc = tk.Label(main.body, text="Ağ arayüzleri, Wi-Fi listeleme, özel LAN keşfi, başlık düzeyinde paket izleme ve "
                        "TCP port analizini tek pencerede sunar.\n\nGüvenlik için LAN keşfi özel alt ağla sınırlandırılır; "
                        "özel olmayan hedeflerde port taraması açık yetki onayı ister. Paket içeriği hiçbir zaman görüntülenmez.",
                        bg=C.SURFACE, fg=C.TEXT2, font=FONT["body"], justify="left", anchor="w", wraplength=S(400))
        desc.pack(fill="x", pady=(S(22), S(24)))
        main.body.bind("<Configure>", lambda e: desc.configure(wraplength=max(200, e.width - 4)))
        btns = tk.Frame(main.body, bg=C.SURFACE)
        btns.pack(anchor="w")
        Btn(btns, "GitHub deposunu aç", lambda: webbrowser.open("https://github.com/cn-Ky/Turtle"), "primary",
            icon="external", bg=C.SURFACE).pack(side="left")
        Btn(btns, "Lisans", lambda: messagebox.showinfo("MIT Lisansı", "Bu proje MIT lisansı kapsamında sunulur. "
            "Ayrıntılar için paketteki LICENSE dosyasına bak."), "secondary", bg=C.SURFACE).pack(side="left", padx=S(10))

        side = Card(body, (24, 22))
        side.grid(row=0, column=1, sticky="nsew")
        tk.Label(side.body, text="Güvenlik ilkeleri", bg=C.SURFACE, fg=C.TEXT, font=FONT["h2"], anchor="w").pack(fill="x", pady=(0, S(10)))
        for text in ("LAN keşfi en fazla /22 alt ağla sınırlıdır.", "Harici hedefler için açık yetki onayı gerekir.",
                     "Paket yakalama yalnızca başlık metaverisini gösterir.", "Wi-Fi taraması pasiftir; enjeksiyon yapılmaz.",
                     "Kısayollar: " + ("⌘" if MAC else "Ctrl") + " + 1–7 ile sayfalar arasında geç."):
            row = tk.Frame(side.body, bg=C.SURFACE)
            row.pack(fill="x", pady=S(6))
            Icon(row, "check", C.ACCENT, 14, C.SURFACE).pack(side="left", anchor="n", pady=2)
            tk.Label(row, text=text, bg=C.SURFACE, fg=C.TEXT2, font=FONT["small"], justify="left", anchor="w",
                     wraplength=S(260)).pack(side="left", padx=S(10))

    def destroy(self):
        if self.capture:
            self.capture.stop()
        try:
            self.after_cancel(self._pump_id)
        except Exception:
            pass
        super().destroy()


if __name__ == "__main__":
    TurtleApp().mainloop()
