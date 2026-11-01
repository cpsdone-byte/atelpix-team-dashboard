import json
import os
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo, available_timezones

APP_NAME = "ATELPIX WORLD CLOCK"
BG = "#101426"
PANEL = "#171E35"
BORDER = "#2B3658"
CYAN = "#25D9DF"
BLUE = "#6478FF"
PURPLE = "#9272FF"
WHITE = "#EEF2FF"
MUTED = "#9DA9C7"
LIGHT_CYAN = "#BCEEF0"
TEAL = "#142B3B"

DEFAULT_CITIES = [
    ("Dhaka", "Asia/Dhaka"),
    ("New York", "America/New_York"),
    ("London", "Europe/London"),
    ("Toronto", "America/Toronto"),
    ("Amsterdam", "Europe/Amsterdam"),
    ("Sydney", "Australia/Sydney"),
    ("Auckland", "Pacific/Auckland"),
    ("Tokyo", "Asia/Tokyo"),
    ("Dubai", "Asia/Dubai"),
]

DATA_DIR = Path(os.getenv("APPDATA", str(Path.home()))) / "ATELPIX" / "WorldClock"
DATA_FILE = DATA_DIR / "cities.json"


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
        ensure_ascii=False, indent=2
    ), encoding="utf-8")


class WorldClockApp:
    def __init__(self, root):
        self.root = root
        self.root.title("ATELPIX World Clock")
        self.root.geometry("1180x790")
        self.root.minsize(900, 650)
        self.root.configure(bg=BG)
        self.cities = load_cities()
        self.use_24h = True
        self.cards = []
        self._style()
        self._build()
        self.render_cards()
        self.tick()

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
        self.header = tk.Canvas(self.root, height=126, bg=BG, highlightthickness=0)
        self.header.pack(fill="x")
        self.header.bind("<Configure>", self.draw_header)

        body = tk.Frame(self.root, bg=BG)
        body.pack(fill="both", expand=True, padx=28, pady=(0, 18))

        top = tk.Frame(body, bg=BG)
        top.pack(fill="x", pady=(2, 16))
        self.section_title = tk.Label(top, text="GLOBAL TIME ZONES", bg=BG,
                                      fg=WHITE, font=("Segoe UI", 13, "bold"))
        self.section_title.pack(side="left")
        self.city_count = tk.Label(top, text="", bg=BG, fg=MUTED,
                                   font=("Segoe UI", 9))
        self.city_count.pack(side="left", padx=12)

        actions = tk.Frame(top, bg=BG)
        actions.pack(side="right")
        self.format_btn = self._button(actions, "24H FORMAT", self.toggle_format, BLUE)
        self.format_btn.pack(side="left", padx=(0, 9))
        self._button(actions, "+ ADD CITY", self.add_city, CYAN, dark_text=True).pack(side="left")

        self.grid = tk.Frame(body, bg=BG)
        self.grid.pack(fill="both", expand=True)

        footer = tk.Frame(body, bg=BG)
        footer.pack(fill="x", pady=(12, 0))
        tk.Label(footer, text="LOCAL TIME • AUTOMATIC DAYLIGHT-SAVING ADJUSTMENT",
                 bg=BG, fg=MUTED, font=("Segoe UI", 8, "bold")).pack(side="left")
        tk.Label(footer, text="ATELPIX  /  WHERE PIXELS BECOME ART",
                 bg=BG, fg=CYAN, font=("Segoe UI", 8, "bold")).pack(side="right")

    def draw_header(self, event=None):
        c = self.header
        c.delete("all")
        w = max(c.winfo_width(), 700)
        # Subtle blue-to-cyan horizontal gradient
        for x in range(w):
            t = x / max(w - 1, 1)
            a = (16, 20, 38)
            b = (20, 43, 59)
            rgb = tuple(int(a[i] * (1-t) + b[i] * t) for i in range(3))
            c.create_line(x, 0, x, 126, fill="#%02x%02x%02x" % rgb)
        c.create_oval(w-210, -120, w+40, 130, outline="#203e64", width=2)
        c.create_oval(w-165, -92, w+5, 78, outline="#244e68", width=1)
        c.create_text(30, 34, anchor="w", text="ATELPIX",
                      fill=CYAN, font=("Segoe UI", 11, "bold"))
        c.create_text(30, 69, anchor="w", text="WORLD CLOCK",
                      fill=WHITE, font=("Segoe UI", 25, "bold"))
        c.create_text(32, 101, anchor="w", text="One world. Every time zone.",
                      fill=LIGHT_CYAN, font=("Segoe UI", 10))
        c.create_text(w-30, 43, anchor="e", text="LIVE GLOBAL TIME",
                      fill=MUTED, font=("Segoe UI", 9, "bold"))
        c.create_text(w-30, 70, anchor="e", text=datetime.now().strftime("%A, %d %B %Y"),
                      fill=WHITE, font=("Segoe UI", 11, "bold"))
        c.create_text(w-30, 94, anchor="e", text="OFFLINE DESKTOP EDITION",
                      fill=CYAN, font=("Segoe UI", 8, "bold"))

    def _button(self, parent, text, command, color, dark_text=False):
        fg = BG if dark_text else WHITE
        b = tk.Button(parent, text=text, command=command, bg=color, fg=fg,
                      activebackground=CYAN, activeforeground=BG,
                      relief="flat", bd=0, padx=15, pady=9,
                      font=("Segoe UI", 8, "bold"), cursor="hand2")
        b.bind("<Enter>", lambda e: b.configure(highlightthickness=1, highlightbackground=CYAN))
        b.bind("<Leave>", lambda e: b.configure(highlightthickness=0))
        return b

    def render_cards(self):
        for child in self.grid.winfo_children():
            child.destroy()
        self.cards = []
        self.city_count.configure(text=f"{len(self.cities)} CITIES")
        for i, (city, zone) in enumerate(self.cities):
            card = tk.Frame(self.grid, bg=PANEL, highlightbackground=BORDER,
                            highlightthickness=1, bd=0)
            r, col = divmod(i, 3)
            card.grid(row=r, column=col, sticky="nsew", padx=7, pady=7)
            self.grid.grid_columnconfigure(col, weight=1, uniform="cards")
            self.grid.grid_rowconfigure(r, weight=1, uniform="rows")

            top = tk.Frame(card, bg=PANEL)
            top.pack(fill="x", padx=15, pady=(13, 3))
            tk.Label(top, text=city.upper(), bg=PANEL, fg=WHITE,
                     font=("Segoe UI", 10, "bold")).pack(side="left")
            tk.Label(top, text="●", bg=PANEL, fg=CYAN,
                     font=("Segoe UI", 8)).pack(side="left", padx=7)
            if zone != "Asia/Dhaka":
                rm = tk.Label(top, text="×", bg=PANEL, fg=MUTED,
                              font=("Segoe UI", 15), cursor="hand2")
                rm.pack(side="right")
                rm.bind("<Button-1>", lambda e, z=zone: self.remove_city(z))
            tk.Label(card, text=zone, bg=PANEL, fg=MUTED,
                     font=("Segoe UI", 8)).pack(anchor="w", padx=15)

            clock = tk.Label(card, text="--:--:--", bg=PANEL, fg=CYAN,
                             font=("Segoe UI", 27, "bold"))
            clock.pack(anchor="w", padx=14, pady=(12, 0))
            date = tk.Label(card, text="", bg=PANEL, fg=LIGHT_CYAN,
                            font=("Segoe UI", 9))
            date.pack(anchor="w", padx=15, pady=(1, 8))
            info = tk.Label(card, text="", bg=PANEL, fg=MUTED,
                            font=("Segoe UI", 8))
            info.pack(anchor="w", padx=15, pady=(0, 13))
            self.cards.append((zone, clock, date, info))

    def tick(self):
        now_utc = datetime.now().astimezone().astimezone(ZoneInfo("UTC"))
        for zone, clock, date, info in self.cards:
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
        self.header.itemconfigure if False else None
        self.root.after(500, self.tick)

    def toggle_format(self):
        self.use_24h = not self.use_24h
        self.format_btn.configure(text="12H FORMAT" if self.use_24h else "24H FORMAT")

    def add_city(self):
        win = tk.Toplevel(self.root)
        win.title("Add a city")
        win.configure(bg=BG)
        win.geometry("430x230")
        win.resizable(False, False)
        win.transient(self.root)
        win.grab_set()
        tk.Label(win, text="ADD A TIME ZONE", bg=BG, fg=WHITE,
                 font=("Segoe UI", 15, "bold")).pack(anchor="w", padx=24, pady=(22, 5))
        tk.Label(win, text="Choose a city / time zone from the list.",
                 bg=BG, fg=MUTED, font=("Segoe UI", 9)).pack(anchor="w", padx=24)
        zones = sorted(available_timezones())
        combo = ttk.Combobox(win, values=zones, state="readonly", style="Dark.TCombobox",
                             font=("Segoe UI", 10))
        combo.pack(fill="x", padx=24, pady=18)
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
        self._button(win, "ADD TO DASHBOARD", add, CYAN, dark_text=True).pack(anchor="e", padx=24)

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
