# URL Shortner using Flask

from flask import Flask, request, jsonify, redirect, render_template
import mysql.connector
from mysql.connector import Error
from datetime import datetime
import string, random
import time
import os


app = Flask(__name__)

# ----------------- MySQL Config ---------------------------
DB_CONFIG = {
    "host": os.getenv("DB_HOST", "db"),
    "user": os.getenv("DB_USER", "flaskuser"),
    "password": os.getenv("DB_PASSWORD", "flaskpass"),
    "database": "url_shortener",
    "port": 3307
}

# ----------------- Database Setup ---------------------------

def get_db_connection(retries=5, delay=5):
    for i in range(retries):
        try:
            connection = mysql.connector.connect(**DB_CONFIG)
            if connection.is_connected():
                return connection
        except Exception as e:
            print(f"DB connection failed ({i+1}/{retries}): {e}")
            time.sleep(delay)
    raise Exception("Could not connect to DB after retries")

def init_db():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS short_urls (
            id INT AUTO_INCREMENT PRIMARY KEY,
            url TEXT NOT NULL,
            short_code VARCHAR(10) UNIQUE NOT NULL,
            access_count INT DEFAULT 0,
            created_at DATETIME,
            updated_at DATETIME
        )               
        """)
        conn.commit()
        cursor.close()
        conn.close()
        print("Database initialized successfully.")
    except Error as e:
        print("Error initializing DB:", e)

def generate_short_code(length=6):
    chars = string.ascii_letters + string.digits
    return ''.join(random.choice(chars) for _ in range(length))    

# -------------- FRONTEND ROUTES -----------------
@app.route('/')
def home():
    return render_template("index.html") # create, update, delete

@app.route('/stats')
def stats_page():
    return render_template("stats.html")

# -------------- API ROUTES ----------------- 

@app.route('/shorten', methods=['POST'])
def create_short_url():
    data = request.get_json()
    if not data or 'url' not in data:
        return jsonify({"errors": ["URL is required!"]}), 400

    url = data['url']
    if not (url.startswith('http://') or url.startswith('https://')):
        return jsonify({"errors": ["URL must be a valid format"]}), 400
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # generate unique short_code
    short_code = generate_short_code()
    cursor.execute("SELECT id FROM short_urls WHERE short_code = %s", (short_code,))
    while cursor.fetchone():
        short_code = generate_short_code()
    
    timestamp = datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d %H:%M:%S')

    cursor.execute(
        "INSERT INTO short_urls (url, short_code, created_at, updated_at, access_count) VALUES (%s, %s, %s, %s, %s)",
        (url, short_code, timestamp, timestamp, 0)
    )
    conn.commit()
    new_id = cursor.lastrowid

    cursor.execute("SELECT * FROM short_urls WHERE id = %s", (new_id,))
    record = cursor.fetchone()

    cursor.close()
    conn.close()

    return jsonify(record), 201

@app.route('/shorten/<string:code>', methods=['GET'])
def get_url(code):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM short_urls WHERE short_code = %s", (code,))
    record = cursor.fetchone()
    cursor.close()
    conn.close()
    if not record:
        return jsonify({"error": "Not found"}), 404
    
    return jsonify(record)

@app.route('/shorten/<string:code>', methods=['PUT'])
def update_url(code):
    data = request.get_json()
    if not data or 'url' not in data:
        return jsonify({"errors": ["URL is required"]}), 400
    
    url = data['url']
    if not (url.startswith("http://") or url.startswith("https://")):
        return jsonify({"errors": ["URL must be a valid format"]}), 400
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT * FROM short_urls WHERE short_code = %s", (code,))
    record = cursor.fetchone()
    if not record:
        cursor.close()
        conn.close()
        return jsonify({"error": "Not found"}), 404

    timestamp = datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
    cursor.execute(
        "UPDATE short_urls SET url = %s, updated_at = %s WHERE short_code = %s",
        (url, timestamp, code)
    )
    conn.commit()

    cursor.execute("SELECT * FROM short_urls WHERE short_code = %s", (code,))
    updated = cursor.fetchone()

    cursor.close()
    conn.close()

    return jsonify(updated), 200



@app.route('/shorten/<string:code>', methods=['DELETE'])
def delete_url(code):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM short_urls WHERE short_code = %s", (code,))
    conn.commit()
    affected = cursor.rowcount
    cursor.close()
    conn.close()

    if affected == 0:
        return jsonify({"error": "Not found"}), 404

    return ("", 204)

@app.route('/shorten/<string:code>/stats', methods=['GET'])
def stats_url(code):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM short_urls WHERE short_code = %s", (code,))
    record = cursor.fetchone()
    cursor.close()
    conn.close()
    if not record:
        return jsonify({"error": "Not found"}), 404
    
    return jsonify(record)

@app.route('/<string:code>')
def redirect_short(code):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM short_urls WHERE short_code = %s", (code,))
    record = cursor.fetchone()

    if not record:
        cursor.close()
        conn.close()
        return jsonify({"error": "Not found"}), 404
    
    cursor.execute("UPDATE short_urls SET access_count = access_count + 1 WHERE short_code = %s", (code,))
    conn.commit()
    cursor.close()
    conn.close()

    return redirect(record["url"], code=302)

# --------------------- DB INIT (run once) -------------------------

if __name__ == '__main__':
    init_db()
    app.run(debug=True)