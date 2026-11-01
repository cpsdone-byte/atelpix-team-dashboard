import json
import os
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo, available_timezones

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
        self.use_24h = True
        self.cards = []
        self.pulse = 0
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
        self.header = tk.Canvas(self.root, height=164, bg=BG, highlightthickness=0)
        self.header.pack(fill="x")
        self.header.bind("<Configure>", self.draw_header)

        body = tk.Frame(self.root, bg=BG)
        body.pack(fill="both", expand=True, padx=30, pady=(0, 20))

        top = tk.Frame(body, bg=BG)
        top.pack(fill="x", pady=(2, 15))
        tk.Label(top, text="WORLD TIME DASHBOARD", bg=BG, fg=WHITE,
                 font=("Segoe UI", 14, "bold")).pack(side="left")
        self.city_count = tk.Label(top, text="", bg=BG, fg=CYAN,
                                   font=("Segoe UI", 10, "bold"))
        self.city_count.pack(side="left", padx=13)

        actions = tk.Frame(top, bg=BG)
        actions.pack(side="right")
        self.format_btn = self._button(actions, "24H FORMAT", self.toggle_format, BLUE)
        self.format_btn.pack(side="left", padx=(0, 10))
        self._button(actions, "+ ADD CITY", self.add_city, CYAN, True).pack(side="left")

        self.grid = tk.Frame(body, bg=BG)
        self.grid.pack(fill="both", expand=True)

        footer = tk.Frame(body, bg=BG)
        footer.pack(fill="x", pady=(13, 0))
        tk.Label(footer, text="● LIVE TIME  •  AUTOMATIC DAYLIGHT-SAVING ADJUSTMENT",
                 bg=BG, fg=MUTED, font=("Segoe UI", 8, "bold")).pack(side="left")
        tk.Label(footer, text="ATELPIX  /  WHERE PIXELS BECOME ART",
                 bg=BG, fg=CYAN, font=("Segoe UI", 9, "bold")).pack(side="right")

    def draw_header(self, event=None):
        c = self.header
        c.delete("all")
        w = max(c.winfo_width(), 800)
        h = 164
        for x in range(w):
            c.create_line(x, 0, x, h, fill=mix("#10162B", "#142C43", x/max(w-1, 1)))
        # Decorative rings and flowing accent strokes
        c.create_oval(w-245, -155, w+55, 145, outline="#254565", width=2)
        c.create_oval(w-200, -118, w+10, 92, outline="#28516A", width=1)
        c.create_line(0, 158, w, 158, fill="#26385B", width=1)

        # Dedicated company logo space: replace this framed area with the ATELPIX logo later.
        c.create_rectangle(28, 25, 166, 137, outline="#3B5A80", width=2, dash=(5, 4))
        c.create_text(97, 72, text="YOUR LOGO", fill="#B7C7E7",
                      font=("Segoe UI", 12, "bold"))
        c.create_text(97, 98, text="PLACEHOLDER", fill="#7185AA",
                      font=("Segoe UI", 7, "bold"))

        c.create_text(196, 48, anchor="w", text="ATELPIX",
                      fill=CYAN, font=("Segoe UI", 13, "bold"))
        c.create_text(194, 83, anchor="w", text="WORLD CLOCK",
                      fill=WHITE, font=("Segoe UI", 29, "bold"))
        c.create_text(197, 116, anchor="w", text="One world. Every time zone.",
                      fill=PALE, font=("Segoe UI", 11))
        c.create_text(w-32, 47, anchor="e", text="LIVE GLOBAL TIME",
                      fill=MUTED, font=("Segoe UI", 9, "bold"))
        c.create_text(w-32, 78, anchor="e", text=datetime.now().strftime("%A, %d %B %Y"),
                      fill=WHITE, font=("Segoe UI", 12, "bold"))
        c.create_text(w-32, 108, anchor="e", text="OFFLINE DESKTOP EDITION",
                      fill=CYAN, font=("Segoe UI", 9, "bold"))
        self.live_dot = c.create_oval(w-160, 128, w-150, 138, fill=CYAN, outline="")

    def animate_header(self):
        self.pulse = (self.pulse + 1) % 40
        if self.header.winfo_exists():
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
        self.city_count.configure(text=f"{len(self.cities)} CITIES")
        for i, (city, zone) in enumerate(self.cities):
            card = tk.Frame(self.grid, bg=PANEL, highlightbackground=BORDER,
                            highlightthickness=1, bd=0)
            r, col = divmod(i, 3)
            card.grid(row=r, column=col, sticky="nsew", padx=8, pady=8)
            self.grid.grid_columnconfigure(col, weight=1, uniform="cards")
            self.grid.grid_rowconfigure(r, weight=1, uniform="rows")
            card.bind("<Enter>", lambda e, f=card: self.card_hover(f, True))
            card.bind("<Leave>", lambda e, f=card: self.card_hover(f, False))

            accent = tk.Frame(card, bg=CYAN, height=3)
            accent.pack(fill="x")
            top = tk.Frame(card, bg=PANEL)
            top.pack(fill="x", padx=18, pady=(14, 2))
            top.bind("<Enter>", lambda e, f=card: self.card_hover(f, True))
            top.bind("<Leave>", lambda e, f=card: self.card_hover(f, False))

            # Larger, prominent country/city name
            name = tk.Label(top, text=city.upper(), bg=PANEL, fg=WHITE,
                            font=("Segoe UI", 16, "bold"))
            name.pack(side="left")
            name.bind("<Enter>", lambda e, f=card: self.card_hover(f, True))
            name.bind("<Leave>", lambda e, f=card: self.card_hover(f, False))
            dot = tk.Label(top, text="●", bg=PANEL, fg=CYAN, font=("Segoe UI", 9))
            dot.pack(side="left", padx=8)
            dot.bind("<Enter>", lambda e, f=card: self.card_hover(f, True))
            dot.bind("<Leave>", lambda e, f=card: self.card_hover(f, False))

            if zone != "Asia/Dhaka":
                rm = tk.Label(top, text="×", bg=PANEL, fg=MUTED,
                              font=("Segoe UI", 17), cursor="hand2")
                rm.pack(side="right")
                rm.bind("<Button-1>", lambda e, z=zone: self.remove_city(z))
                rm.bind("<Enter>", lambda e, x=rm: x.configure(fg=CYAN))
                rm.bind("<Leave>", lambda e, x=rm: x.configure(fg=MUTED))

            zone_label = tk.Label(card, text=zone.replace("_", " "), bg=PANEL,
                                  fg=MUTED, font=("Segoe UI", 9))
            zone_label.pack(anchor="w", padx=19)

            clock = tk.Label(card, text="--:--:--", bg=PANEL, fg=CYAN,
                             font=("Segoe UI", 31, "bold"))
            clock.pack(anchor="w", padx=17, pady=(12, 0))
            date = tk.Label(card, text="", bg=PANEL, fg=PALE,
                            font=("Segoe UI", 10))
            date.pack(anchor="w", padx=19, pady=(2, 9))
            info = tk.Label(card, text="", bg=PANEL, fg=MUTED,
                            font=("Segoe UI", 9, "bold"))
            info.pack(anchor="w", padx=19, pady=(0, 16))
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
