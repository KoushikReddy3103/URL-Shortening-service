# URL Shortner using Flask

from flask import Flask, request, jsonify, redirect, render_template
import mysql.connector
from mysql.connector import Error
from datetime import datetime
import string, random

app = Flask(__name__)

# ----------------- MySQL Config ---------------------------
db_config = {
    "host": "localhost",
    "user": "root",
    "password": "password",
    "database": "url_shortener"
}

# ----------------- DB Helper ---------------------------

def get_db_connection():
    try:
        connection = mysql.connector.connect(**db_config)
        return connection
    except Error as e:
        print(f"Error connecting to MySQL: {e}")
        return None


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
def retrieve_original(code):
    entry = ShortURL.query.filter_by(short_code=code).first_or_404()
    return jsonify({
        "id": str(entry.id),
        "url": entry.url,
        "shortCode": entry.short_code,
        "createdAt": entry.created_at.isoformat() + "Z",
        "updatedAt": entry.updated_at.isoformat() + "Z"
    })

@app.route('/shorten/<string:code>', methods=['PUT'])
def update_short_url(code):
    entry = ShortURL.query.filter_by(short_code=code).first_or_404()
    data = request.get_json()
    if not data or 'url' not in data:
        return jsonify({"errors": ["URL is required"]}), 400
    
    url = data['url']
    if not (url.startswith("http://") or url.startswith("https://")):
        return jsonify({"errors": ["URL must be a valid format"]}), 400
    
    entry.url = url
    db.session.commit()
    return jsonify({
        "id": str(entry.id),
        "url": entry.url,
        "shortCode": entry.short_code,
        "createdAt": entry.created_at.isoformat() + "Z",
        "updatedAt": entry.updated_at.isoformat() + "Z"
    }), 200

@app.route('/shorten/<string:code>', methods=['DELETE'])
def delete_short_url(code):
    entry = ShortURL.query.filter_by(short_code=code).first_or_404()
    db.session.delete(entry)
    db.session.commit()
    return ('', 204)

@app.route('/shorten/<string:code>/stats', methods=['GET'])
def get_stats(code):
    entry = ShortURL.query.filter_by(short_code=code).first_or_404()
    return jsonify({
        "id": str(entry.id),
        "url": entry.url,
        "shortCode": entry.short_code,
        "createdAt": entry.created_at.isoformat() + "Z",
        "updatedAt": entry.updated_at.isoformat() + "Z",
        "accessCount": entry.access_count
    })

@app.route('/<string:code>')
def redirect_short_url(code):
    entry = ShortURL.query.filter_by(short_code=code).first_or_404()
    entry.access_count += 1
    db.session.commit()
    return redirect(entry.url, code=302)

if __name__ == '__main__':
    app.run(debug=True)