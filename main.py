############################################################################################################
# import                                                                                                   #
############################################################################################################
import os
import sqlite3
import sys
import tkinter as tk
import webbrowser
from pickle import FALSE
from tkinter import filedialog, messagebox, ttk, PhotoImage, Label

import matplotlib
from werkzeug.serving import make_server

matplotlib.use('Agg')
import matplotlib.pyplot as plt
import io
import base64
from flask import Flask, render_template_string, request, jsonify, Response
import threading
import time
import json

############################################################################################################
# globals                                                                                                  #
############################################################################################################
flask_server = None
app = Flask(__name__)
stop_cleanup_thread = False
stop_update_index_thread = False
stop_watchdog_thread = False
cleanup_files_thread_status = None
update_index_thread_status = None
watchdog_thread_status = None
flask_thread = None
db_lock = threading.Lock()
PathToApp = ""
IntervallSeconds = 10
IntervallTicks = 600
NeedToLog = []
browser_started = False

############################################################################################################
# Misc                                                                                                     #
############################################################################################################
def create_control_and_info_files(path):
    control_lua_content = """
    -- control.lua

    script.on_event(defines.events.on_tick, function(event)
        if event.tick % 60 == 0 then
            local force = game.forces["player"] -- "player" ist die Standard-Fraktion
            local production_stats = force.get_item_production_statistics(1)

    local items = {"coal", "copper-plate", "iron-plate"}

            for i = 1, #items do
                local item = items[i]
                local produced = production_stats.get_flow_count{name=item, category="input", precision_index=defines.flow_precision_index.one_minute}
                local used = production_stats.get_flow_count{name=item, category="output", precision_index=defines.flow_precision_index.one_minute}

                -- Schreibe die Produktionsdaten in die Datei
                helpers.write_file("production_log.txt", "t:" .. event.tick .. " " .. item .. "= i:" .. produced .. " o:" .. used .. "\\n", true)

            end

        end
    end)
        """

    info_json_content = {
      "name": "production_data_logger",
      "version": "1.0.0",
      "title": "Production Data Logger",
      "author": "Ben, Lisa, Maverick",
      "description": "Loggt Produktionsdaten und speichert sie in einer Datenbank.",
      "factorio_version": "2.0",
      "dependencies": []
    }


    with open(os.path.join(path, "control.lua"), "w") as control_file:
        control_file.write(control_lua_content)

    with open(os.path.join(path, "info.json"), "w") as info_file:
        json.dump(info_json_content, info_file, indent=4)

    print("control.lua und info.json wurden erstellt.")


def ask_user(target_dir_mod, target_dir_output):
    root = tk.Tk()
    root.withdraw()  # Versteckt das Hauptfenster

    answer = messagebox.askyesno("Datei-Erstellung",
                                 "Die Datei 'control.lua' existiert nicht. Möchten Sie sie erstellen?")
    if answer:
        # Ordnerstruktur erstellen
        os.makedirs(target_dir_mod, exist_ok=True)
        os.makedirs(target_dir_output, exist_ok=True)
        create_control_and_info_files(target_dir_mod)
        messagebox.showinfo("Erfolg", "'control.lua' und 'info.lua' wurden erstellt.")
    else:
        messagebox.showinfo("Programmende", "Das Programm wird beendet.")
        root.destroy()
        exit()


def cleanup_files():
    target_pathDB = os.path.join(PathToApp, "script-output", "production.db")
    target_pathTXT = os.path.join(PathToApp, "script-output", "production_log.txt")

    while is_file_in_use(target_pathDB):
        print(f"Waiting for database file '{target_pathDB}' to be available...")
        time.sleep(1)

    if os.path.exists(target_pathDB):
        try:
            os.remove(target_pathDB)
            print(f"Deleted database file '{target_pathDB}'.")
        except Exception as e:
            print(f"Error deleting database file '{target_pathDB}': {e}")
            return

    while is_file_in_use(target_pathTXT):
        print(f"Waiting for log file '{target_pathTXT}' to be available...")
        time.sleep(1)

    if os.path.exists(target_pathTXT):
        try:
            os.remove(target_pathTXT)
            print(f"Deleted log file '{target_pathTXT}'.")
        except Exception as e:
            print(f"Error deleting log file '{target_pathTXT}': {e}")


def create_database():
    target_pathDB = os.path.join(PathToApp, "script-output", "production.db")
    if os.path.exists(target_pathDB):
        print("production.db exists already.")
        return
    else:
        print("new production.db created.")
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
        return


def is_file_in_use(file_path):
    try:
        with open(file_path, 'a'):
            return False
    except IOError:
        return True


def calculate_cleanup_interval():
    global IntervallSeconds, NeedToLog

    MIN_TIME = 300
    MAX_TIME = 1800
    BASE_TIME = 1800
    WEIGHT_NEED_TO_LOG = 50
    WEIGHT_INTERVAL_SECONDS = 5

    calculated_time = BASE_TIME - (WEIGHT_NEED_TO_LOG * len(NeedToLog)) - (WEIGHT_INTERVAL_SECONDS * IntervallSeconds)

    return max(MIN_TIME, min(MAX_TIME, calculated_time))


def open_browser():
    webbrowser.open("http://127.0.0.1:5000")

############################################################################################################
# Database                                                                                                 #
############################################################################################################
def insert_data_from_log():
    target_pathDB = os.path.join(PathToApp, "script-output", "production.db")
    target_pathTXT = os.path.join(PathToApp, "script-output", "production_log.txt")

    conn = sqlite3.connect(target_pathDB)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS meta_data (
            key TEXT PRIMARY KEY,
            value INTEGER
        )
    ''')
    conn.commit()

    c.execute("SELECT value FROM meta_data WHERE key = 'last_timestamp'")
    result = c.fetchone()
    last_timestamp = result[0] if result else 0

    if not os.path.exists(target_pathTXT):
        print("production_log.txt doesn't exist.")
        return

    with open(target_pathTXT, 'r') as file:
        lines = file.readlines()
        if not lines:
            print("production_log.txt is empty.")
            return
        last_line = lines[-1].strip()
        new_timestamp = int(last_line.split()[0].split(':')[1])

    if new_timestamp < last_timestamp:
        print("Inconsistent timestamp detected. Running cleanup and database creation.")
        conn.close()
        cleanup_files()
        create_database()
        return

    log_entries = {}
    for line in lines:
        try:
            parts = line.strip().split()
            if len(parts) < 3:
                print(f"Skipping invalid line: {line}")
                continue

            timestamp = int(parts[0].split(':')[1])
            item_data = parts[1].split('=')
            item = item_data[0]
            produced = int(parts[2].split('i:')[1])
            used = int(parts[3].split('o:')[1])

            if produced == 0 and used == 0:
                continue

            if item not in log_entries or timestamp > log_entries[item]["timestamp"]:
                log_entries[item] = {
                    "timestamp": timestamp,
                    "produced": produced,
                    "used": used
                }

        except IndexError as e:
            print(f"Error processing line: {line} - {e}")
        except ValueError as e:
            print(f"Error processing values in line: {line} - {e}")

    for item, data in log_entries.items():
        c.execute('''
            INSERT INTO production_log (timestamp, item, produced, used) 
            VALUES (?, ?, ?, ?)
        ''', (data["timestamp"], item, data["produced"], data["used"]))

    c.execute('''
        INSERT OR REPLACE INTO meta_data (key, value) 
        VALUES ('last_timestamp', ?)
    ''', (new_timestamp,))

    conn.commit()
    conn.close()


def update_database():
    target_pathDB = os.path.join(PathToApp, "script-output", "production.db")
    target_pathTXT = os.path.join(PathToApp, "script-output", "production_log.txt")

    conn = sqlite3.connect(target_pathDB)
    c = conn.cursor()

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

                if produced == 0 and used == 0:
                    continue

                c.execute('SELECT COUNT(*) FROM production_log WHERE timestamp = ? AND item = ?', (timestamp, item))
                if c.fetchone()[0] == 0:
                    c.execute('''
                        INSERT INTO production_log (timestamp, item, produced, used)
                        VALUES (?, ?, ?, ?)
                    ''', (timestamp, item, produced, used))

    conn.commit()
    conn.close()
    return


############################################################################################################
# FLASK                                                                                                    #
############################################################################################################
def run_flask():
    global cleanup_files_thread_status, update_index_thread_status, watchdog_thread_status
    global stop_cleanup_thread, stop_update_index_thread, stop_watchdog_thread

    stop_cleanup_thread = False
    stop_update_index_thread = False
    stop_watchdog_thread = False

    cleanup_files()
    create_database()
    insert_data_from_log()

    cleanup_files_thread_status = threading.Thread(target=cleanup_files_thread, daemon=True)
    update_index_thread_status = threading.Thread(target=update_index_thread, daemon=True)
    watchdog_thread_status = threading.Thread(target=watchdog_thread, daemon=True)
    cleanup_files_thread_status.start()
    update_index_thread_status.start()
    watchdog_thread_status.start()

    try:
        global flask_server
        flask_server = make_server("127.0.0.1", 5000, app)
        flask_server.serve_forever()
    except Exception as e:
        print(f"Error running Flask: {e}")


@app.route('/', methods=['GET', 'POST'])
def index():
    global NeedToLog, PathToApp

    target_pathDB = os.path.join(PathToApp, "script-output", "production.db")

    conn = sqlite3.connect(target_pathDB)
    c = conn.cursor()

    items = NeedToLog
    print(f"selectable Items : {items}")

    selected_item = request.form.get('item') if request.method == 'POST' else None

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

    return render_template_string(html_template, data=data, items=items, selected_item=selected_item)


@app.route('/fetch_graph', methods=['GET'])
def fetch_graph():
    target_pathDB = os.path.join(PathToApp, "script-output", "production.db")

    item = request.args.get('item')

    conn = sqlite3.connect(target_pathDB)
    c = conn.cursor()

    c.execute('''
        SELECT timestamp, produced, used 
        FROM production_log 
        WHERE item = ? 
        ORDER BY timestamp DESC 
        LIMIT 20
    ''', (item,))
    item_data = c.fetchall()
    item_data = item_data[::1]

    timestamps = [(-i) * IntervallSeconds for i in range(len(item_data))]
    produced_values = [row[1] for row in item_data]
    used_values = [row[2] for row in item_data]

    plt.figure(figsize=(10, 6))
    plt.plot(timestamps, produced_values, label='Produced', marker='o', color='#1E90FF')
    plt.plot(timestamps, used_values, label='Used', marker='o', color='#FF4500')
    plt.xlabel('Time (s)', color='white')
    plt.ylabel('Amount', color='white')
    plt.title(f'Production vs. Usage for {item}', color='white')
    plt.grid(True, color='#3A3A3A')

    max_value = max(max(produced_values, default=0), max(used_values, default=0))
    plt.ylim(0, max_value + 1)
    plt.legend()

    x_ticks = [i * IntervallSeconds for i in range(-19, 1)]
    x_labels = [f"{t}s" for t in x_ticks]
    plt.xticks(ticks=x_ticks, labels=x_labels, rotation=45, ha='right', color='white')

    plt.yticks(color='white')
    plt.gca().set_facecolor('#282828')
    plt.gcf().set_facecolor('#1D1D1D')

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

############################################################################################################
# Threads                                                                                                  #
############################################################################################################
def cleanup_files_thread():
    global stop_cleanup_thread
    calculated_time = calculate_cleanup_interval()
    while not stop_cleanup_thread:
        try:
            print(f"Running cleanup_files_thread... calculated_time: {calculated_time} seconds")
            time.sleep(calculated_time)
            cleanup_files()
            create_database()
        except Exception as e:
            print(f"Error in cleanup_files_thread: {e}")
            break


def update_index_thread():
    global stop_update_index_thread, IntervallSeconds
    while not stop_update_index_thread:
        try:
            insert_data_from_log()
            update_database()
            time.sleep(IntervallSeconds)
        except Exception as e:
            print(f"Error in update_index_thread: {e}")
            break


def watchdog_thread():
    global cleanup_files_thread_status, update_index_thread_status
    global stop_watchdog_thread

    print("Watchdog started.")
    while not stop_watchdog_thread:
        try:
            if cleanup_files_thread_status is None or not cleanup_files_thread_status.is_alive():
                print("Watchdog: cleanup_files_thread stopped. Restart...")
                cleanup_files_thread_status = threading.Thread(target=cleanup_files_thread, daemon=True)
                cleanup_files_thread_status.start()

            if update_index_thread_status is None or not update_index_thread_status.is_alive():
                print("Watchdog: update_index_thread stopped. Restart...")
                update_index_thread_status = threading.Thread(target=update_index_thread, daemon=True)
                update_index_thread_status.start()

            time.sleep(5)
        except Exception as e:
            print(f"Error in watchdog_thread: {e}")

    print("Watchdog terminated.\n\n\n\n\n\n\n\n\n\n\n\n")


############################################################################################################
# GUI                                                                                                      #
############################################################################################################

def select_path():
    global PathToApp
    path = filedialog.askdirectory(title="Select Application Path")
    if path:
        PathToApp = path
        path_label.config(text=PathToApp)
        start_button.config(state=tk.NORMAL)
        set_start_Intervall()
        update_interval_entry()


def set_start_Intervall():
    global IntervallSeconds, NeedToLog

    target_path_control_lua = os.path.join(PathToApp, "mods", "production_data_logger", "control.lua")
    target_path_output = os.path.join(PathToApp, "script-output")
    target_dir_mod = os.path.dirname(target_path_control_lua)

    if not os.path.exists(target_path_control_lua):
        ask_user(target_dir_mod, target_path_output)

    try:
        with open(target_path_control_lua, "r") as file:
            content = file.readlines()

        current_interval = None
        current_items = []

        for line in content:
            if "if event.tick %" in line:
                current_interval = int(int(line.split("%")[1].split("==")[0].strip()) / 60)
                continue

            if "local items = {" in line:
                items_str = line.split("{")[1].split("}")[0]
                current_items = [item.strip().strip('"') for item in items_str.split(",")]
                continue

        if current_interval is not None:
            IntervallSeconds = current_interval
        else:
            messagebox.showwarning("Warning", "No interval value found in control.lua.")

        if current_items:
            NeedToLog = current_items
            items_message = ", ".join(current_items)
            messagebox.showinfo(
                "Control.lua",
                f"Current Interval: {IntervallSeconds}s\n\nItems:\n{items_message}"
            )
        else:
            messagebox.showinfo(
                "Intervall & Items",
                f"Current Interval: {IntervallSeconds}\n\nNo items found in control.lua."
            )
    except Exception as e:
        messagebox.showerror("Error", f"Failed to read control.lua: {e}")


def update_interval_entry():
    global interval_entry
    interval_entry.delete(0, tk.END)
    interval_entry.insert(0, str(IntervallSeconds))


def update_settings():
    global IntervallTicks, NeedToLog
    try:
        IntervallTicks = int(interval_entry.get()) * 60
        NeedToLog.clear()
        for var, name in checkbox_vars:
            if var.get():
                NeedToLog.append(name)
        update_control_lua()
    except ValueError:
        messagebox.showerror("Error", "Interval must be an integer!")


def update_control_lua():
    target_path_control_lua = os.path.join(PathToApp, "mods", "production_data_logger", "control.lua")

    if not os.path.exists(target_path_control_lua):
        messagebox.showerror("Error", f"control.lua not found at {target_path_control_lua}")
        return

    try:
        with open(target_path_control_lua, "r") as file:
            content = file.readlines()

        updated_content = []
        items_replaced = False
        interval_replaced = False

        for line in content:
            if "local items = {" in line and not items_replaced:
                items_str = ", ".join(f'"{item}"' for item in NeedToLog)
                updated_content.append(f"local items = {{{items_str}}}\n")
                items_replaced = True
                continue

            if "if event.tick %" in line and not interval_replaced:
                updated_content.append(f"    if event.tick % {IntervallTicks} == 0 then\n")
                interval_replaced = True
                continue

            updated_content.append(line)

        with open(target_path_control_lua, "w") as file:
            file.writelines(updated_content)

        messagebox.showinfo("Success", f"control.lua updated successfully at {target_path_control_lua}")
    except Exception as e:
        messagebox.showerror("Error", f"Failed to update control.lua: {e}")


def toggle_main():
    global flask_thread, flask_server, browser_started
    global cleanup_files_thread_status, update_index_thread_status, watchdog_thread_status
    global stop_cleanup_thread, stop_update_index_thread, stop_watchdog_thread

    if start_button["text"] == "Start":
        status_label.config(bg="green", text="Running")

        flask_thread = threading.Thread(target=run_flask, daemon=True)
        flask_thread.start()

        if not browser_started:
            threading.Timer(1, open_browser).start()
            browser_started = True

        start_button.config(text="Stop")

    else:
        stop_cleanup_thread = True
        stop_update_index_thread = True
        stop_watchdog_thread = True

        if flask_server:
            flask_server.shutdown()
            flask_thread.join(timeout=2)
            flask_server = None

        if watchdog_thread_status and watchdog_thread_status.is_alive():
            watchdog_thread_status.join(timeout=2)

        if cleanup_files_thread_status and cleanup_files_thread_status.is_alive():
            cleanup_files_thread_status.join(timeout=2)

        if update_index_thread_status and update_index_thread_status.is_alive():
            update_index_thread_status.join(timeout=2)

        cleanup_files()

        status_label.config(bg="red", text="Stopped")
        start_button.config(text="Start")


def open_settings():
    def adjust_window_size(event):
        current_tab = notebook.index(notebook.select())
        if current_tab == 0:
            settings_window.geometry("600x150")
        elif current_tab == 1:  # Tab "Mod"
            settings_window.geometry("600x800")

    settings_window = tk.Toplevel(root)
    settings_window.title("Settings")
    settings_window.geometry("600x600")
    settings_window.configure(bg="#1D1D1D")

    style = ttk.Style()
    style.theme_use("default")
    style.configure("TNotebook", background="#1D1D1D", borderwidth=0)
    style.configure("TNotebook.Tab", font=("Arial", 14), padding=[10, 10])
    style.map("TNotebook.Tab", background=[("selected", "#333333")], foreground=[("selected", "white")])

    notebook = ttk.Notebook(settings_window)
    notebook.pack(expand=True, fill="both")
    notebook.bind("<<NotebookTabChanged>>", adjust_window_size)

    # _Tab_1_Path_######################################################################################################

    path_tab = tk.Frame(notebook, bg="#1D1D1D")
    notebook.add(path_tab, text="Path")

    global path_label

    path_label = tk.Label(path_tab, text=PathToApp if PathToApp else "No path selected", bg="#1D1D1D", fg="white",
                          font=("Arial", 12))
    path_label.pack(pady=10)

    select_path_button = tk.Button(path_tab, text="Select Path", command=select_path, font=("Arial", 12), bg="#333333",
                                   fg="white")
    select_path_button.pack()

    # _Tab_2_Mod_######################################################################################################

    mod_tab = tk.Frame(notebook, bg="#1D1D1D")
    notebook.add(mod_tab, text="Mod")

    global interval_entry, checkbox_vars

    interval_frame = tk.Frame(mod_tab, bg="#1D1D1D")
    interval_frame.pack(pady=10)

    tk.Label(interval_frame, text="Interval:", bg="#1D1D1D", fg="white", font=("Arial", 12)).pack(side="left")
    interval_entry = tk.Entry(interval_frame, width=5, font=("Arial", 12))
    interval_entry.insert(0, str(IntervallSeconds))
    interval_entry.pack(side="left", padx=5)
    tk.Label(interval_frame, text="s", bg="#1D1D1D", fg="white", font=("Arial", 12)).pack(side="left")

    update_button = tk.Button(interval_frame, text="Update", command=update_settings, font=("Arial", 12), bg="#E39827",
                              fg="white")
    update_button.pack(side="left", padx=10)

    tk.Label(interval_frame, text="Note: to take effect the mods needs to reload", bg="#1D1D1D", fg="red",
             font=("Arial", 12)).pack(pady=20)

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

    third_index = len(items) // 3
    two_third_index = 2 * third_index

    left_frame = tk.Frame(checkbox_frame, bg="#1D1D1D")
    middle_frame = tk.Frame(checkbox_frame, bg="#1D1D1D")
    right_frame = tk.Frame(checkbox_frame, bg="#1D1D1D")

    left_frame.pack(side="left", padx=10)
    middle_frame.pack(side="left", padx=10)
    right_frame.pack(side="left", padx=10)

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

############################################################################################################
# tkinter                                                                                                  #
############################################################################################################

root = tk.Tk()
root.title("Factorio Datalogger")
root.geometry("600x250")
root.configure(bg="#1D1D1D")

# Titel mit PNG
if getattr(sys, 'frozen', False):
    application_path = sys._MEIPASS
    logo_path = os.path.join(application_path, 'logo.png')
else:
    logo_path = 'logo.png'

logo_image = PhotoImage(file=logo_path)
title_label = Label(root, image=logo_image, bg="#1D1D1D")
title_label.pack(pady=10)

button_frame = tk.Frame(root, bg="#1D1D1D")
button_frame.pack(pady=40)
start_button = tk.Button(button_frame, text="Start", width=20, height=2, bg="#E39827", fg="white", state=tk.DISABLED, command=toggle_main)
start_button.grid(row=0, column=1, padx=20)
settings_button = tk.Button(button_frame, text="Settings", compound="left", width=20, height=2, bg="#333333", fg="white", command=open_settings)
settings_button.grid(row=0, column=0, padx=20)
status_label = Label(button_frame, text="Stopped", bg="red", fg="white", width=20, height=2, anchor="center")
status_label.grid(row=0, column=2, padx=20)
open_web_button = tk.Button(root, text="Website öffnen", width=20, bg="#E39827", fg="white", command=open_browser)
open_web_button.pack(pady=10)
root.mainloop()
