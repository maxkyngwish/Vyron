import datetime
import json
import os
import random
import subprocess
import sys
import threading
import tkinter as tk
import tkinter.font as tkfont
import traceback
from tkinter import filedialog, messagebox

import customtkinter as ctk
import psutil

from . import boost as boostmod
from . import trim as trimmod
from .accounts import AccountStore, game_name
from .detection import detect_game, detected_games
from .i18n import LANGUAGES, tr
from .processes import list_running_apps
from .servers import REGIONS as SERVER_REGIONS, best_region, rank_regions
from .system_info import snapshot, ping_host

BG = "#07100C"
PANEL = "#0C1712"
PANEL2 = "#122019"
BORDER = "#22382A"
SIDEBAR = "#091310"
LIME = "#B6FF38"
LIME_HOVER = "#9FE32A"
MINT = "#41E0A0"
MINT_HOVER = "#33C88C"
TEAL = "#2ED0BE"
MUTED = "#8CA79A"
WHITE = "#EFF7EF"
ERROR = "#FF7B7B"
WARN = "#FFC24B"
DARK_TEXT = "#0A1207"
PREF = os.path.join(os.path.expanduser("~"), ".vyron_settings.json")
CRASH = os.path.join(os.path.expanduser("~"), ".vyron_crash.log")

if hasattr(sys, "_MEIPASS"):
    ASSETS = os.path.join(sys._MEIPASS, "vyron", "assets")
else:
    ASSETS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")
ICON = os.path.join(ASSETS, "vyron.ico")
LOGO = os.path.join(ASSETS, "vyron.png")
LOGO_SMALL = os.path.join(ASSETS, "vyron-36.png")
LOGO_SPLASH = os.path.join(ASSETS, "vyron-96.png")
WORDMARK = os.path.join(ASSETS, "vyron-wordmark.png")
WORDMARK_XL = os.path.join(ASSETS, "vyron-wordmark-xl.png")

_BRAND_FAMILIES = (
    "Bahnschrift SemiCondensed", "Bahnschrift Condensed", "Bahnschrift SemiBold",
    "Bahnschrift", "Arial Narrow", "Arial",
)

# CustomTkinter polls the monitor DPI ten times per second by default. That is
# wasted work while gaming; 1.5 s is still fast enough for a DPI change.
if hasattr(ctk, "ScalingTracker"):
    ctk.ScalingTracker.update_loop_interval = 1500


class VyronApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("green")
        self.configure(fg_color=BG)
        self.geometry("1180x770")
        self.minsize(960, 660)
        self.title("VYRON")

        self.settings = self._load_settings()
        try:
            # Undo a crash: never leave an app frozen from a previous session.
            trimmod.resume_leftovers()
        except Exception:
            pass
        self.accounts = AccountStore()
        lang = self.settings.get("language", "en")
        self.lang = lang if lang in LANGUAGES else "en"

        self.user = None
        session = self.settings.get("session")
        if session:
            self.user = self.accounts.profile(session)
            if self.user is None:
                self.settings.pop("session", None)
                self._save_settings()

        self.game_path = ""
        self.game_pid = None
        self.current_page = "overview"
        self.metrics = None
        self.perf = None
        self.game_label = None
        self.game_status = None
        self.library_frame = None
        self.library_count = None
        self.ping_label = None
        self.ping_btn = None
        self.host = None
        self.games_page = None
        self._apps_dialog = None
        self._auth_dialog = None
        self.splash = None

        self.activity = None
        self.activity_dot = None
        self.activity_text = None
        self.session_title = None
        self.session_sub = None
        self.session_chip = None
        self.session_action = None
        self.detected_panel = None
        self.detected_name = None
        self.detected_sub = None
        self.detected_tag = None
        self.detected_add = None
        self.detected_boost = None
        self._toast_widget = None
        self._toast_job = None
        self._welcomed = False
        self._tuned_pids = set()
        self._fg_watch = False
        self._auto_plan_previous = None
        self._scan_busy = False
        self._closing = False
        self._last_servers = None
        self.server_rows_frame = None
        self.server_status = None
        self.server_summary = None
        self.server_count = None
        self.server_game = None
        self.server_test_btn = None
        self.server_scan_btn = None
        self.server_ignore_btn = None
        self.cleanup_frame = None
        self.cleanup_status = None

        self._set_icon()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self._build_splash()
        self._animate_splash()
        self.after(60, self._style_titlebar)
        self.after(1150, self._finish_splash)

    # ------------------------------------------------------------------ icon
    def _set_icon(self):
        try:
            if os.name == "nt":
                import ctypes

                ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("Vyron.GamingCompanion")
        except Exception:
            pass
        try:
            if os.path.exists(ICON):
                self.iconbitmap(default=ICON)
        except Exception:
            pass
        try:
            if os.path.exists(LOGO):
                self._logo_image = tk.PhotoImage(file=LOGO)
                self.iconphoto(True, self._logo_image)
        except Exception:
            pass

    # ------------------------------------------------------------------ settings
    def _load_settings(self):
        try:
            with open(PREF, encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    def _save_settings(self):
        try:
            with open(PREF, "w", encoding="utf-8") as f:
                json.dump(self.settings, f, indent=2)
        except Exception:
            pass

    def t(self, key):
        return tr(self.lang, key)

    def _handle(self):
        username = (self.user or {}).get("username", "")
        return "@" + username.lower() if username else "@" + self.t("guest").lower()

    def report_callback_exception(self, exc, val, tb):
        try:
            with open(CRASH, "a", encoding="utf-8") as f:
                f.write(f"\n[{datetime.datetime.now().isoformat()}]\n")
                f.write("".join(traceback.format_exception(exc, val, tb)))
        except Exception:
            pass

    # ------------------------------------------------------------------ brand
    def _brand_font(self, size, weight="bold"):
        try:
            families = set(tkfont.families(self))
        except Exception:
            families = set()
        for family in _BRAND_FAMILIES:
            if family in families:
                return (family, size, weight)
        return ("Arial", size, weight)

    def _photo(self, path):
        try:
            return tk.PhotoImage(file=path)
        except Exception:
            return None

    def _lower_own_priority(self):
        """Never compete with the game: VYRON is a companion, not a workload."""
        if os.name != "nt":
            return
        try:
            psutil.Process().nice(psutil.BELOW_NORMAL_PRIORITY_CLASS)
        except Exception:
            pass

    def _style_titlebar(self):
        """Blend the native Windows title bar with the dark green shell."""
        if os.name != "nt":
            return
        try:
            import ctypes

            hwnd = ctypes.windll.user32.GetParent(self.winfo_id())
            if not hwnd:
                return

            def attribute(index, value):
                data = ctypes.c_int(value)
                ctypes.windll.dwmapi.DwmSetWindowAttribute(
                    hwnd, index, ctypes.byref(data), ctypes.sizeof(data),
                )

            attribute(20, 1)              # immersive dark mode
            attribute(35, 0x00101309)     # caption colour: SIDEBAR
            attribute(36, 0x0038FFB6)     # caption text: LIME
            attribute(34, 0x002A3822)     # window border: BORDER
        except Exception:
            pass

    # ------------------------------------------------------------------ splash
    def _build_splash(self):
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self.splash = ctk.CTkFrame(self, fg_color=BG, corner_radius=0)
        self.splash.grid(row=0, column=0, sticky="nsew")
        center = ctk.CTkFrame(self.splash, fg_color="transparent")
        center.place(relx=0.5, rely=0.5, anchor="center")
        self._splash_logo = self._photo(LOGO_SPLASH)
        if self._splash_logo is not None:
            tk.Label(center, image=self._splash_logo, bg=BG, bd=0).pack(pady=(0, 14))
        self._splash_wordmark = self._photo(WORDMARK_XL)
        if self._splash_wordmark is not None:
            tk.Label(center, image=self._splash_wordmark, bg=BG, bd=0).pack()
        ctk.CTkFrame(center, height=3, width=233, fg_color=LIME, corner_radius=2).pack(pady=(12, 26))
        self.splash_bar = ctk.CTkProgressBar(
            center, width=330, height=6, corner_radius=3, progress_color=LIME, fg_color=PANEL2,
        )
        self.splash_bar.set(0)
        self.splash_bar.pack()
        self.splash_label = ctk.CTkLabel(center, text=self.t("loading"), font=("Arial", 10), text_color=MUTED)
        self.splash_label.pack(pady=(12, 0))
        ctk.CTkLabel(
            self.splash, text=self.t("made_by"), font=("Arial", 9), text_color="#42574A",
        ).place(relx=0.5, rely=0.94, anchor="center")

    def _animate_splash(self, value=0.0):
        if self.splash is None:
            return
        try:
            self.splash_bar.set(min(value, 0.95))
            self.after(70, lambda: self._animate_splash(min(value + 0.09, 0.95)))
        except Exception:
            pass

    def _finish_splash(self):
        if self.splash is None:
            return
        try:
            self.splash_bar.set(1.0)
        except Exception:
            pass
        self.after(140, self._open_main)

    def _open_main(self):
        try:
            if not self.winfo_exists():
                return
        except Exception:
            return
        if self.splash is not None:
            try:
                self.splash.destroy()
            except Exception:
                pass
            self.splash = None
        self._build()
        self._lower_own_priority()
        self._refresh_account_card()
        self._show_page("overview")
        self._tick()
        self.after(400, self._watch_games)
        if not os.path.exists(PREF):
            self.after(100, self._first_run)
        else:
            self.after(100, self._ensure_auth)
        self.after(1400, self._welcome)

    # ------------------------------------------------------------------ layout
    def _build(self):
        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.sidebar = ctk.CTkFrame(self, width=244, fg_color=SIDEBAR, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_propagate(False)

        brand = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        brand.pack(fill="x", padx=20, pady=(24, 14))
        self._brand_logo = self._photo(LOGO_SMALL)
        if self._brand_logo is not None:
            tk.Label(brand, image=self._brand_logo, bg=SIDEBAR, bd=0).pack(side="left", padx=(0, 11))
        brand_text = ctk.CTkFrame(brand, fg_color="transparent")
        brand_text.pack(side="left", fill="x", expand=True)
        self._brand_wordmark = self._photo(WORDMARK)
        if self._brand_wordmark is not None:
            tk.Label(brand_text, image=self._brand_wordmark, bg=SIDEBAR, bd=0).pack(anchor="w")
        ctk.CTkFrame(brand_text, height=2, width=85, fg_color=LIME, corner_radius=1).pack(anchor="w", pady=(5, 0))

        chip = ctk.CTkFrame(self.sidebar, fg_color=PANEL, border_color=BORDER, border_width=1, corner_radius=8)
        chip.pack(fill="x", padx=14, pady=(0, 14))
        self.activity_dot = ctk.CTkLabel(chip, text="●", font=("Arial", 11), text_color=MUTED, width=14)
        self.activity_dot.pack(side="left", padx=(10, 4), pady=7)
        self.activity_text = ctk.CTkLabel(
            chip, text=self.t("activity_none"), font=("Arial", 9, "bold"), text_color=MUTED, anchor="w",
        )
        self.activity_text.pack(side="left", fill="x", expand=True, padx=(0, 8))
        for widget in (chip, self.activity_dot, self.activity_text):
            widget.bind("<Button-1>", lambda _e: self._show_page("games"))

        ctk.CTkLabel(self.sidebar, text="MENU", font=("Arial", 9, "bold"), text_color=MUTED).pack(anchor="w", padx=26, pady=(0, 6))
        self.nav = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        self.nav.pack(fill="x", padx=12)
        self.nav_buttons = {}
        pages = [
            ("overview", "overview"), ("games", "games"), ("boost", "boost"), ("servers", "servers"),
            ("performance", "performance"), ("profile", "profile"), ("settings", "settings"), ("about", "about"),
        ]
        for page, key in pages:
            button = ctk.CTkButton(
                self.nav, text=self.t(key), anchor="w", height=36, corner_radius=8,
                fg_color="transparent", hover_color=PANEL2, text_color=WHITE,
                font=("Arial", 12, "bold"), command=lambda p=page: self._show_page(p),
            )
            button.pack(fill="x", pady=2)
            self.nav_buttons[page] = (button, key)

        # ---------------------------------------------------------- credits
        # PROTECTED CREDIT (see ATTRIBUTION.md + tools/check_attribution.py):
        # "Made by Maxkingwish" must stay visible, unchanged and uncovered on
        # every page. Never remove it, translate it or hide it.
        footer = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        footer.pack(side="bottom", fill="x", padx=18, pady=18)
        ctk.CTkFrame(footer, height=1, fg_color=BORDER).pack(fill="x", pady=(0, 12))
        ctk.CTkLabel(footer, text="Made by Maxkingwish", font=("Arial", 10), text_color=MUTED).pack(anchor="w", padx=6)

        self.account_card = ctk.CTkFrame(self.sidebar, fg_color=PANEL, border_color=BORDER, border_width=1, corner_radius=12)
        self.account_card.pack(side="bottom", fill="x", padx=14, pady=(0, 4))

        top = ctk.CTkFrame(self.account_card, fg_color="transparent")
        top.pack(fill="x", padx=12, pady=(12, 8))
        self.account_avatar = ctk.CTkLabel(
            top, text="?", width=38, height=38, corner_radius=19, fg_color=LIME,
            text_color=DARK_TEXT, font=("Arial", 15, "bold"),
        )
        self.account_avatar.pack(side="left", padx=(0, 10))
        info = ctk.CTkFrame(top, fg_color="transparent")
        info.pack(side="left", fill="x", expand=True)
        self.account_name = ctk.CTkLabel(info, text=self.t("guest"), font=("Arial", 12, "bold"), text_color=WHITE, anchor="w")
        self.account_name.pack(fill="x")
        self.account_user = ctk.CTkLabel(info, text=self.t("guest_mode"), font=("Arial", 9), text_color=MUTED, anchor="w")
        self.account_user.pack(fill="x")

        self.account_action = ctk.CTkButton(
            self.account_card, text=self.t("login"), height=30, corner_radius=8,
            fg_color=LIME, hover_color=LIME_HOVER, text_color=DARK_TEXT,
            font=("Arial", 10, "bold"), command=self._account_action,
        )
        self.account_action.pack(fill="x", padx=12, pady=(0, 12))

        for widget in (self.account_card, top, info, self.account_name, self.account_user, self.account_avatar):
            widget.bind("<Button-1>", lambda _e: self._show_page("profile"))

        self.content = ctk.CTkFrame(self, fg_color=BG, corner_radius=0)
        self.content.grid(row=0, column=1, sticky="nsew")
        self.content.grid_rowconfigure(0, weight=1)
        self.content.grid_columnconfigure(0, weight=1)

    def _refresh_account_card(self):
        if not hasattr(self, "account_name"):
            return
        if self.user:
            name = self.user.get("display") or self.user.get("username", "")
            self.account_avatar.configure(text=(name[:1] or "?").upper())
            self.account_name.configure(text=name)
            self.account_user.configure(text=self._handle())
            self.account_action.configure(text=self.t("logout"), fg_color=PANEL2, hover_color=BORDER, text_color=MUTED)
        else:
            self.account_avatar.configure(text="?")
            self.account_name.configure(text=self.t("guest"))
            self.account_user.configure(text=self.t("guest_mode"))
            self.account_action.configure(text=self.t("login"), fg_color=LIME, hover_color=LIME_HOVER, text_color=DARK_TEXT)

    def _clear(self):
        for widget in self.content.winfo_children():
            widget.destroy()
        self.metrics = None
        self.perf = None
        self.game_label = None
        self.game_status = None
        self.library_frame = None
        self.library_count = None
        self.ping_label = None
        self.ping_btn = None
        self.host = None
        self.games_page = None
        self.session_title = None
        self.session_sub = None
        self.session_chip = None
        self.session_action = None
        self.detected_panel = None
        self.detected_name = None
        self.detected_sub = None
        self.detected_tag = None
        self.detected_add = None
        self.detected_boost = None
        self.server_rows_frame = None
        self.server_status = None
        self.server_summary = None
        self.server_count = None
        self.server_game = None
        self.server_test_btn = None
        self.server_scan_btn = None
        self.server_ignore_btn = None
        self.cleanup_frame = None
        self.cleanup_status = None

    def _heading(self, parent, title, sub=None):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x")
        ctk.CTkFrame(row, width=4, height=24, fg_color=LIME, corner_radius=2).pack(side="left", padx=(0, 10))
        ctk.CTkLabel(row, text=title, font=("Arial", 25, "bold"), text_color=WHITE).pack(side="left")
        if sub:
            ctk.CTkLabel(parent, text=sub, font=("Arial", 12), text_color=MUTED, wraplength=780, justify="left").pack(anchor="w", pady=(8, 18))
        else:
            ctk.CTkFrame(parent, height=16, fg_color="transparent").pack()

    def _ring_card(self, parent, title, color):
        frame = ctk.CTkFrame(parent, fg_color=PANEL, border_color=BORDER, border_width=1, corner_radius=18)
        head = ctk.CTkFrame(frame, fg_color="transparent")
        head.pack(fill="x", padx=18, pady=(14, 0))
        ctk.CTkLabel(head, text=title, font=("Arial", 9, "bold"), text_color=MUTED).pack(side="left")
        canvas = tk.Canvas(frame, width=158, height=158, bg=PANEL, highlightthickness=0, bd=0)
        canvas.pack(pady=(2, 0))
        pad = 22
        box = (pad, pad, 158 - pad, 158 - pad)
        canvas.create_oval(*box, outline=PANEL2, width=13)
        arc = canvas.create_arc(*box, start=90, extent=0, style=tk.ARC, outline=color, width=13)
        value = canvas.create_text(79, 79, text="—", fill=WHITE, font=("Arial", 24, "bold"))
        sub = ctk.CTkLabel(frame, text="", font=("Arial", 9), text_color=MUTED)
        sub.pack(pady=(0, 14))
        return {"frame": frame, "canvas": canvas, "arc": arc, "value": value, "sub": sub, "color": color}

    def _set_ring(self, ring, percent, value_text, sub_text):
        percent = max(0.0, min(100.0, float(percent or 0)))
        try:
            ring["canvas"].itemconfigure(ring["arc"], extent=-3.6 * percent)
            ring["canvas"].itemconfigure(ring["value"], text=value_text)
            ring["sub"].configure(text=sub_text)
            ring["canvas"].itemconfigure(ring["arc"], outline=ring["color"] if percent < 85 else WARN)
        except Exception:
            pass

    def _card(self, parent, title, value="—", subtitle="", bar=False):
        frame = ctk.CTkFrame(parent, fg_color=PANEL, border_color=BORDER, border_width=1, corner_radius=14)
        ctk.CTkLabel(frame, text=title, text_color=MUTED, font=("Arial", 10, "bold")).pack(anchor="w", padx=16, pady=(15, 4))
        value_label = ctk.CTkLabel(frame, text=value, text_color=WHITE, font=("Arial", 27, "bold"))
        value_label.pack(anchor="w", padx=16)
        sub_label = ctk.CTkLabel(frame, text=subtitle, text_color=MUTED, font=("Arial", 10))
        sub_label.pack(anchor="w", padx=16, pady=(2, 0))
        progress = None
        if bar:
            progress = ctk.CTkProgressBar(frame, height=6, corner_radius=3, progress_color=LIME, fg_color=PANEL2)
            progress.set(0)
            progress.pack(fill="x", padx=16, pady=(10, 14))
        else:
            ctk.CTkFrame(frame, height=12, fg_color="transparent").pack()
        return frame, value_label, sub_label, progress

    def _section(self, parent, text):
        ctk.CTkLabel(parent, text=text, font=("Arial", 12, "bold"), text_color=LIME).pack(anchor="w", pady=(8, 4))

    def _field(self, parent, label, show=None, padx=20):
        ctk.CTkLabel(parent, text=label, font=("Arial", 10, "bold"), text_color=MUTED).pack(anchor="w", padx=padx, pady=(8, 4))
        entry = ctk.CTkEntry(parent, height=38, fg_color=PANEL2, border_color=BORDER, text_color=WHITE, show=show)
        entry.pack(fill="x", padx=padx)
        return entry

    def _show_page(self, page):
        self.current_page = page
        self._clear()
        for name, (button, key) in self.nav_buttons.items():
            button.configure(
                fg_color=PANEL2 if name == page else "transparent",
                text_color=LIME if name == page else WHITE,
                text=self.t(key),
            )
        root = ctk.CTkFrame(self.content, fg_color="transparent")
        root.grid(row=0, column=0, sticky="nsew", padx=28, pady=24)
        root.grid_columnconfigure(0, weight=1)
        pages = {
            "overview": self._overview, "games": self._games, "boost": self._boost,
            "servers": self._servers, "performance": self._performance,
            "profile": self._profile, "settings": self._settings, "about": self._about,
        }
        pages[page](root)

    # ------------------------------------------------------------------ pages
    def _overview(self, root):
        self._heading(root, self.t("welcome"), self.t("welcome_sub"))
        cards = ctk.CTkFrame(root, fg_color="transparent")
        cards.pack(fill="x")
        cards.grid_columnconfigure((0, 1, 2), weight=1)
        self.metrics = {}
        rings = (("cpu", LIME), ("ram", MINT), ("disk", TEAL))
        for i, (metric, color) in enumerate(rings):
            ring = self._ring_card(cards, self.t(metric), color)
            ring["frame"].grid(
                row=0, column=i, sticky="ew", padx=(0 if i == 0 else 10, 0 if i == 2 else 10),
            )
            self.metrics[metric] = ring

        session = ctk.CTkFrame(root, fg_color=PANEL, border_color=BORDER, border_width=1, corner_radius=14)
        session.pack(fill="x", pady=(18, 4))
        session_top = ctk.CTkFrame(session, fg_color="transparent")
        session_top.pack(fill="x", padx=20, pady=(16, 0))
        ctk.CTkLabel(
            session_top, text=self.t("session_title"), font=("Arial", 9, "bold"), text_color=MUTED,
        ).pack(side="left")
        self.session_chip = ctk.CTkLabel(
            session_top, text=self.t("boost_ready"), font=("Arial", 9, "bold"),
            text_color=LIME, fg_color=PANEL2, corner_radius=6,
        )
        self.session_chip.pack(side="right", ipadx=8, ipady=2)
        row = ctk.CTkFrame(session, fg_color="transparent")
        row.pack(fill="x", padx=20, pady=(4, 16))
        column = ctk.CTkFrame(row, fg_color="transparent")
        column.pack(side="left", fill="x", expand=True)
        self.session_title = ctk.CTkLabel(
            column, text=self.t("session_idle"), font=("Arial", 21, "bold"), text_color=WHITE, anchor="w",
        )
        self.session_title.pack(fill="x")
        self.session_sub = ctk.CTkLabel(
            column, text=self.t("session_idle_sub"), font=("Arial", 11), text_color=MUTED,
            anchor="w", justify="left", wraplength=560,
        )
        self.session_sub.pack(fill="x", pady=(2, 0))
        self.session_action = ctk.CTkButton(
            row, text=self.t("session_games"), width=150, height=38, fg_color=LIME,
            hover_color=LIME_HOVER, text_color=DARK_TEXT, font=("Arial", 11, "bold"),
            command=lambda: self._show_page("games"),
        )
        self.session_action.pack(side="right", padx=(14, 0))

        ctk.CTkLabel(
            root, text=self.t("safe_body"), font=("Arial", 11), text_color=MUTED,
            wraplength=780, justify="left",
        ).pack(anchor="w", pady=(10, 8))

        self._section(root, self.t("recommendations"))
        for key in ("rec1", "rec2", "rec3"):
            row = ctk.CTkFrame(root, fg_color=PANEL, corner_radius=8)
            row.pack(fill="x", pady=4)
            ctk.CTkLabel(row, text="›", text_color=LIME, font=("Arial", 18, "bold")).pack(side="left", padx=(14, 8))
            ctk.CTkLabel(row, text=self.t(key), text_color=WHITE, font=("Arial", 11), anchor="w", wraplength=720).pack(side="left", padx=(0, 12), pady=10)
        self._update_session()

    def _games(self, root):
        page = ctk.CTkScrollableFrame(
            root, fg_color="transparent", corner_radius=0, scrollbar_fg_color=PANEL,
            scrollbar_button_color=BORDER, scrollbar_button_hover_color=LIME,
        )
        page.pack(fill="both", expand=True)
        self.games_page = page
        self._heading(page, self.t("games"), self.t("priority_note"))

        self._build_detected_panel(page)

        panel = ctk.CTkFrame(page, fg_color=PANEL, border_color=BORDER, border_width=1, corner_radius=14)
        panel.pack(fill="x", pady=(0, 16))
        ctk.CTkLabel(panel, text=self.t("launch_game"), font=("Arial", 15, "bold"), text_color=WHITE).pack(anchor="w", padx=20, pady=(18, 10))

        selected = ctk.CTkFrame(panel, fg_color=PANEL2, corner_radius=10)
        selected.pack(fill="x", padx=20)
        self.game_label = ctk.CTkLabel(
            selected, text=self._selected_text(), text_color=WHITE if self.game_path else MUTED,
            anchor="w", justify="left", font=("Arial", 11), wraplength=640,
        )
        self.game_label.pack(side="left", fill="x", expand=True, padx=14, pady=12)

        actions = ctk.CTkFrame(panel, fg_color="transparent")
        actions.pack(fill="x", padx=20, pady=(12, 0))
        ctk.CTkButton(
            actions, text=self.t("browse"), height=36, fg_color=PANEL2, hover_color=BORDER,
            text_color=WHITE, command=self._browse,
        ).pack(side="left")
        ctk.CTkButton(
            actions, text=self.t("running_apps"), height=36, fg_color=PANEL2, hover_color=BORDER,
            text_color=LIME, command=self._show_running_apps,
        ).pack(side="left", padx=(10, 0))

        self.priority_var = tk.BooleanVar(value=False)
        ctk.CTkCheckBox(
            panel, text=self.t("priority"), variable=self.priority_var, text_color=WHITE,
            fg_color=LIME, hover_color=LIME_HOVER, border_color=BORDER, command=self._set_priority,
        ).pack(anchor="w", padx=20, pady=(14, 0))

        ctk.CTkButton(
            panel, text=self.t("launch"), height=42, fg_color=LIME, hover_color=LIME_HOVER,
            text_color=DARK_TEXT, font=("Arial", 12, "bold"), command=self._launch,
        ).pack(fill="x", padx=20, pady=(12, 18))

        head = ctk.CTkFrame(page, fg_color="transparent")
        head.pack(fill="x", pady=(6, 4))
        ctk.CTkLabel(head, text=self.t("my_games"), font=("Arial", 12, "bold"), text_color=LIME).pack(side="left")
        self.library_count = ctk.CTkLabel(head, text="", font=("Arial", 10, "bold"), text_color=MUTED)
        self.library_count.pack(side="right", padx=(0, 14))

        self.library_frame = ctk.CTkFrame(page, fg_color="transparent")
        self.library_frame.pack(fill="x")
        self._render_library()

        self.game_status = ctk.CTkLabel(page, text="", text_color=LIME, wraplength=760, justify="left", font=("Arial", 10))
        self.game_status.pack(anchor="w", pady=(10, 0))

    def _build_detected_panel(self, parent):
        frame = ctk.CTkFrame(parent, fg_color=PANEL2, border_color=BORDER, border_width=1, corner_radius=12)
        frame.pack(fill="x", pady=(0, 14))
        self.detected_panel = frame
        left = ctk.CTkFrame(frame, fg_color="transparent")
        left.pack(side="left", fill="x", expand=True, padx=16, pady=12)
        self.detected_tag = ctk.CTkLabel(
            left, text=self.t("activity_detected"), font=("Arial", 8, "bold"), text_color=LIME, anchor="w",
        )
        self.detected_tag.pack(fill="x")
        self.detected_name = ctk.CTkLabel(
            left, text="", font=("Arial", 14, "bold"), text_color=WHITE, anchor="w",
        )
        self.detected_name.pack(fill="x")
        self.detected_sub = ctk.CTkLabel(
            left, text=self.t("activity_hint"), font=("Arial", 9), text_color=MUTED,
            anchor="w", justify="left", wraplength=560,
        )
        self.detected_sub.pack(fill="x", pady=(2, 0))
        self.detected_add = ctk.CTkButton(
            frame, text=self.t("activity_add"), width=180, height=32, fg_color=LIME,
            hover_color=LIME_HOVER, text_color=DARK_TEXT, font=("Arial", 9, "bold"),
            command=self._add_detected_game,
        )
        self.detected_boost = ctk.CTkButton(
            frame, text=self.t("session_boost"), width=104, height=32, fg_color=PANEL,
            hover_color=BORDER, text_color=LIME, border_color=BORDER, border_width=1,
            font=("Arial", 9, "bold"), command=self._boost_detected,
        )
        self._refresh_detected()

    def _refresh_detected(self):
        if self.detected_name is None:
            return
        try:
            game = self.activity
            if not game:
                self.detected_tag.configure(text=self.t("activity_detected"), text_color=MUTED)
                self.detected_name.configure(text=self.t("activity_none"))
                self.detected_sub.configure(text=self.t("activity_hint"))
                self.detected_add.pack_forget()
                self.detected_boost.pack_forget()
                return
            self.detected_tag.configure(text=self.t("activity_detected"), text_color=LIME)
            self.detected_name.configure(text=game.get("name", ""))
            self.detected_sub.configure(text=self._short_path(game.get("path", ""), 74))
            in_library = False
            if self.user:
                wanted = os.path.normcase(game.get("path", ""))
                in_library = any(
                    os.path.normcase(item.get("path", "")) == wanted
                    for item in self.user.get("games", [])
                )
            if self.user and not in_library:
                self.detected_add.pack(side="right", padx=(0, 8))
            else:
                self.detected_add.pack_forget()
            if self.user:
                self.detected_boost.pack(side="right", padx=(0, 10))
            else:
                self.detected_boost.pack_forget()
        except Exception:
            pass

    def _update_session(self):
        game = self.activity
        try:
            if self.session_title is None:
                return
            if game:
                self.session_title.configure(text=game.get("name", ""))
                self.session_sub.configure(text=self._short_path(game.get("path", ""), 70))
                self.session_chip.configure(text=self.t("boost_active"), text_color=LIME)
                if self.user:
                    self.session_action.configure(
                        text=self.t("session_boost"), command=self._boost_detected,
                    )
                else:
                    self.session_action.configure(
                        text=self.t("session_games"), command=lambda: self._show_page("games"),
                    )
            else:
                self.session_title.configure(text=self.t("session_idle"))
                self.session_sub.configure(text=self.t("session_idle_sub"))
                self.session_chip.configure(text=self.t("boost_ready"), text_color=MUTED)
                self.session_action.configure(
                    text=self.t("session_games"), command=lambda: self._show_page("games"),
                )
        except Exception:
            pass

    # ------------------------------------------------------------------ detection
    def _watch_games(self):
        if self._closing:
            return
        if not self._scan_busy:
            self._scan_busy = True
            ignored = self._excluded_names()

            def work():
                try:
                    found = detect_game(excluded=ignored)
                except Exception:
                    found = None
                try:
                    self.after(0, lambda: self._apply_activity(found))
                except Exception:
                    pass

            threading.Thread(target=work, daemon=True).start()
        try:
            minimised = self.state() == "iconic"
        except Exception:
            minimised = False
        if self.activity:
            delay = 12000
        elif minimised:
            delay = 10000
        else:
            delay = 6000
        self.after(delay, self._watch_games)

    def _apply_activity(self, found):
        self._scan_busy = False
        try:
            if not self.winfo_exists():
                return
        except Exception:
            return
        previous = (self.activity or {}).get("path")
        current = (found or {}).get("path")
        changed = previous != current
        self.activity = found
        self._refresh_activity_chip()
        if self.current_page == "overview":
            self._update_session()
        if changed and self.current_page == "games":
            self._refresh_detected()
        if changed and found and self.user:
            self._apply_game_profile(found)
            self._auto_boost(found)
            self._auto_trim(found)
        elif changed and not found:
            self._restore_auto_plan()
            self._release_trim()

    def _refresh_activity_chip(self):
        if self.activity_text is None:
            return
        try:
            game = self.activity
            if game:
                name = game.get("name", "")
                if len(name) > 22:
                    name = name[:20] + "…"
                self.activity_dot.configure(text_color=LIME)
                self.activity_text.configure(text=self.t("activity_playing").format(game=name), text_color=WHITE)
            else:
                self.activity_dot.configure(text_color=MUTED)
                self.activity_text.configure(text=self.t("activity_none"), text_color=MUTED)
        except Exception:
            pass

    def _auto_boost(self, game):
        if not self.user:
            return
        prefs = self.settings.get("boost") or {}
        if prefs.get("auto") is False:
            return
        pid = game.get("pid")
        if not pid or pid in self._tuned_pids:
            return
        self._tuned_pids.add(pid)
        want_plan = prefs.get("power", True)

        def work():
            boostmod.tune_process(pid)
            if prefs.get("latency", True):
                boostmod.set_timer_resolution(True)
            if want_plan:
                battery = None
                try:
                    battery = psutil.sensors_battery()
                except Exception:
                    battery = None
                on_battery = bool(battery is not None and not battery.power_plugged)
                if not on_battery and self._auto_plan_previous is None:
                    current = boostmod.current_power_plan()
                    high = boostmod.high_performance_plan()
                    if high and current and current.get("guid") != high:
                        if boostmod.set_power_plan(high):
                            self._auto_plan_previous = current.get("guid")

        threading.Thread(target=work, daemon=True).start()

    def _restore_auto_plan(self):
        guid = self._auto_plan_previous
        if not guid:
            return
        self._auto_plan_previous = None

        def work():
            boostmod.set_power_plan(guid)

        threading.Thread(target=work, daemon=True).start()

    def _release_trim(self):
        """Give throttled background apps their normal priority back."""
        self._fg_watch = False

        def work():
            try:
                trimmod.release_all()
            except Exception:
                pass
            try:
                boostmod.set_timer_resolution(False)
            except Exception:
                pass

        threading.Thread(target=work, daemon=True).start()

    def _auto_trim(self, game):
        """Browsers/launchers give their RAM and CPU back while the game runs."""
        prefs = self.settings.get("boost") or {}
        throttle_apps = prefs.get("trim", True) is not False
        suspend_apps = prefs.get("suspend", True) is not False
        if not throttle_apps and not suspend_apps:
            return
        pid = game.get("pid")

        def work():
            try:
                trimmod.optimize(
                    exclude_pids=(pid, os.getpid()),
                    skip_foreground=True,
                    suspend=suspend_apps,
                )
            except Exception:
                pass

        threading.Thread(target=work, daemon=True).start()
        if suspend_apps:
            self._start_foreground_watch()

    def _start_foreground_watch(self):
        """A suspended app must wake up the moment the user switches to it."""
        if self._fg_watch or self._closing:
            return
        self._fg_watch = True
        self.after(1200, self._watch_foreground)

    def _watch_foreground(self):
        if not self._fg_watch or self._closing:
            return
        try:
            trimmod.suspend_foreground()
        except Exception:
            pass
        try:
            self.after(1200, self._watch_foreground)
        except Exception:
            pass

    def _apply_game_profile(self, game):
        prefs = self.settings.get("boost") or {}
        if prefs.get("profile", True) is False:
            return
        path = (game or {}).get("path")
        if not path:
            return
        saved_all = dict(prefs.get("profile_saved") or {})
        if path in saved_all:
            return
        saved = boostmod.apply_game_profile(path)
        if saved is None:
            return
        saved_all[path] = saved
        prefs = dict(prefs)
        prefs["profile_saved"] = saved_all
        self.settings["boost"] = prefs
        self._save_settings()

    def _add_detected_game(self):
        game = self.activity
        if not game or not self.user:
            return
        self._set_game(game.get("path", ""), game.get("name"))
        self._refresh_detected()
        self._toast(self.t("activity_detected"), self.t("activity_added"))

    def _boost_detected(self):
        game = self.activity
        if not game:
            self._toast(self.t("boost"), self.t("boost_need_game"), WARN)
            return
        if not self.user:
            self._toast(self.t("boost"), self.t("boost_locked_title"), WARN)
            self._show_page("boost")
            return
        pid = game.get("pid")
        if not pid:
            self._toast(self.t("boost"), self.t("boost_need_game"), WARN)
            return

        def work():
            results = boostmod.tune_process(pid)
            self.after(0, lambda: self._boost_feedback(results))

        threading.Thread(target=work, daemon=True).start()

    def _boost_feedback(self, results):
        if results.get("priority") or results.get("affinity") or results.get("io"):
            self._toast(self.t("boost"), self.t("boost_tuned"))
        else:
            self._toast(self.t("boost"), self.t("boost_tuned_failed"), WARN)

    def _selected_text(self):
        if not self.game_path:
            return self.t("no_game")
        return f"{game_name(self.game_path)}  •  {self.game_path}"

    def _render_library(self):
        if self.library_frame is None:
            return
        try:
            if not self.library_frame.winfo_exists():
                return
        except Exception:
            return
        for widget in self.library_frame.winfo_children():
            widget.destroy()

        games = (self.user or {}).get("games", [])
        if self.library_count is not None:
            try:
                self.library_count.configure(text=str(len(games)) if self.user else "")
            except Exception:
                pass

        if not self.user:
            note = ctk.CTkFrame(self.library_frame, fg_color=PANEL, corner_radius=10)
            note.pack(fill="x")
            ctk.CTkLabel(note, text=self.t("guest_library_note"), text_color=MUTED, font=("Arial", 11)).pack(side="left", padx=16, pady=14)
            ctk.CTkButton(
                note, text=self.t("sign_in_now"), width=110, height=30, fg_color=LIME,
                hover_color=LIME_HOVER, text_color=DARK_TEXT, font=("Arial", 10, "bold"),
                command=self._show_auth,
            ).pack(side="right", padx=12, pady=10)
            return

        if not games:
            ctk.CTkLabel(self.library_frame, text=self.t("no_games_yet"), text_color=MUTED, font=("Arial", 11)).pack(anchor="w", pady=10)
            return

        for game in games:
            path = game.get("path", "")
            name = game.get("name") or game_name(path)
            row = ctk.CTkFrame(self.library_frame, fg_color=PANEL, corner_radius=10)
            row.pack(fill="x", pady=4)
            ctk.CTkLabel(
                row, text=(name[:1] or "?").upper(), width=36, height=36, corner_radius=8,
                fg_color=PANEL2, text_color=LIME, font=("Arial", 15, "bold"),
            ).pack(side="left", padx=(10, 10), pady=10)
            info = ctk.CTkFrame(row, fg_color="transparent")
            info.pack(side="left", fill="x", expand=True, pady=8)
            name_label = ctk.CTkLabel(info, text=name, font=("Arial", 12, "bold"), text_color=WHITE, anchor="w")
            name_label.pack(fill="x")
            path_label = ctk.CTkLabel(info, text=self._short_path(path, 72), font=("Arial", 9), text_color=MUTED, anchor="w")
            path_label.pack(fill="x")
            ctk.CTkButton(
                row, text=self.t("launch"), width=76, height=30, fg_color=LIME,
                hover_color=LIME_HOVER, text_color=DARK_TEXT, font=("Arial", 10, "bold"),
                command=lambda p=path: self._launch_path(p),
            ).pack(side="right", padx=(0, 6))
            ctk.CTkButton(
                row, text="×", width=30, height=30, fg_color="transparent", hover_color="#33221F",
                text_color=MUTED, font=("Arial", 16, "bold"),
                command=lambda p=path: self._remove_game(p),
            ).pack(side="right")
            for widget in (row, info, name_label, path_label):
                widget.bind("<Button-1>", lambda _e, p=path, n=name: self._set_game(p, n))

    def _performance(self, root):
        self._heading(root, self.t("performance"), self.t("refresh"))
        cards = ctk.CTkFrame(root, fg_color="transparent")
        cards.pack(fill="x")
        cards.grid_columnconfigure((0, 1), weight=1)
        self.perf = {}
        for i, (metric, key) in enumerate([("gpu", "gpu"), ("gpu_temp", "temperature")]):
            frame, value, sub, bar = self._card(cards, self.t(key), "—", "", bar=True)
            frame.grid(row=0, column=i, sticky="ew", padx=(0 if i == 0 else 8, 0 if i == 1 else 8), pady=(0, 10))
            self.perf[metric] = (value, sub, bar)

        self._section(root, self.t("network"))
        net = ctk.CTkFrame(root, fg_color=PANEL, border_color=BORDER, border_width=1, corner_radius=14)
        net.pack(fill="x", pady=(4, 12))
        self.host = ctk.CTkEntry(net, placeholder_text=self.t("host"), height=38, fg_color=PANEL2, border_color=BORDER)
        self.host.insert(0, "1.1.1.1")
        self.host.pack(fill="x", padx=16, pady=(16, 10))
        self.ping_btn = ctk.CTkButton(
            net, text=self.t("test_ping"), fg_color=LIME, hover_color=LIME_HOVER,
            text_color=DARK_TEXT, font=("Arial", 11, "bold"), command=self._ping,
        )
        self.ping_btn.pack(anchor="w", padx=16, pady=(0, 8))
        self.ping_label = ctk.CTkLabel(net, text=self.t("ping_note"), text_color=MUTED, wraplength=720, justify="left")
        self.ping_label.pack(anchor="w", padx=16, pady=(0, 16))

        self._section(root, self.t("fps_title"))
        ctk.CTkLabel(root, text=self.t("fps_note"), text_color=MUTED, wraplength=780, justify="left").pack(anchor="w", pady=(0, 10))
        self._section(root, self.t("safe_title"))
        ctk.CTkLabel(root, text=self.t("safe_body"), text_color=MUTED, wraplength=780, justify="left").pack(anchor="w")

    def _boost(self, root):
        page = ctk.CTkScrollableFrame(
            root, fg_color="transparent", corner_radius=0, scrollbar_fg_color=PANEL,
            scrollbar_button_color=BORDER, scrollbar_button_hover_color=LIME,
        )
        page.pack(fill="both", expand=True)
        self._heading(page, self.t("boost"), self.t("boost_sub"))

        if not self.user:
            self._boost_locked(page)
            return

        state = boostmod.read_state()
        optimised = boostmod.state_is_optimised(state)

        hero = ctk.CTkFrame(page, fg_color=PANEL, border_color=BORDER, border_width=1, corner_radius=14)
        hero.pack(fill="x", pady=(0, 14))
        top = ctk.CTkFrame(hero, fg_color="transparent")
        top.pack(fill="x", padx=20, pady=(18, 4))
        ctk.CTkLabel(top, text=self.t("boost_engine"), font=("Arial", 15, "bold"), text_color=WHITE).pack(side="left")
        ctk.CTkLabel(
            top, text=self._handle(), font=("Arial", 9, "bold"),
            text_color=MUTED,
        ).pack(side="left", padx=(8, 0))
        status_chip = ctk.CTkLabel(
            top, text=self.t("boost_active") if optimised else self.t("boost_ready"),
            font=("Arial", 9, "bold"), text_color=DARK_TEXT if optimised else LIME,
            fg_color=LIME if optimised else PANEL2, corner_radius=6,
        )
        status_chip.pack(side="right", ipadx=10, ipady=3)
        ctk.CTkLabel(
            hero, text=self.t("boost_auto_hint"), font=("Arial", 11), text_color=MUTED,
            wraplength=720, justify="left",
        ).pack(anchor="w", padx=20, pady=(0, 12))
        hero_actions = ctk.CTkFrame(hero, fg_color="transparent")
        hero_actions.pack(fill="x", padx=20, pady=(0, 18))
        ctk.CTkButton(
            hero_actions, text=self.t("boost_now"), height=40, fg_color=LIME, hover_color=LIME_HOVER,
            text_color=DARK_TEXT, font=("Arial", 11, "bold"), command=self._boost_now,
        ).pack(side="left")
        ctk.CTkButton(
            hero_actions, text=self.t("boost_restore"), height=40, fg_color=PANEL2, hover_color=BORDER,
            text_color=WHITE, border_color=BORDER, border_width=1, font=("Arial", 10, "bold"),
            command=self._boost_restore,
        ).pack(side="left", padx=(10, 0))

        self._section(page, self.t("boost_system_section"))
        panel = ctk.CTkFrame(page, fg_color=PANEL, border_color=BORDER, border_width=1, corner_radius=14)
        panel.pack(fill="x", pady=(2, 14))
        self._state_row(panel, self.t("boost_game_mode"), state.get("game_mode"), True)
        dvr_value = state.get("game_dvr")
        if dvr_value is None:
            dvr_value = state.get("app_capture")
        self._state_row(panel, self.t("boost_dvr"), dvr_value, False)
        plan = state.get("power_plan") or {}
        self._state_row(
            panel, self.t("boost_power_plan"), boostmod.plan_is_high(state), True,
            detail=(plan.get("name") or "").strip(),
        )
        ctk.CTkFrame(panel, height=1, fg_color=BORDER).pack(fill="x", padx=20)
        ctk.CTkLabel(
            panel, text=self.t("boost_priority"), font=("Arial", 10), text_color=MUTED,
        ).pack(anchor="w", padx=20, pady=(10, 14))

        self._section(page, self.t("boost_auto"))
        auto_panel = ctk.CTkFrame(page, fg_color=PANEL, border_color=BORDER, border_width=1, corner_radius=14)
        auto_panel.pack(fill="x", pady=(2, 14))
        prefs = self.settings.get("boost") or {}
        self.boost_auto_var = tk.BooleanVar(value=prefs.get("auto", True))
        self.boost_power_var = tk.BooleanVar(value=prefs.get("power", True))
        ctk.CTkCheckBox(
            auto_panel, text=self.t("boost_auto"), variable=self.boost_auto_var,
            text_color=WHITE, fg_color=LIME, hover_color=LIME_HOVER, border_color=BORDER,
            font=("Arial", 12, "bold"), command=self._save_boost_prefs,
        ).pack(anchor="w", padx=20, pady=(16, 2))
        ctk.CTkLabel(
            auto_panel, text=self.t("boost_auto_hint"), font=("Arial", 10), text_color=MUTED,
            wraplength=700, justify="left",
        ).pack(anchor="w", padx=20)
        ctk.CTkCheckBox(
            auto_panel, text=self.t("boost_power"), variable=self.boost_power_var,
            text_color=WHITE, fg_color=LIME, hover_color=LIME_HOVER, border_color=BORDER,
            font=("Arial", 11, "bold"), command=self._save_boost_prefs,
        ).pack(anchor="w", padx=20, pady=(14, 2))
        ctk.CTkLabel(
            auto_panel, text=self.t("boost_power_hint") + "  " + self.t("boost_auto_plan_note"),
            font=("Arial", 10), text_color=MUTED, wraplength=700, justify="left",
        ).pack(anchor="w", padx=20, pady=(0, 16))

        self._section(page, self.t("fps_section"))
        fps_panel = ctk.CTkFrame(page, fg_color=PANEL, border_color=BORDER, border_width=1, corner_radius=14)
        fps_panel.pack(fill="x", pady=(2, 14))
        self.fps_profile_var = tk.BooleanVar(value=prefs.get("profile", True))
        self.fps_suspend_var = tk.BooleanVar(value=prefs.get("suspend", True))
        self.fps_latency_var = tk.BooleanVar(value=prefs.get("latency", True))
        for index, (variable, label, hint) in enumerate((
            (self.fps_profile_var, "fps_profile", "fps_profile_hint"),
            (self.fps_suspend_var, "fps_suspend", "fps_suspend_hint"),
            (self.fps_latency_var, "fps_latency", "fps_latency_hint"),
        )):
            ctk.CTkCheckBox(
                fps_panel, text=self.t(label), variable=variable,
                text_color=WHITE, fg_color=LIME, hover_color=LIME_HOVER, border_color=BORDER,
                font=("Arial", 12, "bold"), command=self._save_boost_prefs,
            ).pack(anchor="w", padx=20, pady=(16 if index == 0 else 14, 2))
            ctk.CTkLabel(
                fps_panel, text=self.t(hint), font=("Arial", 10), text_color=MUTED,
                wraplength=700, justify="left", anchor="w",
            ).pack(anchor="w", padx=20)
        ctk.CTkLabel(
            fps_panel, text=self.t("fps_note"), font=("Arial", 9), text_color=MUTED,
            wraplength=700, justify="left", anchor="w",
        ).pack(anchor="w", padx=20, pady=(10, 16))

        self._section(page, self.t("boost_trim"))
        trim_panel = ctk.CTkFrame(page, fg_color=PANEL, border_color=BORDER, border_width=1, corner_radius=14)
        trim_panel.pack(fill="x", pady=(2, 14))
        self.trim_auto_var = tk.BooleanVar(value=prefs.get("trim", True))
        ctk.CTkCheckBox(
            trim_panel, text=self.t("boost_trim_auto"), variable=self.trim_auto_var,
            text_color=WHITE, fg_color=LIME, hover_color=LIME_HOVER, border_color=BORDER,
            font=("Arial", 12, "bold"), command=self._save_boost_prefs,
        ).pack(anchor="w", padx=20, pady=(16, 2))
        ctk.CTkLabel(
            trim_panel, text=self.t("boost_trim_hint"), font=("Arial", 10), text_color=MUTED,
            wraplength=700, justify="left",
        ).pack(anchor="w", padx=20)
        trim_actions = ctk.CTkFrame(trim_panel, fg_color="transparent")
        trim_actions.pack(fill="x", padx=20, pady=(12, 4))
        ctk.CTkButton(
            trim_actions, text=self.t("boost_trim_now"), height=34, fg_color=LIME,
            hover_color=LIME_HOVER, text_color=DARK_TEXT, font=("Arial", 10, "bold"),
            command=self._trim_now,
        ).pack(side="left")
        ctk.CTkButton(
            trim_actions, text=self.t("boost_trim_restore"), height=34, fg_color=PANEL2,
            hover_color=BORDER, text_color=WHITE, border_color=BORDER, border_width=1,
            font=("Arial", 10, "bold"), command=self._trim_restore,
        ).pack(side="left", padx=(10, 0))
        throttled = trimmod.throttled_count()
        self.trim_status = ctk.CTkLabel(
            trim_panel, text=self.t("boost_trim_idle").format(count=throttled) if throttled else "",
            font=("Arial", 9), text_color=MINT if throttled else MUTED,
        )
        self.trim_status.pack(anchor="w", padx=20, pady=(2, 14))

        self._section(page, self.t("boost_cleanup"))
        cleanup = ctk.CTkFrame(page, fg_color=PANEL, border_color=BORDER, border_width=1, corner_radius=14)
        cleanup.pack(fill="x", pady=(2, 14))
        head = ctk.CTkFrame(cleanup, fg_color="transparent")
        head.pack(fill="x", padx=20, pady=(16, 0))
        ctk.CTkLabel(
            head, text=self.t("boost_cleanup_hint"), font=("Arial", 10), text_color=MUTED,
            wraplength=580, justify="left", anchor="w",
        ).pack(side="left", fill="x", expand=True)
        ctk.CTkButton(
            head, text=self.t("boost_refresh"), width=100, height=30, fg_color=PANEL2,
            hover_color=BORDER, text_color=WHITE, font=("Arial", 9, "bold"),
            command=self._load_background_apps,
        ).pack(side="right", padx=(10, 0))
        self.cleanup_status = ctk.CTkLabel(cleanup, text="", font=("Arial", 9), text_color=MUTED)
        self.cleanup_status.pack(anchor="w", padx=20, pady=(6, 0))
        self.cleanup_frame = ctk.CTkFrame(cleanup, fg_color="transparent")
        self.cleanup_frame.pack(fill="x", padx=12, pady=(2, 14))
        ctk.CTkLabel(
            page, text=self.t("boost_note"), font=("Arial", 10), text_color=MUTED,
            wraplength=780, justify="left",
        ).pack(anchor="w", pady=(2, 10))
        self.after(60, self._load_background_apps)

    def _state_row(self, parent, label, active, good, detail=""):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", padx=20, pady=7)
        column = ctk.CTkFrame(row, fg_color="transparent")
        column.pack(side="left", fill="x", expand=True)
        ctk.CTkLabel(column, text=label, font=("Arial", 11, "bold"), text_color=WHITE, anchor="w").pack(fill="x")
        if detail:
            ctk.CTkLabel(column, text=detail, font=("Arial", 9), text_color=MUTED, anchor="w").pack(fill="x")
        if active is True:
            text, color = self.t("boost_enabled"), (LIME if good else WARN)
        elif active is False:
            text, color = self.t("boost_disabled"), (WARN if good else MUTED)
        else:
            text, color = self.t("boost_unknown"), MUTED
        ctk.CTkLabel(
            row, text=text, font=("Arial", 9, "bold"), text_color=color, fg_color=PANEL2,
            corner_radius=6,
        ).pack(side="right", ipadx=9, ipady=3)

    def _boost_locked(self, page):
        panel = ctk.CTkFrame(page, fg_color=PANEL, border_color=BORDER, border_width=1, corner_radius=14)
        panel.pack(fill="x", pady=(0, 16))
        inner = ctk.CTkFrame(panel, fg_color="transparent")
        inner.pack(fill="x", padx=24, pady=24)
        ctk.CTkLabel(
            inner, text="🔒", font=("Arial", 30), text_color=LIME,
        ).pack(anchor="w")
        ctk.CTkLabel(
            inner, text=self.t("boost_locked_title"), font=("Arial", 18, "bold"), text_color=WHITE,
        ).pack(anchor="w", pady=(6, 4))
        ctk.CTkLabel(
            inner, text=self.t("boost_locked_body"), font=("Arial", 11), text_color=MUTED,
            wraplength=680, justify="left",
        ).pack(anchor="w")
        actions = ctk.CTkFrame(inner, fg_color="transparent")
        actions.pack(anchor="w", pady=(14, 0))
        ctk.CTkButton(
            actions, text=self.t("boost_locked_cta"), fg_color=LIME, hover_color=LIME_HOVER,
            text_color=DARK_TEXT, font=("Arial", 10, "bold"),
            command=lambda: self._show_auth("register"),
        ).pack(side="left")
        ctk.CTkButton(
            actions, text=self.t("login"), fg_color=PANEL2, hover_color=BORDER,
            text_color=WHITE, command=self._show_auth,
        ).pack(side="left", padx=(10, 0))
        ctk.CTkLabel(
            page, text=self.t("boost_note"), font=("Arial", 10), text_color=MUTED,
            wraplength=780, justify="left",
        ).pack(anchor="w")

    def _save_boost_prefs(self):
        previous = dict(self.settings.get("boost") or {})
        prefs = dict(previous)
        prefs["auto"] = bool(getattr(self, "boost_auto_var", None) and self.boost_auto_var.get())
        prefs["power"] = bool(getattr(self, "boost_power_var", None) and self.boost_power_var.get())
        prefs["trim"] = bool(getattr(self, "trim_auto_var", None) and self.trim_auto_var.get())
        prefs["profile"] = bool(getattr(self, "fps_profile_var", None) and self.fps_profile_var.get())
        prefs["suspend"] = bool(getattr(self, "fps_suspend_var", None) and self.fps_suspend_var.get())
        prefs["latency"] = bool(getattr(self, "fps_latency_var", None) and self.fps_latency_var.get())
        if previous.get("profile", True) and not prefs["profile"]:
            for path, saved in (prefs.pop("profile_saved", {}) or {}).items():
                boostmod.restore_game_profile(path, saved)
        self.settings["boost"] = prefs
        self._save_settings()

    def _boost_now(self):
        if not self.user:
            self._toast(self.t("boost"), self.t("boost_locked_title"), WARN)
            self._show_page("boost")
            return
        include_power = bool(getattr(self, "boost_power_var", None) and self.boost_power_var.get())
        previous, results = boostmod.apply_system(include_power=include_power)
        prefs = dict(self.settings.get("boost") or {})
        prefs["previous"] = previous
        self.settings["boost"] = prefs
        self._save_settings()
        if include_power:
            self._auto_plan_previous = None
        game = self.activity
        if game and game.get("pid"):
            results_tune = boostmod.tune_process(game["pid"])
            if not any(results_tune.values()):
                self._toast(self.t("boost"), self.t("boost_tuned_failed"), WARN)
        if prefs.get("profile", True) and game:
            self._apply_game_profile(game)
        if prefs.get("latency", True):
            boostmod.set_timer_resolution(True)
        ok = sum(1 for item in results if item.get("ok"))
        if ok:
            self._toast(self.t("boost"), self.t("boost_applied").format(count=ok), LIME)
        if ok < len(results):
            self._toast(self.t("boost"), self.t("boost_partial"), WARN)
        self._show_page("boost")
        if getattr(self, "trim_auto_var", None) and self.trim_auto_var.get():
            self._trim_now()

    def _boost_restore(self):
        prefs = dict(self.settings.get("boost") or {})
        previous = prefs.pop("previous", None)
        for path, saved in (prefs.pop("profile_saved", {}) or {}).items():
            boostmod.restore_game_profile(path, saved)
        self.settings["boost"] = prefs
        self._save_settings()
        boostmod.restore_system(previous)
        boostmod.set_timer_resolution(False)
        self._fg_watch = False
        try:
            trimmod.release_all()
        except Exception:
            pass
        if self._auto_plan_previous:
            boostmod.set_power_plan(self._auto_plan_previous)
            self._auto_plan_previous = None
        self._toast(self.t("boost"), self.t("boost_restored"))
        self._show_page("boost")

    def _load_background_apps(self):
        if self.cleanup_frame is None and self.current_page != "boost":
            return
        try:
            if self.cleanup_status is not None:
                self.cleanup_status.configure(text=self.t("loading_apps"))
        except Exception:
            pass
        excluded = [getattr(self, "game_pid", None), (self.activity or {}).get("pid")]

        def work():
            try:
                rows = trimmod.list_apps(exclude_pids=tuple(excluded))
            except Exception:
                rows = []
            try:
                self.after(0, lambda: self._render_background_apps(rows))
            except Exception:
                pass

        threading.Thread(target=work, daemon=True).start()

    def _render_background_apps(self, rows):
        if self.cleanup_frame is None:
            return
        try:
            if not self.cleanup_frame.winfo_exists():
                return
            for widget in self.cleanup_frame.winfo_children():
                widget.destroy()
            if self.cleanup_status is not None:
                self.cleanup_status.configure(text="")
            if not rows:
                ctk.CTkLabel(
                    self.cleanup_frame, text=self.t("boost_no_apps"), font=("Arial", 10), text_color=MUTED,
                ).pack(anchor="w", padx=8, pady=10)
                return
            for row in rows:
                line = ctk.CTkFrame(self.cleanup_frame, fg_color=PANEL2, corner_radius=8)
                line.pack(fill="x", pady=3)
                name = row["name"]
                if row.get("count", 1) > 1:
                    name = f"{name}  ·  {self.t('boost_proc_count').format(count=row['count'])}"
                ctk.CTkLabel(
                    line, text=name, font=("Arial", 11, "bold"), text_color=WHITE, anchor="w",
                ).pack(side="left", padx=(12, 8), pady=9)
                ctk.CTkLabel(
                    line, text=self.t("boost_ram").format(value=row["ram"]), font=("Arial", 9),
                    text_color=MUTED,
                ).pack(side="left")
                if row.get("cpu", 0) >= 2:
                    ctk.CTkLabel(
                        line, text=f"{min(row['cpu'], 100)}% CPU", font=("Arial", 9),
                        text_color=MINT,
                    ).pack(side="left", padx=(8, 0))
                ctk.CTkButton(
                    line, text=self.t("boost_close_app"), width=76, height=26, fg_color="transparent",
                    hover_color="#33221F", text_color=ERROR, border_color="#58322E", border_width=1,
                    font=("Arial", 9, "bold"), command=lambda item=row: self._close_background_app(item),
                ).pack(side="right", padx=8, pady=6)
                if row.get("throttled"):
                    ctk.CTkLabel(
                        line, text=self.t("boost_trim_throttled"), font=("Arial", 8, "bold"),
                        text_color=MINT, fg_color="#16301F", corner_radius=5,
                    ).pack(side="right", padx=(0, 6), ipadx=6, ipady=2)
                else:
                    ctk.CTkButton(
                        line, text=self.t("boost_trim_row"), width=88, height=26, fg_color="transparent",
                        hover_color="#16301F", text_color=LIME, border_color=BORDER, border_width=1,
                        font=("Arial", 9, "bold"), command=lambda item=row: self._optimise_app(item),
                    ).pack(side="right", padx=(0, 6), pady=6)
        except Exception:
            pass

    def _close_background_app(self, row):
        if not messagebox.askyesno(
            "VYRON", self.t("boost_close_confirm").format(app=row["name"]), parent=self,
        ):
            return
        pids = row.get("pids") or ([row["pid"]] if row.get("pid") else [])
        if trimmod.close_apps(pids):
            self._toast(self.t("boost"), self.t("boost_closed").format(app=row["name"]))
        else:
            self._toast(self.t("boost"), self.t("boost_close_failed").format(app=row["name"]), WARN)
        self.after(350, self._load_background_apps)

    def _optimise_app(self, row):
        excluded = [getattr(self, "game_pid", None), (self.activity or {}).get("pid")]

        def work():
            try:
                result = trimmod.optimize(apps=[row], exclude_pids=tuple(excluded))
            except Exception:
                result = None
            try:
                self.after(0, lambda: self._trim_feedback(result))
                self.after(150, self._load_background_apps)
            except Exception:
                pass

        threading.Thread(target=work, daemon=True).start()

    def _trim_now(self):
        if not self.user:
            self._toast(self.t("boost"), self.t("boost_locked_title"), WARN)
            return
        self._set_trim_status(self.t("boost_trim_running"), MUTED)
        excluded = [getattr(self, "game_pid", None), (self.activity or {}).get("pid")]

        def work():
            try:
                # Never touch whatever is in the foreground: that is the game
                # (or the app the user is actively using).
                result = trimmod.optimize(
                    exclude_pids=tuple(excluded), skip_foreground=True,
                )
            except Exception:
                result = None
            try:
                self.after(0, lambda: self._trim_feedback(result))
                self.after(150, self._load_background_apps)
            except Exception:
                pass

        threading.Thread(target=work, daemon=True).start()

    def _set_trim_status(self, text, color=MUTED):
        label = getattr(self, "trim_status", None)
        if label is None:
            return
        try:
            label.configure(text=text, text_color=color)
        except Exception:
            pass

    def _trim_feedback(self, result):
        if not result or not result.get("processes"):
            if result and result.get("already"):
                count = trimmod.throttled_count() or result["already"]
                self._set_trim_status(
                    self.t("boost_trim_idle").format(count=count), MINT,
                )
            else:
                self._set_trim_status(self.t("boost_trim_none"), MUTED)
            return
        self._set_trim_status(
            self.t("boost_trim_result").format(
                apps=result["apps"], processes=result["processes"], freed=result["freed"],
            ),
            MINT,
        )
        self._toast(
            self.t("boost"),
            self.t("boost_trim_done").format(count=result["processes"], freed=result["freed"]),
            LIME,
        )

    def _trim_restore(self):
        count = trimmod.release_all()
        text = self.t("boost_trim_restored").format(count=count)
        self._set_trim_status(text, LIME if count else MUTED)
        self._toast(self.t("boost"), text)
        self.after(120, self._load_background_apps)

    # ------------------------------------------------------------------ servers
    def _excluded_names(self):
        return [
            str(name).strip().lower()
            for name in (self.settings.get("detected_excluded") or [])
            if str(name).strip()
        ]

    def _servers(self, root):
        page = ctk.CTkScrollableFrame(
            root, fg_color="transparent", corner_radius=0, scrollbar_fg_color=PANEL,
            scrollbar_button_color=BORDER, scrollbar_button_hover_color=LIME,
        )
        page.pack(fill="both", expand=True)
        self._heading(page, self.t("servers"), self.t("servers_sub"))

        control = ctk.CTkFrame(page, fg_color=PANEL, border_color=BORDER, border_width=1, corner_radius=14)
        control.pack(fill="x", pady=(0, 12))
        row = ctk.CTkFrame(control, fg_color="transparent")
        row.pack(fill="x", padx=20, pady=(16, 4))
        ctk.CTkLabel(
            row, text=self.t("servers_detected"), font=("Arial", 9, "bold"), text_color=MUTED,
        ).pack(side="left", padx=(0, 10))
        self.server_game = ctk.CTkOptionMenu(
            row, values=[self.t("servers_unknown")], width=260, fg_color=PANEL2,
            button_color="#1B3024", button_hover_color="#284434", text_color=WHITE,
            dropdown_fg_color=PANEL, dropdown_text_color=WHITE, command=self._server_game_changed,
        )
        self.server_game.set(self.t("servers_unknown"))
        self.server_game.pack(side="left")
        self.server_count = ctk.CTkLabel(row, text="", font=("Arial", 9), text_color=MUTED)
        self.server_count.pack(side="right")

        actions = ctk.CTkFrame(control, fg_color="transparent")
        actions.pack(fill="x", padx=20, pady=(12, 0))
        self.server_test_btn = ctk.CTkButton(
            actions, text=self.t("servers_test"), height=34, width=170, fg_color=LIME,
            hover_color=LIME_HOVER, text_color=DARK_TEXT, font=("Arial", 10, "bold"),
            command=self._servers_test, state="disabled",
        )
        self.server_test_btn.pack(side="left")
        self.server_scan_btn = ctk.CTkButton(
            actions, text=self.t("servers_scan"), height=34, width=132, fg_color=PANEL2,
            hover_color=BORDER, text_color=WHITE, font=("Arial", 9, "bold"),
            command=lambda: self._scan_catalog(force=True),
        )
        self.server_scan_btn.pack(side="left", padx=(8, 0))
        self.server_ignore_btn = ctk.CTkButton(
            actions, text=self.t("servers_ignore"), height=34, width=122, fg_color="transparent",
            hover_color=PANEL2, text_color=MUTED, border_color=BORDER, border_width=1,
            font=("Arial", 9, "bold"), command=self._ignore_selected,
        )
        self.server_ignore_btn.pack(side="right")

        self.server_summary = ctk.CTkLabel(
            control, text=self.t("servers_no_result"), font=("Arial", 13, "bold"),
            text_color=WHITE, anchor="w",
        )
        self.server_summary.pack(fill="x", padx=20, pady=(6, 2))
        choice = self.settings.get("server_choice") or {}
        saved_region = SERVER_REGIONS.get(choice.get("region"), (None, None))[1]
        if choice.get("region") and saved_region:
            self.server_summary.configure(
                text=self.t("servers_choice").format(region=self.t(saved_region)),
                text_color=MUTED, font=("Arial", 10),
            )
        self.server_status = ctk.CTkLabel(control, text="", font=("Arial", 9), text_color=MUTED, anchor="w")
        self.server_status.pack(fill="x", padx=20, pady=(0, 14))

        self.server_rows_frame = ctk.CTkFrame(page, fg_color="transparent")
        self.server_rows_frame.pack(fill="x")
        ctk.CTkLabel(
            page, text=self.t("servers_note"), font=("Arial", 10), text_color=MUTED,
            wraplength=780, justify="left",
        ).pack(anchor="w", pady=(14, 8))

        cached = self._last_servers
        if cached and cached.get("rows"):
            self._render_servers(cached.get("rows") or [], cached.get("game"))
        else:
            self._clear_server_rows()
            ctk.CTkLabel(
                self.server_rows_frame, text=self.t("servers_no_result"), font=("Arial", 11),
                text_color=MUTED,
            ).pack(anchor="w", pady=8)
        self.after(60, self._scan_catalog)

    def _scan_catalog(self, force=False):
        if self.server_scan_btn is None:
            return
        try:
            self.server_scan_btn.configure(state="disabled", text=self.t("checking"))
            if self.server_status is not None:
                self.server_status.configure(text=self.t("servers_scanning"), text_color=MUTED)
            if self.server_count is not None:
                self.server_count.configure(text="")
        except Exception:
            pass
        extra = []
        if self.activity:
            extra.append({**self.activity, "running": True})
        if self.user:
            extra.extend(self.user.get("games") or [])
        excluded = self._excluded_names()

        def work():
            try:
                rows = detected_games(extra=extra, excluded=excluded, use_cache=not force)
            except Exception:
                rows = []
            try:
                self.after(0, lambda: self._catalog_done(rows))
            except Exception:
                pass

        threading.Thread(target=work, daemon=True).start()

    def _catalog_done(self, rows):
        if self.server_game is None or self.server_scan_btn is None:
            return
        try:
            if not self.server_game.winfo_exists():
                return
        except Exception:
            return
        self._catalog = rows
        self._server_choices = {row["name"]: row for row in rows}
        try:
            self.server_scan_btn.configure(state="normal", text=self.t("servers_scan"))
        except Exception:
            pass
        labels = list(self._server_choices.keys())
        if not labels:
            try:
                self.server_game.configure(values=[self.t("servers_unknown")], state="disabled")
                self.server_game.set(self.t("servers_unknown"))
                self.server_test_btn.configure(state="disabled")
            except Exception:
                pass
            if self.server_summary is not None:
                try:
                    self.server_summary.configure(text=self.t("servers_none"), text_color=MUTED, font=("Arial", 11))
                except Exception:
                    pass
            if self.server_status is not None:
                self.server_status.configure(text="")
            if self.server_count is not None:
                self.server_count.configure(text="")
            return
        saved = (self.settings.get("server_choice") or {}).get("game")
        current = self.activity.get("name") if self.activity else None
        pick = saved if saved in self._server_choices else (current if current in self._server_choices else labels[0])
        try:
            self.server_game.configure(values=labels, state="normal")
            self.server_game.set(pick)
            self.server_test_btn.configure(state="normal")
        except Exception:
            pass
        if self.server_status is not None:
            self.server_status.configure(text="")
        if self.server_count is not None:
            self.server_count.configure(text=self.t("servers_count").format(count=len(labels)))
        cached = self._last_servers
        if cached and cached.get("rows") and cached.get("game") == pick:
            self._render_servers(cached.get("rows") or [], pick)
        else:
            self._clear_server_rows()
            ctk.CTkLabel(
                self.server_rows_frame, text=self.t("servers_no_result"), font=("Arial", 11),
                text_color=MUTED,
            ).pack(anchor="w", pady=8)
            if self.server_summary is not None:
                self.server_summary.configure(
                    text=self.t("servers_no_result"), text_color=WHITE, font=("Arial", 11),
                )

    def _server_game_changed(self, value):
        if not value:
            return
        cached = self._last_servers or {}
        if cached.get("game") == value and cached.get("rows"):
            self._render_servers(cached.get("rows") or [], value)
            return
        self._clear_server_rows()
        if self.server_rows_frame is not None:
            ctk.CTkLabel(
                self.server_rows_frame, text=self.t("servers_no_result"), font=("Arial", 11),
                text_color=MUTED,
            ).pack(anchor="w", pady=8)
        if self.server_summary is not None:
            self.server_summary.configure(
                text=self.t("servers_no_result"), text_color=MUTED, font=("Arial", 11),
            )

    def _ignore_selected(self):
        if self.server_game is None:
            return
        name = (self.server_game.get() or "").strip()
        if not name or name == self.t("servers_unknown"):
            return
        excluded = self._excluded_names()
        if name.lower() not in excluded:
            excluded.append(name.lower())
            self.settings["detected_excluded"] = excluded
            self._save_settings()
        if self.activity and (self.activity.get("name") or "").lower() == name.lower():
            self.activity = None
            self._refresh_activity_chip()
        self._toast(self.t("servers"), self.t("servers_ignored").format(app=name), WARN)
        self._last_servers = None
        self._scan_catalog()

    def _restore_ignored(self, name):
        excluded = [item for item in self._excluded_names() if item != name.lower()]
        if excluded:
            self.settings["detected_excluded"] = excluded
        else:
            self.settings.pop("detected_excluded", None)
        self._save_settings()
        self._toast(self.t("servers"), self.t("servers_restored").format(app=name))
        self._show_page("settings")

    def _clear_server_rows(self):
        if self.server_rows_frame is None:
            return
        try:
            for widget in self.server_rows_frame.winfo_children():
                widget.destroy()
        except Exception:
            pass

    def _servers_test(self):
        if self.server_game is None or self.server_test_btn is None:
            return
        game = (self.server_game.get() or "").strip()
        if not game or game == self.t("servers_unknown"):
            return
        count = len(SERVER_REGIONS)
        self.server_test_btn.configure(state="disabled", text=self.t("checking"))
        if self.server_status is not None:
            self.server_status.configure(text=self.t("servers_testing").format(count=count), text_color=MUTED)

        def work():
            try:
                rows = rank_regions(None)
                error = None
            except Exception:
                rows, error = [], True
            try:
                self.after(0, lambda: self._servers_done(game, rows, error))
            except Exception:
                pass

        threading.Thread(target=work, daemon=True).start()

    def _servers_done(self, game, rows, error):
        if self.server_test_btn is not None:
            try:
                self.server_test_btn.configure(state="normal", text=self.t("servers_test"))
            except Exception:
                pass
        if error:
            if self.server_status is not None:
                self.server_status.configure(text=self.t("servers_error"), text_color=ERROR)
            return
        self._last_servers = {"game": game, "rows": rows}
        if self.server_status is not None:
            self.server_status.configure(text="", text_color=MUTED)
        self._render_servers(rows, game)

    def _render_servers(self, rows, game):
        if self.server_rows_frame is None:
            return
        try:
            if not self.server_rows_frame.winfo_exists():
                return
        except Exception:
            return
        self._clear_server_rows()
        best = best_region(rows)
        if best and self.server_summary is not None:
            try:
                self.server_summary.configure(
                    text=self.t("servers_best").format(
                        region=self.t(SERVER_REGIONS[best["key"]][1]),
                        ping=f"{best['ping']:.0f}",
                    ),
                    text_color=LIME, font=("Arial", 13, "bold"),
                )
            except Exception:
                pass
        chosen = (self.settings.get("server_choice") or {}).get("region")
        for index, row in enumerate(rows):
            ping = row.get("ping")
            loss = row.get("loss", 100)
            if ping is None:
                color, ping_text, bar = ERROR, self.t("servers_offline"), 0.0
            else:
                color = LIME if ping < 70 else (WARN if ping < 130 else ERROR)
                ping_text = f"{ping:.0f} ms"
                bar = max(0.05, min(1.0, 1.0 - ping / 320.0))
            line = ctk.CTkFrame(
                self.server_rows_frame,
                fg_color=PANEL if row["key"] != chosen else PANEL2,
                border_color=LIME if row["key"] == chosen else BORDER,
                border_width=1, corner_radius=10,
            )
            line.pack(fill="x", pady=3)
            ctk.CTkLabel(
                line, text=f"{index + 1:02d}", font=("Arial", 12, "bold"), text_color=MUTED, width=26,
            ).pack(side="left", padx=(12, 6), pady=10)
            column = ctk.CTkFrame(line, fg_color="transparent")
            column.pack(side="left", fill="x", expand=True, pady=8)
            name_row = ctk.CTkFrame(column, fg_color="transparent")
            name_row.pack(fill="x")
            ctk.CTkLabel(
                name_row, text=self.t(SERVER_REGIONS[row["key"]][1]), font=("Arial", 12, "bold"),
                text_color=WHITE, anchor="w",
            ).pack(side="left")
            if best and row["key"] == best["key"]:
                ctk.CTkLabel(
                    name_row, text=self.t("servers_best_short"), font=("Arial", 8, "bold"),
                    text_color=DARK_TEXT, fg_color=LIME, corner_radius=5,
                ).pack(side="left", padx=(8, 0), ipadx=6, ipady=1)
            bar_widget = ctk.CTkProgressBar(
                column, height=4, corner_radius=2, progress_color=color, fg_color=PANEL2,
            )
            bar_widget.set(bar)
            bar_widget.pack(fill="x", pady=(5, 0))
            ctk.CTkLabel(
                column, text=f"{row.get('host', '')}   ·   {self.t('servers_loss').format(value=loss)}",
                font=("Arial", 8), text_color=MUTED, anchor="w",
            ).pack(fill="x", pady=(3, 0))
            ctk.CTkLabel(
                line, text=ping_text, font=("Arial", 13, "bold"), text_color=color, width=80,
            ).pack(side="right", padx=(0, 6))
            ctk.CTkButton(
                line, text=self.t("servers_choose"), width=84, height=30,
                fg_color=LIME if row["key"] != chosen else PANEL, hover_color=LIME_HOVER,
                text_color=DARK_TEXT if row["key"] != chosen else LIME,
                font=("Arial", 9, "bold"),
                command=lambda item=row, g=game: self._choose_server(g, item),
            ).pack(side="right", padx=8)

    def _choose_server(self, game, row):
        region = row["key"]
        self.settings["server_choice"] = {"game": game, "region": region}
        self._save_settings()
        self._toast(self.t("servers"), self.t("servers_chosen").format(
            region=self.t(SERVER_REGIONS[region][1]),
        ))
        self._render_servers((self._last_servers or {}).get("rows") or [], game)

    def _profile(self, root):
        page = ctk.CTkScrollableFrame(
            root, fg_color="transparent", corner_radius=0, scrollbar_fg_color=PANEL,
            scrollbar_button_color=BORDER, scrollbar_button_hover_color=LIME,
        )
        page.pack(fill="both", expand=True)
        self._heading(page, self.t("profile"), self.t("profile_sub"))

        if not self.user:
            panel = ctk.CTkFrame(page, fg_color=PANEL, border_color=BORDER, border_width=1, corner_radius=14)
            panel.pack(fill="x", pady=(0, 16))
            ctk.CTkLabel(panel, text=self.t("not_signed_in"), font=("Arial", 16, "bold"), text_color=WHITE).pack(anchor="w", padx=22, pady=(20, 4))
            ctk.CTkLabel(panel, text=self.t("not_signed_in_sub"), font=("Arial", 11), text_color=MUTED, wraplength=660, justify="left").pack(anchor="w", padx=22)
            actions = ctk.CTkFrame(panel, fg_color="transparent")
            actions.pack(anchor="w", padx=22, pady=(14, 20))
            ctk.CTkButton(
                actions, text=self.t("sign_in_now"), fg_color=LIME, hover_color=LIME_HOVER,
                text_color=DARK_TEXT, font=("Arial", 11, "bold"), command=self._show_auth,
            ).pack(side="left")
            ctk.CTkButton(
                actions, text=self.t("create_now"), fg_color=PANEL2, hover_color=BORDER,
                text_color=WHITE, command=lambda: self._show_auth("register"),
            ).pack(side="left", padx=(10, 0))
            return

        name = self.user.get("display") or self.user.get("username", "")
        hero = ctk.CTkFrame(page, fg_color=PANEL, border_color=BORDER, border_width=1, corner_radius=14)
        hero.pack(fill="x", pady=(0, 14))
        inner = ctk.CTkFrame(hero, fg_color="transparent")
        inner.pack(fill="x", padx=22, pady=20)
        ctk.CTkLabel(
            inner, text=(name[:1] or "?").upper(), width=64, height=64, corner_radius=32,
            fg_color=LIME, text_color=DARK_TEXT, font=("Arial", 26, "bold"),
        ).pack(side="left", padx=(0, 16))
        column = ctk.CTkFrame(inner, fg_color="transparent")
        column.pack(side="left", fill="x", expand=True)
        ctk.CTkLabel(column, text=name, font=("Arial", 20, "bold"), text_color=WHITE).pack(anchor="w")
        ctk.CTkLabel(column, text=self._handle(), font=("Arial", 11), text_color=MUTED).pack(anchor="w")
        ctk.CTkLabel(
            column, text=f"{self.t('member_since')} {self._fmt_date(self.user.get('created'))}",
            font=("Arial", 10), text_color=MUTED,
        ).pack(anchor="w", pady=(4, 0))
        ctk.CTkButton(
            inner, text=self.t("logout"), width=110, height=34, fg_color=PANEL2,
            hover_color=BORDER, text_color=WHITE, command=self._account_action,
        ).pack(side="right")

        stats = ctk.CTkFrame(page, fg_color="transparent")
        stats.pack(fill="x", pady=(0, 4))
        stats.grid_columnconfigure((0, 1), weight=1)
        games = self.user.get("games", [])
        last = self.user.get("last_played")
        last_text = self._fmt_date(last, self.t("never")) if last else self.t("never")
        card1, _, _, _ = self._card(stats, self.t("games_in_library"), str(len(games)), self.t("my_games"))
        card1.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        card2, _, _, _ = self._card(stats, self.t("launches"), str(self.user.get("launches", 0)), f"{self.t('last_played')}: {last_text}")
        card2.grid(row=0, column=1, sticky="ew", padx=(8, 0))

        self._section(page, self.t("security"))
        security = ctk.CTkFrame(page, fg_color=PANEL, border_color=BORDER, border_width=1, corner_radius=14)
        security.pack(fill="x", pady=(4, 16))
        ctk.CTkLabel(security, text=self.t("change_password"), font=("Arial", 13, "bold"), text_color=WHITE).pack(anchor="w", padx=20, pady=(16, 0))
        old = self._field(security, self.t("current_password"), show="•")
        new = self._field(security, self.t("new_password"), show="•")
        confirm = self._field(security, self.t("confirm_password"), show="•")
        status = ctk.CTkLabel(security, text="", font=("Arial", 10), text_color=MUTED)

        def change():
            if new.get() != confirm.get():
                status.configure(text=self.t("password_mismatch"), text_color=ERROR)
                return
            ok, result = self.accounts.change_password(self.user.get("username", ""), old.get(), new.get())
            if not ok:
                status.configure(text=self.t(result), text_color=ERROR)
                return
            self.user = result
            status.configure(text=self.t("password_changed"), text_color=LIME)
            for entry in (old, new, confirm):
                entry.delete(0, "end")

        ctk.CTkButton(
            security, text=self.t("change_password"), fg_color=LIME, hover_color=LIME_HOVER,
            text_color=DARK_TEXT, font=("Arial", 11, "bold"), command=change,
        ).pack(anchor="w", padx=20, pady=(10, 8))
        status.pack(anchor="w", padx=20, pady=(0, 16))

        self._section(page, self.t("delete_account"))
        danger = ctk.CTkFrame(page, fg_color=PANEL, border_color="#33221F", border_width=1, corner_radius=14)
        danger.pack(fill="x", pady=(4, 16))
        ctk.CTkLabel(
            danger, text=self.t("delete_account_hint"), font=("Arial", 11), text_color=MUTED,
            wraplength=680, justify="left",
        ).pack(anchor="w", padx=20, pady=(16, 0))
        danger_password = self._field(danger, self.t("password"), show="•")
        danger_status = ctk.CTkLabel(danger, text="", font=("Arial", 10), text_color=MUTED)

        def delete_account():
            if not messagebox.askyesno("VYRON", self.t("delete_confirm"), parent=self):
                return
            ok, code = self.accounts.delete(self.user.get("username", ""), danger_password.get())
            if not ok:
                danger_status.configure(text=self.t(code), text_color=ERROR)
                return
            if self.settings.get("last_user", "").lower() == self.user.get("username", "").lower():
                self.settings.pop("last_user", None)
            self.user = None
            self.settings.pop("session", None)
            self._save_settings()
            self._refresh_account_card()
            self._show_page("overview")
            messagebox.showinfo("VYRON", self.t("account_deleted"), parent=self)
            self.after(120, self._show_auth)

        ctk.CTkButton(
            danger, text=self.t("delete_account"), fg_color="transparent", hover_color="#33221F",
            text_color=ERROR, border_color="#58322E", border_width=1,
            font=("Arial", 10, "bold"), command=delete_account,
        ).pack(anchor="w", padx=20, pady=(10, 8))
        danger_status.pack(anchor="w", padx=20, pady=(0, 16))

        self._section(page, self.t("safe_title"))
        ctk.CTkLabel(page, text=self.t("auth_note"), text_color=MUTED, wraplength=760, justify="left").pack(anchor="w")

    def _settings(self, root):
        page = ctk.CTkScrollableFrame(
            root, fg_color="transparent", corner_radius=0, scrollbar_fg_color=PANEL,
            scrollbar_button_color=BORDER, scrollbar_button_hover_color=LIME,
        )
        page.pack(fill="both", expand=True)
        self._heading(page, self.t("settings"), self.t("settings_sub"))
        panel = ctk.CTkFrame(page, fg_color=PANEL, border_color=BORDER, border_width=1, corner_radius=14)
        panel.pack(fill="x", pady=(0, 16))
        ctk.CTkLabel(panel, text=self.t("language"), font=("Arial", 13, "bold"), text_color=WHITE).pack(anchor="w", padx=20, pady=(18, 8))
        self.lang_menu = ctk.CTkOptionMenu(
            panel, values=list(LANGUAGES.values()), command=self._change_language,
            fg_color=PANEL2, button_color="#1B3024", button_hover_color="#284434",
            text_color=WHITE, dropdown_fg_color=PANEL, dropdown_text_color=WHITE,
        )
        self.lang_menu.set(LANGUAGES[self.lang])
        self.lang_menu.pack(anchor="w", padx=20, pady=(0, 18))
        ctk.CTkLabel(panel, text=self.t("language_saved"), text_color=MUTED, font=("Arial", 10)).pack(anchor="w", padx=20, pady=(0, 18))

        self._section(page, self.t("account"))
        account = ctk.CTkFrame(page, fg_color=PANEL, border_color=BORDER, border_width=1, corner_radius=14)
        account.pack(fill="x", pady=(4, 16))
        if self.user:
            name = self.user.get("display") or self.user.get("username", "")
            ctk.CTkLabel(account, text=self.t("signed_in_as"), font=("Arial", 10, "bold"), text_color=MUTED).pack(anchor="w", padx=20, pady=(16, 2))
            ctk.CTkLabel(account, text=f"{name}  {self._handle()}", font=("Arial", 15, "bold"), text_color=WHITE).pack(anchor="w", padx=20)
            ctk.CTkButton(
                account, text=self.t("profile"), fg_color=PANEL2, hover_color=BORDER,
                text_color=LIME, command=lambda: self._show_page("profile"),
            ).pack(anchor="w", padx=20, pady=(10, 16))
        else:
            ctk.CTkLabel(account, text=self.t("not_signed_in"), font=("Arial", 14, "bold"), text_color=WHITE).pack(anchor="w", padx=20, pady=(16, 2))
            ctk.CTkLabel(account, text=self.t("not_signed_in_sub"), text_color=MUTED, font=("Arial", 10), wraplength=680, justify="left").pack(anchor="w", padx=20)
            actions = ctk.CTkFrame(account, fg_color="transparent")
            actions.pack(anchor="w", padx=20, pady=(10, 16))
            ctk.CTkButton(
                actions, text=self.t("login"), fg_color=LIME, hover_color=LIME_HOVER,
                text_color=DARK_TEXT, font=("Arial", 10, "bold"), command=self._show_auth,
            ).pack(side="left")
            ctk.CTkButton(
                actions, text=self.t("register"), fg_color=PANEL2, hover_color=BORDER,
                text_color=WHITE, command=lambda: self._show_auth("register"),
            ).pack(side="left", padx=(10, 0))

        self._section(page, self.t("detection_section"))
        detected = ctk.CTkFrame(page, fg_color=PANEL, border_color=BORDER, border_width=1, corner_radius=14)
        detected.pack(fill="x", pady=(4, 16))
        ctk.CTkLabel(
            detected, text=self.t("detection_hint"), font=("Arial", 10), text_color=MUTED,
            wraplength=700, justify="left",
        ).pack(anchor="w", padx=20, pady=(16, 8))
        ignored = self._excluded_names()
        if ignored:
            ctk.CTkLabel(
                detected, text=self.t("servers_ignored_title"), font=("Arial", 9, "bold"),
                text_color=MUTED,
            ).pack(anchor="w", padx=20, pady=(2, 4))
            for name in ignored:
                line = ctk.CTkFrame(detected, fg_color=PANEL2, corner_radius=8)
                line.pack(fill="x", padx=14, pady=3)
                ctk.CTkLabel(
                    line, text=name, font=("Arial", 11, "bold"), text_color=WHITE, anchor="w",
                ).pack(side="left", padx=12, pady=8)
                ctk.CTkButton(
                    line, text=self.t("servers_restore"), width=104, height=26,
                    fg_color="transparent", hover_color=BORDER, text_color=LIME,
                    border_color=BORDER, border_width=1, font=("Arial", 9, "bold"),
                    command=lambda n=name: self._restore_ignored(n),
                ).pack(side="right", padx=8, pady=6)
            ctk.CTkFrame(detected, height=8, fg_color="transparent").pack()

        self._section(page, self.t("safe_title"))
        ctk.CTkLabel(page, text=self.t("safe_body"), text_color=MUTED, wraplength=780, justify="left").pack(anchor="w")

    def _about(self, root):
        # PROTECTED CREDIT: both made_by lines below are mandatory.
        self._heading(root, "VYRON", self.t("made_by"))
        panel = ctk.CTkFrame(root, fg_color=PANEL, border_color=BORDER, border_width=1, corner_radius=14)
        panel.pack(fill="x")
        ctk.CTkLabel(panel, text="VYRON", font=self._brand_font(34), text_color=LIME).pack(anchor="w", padx=22, pady=(22, 4))
        ctk.CTkLabel(panel, text=self.t("about_body"), text_color=WHITE, wraplength=720, justify="left").pack(anchor="w", padx=22, pady=(0, 8))
        ctk.CTkLabel(panel, text=self.t("auth_note"), text_color=MUTED, wraplength=720, justify="left").pack(anchor="w", padx=22, pady=(0, 8))
        ctk.CTkLabel(panel, text=self.t("made_by"), text_color=MUTED, font=("Arial", 11)).pack(anchor="w", padx=22, pady=(0, 22))

    # ------------------------------------------------------------------ language
    def _first_run(self):
        self._show_language_first_run(self._ensure_auth)

    def _show_language_first_run(self, callback=None):
        win = ctk.CTkToplevel(self)
        win.title("VYRON")
        win.configure(fg_color=BG)
        win.resizable(False, False)
        win.transient(self)
        win.grab_set()
        self._center(win, 500, 440)

        ctk.CTkLabel(win, text="VYRON", font=("Arial", 42, "bold"), text_color=LIME).pack(pady=(35, 2))
        ctk.CTkLabel(win, text=self.t("choose_language"), font=("Arial", 18, "bold"), text_color=WHITE).pack(pady=(8, 4))
        ctk.CTkLabel(win, text=self.t("language_hint"), font=("Arial", 11), text_color=MUTED, wraplength=390).pack(pady=(0, 18))
        choice = ctk.CTkOptionMenu(
            win, values=list(LANGUAGES.values()), fg_color=PANEL2, button_color="#1B3024",
            button_hover_color="#284434", dropdown_fg_color=PANEL, dropdown_text_color=WHITE, width=250,
        )
        choice.set(LANGUAGES[self.lang])
        choice.pack(pady=8)

        def done():
            self.lang = next((k for k, v in LANGUAGES.items() if v == choice.get()), "en")
            self.settings["language"] = self.lang
            self.settings["language_chosen"] = True
            self._save_settings()
            try:
                win.grab_release()
            except Exception:
                pass
            win.destroy()
            self._refresh_account_card()
            self._show_page(self.current_page)
            if callback:
                self.after(60, callback)

        win.protocol("WM_DELETE_WINDOW", done)
        ctk.CTkButton(
            win, text=self.t("continue"), fg_color=LIME, hover_color=LIME_HOVER,
            text_color=DARK_TEXT, font=("Arial", 12, "bold"), width=250, height=42, command=done,
        ).pack(pady=20)
        win.lift()
        win.focus_force()

    def _change_language(self, value):
        self.lang = next((k for k, v in LANGUAGES.items() if v == value), "en")
        self.settings["language"] = self.lang
        self._save_settings()
        self._refresh_account_card()
        self._show_page("settings")

    # ------------------------------------------------------------------ accounts
    def _ensure_auth(self):
        if self.user is None:
            self._show_auth(first_run=True)

    def _account_action(self):
        if self.user:
            if messagebox.askyesno("VYRON", self.t("logout_confirm"), parent=self):
                self._logout()
        else:
            self._show_auth()

    def _login(self, profile):
        self.user = profile
        if self.game_path:
            self.user = self.accounts.add_game(self.user.get("username", ""), self.game_path, game_name(self.game_path)) or self.user
        self.settings["session"] = self.user.get("username", "")
        self.settings["last_user"] = self.user.get("username", "")
        self._save_settings()
        self._refresh_account_card()
        self._show_page(self.current_page)
        self._guest_chosen = False
        self._welcomed = False
        self.after(350, self._welcome)
        if self.activity:
            self.after(600, lambda: self._auto_boost(self.activity))

    def _logout(self):
        self.user = None
        self.settings.pop("session", None)
        self._save_settings()
        self._refresh_account_card()
        self._show_page("overview")
        self.after(120, self._show_auth)

    def _show_auth(self, initial="login", first_run=False):
        if self._auth_dialog is not None and self._auth_dialog.winfo_exists():
            self._auth_dialog.lift()
            self._auth_dialog.focus_force()
            return

        win = ctk.CTkToplevel(self)
        self._auth_dialog = win
        win.title("VYRON")
        win.configure(fg_color=BG)
        win.resizable(False, False)
        win.transient(self)
        win.grab_set()
        win.geometry("540x620")

        state = {"mode": initial, "guest": False}
        fields = {}

        ctk.CTkLabel(win, text="VYRON", font=("Arial", 36, "bold"), text_color=LIME).pack(pady=(16, 0))
        ctk.CTkLabel(
            win, text=self.t("auth_sub"), font=("Arial", 11), text_color=MUTED,
            wraplength=440, justify="center",
        ).pack(pady=(4, 12), padx=40)

        tabbar = ctk.CTkFrame(win, fg_color=PANEL2, corner_radius=10)
        tabbar.pack(fill="x", padx=40)
        tabbar.grid_columnconfigure((0, 1), weight=1)
        login_tab = ctk.CTkButton(
            tabbar, text=self.t("login"), height=32, corner_radius=8, font=("Arial", 10, "bold"),
            fg_color="transparent", hover_color=PANEL, command=lambda: switch("login"),
        )
        login_tab.grid(row=0, column=0, sticky="ew", padx=4, pady=4)
        register_tab = ctk.CTkButton(
            tabbar, text=self.t("register"), height=32, corner_radius=8, font=("Arial", 10, "bold"),
            fg_color="transparent", hover_color=PANEL, command=lambda: switch("register"),
        )
        register_tab.grid(row=0, column=1, sticky="ew", padx=(0, 4), pady=4)

        form = ctk.CTkFrame(win, fg_color="transparent")
        form.pack(fill="x", padx=40, pady=(10, 0))
        error = ctk.CTkLabel(win, text="", text_color=ERROR, font=("Arial", 10), wraplength=440, justify="center")
        error.pack(pady=(4, 0))
        submit = ctk.CTkButton(
            win, text=self.t("login"), height=40, fg_color=LIME, hover_color=LIME_HOVER,
            text_color=DARK_TEXT, font=("Arial", 12, "bold"), command=lambda: do_submit(),
        )
        submit.pack(fill="x", padx=40, pady=(6, 4))
        ctk.CTkButton(
            win, text=self.t("guest_continue"), fg_color="transparent", hover_color=PANEL2,
            text_color=MUTED, height=28, command=lambda: do_guest(),
        ).pack()
        ctk.CTkLabel(
            win, text=self.t("auth_note"), font=("Arial", 9), text_color=MUTED,
            wraplength=440, justify="center",
        ).pack(padx=40, pady=(10, 14))

        def fit():
            win.update_idletasks()
            height = max(win.winfo_reqheight(), 460)
            try:
                x = self.winfo_rootx() + max((self.winfo_width() - 540) // 2, 0)
                y = self.winfo_rooty() + max((self.winfo_height() - height) // 2, 0)
            except Exception:
                x = y = 0
            win.geometry(f"540x{height}+{x}+{y}")

        def add_field(label, show=None, hint=None):
            ctk.CTkLabel(form, text=label, font=("Arial", 10, "bold"), text_color=MUTED).pack(anchor="w", pady=(6, 3))
            entry = ctk.CTkEntry(form, height=36, fg_color=PANEL2, border_color=BORDER, text_color=WHITE, show=show)
            entry.pack(fill="x")
            if hint:
                ctk.CTkLabel(form, text=hint, font=("Arial", 9), text_color=MUTED, anchor="w").pack(anchor="w", pady=(2, 0))
            entry.bind("<Return>", lambda _e: do_submit())
            return entry

        def switch(mode):
            state["mode"] = mode
            for widget in form.winfo_children():
                widget.destroy()
            fields.clear()
            fields["username"] = add_field(self.t("username"), hint=self.t("username_hint"))
            if mode == "register":
                fields["display"] = add_field(self.t("display_name"))
            fields["password"] = add_field(self.t("password"), show="•", hint=self.t("password_hint"))
            if mode == "register":
                fields["confirm"] = add_field(self.t("confirm_password"), show="•")
            active, inactive = (LIME, DARK_TEXT), ("transparent", MUTED)
            login_tab.configure(fg_color=active[0] if mode == "login" else inactive[0], text_color=active[1] if mode == "login" else inactive[1])
            register_tab.configure(fg_color=active[0] if mode == "register" else inactive[0], text_color=active[1] if mode == "register" else inactive[1])
            submit.configure(text=self.t("login") if mode == "login" else self.t("register"))
            error.configure(text="")
            fields["username"].focus_set()
            last_user = self.settings.get("last_user")
            if mode == "login" and last_user:
                fields["username"].insert(0, last_user)
                fields["password"].focus_set()
            fit()

        def fail(code):
            error.configure(text=self.t(code))
            fit()

        def finish(profile):
            self._login(profile)
            close()

        def do_submit():
            error.configure(text="")
            username = fields["username"].get().strip()
            password = fields["password"].get()
            if not username or not password:
                fail("empty_fields")
                return
            if state["mode"] == "login":
                ok, result = self.accounts.authenticate(username, password)
                if ok:
                    finish(result)
                else:
                    fail(result)
                return
            if password != fields["confirm"].get():
                fail("password_mismatch")
                return
            ok, result = self.accounts.create(username, password, fields["display"].get())
            if ok:
                finish(result)
            else:
                fail(result)

        def do_guest():
            state["guest"] = True
            self.user = None
            self._guest_chosen = True
            self._welcomed = False
            self.settings.pop("session", None)
            self._save_settings()
            self._refresh_account_card()
            close()
            self._show_page("overview")
            self.after(350, lambda: self._welcome(allow_guest=True))

        def close():
            try:
                win.grab_release()
            except Exception:
                pass
            win.destroy()
            if self._auth_dialog is win:
                self._auth_dialog = None
            if first_run and self.user is None and not state["guest"]:
                self.destroy()

        win.protocol("WM_DELETE_WINDOW", close)
        win.bind("<Escape>", lambda _e: close())
        switch(initial)
        win.lift()
        win.focus_force()

    # ------------------------------------------------------------------ running apps
    def _show_running_apps(self):
        if self._apps_dialog is not None and self._apps_dialog.winfo_exists():
            self._apps_dialog.lift()
            self._apps_dialog.focus_force()
            return

        win = ctk.CTkToplevel(self)
        self._apps_dialog = win
        win.title(self.t("pick_running"))
        win.configure(fg_color=BG)
        win.resizable(False, False)
        win.transient(self)
        win.grab_set()
        self._center(win, 680, 660)

        head = ctk.CTkFrame(win, fg_color="transparent")
        head.pack(fill="x", padx=24, pady=(20, 0))
        ctk.CTkLabel(head, text=self.t("pick_running"), font=("Arial", 18, "bold"), text_color=WHITE).pack(side="left")
        ctk.CTkButton(
            head, text=self.t("refresh_list"), width=96, height=30, fg_color=PANEL2,
            hover_color=BORDER, text_color=WHITE, font=("Arial", 10, "bold"), command=lambda: load(),
        ).pack(side="right")
        ctk.CTkLabel(
            win, text=self.t("pick_running_sub"), font=("Arial", 11), text_color=MUTED,
            wraplength=630, justify="left",
        ).pack(anchor="w", padx=24, pady=(4, 10))

        search_var = tk.StringVar()
        ctk.CTkEntry(
            win, textvariable=search_var, placeholder_text=self.t("search_apps"),
            height=38, fg_color=PANEL2, border_color=BORDER,
        ).pack(fill="x", padx=24, pady=(0, 8))
        status = ctk.CTkLabel(win, text=self.t("loading_apps"), text_color=MUTED, font=("Arial", 10))
        status.pack(anchor="w", padx=24)
        list_frame = ctk.CTkScrollableFrame(
            win, fg_color="transparent", corner_radius=0, scrollbar_fg_color=PANEL,
            scrollbar_button_color=BORDER, scrollbar_button_hover_color=LIME,
        )
        list_frame.pack(fill="both", expand=True, padx=18, pady=(6, 16))
        apps = []

        def close():
            try:
                win.grab_release()
            except Exception:
                pass
            win.destroy()
            if self._apps_dialog is win:
                self._apps_dialog = None

        def choose(app):
            if not app.get("path"):
                status.configure(text=self.t("pick_running_error"), text_color=ERROR)
                return
            name = app.get("title") or app.get("name")
            if len(name) > 42:
                name = os.path.splitext(app.get("name", ""))[0]
            self._set_game(app["path"], name)
            self._status(self.t("game_selected"))
            close()

        def render():
            for widget in list_frame.winfo_children():
                widget.destroy()
            query = search_var.get().strip().lower()
            shown = [
                app for app in apps
                if not query or query in (app["name"] + " " + app["title"] + " " + app["path"]).lower()
            ]
            if not shown:
                ctk.CTkLabel(list_frame, text=self.t("no_running_apps"), text_color=MUTED, font=("Arial", 11)).pack(pady=30)
                return
            for app in shown:
                row = ctk.CTkFrame(list_frame, fg_color=PANEL, corner_radius=10)
                row.pack(fill="x", pady=4, padx=2)
                ctk.CTkLabel(
                    row, text=(app["name"][:1] or "?").upper(), width=36, height=36, corner_radius=8,
                    fg_color=PANEL2, text_color=LIME, font=("Arial", 15, "bold"),
                ).pack(side="left", padx=(10, 10), pady=10)
                column = ctk.CTkFrame(row, fg_color="transparent")
                column.pack(side="left", fill="x", expand=True, pady=8)
                ctk.CTkLabel(column, text=app["name"], font=("Arial", 12, "bold"), text_color=WHITE, anchor="w").pack(fill="x")
                ctk.CTkLabel(column, text=self._short_path(app["title"], 64), font=("Arial", 10), text_color=MUTED, anchor="w").pack(fill="x")
                ctk.CTkLabel(column, text=self._short_path(app["path"], 68), font=("Arial", 9), text_color=MUTED, anchor="w").pack(fill="x")
                ctk.CTkButton(
                    row, text=self.t("select"), width=84, height=32, fg_color=LIME,
                    hover_color=LIME_HOVER, text_color=DARK_TEXT, font=("Arial", 10, "bold"),
                    command=lambda a=app: choose(a),
                ).pack(side="right", padx=10)

        def load():
            status.configure(text=self.t("loading_apps"), text_color=MUTED)
            for widget in list_frame.winfo_children():
                widget.destroy()

            def work():
                try:
                    found = list_running_apps()
                except Exception:
                    found = []

                def done():
                    try:
                        if not win.winfo_exists():
                            return
                    except Exception:
                        return
                    apps.clear()
                    apps.extend(found)
                    status.configure(text="")
                    render()

                try:
                    self.after(0, done)
                except Exception:
                    pass

            threading.Thread(target=work, daemon=True).start()

        search_var.trace_add("write", lambda *_a: render())
        win.protocol("WM_DELETE_WINDOW", close)
        win.bind("<Escape>", lambda _e: close())
        load()
        win.lift()
        win.focus_force()

    # ------------------------------------------------------------------ game actions
    def _short_path(self, path, limit=72):
        path = path or ""
        if len(path) <= limit:
            return path
        return "…" + path[-max(limit - 3, 8):]

    def _fmt_date(self, timestamp, fallback="—"):
        if not timestamp:
            return fallback
        try:
            return datetime.date.fromtimestamp(int(timestamp)).strftime("%d/%m/%Y")
        except Exception:
            return fallback

    def _browse(self):
        path = filedialog.askopenfilename(
            title=self.t("select_exe"),
            filetypes=[(self.t("exe_files"), "*.exe"), ("All files", "*.*")],
        )
        if path:
            self._set_game(path)

    def _set_game(self, path, name=None):
        if not path:
            return
        path = os.path.abspath(path)
        self.game_path = path
        if self.user:
            self.user = self.accounts.add_game(self.user.get("username", ""), path, name) or self.user
        if self.game_label is not None:
            try:
                self.game_label.configure(text=self._selected_text(), text_color=WHITE)
            except Exception:
                pass
        self._render_library()

    def _remove_game(self, path):
        if not self.user:
            return
        self.user = self.accounts.remove_game(self.user.get("username", ""), path) or self.user
        self._render_library()

    def _launch(self):
        if not self.game_path:
            self._browse()
            if not self.game_path:
                return
        self._launch_path(self.game_path)

    def _launch_path(self, path):
        if not path:
            return
        self._set_game(path)
        try:
            kwargs = {}
            if os.name == "nt" and path.lower().endswith((".bat", ".cmd")):
                command = ["cmd", "/c", path]
                kwargs["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0)
            else:
                command = [path]
            process = subprocess.Popen(command, cwd=os.path.dirname(path) or None, **kwargs)
            self.game_pid = process.pid
            if self.user:
                self.user = self.accounts.record_launch(self.user.get("username", ""), path) or self.user
            self._status(self.t("launched"))
            if getattr(self, "priority_var", None) is not None and self.priority_var.get():
                self.after(1200, self._set_priority)
        except Exception as error:
            messagebox.showerror(self.t("error"), f"{self.t('launch_error')}\n{error}", parent=self)

    def _status(self, text, color=LIME):
        if self.game_status is not None:
            try:
                self.game_status.configure(text=text, text_color=color)
            except Exception:
                pass

    def _set_priority(self):
        enabled = bool(getattr(self, "priority_var", None) is not None and self.priority_var.get())
        if not self.game_pid:
            self._status(self.t("no_process"))
            return
        try:
            process = psutil.Process(self.game_pid)
            if os.name == "nt":
                process.nice(psutil.ABOVE_NORMAL_PRIORITY_CLASS if enabled else psutil.NORMAL_PRIORITY_CLASS)
            else:
                process.nice(-5 if enabled else 0)
            self._status(self.t("priority_set"))
        except Exception:
            self._status(self.t("priority_error"), WARN)

    # ------------------------------------------------------------------ network / system
    def _ping(self):
        if self.host is None or self.ping_btn is None or self.ping_label is None:
            return
        host = self.host.get().strip()
        self.ping_btn.configure(state="disabled", text=self.t("checking"))
        self.ping_label.configure(text=self.t("checking"))

        def work():
            try:
                average, loss, _ = ping_host(host)
                label = self.t("packet_loss")
                if average is not None:
                    text = f"{self.t('ping_result')}: {average:.1f} {self.t('ms')}  |  {label}: {loss}%"
                else:
                    text = f"{self.t('ping_result')}: —  |  {label}: {loss}%"
                color = LIME if loss == 0 else WARN
            except Exception as error:
                text = f"{self.t('error')}: {error}"
                color = ERROR

            def done():
                if self.winfo_exists() and self.ping_label is not None and self.ping_btn is not None:
                    try:
                        self.ping_label.configure(text=text, text_color=color)
                        self.ping_btn.configure(state="normal", text=self.t("test_ping"))
                    except Exception:
                        pass

            try:
                self.after(0, done)
            except Exception:
                pass

        threading.Thread(target=work, daemon=True).start()

    def _tick(self):
        try:
            iconic = self.state() == "iconic"
        except Exception:
            iconic = False
        page = self.current_page
        active_page = page in ("overview", "performance") and not iconic

        if active_page:
            # CPU/RAM/disk are cheap. nvidia-smi is not, so it only runs for the
            # Performance page and its result is cached for 15 seconds.
            try:
                data = snapshot(include_gpu=(page == "performance"))
            except Exception:
                data = None
            if data:
                if page == "overview" and self.metrics:
                    values = {
                        "cpu": (f"{data['cpu']:.0f}%", self.t("refresh"), data["cpu"]),
                        "ram": (f"{data['ram']:.0f}%", f"{data['ram_used']:.1f} / {data['ram_total']:.1f} GB", data["ram"]),
                        "disk": (f"{data['disk']:.0f}%", f"{data['disk_used']:.0f} / {data['disk_total']:.0f} GB", data["disk"]),
                    }
                    for key, (value, sub, percent) in values.items():
                        ring = self.metrics.get(key)
                        if ring:
                            self._set_ring(ring, percent, value, sub)
                elif page == "performance" and self.perf:
                    gpu = self.perf.get("gpu")
                    temp = self.perf.get("gpu_temp")
                    try:
                        if gpu:
                            if data["gpu"] is None:
                                gpu[0].configure(text="—")
                                gpu[1].configure(text=self.t("gpu_unavailable"))
                                if gpu[2] is not None:
                                    gpu[2].set(0)
                            else:
                                gpu[0].configure(text=f"{data['gpu']:.0f}%")
                                gpu[1].configure(text=data["gpu_name"] or "GPU")
                                if gpu[2] is not None:
                                    gpu[2].set(max(0.0, min(1.0, data["gpu"] / 100)))
                        if temp:
                            if data["gpu_temp"] is None:
                                temp[0].configure(text="—")
                                temp[1].configure(text=self.t("temp_unavailable"))
                                if temp[2] is not None:
                                    temp[2].set(0)
                            else:
                                temp[0].configure(text=f"{data['gpu_temp']:.0f}°C")
                                temp[1].configure(text=self.t("temperature"))
                                if temp[2] is not None:
                                    temp[2].set(max(0.0, min(1.0, data["gpu_temp"] / 100)))
                    except Exception:
                        pass

        if iconic or page not in ("overview", "performance"):
            delay = 10000
        else:
            delay = 4000 if self.activity else 2000
        try:
            self.after(delay, self._tick)
        except Exception:
            pass

    # ------------------------------------------------------------------ toast
    def _toast(self, title, message, accent=LIME):
        self._hide_toast()
        try:
            frame = ctk.CTkFrame(
                self.content, fg_color=PANEL2, border_color=BORDER, border_width=1,
                corner_radius=12, width=376, height=84,
            )
            frame.pack_propagate(False)
            frame.place(relx=1.0, rely=1.0, x=-24, y=-24, anchor="se")
            frame.lift()
            ctk.CTkFrame(frame, fg_color=accent, width=4, corner_radius=2).pack(side="left", fill="y")
            body = ctk.CTkFrame(frame, fg_color="transparent")
            body.pack(side="left", fill="x", expand=True, padx=(11, 8), pady=11)
            ctk.CTkLabel(
                body, text=str(title).upper(), font=("Arial", 8, "bold"), text_color=accent, anchor="w",
            ).pack(fill="x")
            ctk.CTkLabel(
                body, text=message, font=("Arial", 11), text_color=WHITE, anchor="w",
                wraplength=286, justify="left",
            ).pack(fill="x", pady=(2, 0))
            ctk.CTkButton(
                frame, text="×", width=24, height=24, fg_color="transparent", hover_color=BORDER,
                text_color=MUTED, font=("Arial", 13, "bold"), command=self._hide_toast,
            ).pack(side="right", padx=(0, 8), pady=8, anchor="n")
            self._toast_widget = frame
            self._toast_job = self.after(6500, self._hide_toast)
        except Exception:
            pass

    def _hide_toast(self):
        if self._toast_job is not None:
            try:
                self.after_cancel(self._toast_job)
            except Exception:
                pass
            self._toast_job = None
        if self._toast_widget is not None:
            try:
                self._toast_widget.destroy()
            except Exception:
                pass
            self._toast_widget = None

    def _welcome(self, allow_guest=False):
        if self._welcomed or self._closing:
            return
        try:
            if not self.winfo_exists():
                return
        except Exception:
            return
        if self.user is None and not allow_guest:
            return
        self._welcomed = True
        if self.user:
            template = self.t(random.choice(("welcome_back_1", "welcome_back_2", "welcome_back_3", "welcome_back_4")))
            message = template.format(user=self._handle())
        else:
            message = self.t(random.choice(("welcome_guest_1", "welcome_guest_2", "welcome_guest_3")))
        self._toast("VYRON", message)

    def _on_close(self):
        self._closing = True
        self._fg_watch = False
        self._hide_toast()
        try:
            trimmod.release_all()
        except Exception:
            pass
        try:
            boostmod.set_timer_resolution(False)
        except Exception:
            pass
        guid = self._auto_plan_previous
        if guid:
            try:
                boostmod.set_power_plan(guid)
            except Exception:
                pass
            self._auto_plan_previous = None
        try:
            self.destroy()
        except Exception:
            pass

    # ------------------------------------------------------------------ window
    def _center(self, win, width, height):
        try:
            self.update_idletasks()
            x = self.winfo_rootx() + max((self.winfo_width() - width) // 2, 0)
            y = self.winfo_rooty() + max((self.winfo_height() - height) // 2, 0)
        except Exception:
            x = y = 0
        win.geometry(f"{width}x{height}+{x}+{y}")


def main():
    try:
        VyronApp().mainloop()
    except Exception:
        details = traceback.format_exc()
        try:
            with open(CRASH, "w", encoding="utf-8") as f:
                f.write(details)
        except Exception:
            pass
        try:
            messagebox.showerror(
                "VYRON",
                f"VYRON n'a pas pu démarrer.\nVYRON could not start.\n\n{CRASH}",
            )
        except Exception:
            pass
