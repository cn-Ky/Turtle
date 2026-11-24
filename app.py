from __future__ import annotations

import threading
import tkinter as tk
from tkinter import messagebox, ttk
import webbrowser

import network

BG = "#0b1120"
SIDEBAR = "#0e1728"
PANEL = "#121e31"
PANEL_ALT = "#17253a"
BORDER = "#26364d"
TEXT = "#e7eef8"
MUTED = "#8da0b8"
ACCENT = "#55d6a7"
ACCENT_DARK = "#173f3b"
BLUE = "#6da8ff"
ORANGE = "#f2b66d"
RED = "#f17f87"
FONT = "Helvetica"


class TurtleApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Turtle · Network Explorer")
        self.geometry("1220x790")
        self.minsize(1020, 680)
        self.configure(bg=BG)
        self.current_page = "dashboard"
        self.interface_names: list[str] = []
        self.capture: network.PacketCapture | None = None
        self.capture_active = False
        self._configure_style()
        self._build_shell()
        self.show_page("dashboard")
        self.after(250, self.refresh_interfaces_silent)

    def _configure_style(self):
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("TFrame", background=BG)
        style.configure("Panel.TFrame", background=PANEL)
        style.configure("Sidebar.TFrame", background=SIDEBAR)
        style.configure("TLabel", background=BG, foreground=TEXT, font=(FONT, 10))
        style.configure("Muted.TLabel", background=BG, foreground=MUTED, font=(FONT, 9))
        style.configure("Panel.TLabel", background=PANEL, foreground=TEXT, font=(FONT, 10))
        style.configure("PanelMuted.TLabel", background=PANEL, foreground=MUTED, font=(FONT, 9))
        style.configure("CardTitle.TLabel", background=PANEL, foreground=MUTED, font=(FONT, 9, "bold"))
        style.configure("Metric.TLabel", background=PANEL, foreground=TEXT, font=(FONT, 22, "bold"))
        style.configure("Title.TLabel", background=BG, foreground=TEXT, font=(FONT, 22, "bold"))
        style.configure("Subtitle.TLabel", background=BG, foreground=MUTED, font=(FONT, 10))
        style.configure("TButton", background=PANEL_ALT, foreground=TEXT, borderwidth=0,
                        padding=(12, 8), font=(FONT, 9, "bold"))
        style.map("TButton", background=[("active", "#22344d"), ("disabled", "#172235")],
                  foreground=[("disabled", "#60738c")])
        style.configure("Accent.TButton", background=ACCENT, foreground="#062219",
                        padding=(14, 9), font=(FONT, 9, "bold"))
        style.map("Accent.TButton", background=[("active", "#78e6bd"), ("disabled", "#315d54")])
        style.configure("Danger.TButton", background="#532d3a", foreground="#ffdce0", padding=(12, 8))
        style.configure("TEntry", fieldbackground=PANEL_ALT, foreground=TEXT,
                        insertcolor=TEXT, bordercolor=BORDER, padding=8)
        style.configure("TCombobox", fieldbackground=PANEL_ALT, foreground=TEXT,
                        background=PANEL_ALT, arrowcolor=ACCENT, bordercolor=BORDER, padding=7)
        style.map("TCombobox", fieldbackground=[("readonly", PANEL_ALT)],
                  foreground=[("readonly", TEXT)])
        style.configure("Treeview", background=PANEL, fieldbackground=PANEL,
                        foreground=TEXT, rowheight=30, bordercolor=BORDER,
                        font=(FONT, 9))
        style.configure("Treeview.Heading", background=PANEL_ALT, foreground=MUTED,
                        relief="flat", font=(FONT, 9, "bold"), padding=8)
        style.map("Treeview", background=[("selected", "#23423f")],
                  foreground=[("selected", "#ffffff")])
        style.configure("Horizontal.TProgressbar", troughcolor=PANEL_ALT,
                        background=ACCENT, bordercolor=PANEL_ALT, lightcolor=ACCENT,
                        darkcolor=ACCENT)
        style.configure("TCheckbutton", background=BG, foreground=TEXT, font=(FONT, 9))
        style.map("TCheckbutton", background=[("active", BG)], foreground=[("active", TEXT)])

    def _build_shell(self):
        shell = tk.Frame(self, bg=BG)
        shell.pack(fill="both", expand=True)
        self.sidebar = tk.Frame(shell, bg=SIDEBAR, width=222)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)
        brand = tk.Frame(self.sidebar, bg=SIDEBAR)
        brand.pack(fill="x", padx=22, pady=(25, 30))
        tk.Label(brand, text="◉", bg=SIDEBAR, fg=ACCENT, font=(FONT, 25, "bold")).pack(side="left")
        title_box = tk.Frame(brand, bg=SIDEBAR)
        title_box.pack(side="left", padx=10)
        tk.Label(title_box, text="TURTLE", bg=SIDEBAR, fg=TEXT,
                 font=(FONT, 16, "bold")).pack(anchor="w")
        tk.Label(title_box, text="NETWORK EXPLORER", bg=SIDEBAR, fg=MUTED,
                 font=(FONT, 7, "bold")).pack(anchor="w")
        tk.Label(self.sidebar, text="ÇALIŞMA ALANI", bg=SIDEBAR, fg="#60748e",
                 font=(FONT, 8, "bold")).pack(anchor="w", padx=22, pady=(0, 10))
        self.nav_buttons = {}
        nav_items = [
            ("dashboard", "⌂", "Genel Bakış"),
            ("interfaces", "▦", "Ağ Arayüzleri"),
            ("wifi", "◔", "Wi-Fi Ağları"),
            ("lan", "⌘", "Yerel Ağ Keşfi"),
            ("capture", "◉", "Paket İzleme"),
            ("ports", "⇄", "Port Analizi"),
            ("about", "ⓘ", "Hakkında"),
        ]
        for key, icon, label in nav_items:
            button = tk.Button(self.sidebar, text=f"  {icon}     {label}", anchor="w",
                               bg=SIDEBAR, fg=MUTED, activebackground=PANEL_ALT,
                               activeforeground=TEXT, relief="flat", bd=0,
                               font=(FONT, 10, "bold"), padx=17, pady=12,
                               command=lambda k=key: self.show_page(k), cursor="hand2")
            button.pack(fill="x", padx=10, pady=2)
            self.nav_buttons[key] = button
        bottom = tk.Frame(self.sidebar, bg=SIDEBAR)
        bottom.pack(side="bottom", fill="x", padx=18, pady=18)
        tk.Frame(bottom, bg=BORDER, height=1).pack(fill="x", pady=(0, 13))
        tk.Label(bottom, text="Turtle GUI  ·  v1.1.0", bg=SIDEBAR,
                 fg=MUTED, font=(FONT, 8)).pack(anchor="w")
        tk.Label(bottom, text="Eğitim ve yetkili kullanım için", bg=SIDEBAR,
                 fg="#647b96", font=(FONT, 8)).pack(anchor="w", pady=(4, 0))

        main = tk.Frame(shell, bg=BG)
        main.pack(side="left", fill="both", expand=True)
        self.content = tk.Frame(main, bg=BG)
        self.content.pack(fill="both", expand=True, padx=30, pady=(24, 12))
        status = tk.Frame(main, bg=SIDEBAR, height=34)
        status.pack(side="bottom", fill="x")
        status.pack_propagate(False)
        self.status_label = tk.Label(status, text="●  Hazır", bg=SIDEBAR, fg=ACCENT,
                                     font=(FONT, 8), anchor="w")
        self.status_label.pack(side="left", padx=20, pady=7)
        tk.Label(status, text="Yalnızca izinli ağlarda kullanın", bg=SIDEBAR,
                 fg=MUTED, font=(FONT, 8)).pack(side="right", padx=20)

    def set_status(self, message: str, color: str = ACCENT):
        self.after(0, lambda: self.status_label.configure(text=f"●  {message}", fg=color))

    def worker(self, label: str, fn, on_success, on_error=None):
        self.set_status(f"{label} çalışıyor…", BLUE)
        def run():
            try:
                result = fn()
                self.after(0, lambda: on_success(result))
            except Exception as exc:
                message = str(exc)
                def show_error():
                    self.set_status("İşlem tamamlanamadı", RED)
                    if on_error:
                        on_error(message)
                    else:
                        messagebox.showerror("Turtle · İşlem hatası", message)
                self.after(0, show_error)
        threading.Thread(target=run, daemon=True).start()

    def _clear(self):
        for child in self.content.winfo_children():
            child.destroy()

    def _heading(self, title: str, subtitle: str):
        header = tk.Frame(self.content, bg=BG)
        header.pack(fill="x", pady=(0, 22))
        ttk.Label(header, text=title, style="Title.TLabel").pack(anchor="w")
        ttk.Label(header, text=subtitle, style="Subtitle.TLabel").pack(anchor="w", pady=(6, 0))

    def _panel(self, parent, padx=18, pady=16):
        frame = tk.Frame(parent, bg=PANEL, highlightbackground=BORDER,
                         highlightthickness=1, padx=padx, pady=pady)
        return frame

    def _tree(self, parent, columns, headings, widths=None, height=12):
        wrap = tk.Frame(parent, bg=PANEL)
        wrap.pack(fill="both", expand=True)
        tree = ttk.Treeview(wrap, columns=columns, show="headings", height=height)
        for i, (col, heading) in enumerate(zip(columns, headings)):
            tree.heading(col, text=heading)
            tree.column(col, width=(widths[i] if widths else 140), anchor="w")
        scroll = ttk.Scrollbar(wrap, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=scroll.set)
        tree.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")
        return tree

    def _card_metric(self, parent, title, value, note, accent=ACCENT):
        card = self._panel(parent, 17, 15)
        card.pack(side="left", fill="both", expand=True, padx=(0, 12))
        tk.Label(card, text=title.upper(), bg=PANEL, fg=MUTED,
                 font=(FONT, 8, "bold")).pack(anchor="w")
        tk.Label(card, text=value, bg=PANEL, fg=accent,
                 font=(FONT, 23, "bold")).pack(anchor="w", pady=(9, 3))
        tk.Label(card, text=note, bg=PANEL, fg=MUTED,
                 font=(FONT, 8)).pack(anchor="w")
        return card

    def show_page(self, page: str):
        self.current_page = page
        for key, button in self.nav_buttons.items():
            active = key == page
            button.configure(bg=ACCENT_DARK if active else SIDEBAR,
                             fg=ACCENT if active else MUTED)
        self._clear()
        pages = {"dashboard": self._page_dashboard, "interfaces": self._page_interfaces,
                 "wifi": self._page_wifi, "lan": self._page_lan,
                 "capture": self._page_capture, "ports": self._page_ports,
                 "about": self._page_about}
        pages.get(page, self._page_dashboard)()

    def refresh_interfaces_silent(self):
        try:
            rows = network.get_interfaces()
            self.interface_names = [r["name"] for r in rows]
        except Exception:
            pass

    def _page_dashboard(self):
        self._heading("Genel Bakış", "Yerel ağını gözlemle, cihazlarını keşfet ve bağlantılarını analiz et.")
        metrics = tk.Frame(self.content, bg=BG)
        metrics.pack(fill="x", pady=(0, 18))
        self._card_metric(metrics, "Platform", "macOS / Win / Linux", "Çoklu işletim sistemi", BLUE)
        self._card_metric(metrics, "Modüller", "05", "Ağ ve analiz araçları")
        self._card_metric(metrics, "Güvenlik", "Yerel öncelikli", "LAN sınırları ve yetki kontrolü", ORANGE)
        body = tk.Frame(self.content, bg=BG)
        body.pack(fill="both", expand=True)
        left = self._panel(body, 20, 18)
        left.pack(side="left", fill="both", expand=True, padx=(0, 14))
        tk.Label(left, text="HIZLI ERİŞİM", bg=PANEL, fg=MUTED,
                 font=(FONT, 8, "bold")).pack(anchor="w")
        actions = [
            ("Ağ arayüzlerini görüntüle", "Bağdaştırıcı, IPv4 ve MAC bilgileri", "interfaces"),
            ("Yakındaki Wi-Fi ağları", "SSID, BSSID, kanal ve güvenlik", "wifi"),
            ("Yerel ağ cihazlarını keşfet", "Bağlı olduğun özel LAN üzerinde", "lan"),
            ("Paket başlıklarını izle", "Payload gösterilmez", "capture"),
            ("TCP portlarını analiz et", "Yetki kontrollü hedef taraması", "ports"),
        ]
        for title, desc, key in actions:
            row = tk.Frame(left, bg=PANEL)
            row.pack(fill="x", pady=(13, 0))
            tk.Button(row, text="›", bg=PANEL_ALT, fg=ACCENT, relief="flat",
                      font=(FONT, 14, "bold"), width=3, command=lambda k=key: self.show_page(k)).pack(side="left")
            text = tk.Frame(row, bg=PANEL)
            text.pack(side="left", padx=12)
            tk.Label(text, text=title, bg=PANEL, fg=TEXT, font=(FONT, 10, "bold")).pack(anchor="w")
            tk.Label(text, text=desc, bg=PANEL, fg=MUTED, font=(FONT, 8)).pack(anchor="w", pady=(3, 0))
        right = self._panel(body, 20, 18)
        right.configure(width=260)
        right.pack(side="right", fill="y")
        right.pack_propagate(False)
        tk.Label(right, text="KULLANIM NOTU", bg=PANEL, fg=ORANGE,
                 font=(FONT, 8, "bold")).pack(anchor="w")
        tk.Label(right, text="Turtle yalnızca kendi ağında veya yazılı izin aldığın sistemlerde kullanılmalıdır.",
                 bg=PANEL, fg=TEXT, font=(FONT, 10), wraplength=220,
                 justify="left").pack(anchor="w", pady=(12, 15))
        tk.Label(right, text="• LAN keşfi en fazla /22 alt ağla sınırlıdır.\n\n• Harici IP taraması için açık yetki onayı gerekir.\n\n• Paket yakalama yalnızca başlık metaverisini gösterir.\n\n• Wi-Fi listesi işletim sisteminin yerel aracını kullanır.",
                 bg=PANEL, fg=MUTED, font=(FONT, 9), justify="left", wraplength=220).pack(anchor="w")

    def _page_interfaces(self):
        self._heading("Ağ Arayüzleri", "Sistemdeki ağ bağdaştırıcılarını ve temel adres bilgilerini listele.")
        top = tk.Frame(self.content, bg=BG)
        top.pack(fill="x", pady=(0, 12))
        ttk.Button(top, text="↻  Yenile", style="Accent.TButton",
                   command=self.load_interfaces).pack(side="left")
        self.iface_count = ttk.Label(top, text="", style="Subtitle.TLabel")
        self.iface_count.pack(side="left", padx=14)
        panel = self._panel(self.content)
        panel.pack(fill="both", expand=True)
        self.iface_tree = self._tree(panel, ("name", "state", "ipv4", "mac"),
                                     ("ARAYÜZ", "DURUM", "IPv4 ADRESİ", "MAC ADRESİ"),
                                     (230, 100, 220, 220), 16)
        self.load_interfaces()

    def load_interfaces(self):
        def success(rows):
            self.interface_names = [r["name"] for r in rows]
            for item in self.iface_tree.get_children(): self.iface_tree.delete(item)
            for r in rows:
                self.iface_tree.insert("", "end", values=(r["name"], r["state"], r["ipv4"], r["mac"]))
            self.iface_count.configure(text=f"{len(rows)} arayüz bulundu")
            self.set_status("Ağ arayüzleri güncellendi")
        self.worker("Arayüz listesi", network.get_interfaces, success)

    def _page_wifi(self):
        self._heading("Wi-Fi Ağları", "İşletim sisteminin Wi-Fi taramasını kullanarak yakındaki ağları pasif biçimde listele.")
        bar = tk.Frame(self.content, bg=BG)
        bar.pack(fill="x", pady=(0, 12))
        ttk.Button(bar, text="⌕  Ağları Tara", style="Accent.TButton",
                   command=self.load_wifi).pack(side="left")
        ttk.Label(bar, text="Paket enjeksiyonu veya bağlantı kesme işlemi yapılmaz.",
                  style="Subtitle.TLabel").pack(side="left", padx=14)
        panel = self._panel(self.content)
        panel.pack(fill="both", expand=True)
        self.wifi_tree = self._tree(panel, ("ssid", "bssid", "channel", "signal", "security"),
                                    ("SSID", "BSSID", "KANAL", "SİNYAL", "GÜVENLİK"),
                                    (250, 190, 90, 110, 180), 16)
        tk.Label(self.content, text="Not: Bazı macOS sürümlerinde Wi-Fi/konum izni veya yönetici onayı gerekebilir.",
                 bg=BG, fg=MUTED, font=(FONT, 8)).pack(anchor="w", pady=(9, 0))

    def load_wifi(self):
        def success(rows):
            for item in self.wifi_tree.get_children(): self.wifi_tree.delete(item)
            for r in rows:
                self.wifi_tree.insert("", "end", values=(r["ssid"], r["bssid"], r["channel"], r["signal"], r["security"]))
            self.set_status(f"{len(rows)} Wi-Fi ağı listelendi")
        self.worker("Wi-Fi taraması", network.scan_wifi, success)

    def _page_lan(self):
        self._heading("Yerel Ağ Keşfi", "Yalnızca bağlı olduğun özel IPv4 LAN üzerinde erişilebilir cihazları bul.")
        controls = self._panel(self.content, 16, 14)
        controls.pack(fill="x", pady=(0, 12))
        row = tk.Frame(controls, bg=PANEL)
        row.pack(fill="x")
        tk.Label(row, text="AĞ ARAYÜZÜ", bg=PANEL, fg=MUTED,
                 font=(FONT, 8, "bold")).pack(side="left", padx=(0, 10))
        self.lan_iface = ttk.Combobox(row, state="readonly", width=28, values=self.interface_names)
        self.lan_iface.pack(side="left")
        if self.interface_names: self.lan_iface.set(self.interface_names[0])
        ttk.Button(row, text="↻", command=self._refresh_lan_ifaces).pack(side="left", padx=6)
        ttk.Button(row, text="⌕  LAN Keşfini Başlat", style="Accent.TButton",
                   command=self.start_lan_scan).pack(side="right")
        self.lan_progress_label = ttk.Label(controls, text="Tarama /22 sınırı içinde tutulur.", style="PanelMuted.TLabel")
        self.lan_progress_label.pack(anchor="w", pady=(10, 0))
        self.lan_progress = ttk.Progressbar(controls, mode="determinate", maximum=100)
        self.lan_progress.pack(fill="x", pady=(8, 0))
        panel = self._panel(self.content)
        panel.pack(fill="both", expand=True)
        self.lan_tree = self._tree(panel, ("ip", "mac", "vendor", "hostname"),
                                   ("IP ADRESİ", "MAC ADRESİ", "ÜRETİCİ", "ANA BİLGİSAYAR"),
                                   (180, 200, 190, 260), 12)
        self._refresh_lan_ifaces()

    def _refresh_lan_ifaces(self):
        try:
            rows = network.get_interfaces()
            self.interface_names = [r["name"] for r in rows]
            self.lan_iface["values"] = self.interface_names
            if self.interface_names and not self.lan_iface.get(): self.lan_iface.set(self.interface_names[0])
        except Exception as exc:
            messagebox.showerror("Arayüz listesi", str(exc))

    def start_lan_scan(self):
        iface = self.lan_iface.get().strip() or None
        self.lan_progress["value"] = 0
        self.lan_progress_label.configure(text="Ağ taranıyor…")
        def progress(done, total):
            self.after(0, lambda: (self.lan_progress.configure(value=done / max(total, 1) * 100),
                                   self.lan_progress_label.configure(text=f"{done}/{total} adres kontrol edildi")))
        def success(rows):
            for item in self.lan_tree.get_children(): self.lan_tree.delete(item)
            for r in rows:
                self.lan_tree.insert("", "end", values=(r["ip"], r["mac"], r["vendor"], r["hostname"]))
            self.lan_progress["value"] = 100
            self.lan_progress_label.configure(text=f"Tamamlandı · {len(rows)} cihaz bulundu")
            self.set_status(f"LAN keşfi tamamlandı · {len(rows)} cihaz")
        self.worker("LAN keşfi", lambda: network.discover_lan(iface, progress), success)

    def _page_capture(self):
        try:
            self.interface_names = [r["name"] for r in network.get_interfaces()]
        except Exception:
            self.interface_names = []
        self._heading("Paket İzleme", "Seçili ağ arayüzündeki paketlerin yalnızca başlık metaverisini görüntüle.")
        controls = self._panel(self.content, 16, 14)
        controls.pack(fill="x", pady=(0, 12))
        row = tk.Frame(controls, bg=PANEL)
        row.pack(fill="x")
        tk.Label(row, text="ARAYÜZ", bg=PANEL, fg=MUTED, font=(FONT, 8, "bold")).pack(side="left", padx=(0, 8))
        self.capture_iface = ttk.Combobox(row, state="readonly", width=20, values=self.interface_names)
        self.capture_iface.pack(side="left", padx=(0, 14))
        if self.interface_names: self.capture_iface.set(self.interface_names[0])
        tk.Label(row, text="FİLTRE", bg=PANEL, fg=MUTED, font=(FONT, 8, "bold")).pack(side="left", padx=(0, 8))
        self.capture_filter = ttk.Combobox(row, state="readonly", width=15,
                                           values=("Tümü", "TCP", "UDP", "ICMP", "ARP", "DNS", "Port:443"))
        self.capture_filter.set("Tümü")
        self.capture_filter.pack(side="left")
        self.capture_button = ttk.Button(row, text="▶  İzlemeyi Başlat", style="Accent.TButton", command=self.toggle_capture)
        self.capture_button.pack(side="right")
        tk.Label(controls, text="Paket gövdesi (payload) kaydedilmez veya ekranda gösterilmez. Scapy ve yönetici izni gerekebilir.",
                 bg=PANEL, fg=MUTED, font=(FONT, 8)).pack(anchor="w", pady=(10, 0))
        panel = self._panel(self.content)
        panel.pack(fill="both", expand=True)
        self.capture_tree = self._tree(panel, ("time", "protocol", "source", "dest", "info"),
                                       ("SAAT", "PROTOKOL", "KAYNAK", "HEDEF", "BAŞLIK BİLGİSİ"),
                                       (90, 100, 170, 170, 300), 14)
        bottom = tk.Frame(self.content, bg=BG)
        bottom.pack(fill="x", pady=(8, 0))
        ttk.Button(bottom, text="Listeyi Temizle", command=self.clear_capture).pack(side="right")

    def toggle_capture(self):
        if self.capture_active:
            if self.capture: self.capture.stop()
            self.capture_active = False
            self.capture_button.configure(text="▶  İzlemeyi Başlat", style="Accent.TButton")
            self.set_status("Paket izleme durduruldu")
            return
        iface = self.capture_iface.get().strip()
        if not iface:
            messagebox.showwarning("Arayüz seç", "Önce izlenecek ağ arayüzünü seç.")
            return
        self.capture = network.PacketCapture(iface, self.capture_filter.get(), self._on_packet, self._capture_error)
        self.capture_active = True
        self.capture_button.configure(text="■  İzlemeyi Durdur", style="Danger.TButton")
        self.set_status("Paket başlıkları izleniyor", BLUE)
        self.capture.start()

    def _on_packet(self, row):
        def insert():
            if not self.winfo_exists(): return
            self.capture_tree.insert("", "end", values=(row["time"], row["protocol"], row["source"], row["dest"], row["info"]))
            children = self.capture_tree.get_children()
            if len(children) > 500:
                self.capture_tree.delete(children[0])
            if children:
                self.capture_tree.see(self.capture_tree.get_children()[-1])
        self.after(0, insert)

    def _capture_error(self, error):
        def show():
            self.capture_active = False
            self.capture_button.configure(text="▶  İzlemeyi Başlat", style="Accent.TButton")
            self.set_status("Paket izleme hatası", RED)
            messagebox.showerror("Paket izleme", error)
        self.after(0, show)

    def clear_capture(self):
        for item in self.capture_tree.get_children(): self.capture_tree.delete(item)

    def _page_ports(self):
        self._heading("Port Analizi", "TCP bağlantı kontrolüyle açık servis portlarını belirle.")
        controls = self._panel(self.content, 18, 17)
        controls.pack(fill="x", pady=(0, 12))
        grid = tk.Frame(controls, bg=PANEL)
        grid.pack(fill="x")
        self.port_target = self._field(grid, "HEDEF IP", "192.168.1.1", 0, 0, 24)
        self.port_spec = self._field(grid, "PORTLAR", "22,80,443,8080", 0, 1, 24)
        self.port_authorized = tk.BooleanVar(value=False)
        check = tk.Checkbutton(controls, text="Özel LAN dışında kalan hedef için yazılı tarama yetkim var.",
                               variable=self.port_authorized, bg=PANEL, fg=ORANGE,
                               activebackground=PANEL, activeforeground=ORANGE,
                               selectcolor=PANEL_ALT, font=(FONT, 9))
        check.pack(anchor="w", pady=(13, 12))
        action_row = tk.Frame(controls, bg=PANEL)
        action_row.pack(fill="x")
        ttk.Button(action_row, text="⌕  Portları Tara", style="Accent.TButton",
                   command=self.start_port_scan).pack(side="right")
        self.port_progress_label = ttk.Label(action_row, text="Maksimum 4096 port / tarama", style="PanelMuted.TLabel")
        self.port_progress_label.pack(side="left")
        self.port_progress = ttk.Progressbar(controls, mode="determinate", maximum=100)
        self.port_progress.pack(fill="x", pady=(10, 0))
        panel = self._panel(self.content)
        panel.pack(fill="both", expand=True)
        self.port_tree = self._tree(panel, ("port", "service", "state"),
                                    ("PORT", "OLASI SERVİS", "DURUM"), (130, 230, 140), 12)

    def _field(self, parent, label, value, row, col, width):
        group = tk.Frame(parent, bg=PANEL)
        group.grid(row=row, column=col, sticky="ew", padx=(0 if col == 0 else 14, 0))
        parent.grid_columnconfigure(col, weight=1)
        tk.Label(group, text=label, bg=PANEL, fg=MUTED,
                 font=(FONT, 8, "bold")).pack(anchor="w", pady=(0, 7))
        entry = ttk.Entry(group, width=width)
        entry.insert(0, value)
        entry.pack(fill="x")
        return entry

    def start_port_scan(self):
        target = self.port_target.get().strip()
        spec = self.port_spec.get().strip()
        authorized = self.port_authorized.get()
        try:
            network.parse_ports(spec)
        except Exception as exc:
            messagebox.showerror("Port aralığı", str(exc)); return
        self.port_progress["value"] = 0
        for item in self.port_tree.get_children(): self.port_tree.delete(item)
        self.port_progress_label.configure(text="Portlar kontrol ediliyor…")
        def progress(done, total):
            self.after(0, lambda: (self.port_progress.configure(value=done / max(total, 1) * 100),
                                   self.port_progress_label.configure(text=f"{done}/{total} port kontrol edildi")))
        def success(rows):
            for r in rows:
                self.port_tree.insert("", "end", values=(r["port"], r["service"], r["state"]))
            self.port_progress["value"] = 100
            self.port_progress_label.configure(text=f"Tamamlandı · {len(rows)} açık port bulundu")
            self.set_status(f"Port analizi tamamlandı · {len(rows)} açık port")
            if not rows:
                messagebox.showinfo("Port analizi", "Belirtilen aralıkta açık TCP portu bulunamadı.")
        self.worker("TCP port analizi", lambda: network.scan_ports(target, spec, authorized, progress=progress), success)

    def _page_about(self):
        self._heading("Turtle Hakkında", "Türkçe ağ keşif ve analiz aracı · Masaüstü GUI sürümü")
        panel = self._panel(self.content, 22, 22)
        panel.pack(fill="both", expand=True)
        tk.Label(panel, text="TURTLE  /  NETWORK EXPLORER", bg=PANEL, fg=ACCENT,
                 font=(FONT, 17, "bold")).pack(anchor="w")
        tk.Label(panel, text="Sürüm 1.1.0  ·  Python + Tkinter", bg=PANEL, fg=MUTED,
                 font=(FONT, 9)).pack(anchor="w", pady=(5, 18))
        tk.Label(panel, text=(
                 "Bu masaüstü arayüzü cn-Ky/Turtle deposundaki ağ keşif kapsamını Python ile yeniden uygular.\n\n"
                 "Ağ arayüzleri, Wi-Fi listeleme, özel LAN keşfi, başlık düzeyinde paket izleme ve TCP port analizi tek pencerede sunulur.\n\n"
                 "Güvenlik için LAN keşfi özel alt ağla sınırlandırılır; özel olmayan hedeflerde port taraması açık yetki onayı ister. Paket içeriği hiçbir zaman görüntülenmez."),
                 bg=PANEL, fg=TEXT, font=(FONT, 10), justify="left", wraplength=780).pack(anchor="w")
        actions = tk.Frame(panel, bg=PANEL)
        actions.pack(anchor="w", pady=(24, 0))
        ttk.Button(actions, text="GitHub deposunu aç", style="Accent.TButton",
                   command=lambda: webbrowser.open("https://github.com/cn-Ky/Turtle")).pack(side="left")
        ttk.Button(actions, text="Lisans bilgisi", command=lambda: messagebox.showinfo(
            "MIT Lisansı", "Bu proje MIT lisansı kapsamında sunulur. Ayrıntılar için paketteki LICENSE dosyasına bak.")).pack(side="left", padx=10)

    def destroy(self):
        if self.capture:
            self.capture.stop()
        super().destroy()


if __name__ == "__main__":
    app = TurtleApp()
    app.mainloop()
