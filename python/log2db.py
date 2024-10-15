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

# Datenbank und Log-Datei beim Start löschen, falls sie existieren
def cleanup_files():
    if os.path.exists('production.db'):
        os.remove('production.db')
    if os.path.exists('production_log.txt'):
        os.remove('production_log.txt')

def wait_for_file(file_path, retries=5, delay=2):
    """
    Warten auf die Existenz der Datei mit wiederholten Versuchen.
    :param file_path: Pfad zur Datei
    :param retries: Anzahl der Wiederholungsversuche
    :param delay: Wartezeit zwischen den Versuchen (in Sekunden)
    """
    for _ in range(retries):
        if os.path.exists(file_path):
            return True
        print(f"Warte auf Datei: {file_path}. Versuche erneut in {delay} Sekunden.")
        time.sleep(delay)
    return False


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
    file_path = 'production_log.txt'
    if wait_for_file(file_path):  # Warten, bis die Datei existiert
        conn = sqlite3.connect('production.db')
        c = conn.cursor()
        # Datei existiert, weiter mit dem Einfügen der Daten
        with open(file_path, 'r') as file:
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
    else:
        print(f"Datei {file_path} wurde nach mehreren Versuchen nicht gefunden.")


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

                # Überprüfen, wie viele verschiedene Timestamps vorhanden sind
                c.execute('SELECT COUNT(DISTINCT timestamp) FROM production_log')
                timestamp_count = c.fetchone()[0]

                if timestamp_count >= 6:
                    # Finde den kleinsten Timestamp
                    c.execute('SELECT MIN(timestamp) FROM production_log')
                    min_timestamp = c.fetchone()[0]

                    # Lösche alle Einträge mit dem kleinsten Timestamp
                    c.execute('DELETE FROM production_log WHERE timestamp = ?', (min_timestamp,))

                # Füge den neuen Eintrag hinzu
                c.execute('INSERT INTO production_log (timestamp, item, produced, used) VALUES (?, ?, ?, ?)',
                          (timestamp, item, produced, used))



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
    <title>Produktionsprotokoll</title>
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

        function fetchTable(item = '') {
            fetch(`/fetch_table?item=${item}`)
                .then(response => response.json())
                .then(data => {
                    const tableBody = document.getElementById('table_body');
                    tableBody.innerHTML = '';
                    data.forEach(row => {
                        const tr = document.createElement('tr');
                        const available = row[3] - row[4];  // Verfügbarer Bestand berechnen
                        tr.innerHTML = `
                            <td>${row[0]}</td>
                            <td>${row[1]}</td>
                            <td>${row[2]}</td>
                            <td>${row[3]}</td>
                            <td class="${row[4] > row[3] ? 'red' : ''}">${row[4]}</td>
                            <td>${available}</td>  <!-- Verfügbarer Bestand anzeigen -->
                        `;
                        tableBody.appendChild(tr);
                    });
                });
        }

        function autoFetchGraphAndTable() {
            const selectElementGraph = document.getElementById('item_graph');
            const selectElementTable = document.getElementById('item_table');
            fetchGraph(selectElementGraph.value);
            fetchTable(selectElementTable.value);
            setTimeout(autoFetchGraphAndTable, 5000);  // Alle 5 Sekunden aktualisieren
        }

        window.onload = autoFetchGraphAndTable;  // Starte die automatische Aktualisierung beim Laden der Seite
    </script>
</head>
<body>
    <h1>Produktionsdaten</h1>
    <!-- Dropdown zur Auswahl eines Items für den Graph -->
    <form method="POST" onsubmit="fetchGraph(document.getElementById('item_graph').value); fetchTable(document.getElementById('item_table').value); return false;">
        <label for="item_graph">Wähle ein Item für den Graphen:</label>
        <select name="item_graph" id="item_graph" onchange="fetchGraph(this.value);">
            <option value="">Alle</option>  <!-- Option für alle Items -->
            {% for item in items %}
            <option value="{{ item }}" {% if item == selected_item %}selected{% endif %}>{{ item }}</option>
            {% endfor %}
        </select>
        <input type="submit" value="Zeige Graph">
    </form>
    <h2>Graph für {{ selected_item }}</h2>
    <img id="graph_img" src="" alt="Graph wird hier angezeigt">

    <!-- Dropdown zur Auswahl eines Items für die Produktionstabelle -->
    <form method="POST" onsubmit="fetchTable(document.getElementById('item_table').value); return false;">
        <label for="item_table">Wähle ein Item für die Tabelle:</label>
        <select name="item_table" id="item_table" onchange="fetchTable(this.value);">
            <option value="">Alle</option>  <!-- Option für alle Items -->
            {% for item in items %}
            <option value="{{ item }}" {% if item == selected_item %}selected{% endif %}>{{ item }}</option>
            {% endfor %}
        </select>
        <input type="submit" value="Zeige Tabelle">
    </form>
    <h2>Produktionsdatentabelle</h2>
    <table border="1">
        <thead>
            <tr>
                <th>ID</th>
                <th>Zeitstempel</th>
                <th>Item</th>
                <th>Produziert</th>
                <th>Verbraucht</th>
                <th>Verfügbar</th>  <!-- Neue Spalte für verfügbaren Bestand -->
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
                <td>{{ row[3] - row[4] }}</td>  <!-- Verfügbarer Bestand anzeigen -->
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
    item = request.args.get('item', '')  # Abrufen des ausgewählten Items
    conn = sqlite3.connect('production.db')
    c = conn.cursor()
    # Daten filtern basierend auf dem ausgewählten Item
    if item:
        c.execute('SELECT * FROM production_log WHERE item = ? ORDER BY timestamp DESC', (item,))
    else:
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