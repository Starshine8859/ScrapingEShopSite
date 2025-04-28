import os
import sqlite3
import webbrowser
import tkinter as tk
from playsound import playsound
from collections import defaultdict


# =================== GUI Dashboard ====================

DB_NAME = 'mydata.db'
CHROME_PATH = 'C:/Program Files/Google/Chrome/Application/chrome.exe %s'
ALERT_SOUND = 'ring.mp3'

LIGHT_THEME = {
    "bg": "#f5f5f5",
    "container_bg": "#ffffff",
    "header_bg": "#e1e1e1",
    "row_even": "#ffffff",
    "row_odd": "#f9f9f9",
    "text": "#333333",
    "link": "blue",
    "badge_bg": "#e0e0e0",
    "badge_fg": "#222"
}

DARK_THEME = {
    "bg": "#1e1e1e",
    "container_bg": "#2a2a2a",
    "header_bg": "#3a3a3a",
    "row_even": "#2b2b2b",
    "row_odd": "#1f1f1f",
    "text": "#eeeeee",
    "link": "#4ea3ff",
    "badge_bg": "#444",
    "badge_fg": "#eee"
}

class LinkDashboard(tk.Tk):
    def __init__(self):
        super().__init__()
        self.theme = LIGHT_THEME
        self.rows = {}

        self.title("🛍 Robin's Jean Monitor Dashboard")
        self.geometry("1050x650")
        self.configure(bg=self.theme["bg"])

        self.header = tk.Label(self, text="Robin's Jean Scraper Dashboard", font=("Segoe UI", 16, "bold"),
                               bg=self.theme["bg"], fg=self.theme["text"])
        self.header.pack(pady=(10, 0))

        self.theme_btn = tk.Button(self, text="🌙 Dark Mode", command=self.toggle_theme)
        self.theme_btn.pack(pady=(0, 10))

        self.read_all_btn = tk.Button(self, text="📖 Mark All as Read", command=self.mark_all_as_read)
        self.read_all_btn.pack(pady=(0, 10))

        self.summary_frame = tk.Frame(self, bg=self.theme["bg"])
        self.summary_frame.pack(pady=5)

        self.container = tk.Frame(self, bg=self.theme["container_bg"], padx=10, pady=10, relief="groove", bd=2)
        self.container.pack(fill="both", expand=True, padx=20, pady=10)

        self.canvas = tk.Canvas(self.container, bg=self.theme["container_bg"], highlightthickness=0)
        self.scroll_frame = tk.Frame(self.canvas, bg=self.theme["container_bg"])
        self.scrollbar = tk.Scrollbar(self.container, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.canvas.create_window((0, 0), window=self.scroll_frame, anchor="nw")
        self.scroll_frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

        self.build_table_headers()
        self.check_loop()

    def toggle_theme(self):
        self.theme = DARK_THEME if self.theme == LIGHT_THEME else LIGHT_THEME
        self.update_theme()
        self.theme_btn.config(text="☀️ Light Mode" if self.theme == DARK_THEME else "🌙 Dark Mode")
        self.refresh_table(self.get_status_0_rows())

    def update_theme(self):
        self.configure(bg=self.theme["bg"])
        self.header.config(bg=self.theme["bg"], fg=self.theme["text"])
        self.summary_frame.config(bg=self.theme["bg"])
        self.container.config(bg=self.theme["container_bg"])
        self.canvas.config(bg=self.theme["container_bg"])
        self.scroll_frame.config(bg=self.theme["container_bg"])

    def build_table_headers(self):
        headers = ["Shop", "Item Link"]
        for i, text in enumerate(headers):
            tk.Label(self.scroll_frame, text=text, font=("Segoe UI", 10, "bold"),
                     bg=self.theme["header_bg"], fg=self.theme["text"],
                     padx=10, pady=5, relief="solid", bd=1, anchor="w",
                     width=20 if i == 0 else 100).grid(row=0, column=i, sticky="w")

    def add_row(self, row_num, item_id, shopname, itemlink):
        bg_color = self.theme["row_even"] if row_num % 2 == 0 else self.theme["row_odd"]

        shop_label = tk.Label(self.scroll_frame, text=shopname, font=("Segoe UI", 10),
                              bg=bg_color, fg=self.theme["text"],
                              padx=10, pady=5, relief="solid", bd=1, anchor="w", width=20)
        shop_label.grid(row=row_num, column=0, sticky="w")

        link_label = tk.Label(self.scroll_frame, text=itemlink, font=("Segoe UI", 10),
                              fg=self.theme["link"], bg=bg_color,
                              padx=10, pady=5, relief="solid", bd=1,
                              anchor="w", width=100, cursor="hand2", wraplength=800, justify="left")
        link_label.grid(row=row_num, column=1, sticky="w")
        link_label.bind("<Button-1>", lambda e: self.handle_click(item_id, shop_label, link_label, itemlink))

        self.rows[item_id] = (shop_label, link_label)

    def remove_row(self, item_id):
        for widget in self.rows.get(item_id, []):
            widget.destroy()
        self.rows.pop(item_id, None)

    def refresh_table(self, data):
        for widget in self.scroll_frame.winfo_children()[2:]:
            widget.destroy()
        self.rows.clear()
        self.build_table_headers()
        for i, (item_id, shopname, itemlink) in enumerate(data, start=1):
            self.add_row(i, item_id, shopname, itemlink)
        self.update_summary(data)

    def update_summary(self, data):
        for widget in self.summary_frame.winfo_children():
            widget.destroy()

        counts = defaultdict(int)
        for _, shopname, _ in data:
            counts[shopname] += 1

        if not counts:
            label = tk.Label(self.summary_frame, text="✅ No items with status = 0.",
                             bg=self.theme["bg"], fg=self.theme["text"], font=("Segoe UI", 10, "italic"))
            label.pack()
            return

        tk.Label(self.summary_frame, text="Summary:", bg=self.theme["bg"], fg=self.theme["text"],
                 font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=10)

        row = tk.Frame(self.summary_frame, bg=self.theme["bg"])
        row.pack(pady=5, padx=10, anchor="w")

        for shop, count in counts.items():
            badge = tk.Label(row, text=f"{shop}: {count}", bg=self.theme["badge_bg"], fg=self.theme["badge_fg"],
                             font=("Segoe UI", 10, "bold"), padx=10, pady=4, relief="ridge", bd=1)
            badge.pack(side="left", padx=5)

    def handle_click(self, item_id, shop_widget, link_widget, url):
        self.set_status_to_1(item_id)
        self.remove_row(item_id)
        self.open_link(url)
        self.update_summary(self.get_status_0_rows())

    def set_status_to_1(self, item_id):
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("UPDATE linklist SET status = '1' WHERE id = ?", (item_id,))
        conn.commit()
        conn.close()

    def mark_all_as_read(self):
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("UPDATE linklist SET status = '1' WHERE status = '0'")
        conn.commit()
        conn.close()
        self.refresh_table([])

    def get_status_0_rows(self):
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT id, shopname, itemlink FROM linklist WHERE status = '0'")
        rows = cursor.fetchall()
        conn.close()
        return rows

    def open_link(self, url):
        if os.path.exists(CHROME_PATH.split(' %s')[0]):
            webbrowser.get(CHROME_PATH).open_new(url)
        else:
            webbrowser.open_new(url)

    def play_alert(self):
        if os.path.exists(ALERT_SOUND):
            try:
                playsound(ALERT_SOUND)
            except Exception as e:
                print("Error playing sound:", e)

    def check_loop(self):
        rows = self.get_status_0_rows()
        if rows:
            self.play_alert()
        self.refresh_table(rows)
        self.after(60000, self.check_loop)


if __name__ == "__main__":
    app = LinkDashboard()
    app.mainloop()
