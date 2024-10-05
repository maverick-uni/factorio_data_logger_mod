import os
import sqlite3
import tkinter as tk
from tkinter import ttk
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import time
from threading import Thread


# Backend Funktionen für die Datenbank und Log-Verarbeitung
def create_database_if_not_exists():
    if not os.path.exists('production.db'):
        conn = sqlite3.connect('production.db')
        c = conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS production_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                item TEXT,
                produced INTEGER,
                used INTEGER
            )
        ''')
        conn.commit()
        conn.close()


def insert_data_from_log(log_path):
    conn = sqlite3.connect('production.db')
    c = conn.cursor()

    if os.path.exists(log_path):
        with open(log_path, 'r') as file:
            for line in file:
                try:
                    parts = line.strip().split()
                    if len(parts) < 3:
                        print(f"Skipping invalid line: {line}")
                        continue

                    timestamp = parts[0].split(':')[1]
                    item_data = parts[1].split('=')
                    item = item_data[0]
                    produced = int(parts[2].split('i:')[1])
                    used = int(parts[3].split('o:')[1])

                    if produced != 0 or used != 0:
                        c.execute('''
                            INSERT INTO production_log (timestamp, item, produced, used) 
                            VALUES (?, ?, ?, ?)
                        ''', (timestamp, item, produced, used))

                except IndexError as e:
                    print(f"Error processing line: {line} - {e}")
                except ValueError as e:
                    print(f"Error processing values in line: {line} - {e}")

    conn.commit()
    conn.close()


def update_database(log_path):
    conn = sqlite3.connect('production.db')
    c = conn.cursor()

    if os.path.exists(log_path):
        with open(log_path, 'r') as file:
            for line in file:
                parts = line.strip().split()
                if len(parts) < 3:
                    continue

                timestamp = parts[0].split(':')[1]
                item = parts[1].split('=')[0]
                produced = int(parts[2].split('i:')[1])
                used = int(parts[3].split('o:')[1])

                if produced != 0 or used != 0:
                    c.execute('SELECT COUNT(*) FROM production_log WHERE timestamp = ? AND item = ?', (timestamp, item))
                    if c.fetchone()[0] == 0:
                        c.execute('''
                            INSERT INTO production_log (timestamp, item, produced, used)
                            VALUES (?, ?, ?, ?)
                        ''', (timestamp, item, produced, used))

    conn.commit()
    conn.close()


def update_index(log_path):
    while True:
        update_database(log_path)  # Aktualisiere die Datenbank
        time.sleep(5)  # Warte 5 Sekunden


# GUI Klasse für Tkinter
class ProductionApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Production Monitoring")

        # Einstellungen für das Hauptfenster
        self.root.geometry("1920x1080")  # Größeres Fenster
        self.root.configure(bg="#313031")  # Hintergrundfarbe

        self.update_rate = 5000  # Standardwert für Update-Rate in ms
        self.graph_update_rate = 5000
        self.log_path = 'production_log.txt'
        self.x_axis_limit = 10  # Standardmäßig werden die letzten 5 Einträge angezeigt

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Treeview", background="#403F40", fieldbackground="#403F40", foreground="white", rowheight=25)
        style.map("Treeview", background=[('selected', '#E39827')])
        style.configure("Treeview.Heading", background="#242324", foreground="white")

        # Tabelle einrichten
        self.table_frame = tk.Frame(self.root, bg="#313031")
        self.table_frame.pack(side="bottom", fill="both", expand=True)
        self.tree = ttk.Treeview(self.table_frame, columns=("Item", "Produced", "Used"), show="headings")
        self.tree.heading("Item", text="Item")
        self.tree.heading("Produced", text="Produced")
        self.tree.heading("Used", text="Used")
        self.tree.pack(fill="both", expand=True)
        # Tabellen-Abtrennung visuell absetzen
        self.tree.tag_configure("oddrow", background="#545354")
        self.tree.tag_configure("evenrow", background="#242324")

        # Oberer Bereich für Graphen
        self.graph_frame = tk.Frame(self.root, bg="#313031")
        self.graph_frame.pack(side="top", fill="x")
        self.graph_canvases = []  # Liste für bis zu 3 Graphen
        for _ in range(3):
            fig, ax = plt.subplots()
            canvas = FigureCanvasTkAgg(fig, master=self.graph_frame)
            canvas.get_tk_widget().pack(side="left", fill="both", expand=True)
            self.graph_canvases.append((fig, ax, canvas))
        # Buttons für Graphen
        self.button_frame = tk.Frame(self.root, bg="#313031")
        self.button_frame.pack(side="left", pady=10)
        self.graph_button1 = tk.Button(self.button_frame, text="Graph 1", command=lambda: self.display_selected_on_graph(0), bg="#E39827", fg="white")
        self.graph_button1.pack(side="left", padx=10)
        self.graph_button2 = tk.Button(self.button_frame, text="Graph 2", command=lambda: self.display_selected_on_graph(1), bg="#E39827", fg="white")
        self.graph_button2.pack(side="left", padx=10)
        self.graph_button3 = tk.Button(self.button_frame, text="Graph 3", command=lambda: self.display_selected_on_graph(2), bg="#E39827", fg="white")
        self.graph_button3.pack(side="left", padx=10)

        # Button für Einstellungen
        self.settings_button = tk.Button(self.root, text="Einstellungen", command=self.open_settings, bg="#313031", fg="white")
        self.settings_button.pack(side="right", pady=5, padx=10)

        # Starte regelmäßiges Update der Tabelle
        self.update_table()

    def update_table(self):
        # Alte Daten entfernen
        for row in self.tree.get_children():
            self.tree.delete(row)

        # Hole die neuesten Einträge aus der Datenbank
        conn = sqlite3.connect('production.db')
        c = conn.cursor()
        c.execute('''
            SELECT item, MAX(produced), MAX(used) 
            FROM production_log 
            GROUP BY item
        ''')
        rows = c.fetchall()
        conn.close()

        for i, row in enumerate(rows):
            item, produced, used = row
            tag = "evenrow" if i % 2 == 0 else "oddrow"
            self.tree.insert("", "end", values=(item, produced, used), tags=(tag,))

            if used > produced:
                # Zeile in dunklerem Rot färben
                self.tree.item(self.tree.get_children()[-1], tags=("red",))

        # Roten Stil setzen
        self.tree.tag_configure("red", background="#A90B0C")  # Dunkleres Rot

        # Nach X Sekunden erneut aktualisieren
        self.root.after(self.update_rate, self.update_table)

    def display_selected_on_graph(self, graph_index):
        selected_item = self.tree.focus()
        if selected_item:
            item_data = self.tree.item(selected_item)["values"]
            if item_data:
                item_name = item_data[0]
                self.show_graph(item_name, graph_index)

    def show_graph(self, item_name, graph_index):
        # Update Graph für einen bestimmten Index (max 3 Graphen)
        fig, ax, canvas = self.graph_canvases[graph_index]

        def update_graph():
            # Daten aktualisieren
            conn = sqlite3.connect('production.db')
            c = conn.cursor()
            c.execute('SELECT timestamp, produced, used FROM production_log WHERE item = ?', (item_name,))
            data = c.fetchall()
            conn.close()

            timestamps = [row[0] for row in data]
            produced = [row[1] for row in data]
            used = [row[2] for row in data]

            ax.clear()
            ax.set_facecolor('black')  # Hintergrundfarbe des Graphen
            ax.grid(color="#1F1E1F")  # Gitter hinzufügen

            # Begrenze die Anzahl der Einträge basierend auf dem Slider-Wert
            if self.x_axis_limit != 0:  # 0 wird verwendet, um alle Einträge anzuzeigen
                timestamps = timestamps[-self.x_axis_limit:]
                produced = produced[-self.x_axis_limit:]
                used = used[-self.x_axis_limit:]

            ax.plot(timestamps, produced, label="Produced", color='blue')
            ax.plot(timestamps, used, label="Used", color='orange')
            ax.legend()
            canvas.draw()

        update_graph()

    def open_settings(self):
        settings_window = tk.Toplevel(self.root)
        settings_window.title("Einstellungen")

        tk.Label(settings_window, text="Update Rate (ms):").pack()
        update_rate_entry = tk.Entry(settings_window)
        update_rate_entry.insert(0, str(self.update_rate))
        update_rate_entry.pack()

        tk.Label(settings_window, text="Graph Update Rate (ms):").pack()
        graph_update_rate_entry = tk.Entry(settings_window)
        graph_update_rate_entry.insert(0, str(self.graph_update_rate))
        graph_update_rate_entry.pack()

        tk.Label(settings_window, text="Log File Path:").pack()
        log_path_entry = tk.Entry(settings_window)
        log_path_entry.insert(0, self.log_path)
        log_path_entry.pack()

        # Slider für die X-Achsen-Beschränkung (zwischen 5 und Alle)
        tk.Label(settings_window, text="Anzahl der X-Achsen-Einträge:").pack()
        x_axis_slider = tk.Scale(settings_window, from_=100, to=0, orient="horizontal", label="Einträge (0=Alle)", command=self.update_x_axis_limit)
        x_axis_slider.set(self.x_axis_limit)  # Setze den Standardwert auf 5
        x_axis_slider.pack()

        def save_settings():
            self.update_rate = int(update_rate_entry.get())
            self.graph_update_rate = int(graph_update_rate_entry.get())
            self.log_path = log_path_entry.get()
            self.x_axis_limit = x_axis_slider.get()
            settings_window.destroy()

        save_button = tk.Button(settings_window, text="Speichern", command=save_settings)
        save_button.pack()

    def update_x_axis_limit(self, value):
        self.x_axis_limit = int(value)  # Aktualisiere den X-Achsen-Wert basierend auf dem Slider


if __name__ == "__main__":
    # Nur neue DB erstellen, wenn noch keine vorhanden ist
    create_database_if_not_exists()

    # Start Tkinter Anwendung
    root = tk.Tk()
    app = ProductionApp(root)

    # Starte Thread für die Datenbankaktualisierung im Hintergrund
    db_thread = Thread(target=update_index, args=('production_log.txt',))
    db_thread.daemon = True
    db_thread.start()

    root.mainloop()
