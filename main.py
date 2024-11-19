import tkinter as tk
from tkinter import filedialog, messagebox, ttk, PhotoImage, Label
import os
import sys
import sqlite3
import webbrowser
import matplotlib
from werkzeug.serving import make_server

matplotlib.use('Agg')  # Backend ohne GUI für Webanwendungen
import matplotlib.pyplot as plt
import io
import base64
from flask import Flask, render_template_string, request, jsonify
import threading
import time


# Globale Variablen
PathToApp = ""
Intervall = 10
NeedToLog = []

# FLASK ############################################################################################################

flask_thread = None
flask_server = None  # Variable, um den Flask-Server zu speichern

# Datenbank und Log-Datei beim Start löschen, falls sie existieren
def cleanup_files():
    target_pathDB = os.path.join(PathToApp, "script-output", "production.db")
    target_pathTXT = os.path.join(PathToApp, "script-output", "production_log.txt")
    if os.path.exists(target_pathDB):
        os.remove(target_pathDB)
    if os.path.exists(target_pathTXT):
        os.remove(target_pathTXT)


# Erstellen einer SQLite-Datenbank und einer Tabelle für die Produktion
def create_database():
    target_pathDB = os.path.join(PathToApp, "script-output", "production.db")
    conn = sqlite3.connect(target_pathDB)
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


# Funktion zum Einfügen der Daten aus production_log.txt in die Datenbank
def insert_data_from_log():
    target_pathDB = os.path.join(PathToApp, "script-output", "production.db")
    target_pathTXT = os.path.join(PathToApp, "script-output", "production_log.txt")
    conn = sqlite3.connect(target_pathDB)
    c = conn.cursor()

    # Überprüfen, ob die Datei existiert
    if not os.path.exists(target_pathTXT):
        print("production_log.txt existiert nicht.")
        return

    with open(target_pathTXT, 'r') as file:
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

                # Wenn produced und used beide 0 sind, Eintrag überspringen
                if produced == 0 and used == 0:
                    continue

                c.execute('''
                    INSERT INTO target_pathDB (timestamp, item, produced, used) 
                    VALUES (?, ?, ?, ?)
                ''', (timestamp, item, produced, used))

            except IndexError as e:
                print(f"Error processing line: {line} - {e}")
            except ValueError as e:
                print(f"Error processing values in line: {line} - {e}")

    conn.commit()
    conn.close()


# Funktion zum Aktualisieren der Datenbank mit neuen Log-Einträgen
def update_database():
    target_pathDB = os.path.join(PathToApp, "script-output", "production.db")
    target_pathTXT = os.path.join(PathToApp, "script-output", "production_log.txt")
    conn = sqlite3.connect(target_pathDB)
    c = conn.cursor()

    # Lies die Log-Daten und füge neue Einträge ein, falls vorhanden
    if os.path.exists(target_pathTXT):
        with open(target_pathTXT, 'r') as file:
            for line in file:
                parts = line.strip().split()
                if len(parts) < 3:
                    continue

                timestamp = parts[0].split(':')[1]
                item = parts[1].split('=')[0]
                produced = int(parts[2].split('i:')[1])
                used = int(parts[3].split('o:')[1])

                # Wenn produced und used beide 0 sind, Eintrag überspringen
                if produced == 0 and used == 0:
                    continue

                # Prüfe, ob der Datensatz bereits vorhanden ist
                c.execute('SELECT COUNT(*) FROM production_log WHERE timestamp = ? AND item = ?', (timestamp, item))
                if c.fetchone()[0] == 0:
                    c.execute('''
                        INSERT INTO production_log (timestamp, item, produced, used)
                        VALUES (?, ?, ?, ?)
                    ''', (timestamp, item, produced, used))

    conn.commit()
    conn.close()

# Funktion zum regelmäßigen Löschen der production_log.txt Datei alle 5 Minuten
def cleanup_log_file():
    target_pathTXT = os.path.join(PathToApp, "script-output", "production_log.txt")
    while True:
        time.sleep(300)  # 5 Minuten
        if os.path.exists(target_pathTXT):
            os.remove(target_pathTXT)
            print("production_log.txt wurde gelöscht.")

# Funktion zum Aktualisieren der Daten im Index
def update_index():
    while True:
        update_database()  # Aktualisiere die Datenbank
        time.sleep(1)  # Warte 1 Sekunden

# Flask App für die Weboberfläche
app = Flask(__name__)


# Route zur Anzeige der Produktionsdaten
@app.route('/', methods=['GET', 'POST'])
def index():
    target_pathDB = os.path.join(PathToApp, "script-output", "production.db")

    conn = sqlite3.connect(target_pathDB)
    c = conn.cursor()

    # Dropdown für Item-Namen
    c.execute('SELECT DISTINCT item FROM production_log')
    items = [row[0] for row in c.fetchall()]

    selected_item = request.form.get('item') if request.method == 'POST' else None

    # Nur die aktuellsten Einträge jedes Items abrufen
    c.execute('''
        SELECT id, timestamp, item, produced, used 
        FROM production_log 
        WHERE id IN (
            SELECT MAX(id)
            FROM production_log
            GROUP BY item
        )
        ORDER BY timestamp DESC
    ''')
    data = c.fetchall()

    conn.close()

    # HTML Template mit rot hinterlegtem 'used', falls größer als 'produced'
    # HTML Template mit rot hinterlegtem 'used', falls größer als 'produced'
    html_template = '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Production Log</title>
        <style>
            body { background-color: #1D1D1D; color: #CCCCCC; }
            table { width: 80%; margin-left: auto; margin-right: auto; border-collapse: collapse; }
            th, td { border: 1px solid #444444; padding: 10px; text-align: center; }
            th { background-color: #2E2E2E; color: #F0F0F0; }
            tr:nth-child(even) { background-color: #2A2A2A; }
            tr:nth-child(odd) { background-color: #1E1E1E; }
            .red { background-color: #FF4500; color: white; }
            select { background-color: #333333; color: white; }
        </style>
        <script>
            function fetchGraph(item) {
                fetch(`/fetch_graph?item=${item}`)
                    .then(response => response.json())
                    .then(data => {
                        const imgElement = document.getElementById('graph_img');
                        imgElement.src = 'data:image/png;base64,' + data.graph_url;
                    });
            }

            function fetchTable() {
                fetch(`/fetch_table`)
                    .then(response => response.json())
                    .then(data => {
                        const tableBody = document.getElementById('table_body');
                        tableBody.innerHTML = '';
                        data.forEach(row => {
                            const tr = document.createElement('tr');
                            tr.innerHTML = `
                                <td>${row[0]}</td>
                                <td>${row[1]}</td>
                                <td>${row[2]}</td>
                                <td>${row[3]}</td>
                                <td class="${row[4] > row[3] ? 'red' : ''}">${row[4]}</td>
                            `;
                            tableBody.appendChild(tr);
                        });
                    });
            }

            function autoFetchGraphAndTable() {
                const selectElement = document.getElementById('item');
                fetchGraph(selectElement.value);
                fetchTable();
                setTimeout(autoFetchGraphAndTable, 1000);  // Aktualisierung auf jede Sekunde setzen
            }

            window.onload = autoFetchGraphAndTable;  // Starte die automatische Aktualisierung beim Laden der Seite
        </script>
    </head>
    <body>
        <h1 style="text-align: center;">Production Data</h1>
        <div style="text-align: center;">
            <form method="POST" onsubmit="fetchGraph(document.getElementById('item').value); return false;">
                <label for="item">Select Item:</label>
                <select name="item" id="item" onchange="fetchGraph(this.value)">
                    {% for item in items %}
                    <option value="{{ item }}" {% if item == selected_item %}selected{% endif %}>{{ item }}</option>
                    {% endfor %}
                </select>
                <input type="submit" value="Show Graph">
            </form>
        </div>
        <div style="text-align: center;">
            <img id="graph_img" src="" alt="Graph will be displayed here" style="width:70%; border: 1px solid #555;">
        </div>
        <div style="text-align: center;">
            <h2>Production Data Table</h2>
            <table>
                <thead>
                    <tr>
                        <th>ID</th>
                        <th>Timestamp</th>
                        <th>Item</th>
                        <th>Produced</th>
                        <th>Used</th>
                    </tr>
                </thead>
                <tbody id="table_body">
                    {% for row in data %}
                    <tr>
                        <td>{{ row[0] }}</td>
                        <td>{{ row[1] }}</td>
                        <td>{{ row[2] }}</td>
                        <td>{{ row[3] }}</td>
                        <td class="{% if row[4] > row[3] %}red{% endif %}">{{ row[4] }}</td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
    </body>
    </html>
    '''

    # Stelle sicher, dass `render_template_string(html_template, data=data, items=items, selected_item=selected_item)`
    # in der `index()`-Funktion richtig verwendet wird.

    return render_template_string(html_template, data=data, items=items, selected_item=selected_item)


@app.route('/fetch_graph', methods=['GET'])
def fetch_graph():
    target_pathDB = os.path.join(PathToApp, "script-output", "production.db")

    item = request.args.get('item')

    conn = sqlite3.connect(target_pathDB)
    c = conn.cursor()

    # Die letzten 20 Datenpunkte für das ausgewählte Item abrufen
    c.execute('''
        SELECT timestamp, produced, used 
        FROM production_log 
        WHERE item = ? 
        ORDER BY timestamp DESC 
        LIMIT 20
    ''', (item,))
    item_data = c.fetchall()

    # Die Daten in umgekehrter Reihenfolge anzeigen (damit der aktuellste rechts steht)
    item_data = item_data[::-1]

    timestamps = [row[0] for row in item_data]
    produced_values = [row[1] for row in item_data]
    used_values = [row[2] for row in item_data]

    # Erstelle den Graphen
    plt.figure(figsize=(10, 6))
    plt.plot(timestamps, produced_values, label='Produced', marker='o', color='#1E90FF')  # Blau für Produktion
    plt.plot(timestamps, used_values, label='Used', marker='o', color='#FF4500')  # Rot für Verbrauch
    plt.xlabel('Timestamp', color='white')
    plt.ylabel('Amount', color='white')
    plt.title(f'Production vs. Usage for {item}', color='white')
    plt.grid(True, color='#3A3A3A')  # Dunkle Rasterlinien

    # Legend hinzufügen
    plt.legend()

    plt.xticks(rotation=45, ha='right', color='white')
    plt.yticks(color='white')
    plt.gca().set_facecolor('#282828')  # Dunkler Plot-Hintergrund
    plt.gcf().set_facecolor('#1D1D1D')  # Dunkler allgemeiner Hintergrund

    # Speichere das Bild in einem base64-String, um es direkt in HTML einzubinden
    img = io.BytesIO()
    plt.savefig(img, format='png')
    img.seek(0)
    graph_url = base64.b64encode(img.getvalue()).decode()

    plt.close()
    conn.close()

    return jsonify({'graph_url': graph_url})


@app.route('/fetch_table', methods=['GET'])
def fetch_table():
    target_pathDB = os.path.join(PathToApp, "script-output", "production.db")

    conn = sqlite3.connect(target_pathDB)
    c = conn.cursor()

    # Nur die aktuellsten Einträge jedes Items abrufen
    c.execute('''
        SELECT id, timestamp, item, produced, used 
        FROM production_log 
        WHERE id IN (
            SELECT MAX(id)
            FROM production_log
            GROUP BY item
        )
        ORDER BY timestamp DESC
    ''')
    data = c.fetchall()
    conn.close()

    return jsonify(data)


# GUI ######################################################################################################

def update_control_lua():
    """Updates the control.lua file by replacing the items list and the interval value."""
    # Pfad zur Datei
    target_path = os.path.join(PathToApp, "mods", "production_data_logger", "control.lua")

    if not os.path.exists(target_path):
        messagebox.showerror("Error", f"control.lua not found at {target_path}")
        return

    try:
        with open(target_path, "r") as file:
            content = file.readlines()

        # Aktualisieren der Liste "items"
        updated_content = []
        items_replaced = False
        interval_replaced = False

        for line in content:
            # Ersetzen des items-Blocks
            if "local items = {" in line and not items_replaced:
                items_str = ", ".join(f'"{item}"' for item in NeedToLog)
                updated_content.append(f"local items = {{{items_str}}}\n")
                items_replaced = True
                continue

            # Ersetzen der Tick-Zeile
            if "if event.tick %" in line and not interval_replaced:
                updated_content.append(f"    if event.tick % {Intervall} == 0 then\n")
                interval_replaced = True
                continue

            # Alle anderen Zeilen unverändert hinzufügen
            updated_content.append(line)

        # Datei schreiben
        with open(target_path, "w") as file:
            file.writelines(updated_content)

        messagebox.showinfo("Success", f"control.lua updated successfully at {target_path}")
    except Exception as e:
        messagebox.showerror("Error", f"Failed to update control.lua: {e}")


def select_path():
    """Select a path and update the PathToApp variable."""
    global PathToApp
    path = filedialog.askdirectory(title="Select Application Path")
    if path:
        PathToApp = path
        path_label.config(text=PathToApp)
        start_button.config(state=tk.NORMAL)

def update_settings():
    """Update settings from the Mod tab."""
    global Intervall, NeedToLog
    try:
        Intervall = int(interval_entry.get()) * 60
        NeedToLog.clear()
        for var, name in checkbox_vars:
            if var.get():
                NeedToLog.append(name)
        update_control_lua()
    except ValueError:
        messagebox.showerror("Error", "Interval must be an integer!")

# if start is pressed main starts (Flask Server)
def toggle_main():
    """Startet oder stoppt die Flask-Anwendung."""
    global flask_thread, flask_server

    if start_button["text"] == "Start":
        # Status auf "Running" setzen
        status_label.config(bg="green", text="Running")

        # Flask-Server vorbereiten
        def run_flask():
            cleanup_files()
            create_database()
            insert_data_from_log()

            # Log-Datei und Datenbankaktualisierung in separaten Threads starten
            threading.Thread(target=cleanup_log_file, daemon=True).start()
            threading.Thread(target=update_index, daemon=True).start()

            # Browser öffnen
            threading.Timer(1, lambda: webbrowser.open("http://127.0.0.1:5000")).start()

            # Flask-Server starten
            try:
                global flask_server
                flask_server = make_server("127.0.0.1", 5000, app)
                flask_server.serve_forever()
            except Exception as e:
                print(f"Error running Flask: {e}")

        # Flask-Server in einem separaten Thread starten
        flask_thread = threading.Thread(target=run_flask, daemon=True)
        flask_thread.start()

        # Button-Text ändern
        start_button.config(text="Stop")
    else:
        # Flask-Thread stoppen
        if flask_server:
            flask_server.shutdown()
            flask_thread.join(timeout=2)
            flask_server = None

        # Status auf "Stopped" setzen
        status_label.config(bg="red", text="Stopped")

        # Button-Text zurücksetzen
        start_button.config(text="Start")

# settings GUI
def open_settings():
    """Open the settings window."""
    def adjust_window_size(event):
        """Passt die Fenstergröße basierend auf dem aktiven Reiter an."""
        current_tab = notebook.index(notebook.select())  # Aktuellen Reiter abrufen
        if current_tab == 0:  # Tab "Path"
            settings_window.geometry("600x150")  # Größe für den Path-Reiter
        elif current_tab == 1:  # Tab "Mod"
            settings_window.geometry("600x800")  # Größe für den Mod-Reiter

    settings_window = tk.Toplevel(root)
    settings_window.title("Settings")
    settings_window.geometry("600x600")  # Initiale Größe für den Mod-Reiter
    settings_window.configure(bg="#1D1D1D")

    # Notebook mit angepasstem Stil
    style = ttk.Style()
    style.theme_use("default")
    style.configure("TNotebook", background="#1D1D1D", borderwidth=0)
    style.configure("TNotebook.Tab", font=("Arial", 14), padding=[10, 10])
    style.map("TNotebook.Tab", background=[("selected", "#333333")], foreground=[("selected", "white")])

    notebook = ttk.Notebook(settings_window)
    notebook.pack(expand=True, fill="both")

    # Event für Reiterwechsel binden
    notebook.bind("<<NotebookTabChanged>>", adjust_window_size)

    # Tab 1: Path
    path_tab = tk.Frame(notebook, bg="#1D1D1D")
    notebook.add(path_tab, text="Path")

    global path_label
    path_label = tk.Label(path_tab, text=PathToApp if PathToApp else "No path selected", bg="#1D1D1D", fg="white", font=("Arial", 12))
    path_label.pack(pady=10)
    select_path_button = tk.Button(path_tab, text="Select Path", command=select_path, font=("Arial", 12), bg="#333333", fg="white")
    select_path_button.pack()

    # Tab 2: Mod
    mod_tab = tk.Frame(notebook, bg="#1D1D1D")
    notebook.add(mod_tab, text="Mod")

    global interval_entry, checkbox_vars
    interval_frame = tk.Frame(mod_tab, bg="#1D1D1D")
    interval_frame.pack(pady=10)

    tk.Label(interval_frame, text="Interval:", bg="#1D1D1D", fg="white", font=("Arial", 12)).pack(side="left")
    interval_entry = tk.Entry(interval_frame, width=5, font=("Arial", 12))
    interval_entry.insert(0, str(Intervall))
    interval_entry.pack(side="left", padx=5)
    tk.Label(interval_frame, text="s", bg="#1D1D1D", fg="white", font=("Arial", 12)).pack(side="left")

    update_button = tk.Button(interval_frame, text="Update", command=update_settings, font=("Arial", 12), bg="#E39827", fg="white")
    update_button.pack(side="left", padx=10)

    tk.Label(interval_frame, text="Note: to take effect the mods needs to reload", bg="#1D1D1D", fg="red", font=("Arial", 12)).pack(pady=20)

    # Checkbox list in zwei Spalten
    checkbox_vars = []
    items = [
        "advanced-circuit", "battery", "coal", "concrete", "copper-cable", "copper-ore", "copper-plate",
        "electronic-circuit", "engine-unit", "explosives", "express-loader", "express-splitter",
        "express-transport-belt", "express-underground-belt", "fast-inserter", "fast-loader", "fast-splitter",
        "fast-transport-belt", "fast-underground-belt", "flying-robot-frame", "inserter", "iron-chest",
        "iron-gear-wheel", "iron-ore", "iron-plate", "iron-stick", "linked-belt", "linked-chest", "loader",
        "logistic-robot", "long-handed-inserter", "nuclear-fuel", "pipe", "pipe-to-ground", "plastic-bar",
        "rocket-fuel", "rocket-part", "solar-panel", "solid-fuel", "splitter", "steel-chest", "steel-plate",
        "stone", "stone-brick", "storage-tank", "sulfur", "transport-belt", "underground-belt", "uranium-235",
        "uranium-238", "uranium-fuel-cell", "uranium-ore", "wood", "wooden-chest"
    ]

    checkbox_frame = tk.Frame(mod_tab, bg="#1D1D1D")
    checkbox_frame.pack(pady=30)

    # Checkboxen in drei Spalten anordnen
    third_index = len(items) // 3
    two_third_index = 2 * third_index

    left_frame = tk.Frame(checkbox_frame, bg="#1D1D1D")
    middle_frame = tk.Frame(checkbox_frame, bg="#1D1D1D")
    right_frame = tk.Frame(checkbox_frame, bg="#1D1D1D")

    # Frames anordnen
    left_frame.pack(side="left", padx=10)
    middle_frame.pack(side="left", padx=10)
    right_frame.pack(side="left", padx=10)

    # Checkboxen gleichmäßig auf die drei Frames verteilen
    for i, item in enumerate(items):
        var = tk.BooleanVar()
        if i < third_index:
            parent_frame = left_frame
        elif i < two_third_index:
            parent_frame = middle_frame
        else:
            parent_frame = right_frame

        checkbox = tk.Checkbutton(
            parent_frame,
            text=item,
            variable=var,
            bg="#1D1D1D",
            fg="white",
            font=("Arial", 10),
            selectcolor="#333333",
            anchor="w"
        )
        checkbox.pack(anchor="w", pady=2)
        checkbox_vars.append((var, item))


# Main window #################################################################################################
root = tk.Tk()
root.title("Factorio Datalogger")
root.geometry("600x250")
root.configure(bg="#1D1D1D")  # Hintergrundfarbe

# Titel mit PNG
# Wenn das Skript als .exe ausgeführt wird, befindet sich die Datei im temporären Ordner
if getattr(sys, 'frozen', False):
    # Wenn das Skript als .exe läuft, wird der Pfad zur .exe-Datei benötigt
    application_path = sys._MEIPASS
    logo_path = os.path.join(application_path, 'logo.png')
else:
    # Wenn das Skript im Entwicklungsmodus läuft
    logo_path = 'logo.png'

logo_image = PhotoImage(file=logo_path)  # Ersetze "logo.png" durch deinen Bildpfad
title_label = Label(root, image=logo_image, bg="#1D1D1D")
title_label.pack(pady=10)

# Buttons and status area
button_frame = tk.Frame(root, bg="#1D1D1D")  # Rahmen mit Hintergrundfarbe
button_frame.pack(pady=40)

# Start Button
start_button = tk.Button(
    button_frame,
    text="Start",
    width=20,
    height=2,  # Höhe für größere Buttons
    bg="#E39827",
    fg="white",
    state=tk.DISABLED,
    command=toggle_main
)
start_button.grid(row=0, column=1, padx=20)

settings_button = tk.Button(
    button_frame,
    text="Settings",
    compound="left",  # Bild und Text kombinieren
    width=20,
    height=2,  # Höhe für größere Buttons
    bg="#333333",
    fg="white",
    command=open_settings
)
settings_button.grid(row=0, column=0, padx=20)

# Status Indicator
status_label = Label(
    button_frame,
    text="Stopped",
    bg="red",
    fg="white",
    width=20,
    height=2,
    anchor="center"
)
status_label.grid(row=0, column=2, padx=20)

# Run the application
root.mainloop()
