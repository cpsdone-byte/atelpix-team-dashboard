import json
import os
import shutil
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo, available_timezones
from PIL import Image, ImageTk

APP_NAME = "ATELPIX WORLD CLOCK"
BG = "#0B1020"
PANEL = "#151D33"
PANEL_HOVER = "#1C2945"
BORDER = "#2B3A60"
CYAN = "#25D9DF"
BLUE = "#6478FF"
PURPLE = "#9272FF"
WHITE = "#F2F5FF"
MUTED = "#A5B2D2"
PALE = "#C9F7F7"
DATA_DIR = Path(os.getenv("APPDATA", str(Path.home()))) / "ATELPIX" / "WorldClock"
DATA_FILE = DATA_DIR / "cities.json"
SETTINGS_FILE = DATA_DIR / "settings.json"

DEFAULT_CITIES = [
    ("Dhaka", "Asia/Dhaka"), ("New York", "America/New_York"),
    ("London", "Europe/London"), ("Toronto", "America/Toronto"),
    ("Amsterdam", "Europe/Amsterdam"), ("Sydney", "Australia/Sydney"),
    ("Auckland", "Pacific/Auckland"), ("Tokyo", "Asia/Tokyo"),
    ("Dubai", "Asia/Dubai"),
]

def load_cities():
    try:
        data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
        valid = [(str(x["city"]), str(x["zone"])) for x in data
                 if isinstance(x, dict) and x.get("zone") in available_timezones()]
        return valid or DEFAULT_CITIES[:]
    except Exception:
        return DEFAULT_CITIES[:]

def save_cities(cities):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    DATA_FILE.write_text(json.dumps(
        [{"city": c, "zone": z} for c, z in cities],
        ensure_ascii=False, indent=2), encoding="utf-8")

def mix(a, b, t):
    aa = tuple(int(a[i:i+2], 16) for i in (1, 3, 5))
    bb = tuple(int(b[i:i+2], 16) for i in (1, 3, 5))
    return "#%02x%02x%02x" % tuple(int(aa[i] + (bb[i]-aa[i])*t) for i in range(3))

class WorldClockApp:
    def __init__(self, root):
        self.root = root
        self.root.title("ATELPIX World Clock")
        self.root.geometry("1240x850")
        self.root.minsize(960, 690)
        self.root.configure(bg=BG)
        self.cities = load_cities()
        self.settings = self.load_settings()
        self.logo_photo = None
        self.pending_logo = self.settings.get("logo_path", "")
        self.use_24h = True
        self.cards = []
        self.pulse = 0
        # The canvas creates its animated dot on its first Configure event.
        # Initialize the id first because the animation timer starts immediately.
        self.live_dot = None
        self._style()
        self._build()
        self.render_cards()
        self.tick()
        self.animate_header()

    def _style(self):
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("Dark.TCombobox", fieldbackground=PANEL, background=PANEL,
                        foreground=WHITE, arrowcolor=CYAN, bordercolor=BORDER)
        style.map("Dark.TCombobox", fieldbackground=[("readonly", PANEL)],
                  foreground=[("readonly", WHITE)])

    def _build(self):
        # Premium dashboard shell
        shell = tk.Frame(self.root, bg=BG)
        shell.pack(fill="both", expand=True, padx=26, pady=20)

        self.header = tk.Canvas(shell, height=178, bg=BG, highlightthickness=0)
        self.header.pack(fill="x")
        self.header.bind("<Configure>", self.draw_header)

        body = tk.Frame(shell, bg=BG)
        body.pack(fill="both", expand=True, pady=(18, 0))

        top = tk.Frame(body, bg=BG)
        top.pack(fill="x", pady=(0, 16))
        heading = tk.Frame(top, bg=BG)
        heading.pack(side="left", fill="y")
        tk.Label(heading, text="YOUR WORLD, AT A GLANCE", bg=BG, fg=MUTED,
                 font=("Segoe UI", 9, "bold")).pack(anchor="w")
        title = tk.Label(heading, text="Global Time Dashboard", bg=BG, fg=WHITE,
                         font=("Segoe UI", 20, "bold"))
        title.pack(anchor="w", pady=(3, 0))
        self.city_count = tk.Label(heading, text="", bg=BG, fg=CYAN,
                                   font=("Segoe UI", 9, "bold"))
        self.city_count.pack(anchor="w", pady=(4, 0))

        actions = tk.Frame(top, bg=BG)
        actions.pack(side="right", anchor="center", pady=8)
        self.format_btn = self._button(actions, "24H FORMAT", self.toggle_format, BLUE)
        self.format_btn.pack(side="left", padx=(0, 9))
        self._button(actions, "LOGO SETTINGS", self.logo_settings, PURPLE).pack(side="left", padx=(0, 9))
        self._button(actions, "+ ADD CITY", self.add_city, CYAN, True).pack(side="left")

        self.grid = tk.Frame(body, bg=BG)
        self.grid.pack(fill="both", expand=True)

        footer = tk.Frame(body, bg=BG)
        footer.pack(fill="x", pady=(14, 0))
        tk.Label(footer, text="●  LIVE GLOBAL TIME     •     AUTOMATIC DAYLIGHT-SAVING",
                 bg=BG, fg=MUTED, font=("Segoe UI", 8, "bold")).pack(side="left")
        tk.Label(footer, text="ATELPIX  /  WHERE PIXELS BECOME ART",
                 bg=BG, fg=CYAN, font=("Segoe UI", 8, "bold")).pack(side="right")

    def draw_header(self, event=None):
        c = self.header
        c.delete("all")
        w = max(c.winfo_width(), 800)
        h = 178
        for x in range(w):
            c.create_line(x, 0, x, h, fill=mix("#10172D", "#172F49", x/max(w-1, 1)))
        c.create_oval(w-285, -190, w+70, 165, outline="#244764", width=2)
        c.create_oval(w-238, -145, w+20, 113, outline="#294D69", width=1)
        c.create_oval(w-196, -103, w-24, 69, outline="#285A70", width=1)
        c.create_line(0, h-2, w, h-2, fill="#2B4565", width=1)

        # Brand tile with a subtle luminous frame
        c.create_rectangle(18, 20, 166, 154, fill="#111D34", outline="#3A5B7B", width=2)
        c.create_rectangle(23, 25, 161, 149, outline="#233D5D", width=1)
        self.draw_logo(c)
        c.create_text(194, 42, anchor="w", text="ATELPIX  •  WORLD CLOCK",
                      fill=CYAN, font=("Segoe UI", 10, "bold"))
        c.create_text(192, 82, anchor="w", text="Time, beautifully connected.",
                      fill=WHITE, font=("Segoe UI", 24, "bold"))
        c.create_text(195, 113, anchor="w", text="A premium view of every time zone that matters.",
                      fill=PALE, font=("Segoe UI", 10))
        c.create_text(w-28, 45, anchor="e", text="LOCAL DATE",
                      fill=MUTED, font=("Segoe UI", 8, "bold"))
        c.create_text(w-28, 75, anchor="e", text=datetime.now().strftime("%A, %d %B %Y"),
                      fill=WHITE, font=("Segoe UI", 12, "bold"))
        c.create_text(w-28, 108, anchor="e", text="●  SYSTEM ONLINE",
                      fill=CYAN, font=("Segoe UI", 9, "bold"))
        self.live_dot = c.create_oval(w-146, 127, w-136, 137, fill=CYAN, outline="")

    def load_settings(self):
        defaults = {"logo_path": "", "logo_size": 100, "logo_align": "Center"}
        try:
            saved = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
            if isinstance(saved, dict):
                defaults.update(saved)
        except Exception:
            pass
        return defaults

    def save_settings(self):
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        SETTINGS_FILE.write_text(json.dumps(self.settings, ensure_ascii=False, indent=2),
                                 encoding="utf-8")

    def draw_logo(self, canvas):
        canvas.create_rectangle(28, 25, 166, 137, outline="#3B5A80", width=2)
        path = self.settings.get("logo_path", "")
        if path and os.path.isfile(path):
            try:
                with Image.open(path) as source:
                    image = source.convert("RGBA")
                    scale = int(self.settings.get("logo_size", 100)) / 100
                    image.thumbnail((max(40, int(130 * scale)), max(40, int(100 * scale))),
                                    Image.Resampling.LANCZOS)
                    self.logo_photo = ImageTk.PhotoImage(image)
                align = self.settings.get("logo_align", "Center")
                x = {"Left": 28 + self.logo_photo.width() / 2,
                     "Center": 97,
                     "Right": 166 - self.logo_photo.width() / 2}.get(align, 97)
                canvas.create_image(x, 81, image=self.logo_photo)
                return
            except Exception:
                self.logo_photo = None
        canvas.create_text(97, 72, text="YOUR LOGO", fill="#B7C7E7",
                           font=("Segoe UI", 12, "bold"))
        canvas.create_text(97, 98, text="PLACEHOLDER", fill="#7185AA",
                           font=("Segoe UI", 7, "bold"))

    def logo_settings(self):
        win = tk.Toplevel(self.root)
        win.title("Logo Settings")
        win.configure(bg=BG)
        win.geometry("500x390")
        win.resizable(False, False)
        win.transient(self.root)
        win.grab_set()
        tk.Label(win, text="CUSTOMIZE YOUR LOGO", bg=BG, fg=WHITE,
                 font=("Segoe UI", 17, "bold")).pack(anchor="w", padx=26, pady=(22, 5))
        tk.Label(win, text="Choose an image, adjust its size and alignment, then save.",
                 bg=BG, fg=MUTED, font=("Segoe UI", 9)).pack(anchor="w", padx=26, pady=(0, 18))
        path_var = tk.StringVar(value=self.pending_logo or "No logo selected")
        tk.Label(win, textvariable=path_var, bg=PANEL, fg=PALE, anchor="w",
                 padx=12, pady=10, wraplength=430).pack(fill="x", padx=26)

        def browse():
            selected = filedialog.askopenfilename(
                parent=win, title="Choose your logo",
                filetypes=[("Image files", "*.png *.jpg *.jpeg *.gif *.bmp *.webp"),
                           ("All files", "*.*")])
            if selected:
                self.pending_logo = selected
                path_var.set(os.path.basename(selected))

        self._button(win, "UPLOAD / CHANGE LOGO", browse, CYAN, True).pack(
            anchor="w", padx=26, pady=(12, 18))
        tk.Label(win, text="LOGO SIZE", bg=BG, fg=WHITE,
                 font=("Segoe UI", 9, "bold")).pack(anchor="w", padx=26)
        size_var = tk.IntVar(value=int(self.settings.get("logo_size", 100)))
        ttk.Scale(win, from_=50, to=100, orient="horizontal",
                  variable=size_var).pack(fill="x", padx=26, pady=(5, 14))
        tk.Label(win, text="LOGO ALIGNMENT", bg=BG, fg=WHITE,
                 font=("Segoe UI", 9, "bold")).pack(anchor="w", padx=26)
        align_var = tk.StringVar(value=self.settings.get("logo_align", "Center"))
        ttk.Combobox(win, textvariable=align_var, values=["Left", "Center", "Right"],
                     state="readonly", style="Dark.TCombobox",
                     font=("Segoe UI", 10)).pack(fill="x", padx=26, pady=(5, 18))
        bottom = tk.Frame(win, bg=BG)
        bottom.pack(fill="x", padx=26, pady=(0, 20))

        def remove_logo():
            self.pending_logo = ""
            path_var.set("No logo selected")
            self.settings["logo_path"] = ""
            self.save_settings()
            self.draw_header()

        def save_logo():
            chosen = self.pending_logo
            if chosen and os.path.isfile(chosen):
                try:
                    with Image.open(chosen) as img:
                        img.verify()
                    DATA_DIR.mkdir(parents=True, exist_ok=True)
                    ext = Path(chosen).suffix.lower() or ".png"
                    stored = DATA_DIR / ("custom_logo" + ext)
                    if os.path.abspath(chosen) != os.path.abspath(stored):
                        shutil.copy2(chosen, stored)
                    self.settings["logo_path"] = str(stored)
                except Exception as exc:
                    messagebox.showerror("Logo error", f"Could not use this image.\\n{exc}", parent=win)
                    return
            self.settings["logo_size"] = int(size_var.get())
            self.settings["logo_align"] = align_var.get()
            self.save_settings()
            self.draw_header()
            win.destroy()

        self._button(bottom, "REMOVE LOGO", remove_logo, PANEL_HOVER).pack(side="left")
        self._button(bottom, "SAVE SETTINGS", save_logo, CYAN, True).pack(side="right")

    def animate_header(self):
        self.pulse = (self.pulse + 1) % 40
        if self.header.winfo_exists():
            if self.live_dot is not None:
                color = mix("#1B5364", CYAN, abs(20-self.pulse)/20)
                self.header.itemconfigure(self.live_dot, fill=color)
            self.root.after(70, self.animate_header)

    def _button(self, parent, text, command, color, dark_text=False):
        fg = BG if dark_text else WHITE
        b = tk.Button(parent, text=text, command=command, bg=color, fg=fg,
                      activebackground=CYAN, activeforeground=BG,
                      relief="flat", bd=0, padx=17, pady=10,
                      font=("Segoe UI", 9, "bold"), cursor="hand2")
        b.bind("<Enter>", lambda e: self._button_hover(b, color, CYAN, 0))
        b.bind("<Leave>", lambda e: self._button_hover(b, CYAN, color, 0))
        return b

    def _button_hover(self, button, start, end, step):
        if not button.winfo_exists():
            return
        t = min(step / 5, 1)
        button.configure(bg=mix(start, end, t))
        if step < 5:
            self.root.after(18, lambda: self._button_hover(button, start, end, step+1))

    def render_cards(self):
        for child in self.grid.winfo_children():
            child.destroy()
        self.cards = []
        self.city_count.configure(text=f"{len(self.cities):02d} CITIES CONNECTED")
        for i, (city, zone) in enumerate(self.cities):
            card = tk.Frame(self.grid, bg="#141F35", highlightbackground="#2B405F",
                            highlightthickness=1, bd=0)
            r, col = divmod(i, 3)
            card.grid(row=r, column=col, sticky="nsew", padx=7, pady=7)
            self.grid.grid_columnconfigure(col, weight=1, uniform="cards")
            self.grid.grid_rowconfigure(r, weight=1, uniform="rows")
            card.bind("<Enter>", lambda e, f=card: self.card_hover(f, True))
            card.bind("<Leave>", lambda e, f=card: self.card_hover(f, False))

            accent = tk.Frame(card, bg=CYAN, height=3)
            accent.pack(fill="x")
            inner = tk.Frame(card, bg="#141F35")
            inner.pack(fill="both", expand=True, padx=17, pady=13)
            top = tk.Frame(inner, bg="#141F35")
            top.pack(fill="x")
            name = tk.Label(top, text=city.upper(), bg="#141F35", fg=WHITE,
                            font=("Segoe UI", 12, "bold"))
            name.pack(side="left")
            dot = tk.Label(top, text="●", bg="#141F35", fg=CYAN, font=("Segoe UI", 8))
            dot.pack(side="left", padx=7)
            if zone != "Asia/Dhaka":
                rm = tk.Label(top, text="×", bg="#141F35", fg="#8091AE",
                              font=("Segoe UI", 17), cursor="hand2")
                rm.pack(side="right")
                rm.bind("<Button-1>", lambda e, z=zone: self.remove_city(z))
                rm.bind("<Enter>", lambda e, x=rm: x.configure(fg=CYAN))
                rm.bind("<Leave>", lambda e, x=rm: x.configure(fg="#8091AE"))

            zone_label = tk.Label(inner, text=zone.replace("_", " ").upper(),
                                  bg="#141F35", fg="#8192B0",
                                  font=("Segoe UI", 8, "bold"))
            zone_label.pack(anchor="w", pady=(4, 0))
            clock = tk.Label(inner, text="--:--:--", bg="#141F35", fg="#55E3E6",
                             font=("Segoe UI", 27, "bold"))
            clock.pack(anchor="w", pady=(11, 0))
            date = tk.Label(inner, text="", bg="#141F35", fg="#D1DCEF",
                            font=("Segoe UI", 9))
            date.pack(anchor="w", pady=(2, 9))
            separator = tk.Frame(inner, bg="#293B57", height=1)
            separator.pack(fill="x", pady=(1, 8))
            info = tk.Label(inner, text="", bg="#141F35", fg="#9EAFCA",
                            font=("Segoe UI", 8, "bold"))
            info.pack(anchor="w")
            for widget in (inner, top, name, dot, zone_label, clock, date, info):
                widget.bind("<Enter>", lambda e, f=card: self.card_hover(f, True))
                widget.bind("<Leave>", lambda e, f=card: self.card_hover(f, False))
            self.cards.append((zone, clock, date, info, card, accent))

    def card_hover(self, card, entering):
        target_bg = PANEL_HOVER if entering else PANEL
        target_border = CYAN if entering else BORDER
        target_accent = PURPLE if entering else CYAN
        card.configure(bg=target_bg, highlightbackground=target_border, highlightthickness=2 if entering else 1)
        for child in card.winfo_children():
            try:
                child.configure(bg=target_bg)
                for nested in child.winfo_children():
                    try:
                        nested.configure(bg=target_bg)
                    except tk.TclError:
                        pass
            except tk.TclError:
                pass
        if card.winfo_children():
            card.winfo_children()[0].configure(bg=target_accent)

    def tick(self):
        now_utc = datetime.now().astimezone().astimezone(ZoneInfo("UTC"))
        for zone, clock, date, info, card, accent in self.cards:
            try:
                local = now_utc.astimezone(ZoneInfo(zone))
                fmt = "%H:%M:%S" if self.use_24h else "%I:%M:%S %p"
                clock.configure(text=local.strftime(fmt))
                date.configure(text=local.strftime("%A, %d %B %Y"))
                offset = local.strftime("%z")
                offset = f"UTC{offset[:3]}:{offset[3:]}" if offset else "UTC"
                info.configure(text=f"{offset}   •   {'DAYTIME' if 7 <= local.hour < 19 else 'NIGHT'}")
            except Exception:
                clock.configure(text="Unavailable")
        self.root.after(500, self.tick)

    def toggle_format(self):
        self.use_24h = not self.use_24h
        self.format_btn.configure(text="12H FORMAT" if self.use_24h else "24H FORMAT")

    def add_city(self):
        win = tk.Toplevel(self.root)
        win.title("Add a city")
        win.configure(bg=BG)
        win.geometry("460x250")
        win.resizable(False, False)
        win.transient(self.root)
        win.grab_set()
        tk.Label(win, text="ADD A TIME ZONE", bg=BG, fg=WHITE,
                 font=("Segoe UI", 17, "bold")).pack(anchor="w", padx=26, pady=(24, 5))
        tk.Label(win, text="Choose a city / time zone from the list.",
                 bg=BG, fg=MUTED, font=("Segoe UI", 10)).pack(anchor="w", padx=26)
        zones = sorted(available_timezones())
        combo = ttk.Combobox(win, values=zones, state="readonly",
                             style="Dark.TCombobox", font=("Segoe UI", 11))
        combo.pack(fill="x", padx=26, pady=20)
        combo.set("Europe/Paris")
        def add():
            zone = combo.get()
            if not zone:
                return
            if any(z == zone for _, z in self.cities):
                messagebox.showinfo("Already added", "This time zone is already on your dashboard.", parent=win)
                return
            city = zone.split("/")[-1].replace("_", " ")
            self.cities.append((city, zone))
            save_cities(self.cities)
            self.render_cards()
            win.destroy()
        self._button(win, "ADD TO DASHBOARD", add, CYAN, True).pack(anchor="e", padx=26)

    def remove_city(self, zone):
        self.cities = [(c, z) for c, z in self.cities if z != zone]
        save_cities(self.cities)
        self.render_cards()

def main():
    root = tk.Tk()
    WorldClockApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
