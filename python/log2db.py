import os
import sqlite3
import matplotlib
matplotlib.use('Agg')  # Backend ohne GUI für Webanwendungen
import matplotlib.pyplot as plt
import io
import base64
from flask import Flask, render_template_string, request, jsonify
import threading
import time

# Ändere das Verzeichnis zu deinem Arbeitsverzeichnis
os.chdir('C:/Users/z004cefs/OneDrive - Siemens AG/Dokumente/GitHub/factorio_data_logger_mod/python')
print("Current working directory:", os.getcwd())

# Datenbank und Log-Datei beim Start löschen, falls sie existieren
def cleanup_files():
    if os.path.exists('production.db'):
        os.remove('production.db')
    if os.path.exists('production_log.txt'):
        os.remove('production_log.txt')

# Erstellen einer SQLite-Datenbank und einer Tabelle für die Produktion
def create_database():
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

# Funktion zum Einfügen der Daten aus production_log.txt in die Datenbank
def insert_data_from_log():
    conn = sqlite3.connect('production.db')
    c = conn.cursor()

    # Überprüfen, ob die Datei existiert
    if not os.path.exists('production_log.txt'):
        print("production_log.txt existiert nicht.")
        return

    with open('production_log.txt', 'r') as file:
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

# Funktion zum Aktualisieren der Datenbank mit neuen Log-Einträgen
def update_database():
    conn = sqlite3.connect('production.db')
    c = conn.cursor()

    # Lies die Log-Daten und füge neue Einträge ein, falls vorhanden
    if os.path.exists('production_log.txt'):
        with open('production_log.txt', 'r') as file:
            for line in file:
                parts = line.strip().split()
                if len(parts) < 3:
                    continue

                timestamp = parts[0].split(':')[1]
                item = parts[1].split('=')[0]
                produced = int(parts[2].split('i:')[1])
                used = int(parts[3].split('o:')[1])

                # Prüfe, ob der Datensatz bereits vorhanden ist
                c.execute('SELECT COUNT(*) FROM production_log WHERE timestamp = ? AND item = ?', (timestamp, item))
                if c.fetchone()[0] == 0:
                    c.execute('''
                        INSERT INTO production_log (timestamp, item, produced, used)
                        VALUES (?, ?, ?, ?)
                    ''', (timestamp, item, produced, used))

    conn.commit()
    conn.close()

# Funktion zum Aktualisieren der Daten im Index
def update_index():
    while True:
        update_database()  # Aktualisiere die Datenbank
        time.sleep(5)  # Warte 5 Sekunden

# Flask App für die Weboberfläche
app = Flask(__name__)

# Route zur Anzeige der Produktionsdaten
@app.route('/', methods=['GET', 'POST'])
def index():
    conn = sqlite3.connect('production.db')
    c = conn.cursor()

    # Dropdown für Item-Namen
    c.execute('SELECT DISTINCT item FROM production_log')
    items = [row[0] for row in c.fetchall()]

    selected_item = request.form.get('item') if request.method == 'POST' else None

    # Gesamte Produktionsdaten abrufen
    c.execute('SELECT * FROM production_log ORDER BY timestamp DESC')
    data = c.fetchall()

    conn.close()

    # HTML Template mit rot hinterlegtem 'used', falls größer als 'produced'
    html_template = '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Production Log</title>
        <style>
            .red { background-color: #ffcccc; }
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
                setTimeout(autoFetchGraphAndTable, 5000);  // Alle 5 Sekunden aktualisieren
            }

            window.onload = autoFetchGraphAndTable;  // Starte die automatische Aktualisierung beim Laden der Seite
        </script>
    </head>
    <body>
        <h1>Production Data</h1>

        <!-- Dropdown zur Auswahl eines Items -->
        <form method="POST" onsubmit="fetchGraph(document.getElementById('item').value); return false;">
            <label for="item">Select Item:</label>
            <select name="item" id="item" onchange="fetchGraph(this.value)">
                {% for item in items %}
                <option value="{{ item }}" {% if item == selected_item %}selected{% endif %}>{{ item }}</option>
                {% endfor %}
            </select>
            <input type="submit" value="Show Graph">
        </form>

        <h2>Graph for {{ selected_item }}</h2>
        <img id="graph_img" src="" alt="Graph will be displayed here">

        <h2>Production Data Table</h2>
        <table border="1">
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
    </body>
    </html>
    '''
    
    return render_template_string(html_template, data=data, items=items, selected_item=selected_item)

@app.route('/fetch_graph', methods=['GET'])
def fetch_graph():
    item = request.args.get('item')

    conn = sqlite3.connect('production.db')
    c = conn.cursor()

    # Daten für das ausgewählte Item abrufen
    c.execute('SELECT timestamp, produced, used FROM production_log WHERE item = ? ORDER BY timestamp', (item,))
    item_data = c.fetchall()

    # Erstelle einen Graphen für das ausgewählte Item
    timestamps = [row[0] for row in item_data]
    produced_values = [row[1] for row in item_data]
    used_values = [row[2] for row in item_data]

    plt.figure(figsize=(10, 6))
    plt.plot(timestamps, produced_values, label='Produced', marker='o', color='blue')
    plt.plot(timestamps, used_values, label='Used', marker='o', color='red')
    plt.xlabel('Timestamp')
    plt.ylabel('Amount')
    plt.title(f'Production vs. Usage for {item}')
    plt.legend()

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
    conn = sqlite3.connect('production.db')
    c = conn.cursor()

    # Gesamte Produktionsdaten abrufen
    c.execute('SELECT * FROM production_log ORDER BY timestamp DESC')
    data = c.fetchall()
    conn.close()
    
    return jsonify(data)

if __name__ == '__main__':
    # Datenbank und Log-Datei beim Start löschen
    cleanup_files()
    
    # Datenbank erstellen und initiale Daten einfügen
    create_database()
    insert_data_from_log()

    # Starte den Thread zum Aktualisieren der Datenbank
    threading.Thread(target=update_index, daemon=True).start()

    # Flask-App starten
    app.run(debug=True)
