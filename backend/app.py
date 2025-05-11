from flask import Flask, jsonify, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*"}}, supports_credentials=True)

# In-memory mock DB (replace with real DB integration later)
users = []
photos = []

# In-memory foldered photo storage: {folder_name: [photo_dict, ...]}
photo_folders = {}

@app.route('/')
def index():
    return jsonify({"message": "PhotoPortfolio API is running!"})

@app.route('/api/users', methods=['GET', 'POST'])
def handle_users():
    if request.method == 'GET':
        return jsonify(users)
    elif request.method == 'POST':
        user = request.json
        users.append(user)
        return jsonify(user), 201

@app.route('/api/photos', methods=['GET', 'POST'])
def handle_photos():
    if request.method == 'GET':
        return jsonify(photos)
    elif request.method == 'POST':
        photo = request.json
        photos.append(photo)
        return jsonify(photo), 201

from werkzeug.utils import secure_filename
from google.cloud import storage
import uuid
import sqlite3
import threading

# Set your GCS bucket name
GCS_BUCKET = 'photoportfolio-uploads'

# SQLite setup
DB_PATH = 'metadata.db'
_db_lock = threading.Lock()

def init_db():
    with _db_lock:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS folders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL
        )''')
        c.execute('''CREATE TABLE IF NOT EXISTS photos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            folder TEXT NOT NULL,
            name TEXT NOT NULL,
            url TEXT NOT NULL,
            mimetype TEXT,
            gcs_path TEXT,
            uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )''')
        conn.commit()
        conn.close()

init_db()

def get_gcs_client():
    return storage.Client()

def ensure_bucket_exists():
    client = get_gcs_client()
    bucket = client.bucket(GCS_BUCKET)
    if not bucket.exists():
        bucket = client.create_bucket(GCS_BUCKET, location="us")
        bucket.iam_configuration.uniform_bucket_level_access_enabled = True
        bucket.patch()
        # Make bucket public
        bucket.make_public(future=True)
    return bucket

def upload_to_gcs(file, folder):
    client = get_gcs_client()
    bucket = ensure_bucket_exists()
    filename = secure_filename(file.filename)
    unique_name = f"{uuid.uuid4().hex[:8]}_{filename}"
    blob_path = f"folders/{folder}/{unique_name}"
    blob = bucket.blob(blob_path)
    blob.upload_from_file(file, content_type=file.mimetype)
    # Do not call blob.make_public(); rely on bucket-level IAM for public access
    return {
        'name': filename,
        'url': f'https://storage.googleapis.com/{bucket.name}/{blob_path}',
        'mimetype': file.mimetype,
        'gcs_path': blob_path
    }

def add_folder_to_db(folder):
    with _db_lock:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('INSERT OR IGNORE INTO folders (name) VALUES (?)', (folder,))
        conn.commit()
        conn.close()

def add_photo_to_db(folder, name, url, mimetype, gcs_path):
    with _db_lock:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('''INSERT INTO photos (folder, name, url, mimetype, gcs_path) VALUES (?, ?, ?, ?, ?)''',
                  (folder, name, url, mimetype, gcs_path))
        conn.commit()
        conn.close()

def get_all_folders():
    with _db_lock:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('SELECT name FROM folders')
        folders = [row[0] for row in c.fetchall()]
        conn.close()
        return folders

def get_photos_by_folder():
    with _db_lock:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('SELECT folder, name, url, mimetype FROM photos')
        photos = c.fetchall()
        conn.close()
        folder_dict = {}
        for folder, name, url, mimetype in photos:
            folder_dict.setdefault(folder, []).append({'name': name, 'url': url, 'mimetype': mimetype})
        return folder_dict

def delete_photo_from_db(folder, name):
    with _db_lock:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('SELECT gcs_path FROM photos WHERE folder=? AND name=?', (folder, name))
        row = c.fetchone()
        if row:
            gcs_path = row[0]
            c.execute('DELETE FROM photos WHERE folder=? AND name=?', (folder, name))
            conn.commit()
            conn.close()
            # Delete from GCS
            client = get_gcs_client()
            bucket = client.bucket(GCS_BUCKET)
            blob = bucket.blob(gcs_path)
            blob.delete()
            return True
        conn.close()
        return False

def delete_folder_from_db(folder):
    with _db_lock:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('SELECT gcs_path FROM photos WHERE folder=?', (folder,))
        rows = c.fetchall()
        c.execute('DELETE FROM photos WHERE folder=?', (folder,))
        c.execute('DELETE FROM folders WHERE name=?', (folder,))
        conn.commit()
        conn.close()
        # Delete all blobs in GCS for this folder
        client = get_gcs_client()
        bucket = client.bucket(GCS_BUCKET)
        for (gcs_path,) in rows:
            blob = bucket.blob(gcs_path)
            blob.delete()
        return True

@app.route('/api/upload', methods=['POST'])
def upload_photos():
    import traceback
    try:
        folder = request.form.get('folder')
        files = request.files.getlist('images')
        if not folder or not files:
            return jsonify({'error': 'Folder name and images are required.'}), 400
        folder = secure_filename(folder)
        add_folder_to_db(folder)
        uploaded = []
        for file in files:
            try:
                file.stream.seek(0)
                photo_info = upload_to_gcs(file, folder)
                add_photo_to_db(folder, photo_info['name'], photo_info['url'], photo_info['mimetype'], photo_info['gcs_path'])
                uploaded.append({'name': photo_info['name'], 'url': photo_info['url'], 'mimetype': photo_info['mimetype']})
            except Exception as e:
                print(f"[UPLOAD ERROR] {e}\n{traceback.format_exc()}")
                return jsonify({'error': f'Failed to upload {file.filename}: {str(e)}'}), 500
        return jsonify({'folder': folder, 'uploaded': uploaded, 'folders': get_all_folders()}), 201
    except Exception as e:
        print(f"[UPLOAD ERROR] {e}\n{traceback.format_exc()}")
        return jsonify({'error': f'Upload failed: {str(e)}'}), 500

@app.route('/api/folders', methods=['GET'])
def get_folders():
    # Return folder names and photo metadata (with public URLs)
    return jsonify(get_photos_by_folder())

@app.route('/api/photos/search', methods=['GET'])
def search_photos():
    name = request.args.get('name', '').strip()
    folder = request.args.get('folder', '').strip()
    mimetype = request.args.get('mimetype', '').strip()
    date_from = request.args.get('date_from', '').strip()
    date_to = request.args.get('date_to', '').strip()
    query = "SELECT folder, name, url, mimetype, uploaded_at FROM photos WHERE 1=1"
    params = []
    if name:
        query += " AND name LIKE ?"
        params.append(f"%{name}%")
    if folder:
        query += " AND folder=?"
        params.append(folder)
    if mimetype:
        query += " AND mimetype LIKE ?"
        params.append(f"%{mimetype}%")
    if date_from:
        query += " AND uploaded_at >= ?"
        params.append(date_from)
    if date_to:
        query += " AND uploaded_at <= ?"
        params.append(date_to)
    with _db_lock:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute(query, params)
        rows = c.fetchall()
        conn.close()
    results = [
        {'folder': f, 'name': n, 'url': u, 'mimetype': m, 'uploaded_at': d}
        for f, n, u, m, d in rows
    ]
    return jsonify(results)

@app.route('/api/folders/search', methods=['GET'])
def search_folders():
    name = request.args.get('name', '').strip()
    query = "SELECT name FROM folders WHERE 1=1"
    params = []
    if name:
        query += " AND name LIKE ?"
        params.append(f"%{name}%")
    with _db_lock:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute(query, params)
        rows = c.fetchall()
        conn.close()
    results = [row[0] for row in rows]
    return jsonify(results)

@app.route('/api/folder/<folder>', methods=['DELETE'])
def delete_folder(folder):
    folder = secure_filename(folder)
    success = delete_folder_from_db(folder)
    if success:
        return jsonify({'message': f'Folder {folder} deleted.'}), 200
    else:
        return jsonify({'error': 'Folder not found'}), 404

@app.route('/api/folder/<folder>/<name>', methods=['DELETE'])
def delete_photo(folder, name):
    folder = secure_filename(folder)
    name = secure_filename(name)
    success = delete_photo_from_db(folder, name)
    if success:
        return jsonify({'message': f'Photo {name} deleted from folder {folder}.'}), 200
    else:
        return jsonify({'error': 'Photo not found'}), 404

import os
port = int(os.environ.get('PORT', 8080))
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=port)
