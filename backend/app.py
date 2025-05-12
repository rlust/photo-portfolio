from flask import Flask, jsonify, request
from flask_cors import CORS
from search import search_bp

app = Flask(__name__)
ALLOWED_ORIGINS = [
    "https://photo-portfolio-cloud.windsurf.build",
    "https://photoportfolio-app.windsurf.build",
    "https://photo-frontend-839093975626.us-central1.run.app"
]
CORS(app, origins=ALLOWED_ORIGINS, resources={r"/api/*": {"origins": ALLOWED_ORIGINS}}, allow_headers='Content-Type', expose_headers='Content-Type', supports_credentials=True)
app.config["MAX_CONTENT_LENGTH"] = 32 * 1024 * 1024  # 32 MB limit (Cloud Run/App Engine max)

def get_cors_origin():
    origin = request.headers.get('Origin')
    if origin in ALLOWED_ORIGINS:
        return origin
    return ALLOWED_ORIGINS[0]  # fallback to first allowed origin

app.register_blueprint(search_bp)

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

# Print DB path on startup
DB_PATH = os.environ.get('DB_PATH', 'metadata.db')
print(f"[PHOTO-PORTFOLIO] Using DB file: {os.path.abspath(DB_PATH)}")
logging.info(f"Using DB file: {os.path.abspath(DB_PATH)}")

from PIL import Image
import exifread
from geopy.geocoders import Nominatim
from google.cloud import vision
import io

# --- Location Tag Utilities ---
def extract_gps_from_exif(image_path):
    try:
        with open(image_path, 'rb') as f:
            tags = exifread.process_file(f, details=False)
        gps_lat = tags.get('GPS GPSLatitude')
        gps_lat_ref = tags.get('GPS GPSLatitudeRef')
        gps_lon = tags.get('GPS GPSLongitude')
        gps_lon_ref = tags.get('GPS GPSLongitudeRef')
        if gps_lat and gps_lat_ref and gps_lon and gps_lon_ref:
            def _dms_to_deg(dms, ref):
                d = float(dms.values[0].num) / float(dms.values[0].den)
                m = float(dms.values[1].num) / float(dms.values[1].den)
                s = float(dms.values[2].num) / float(dms.values[2].den)
                deg = d + m/60.0 + s/3600.0
                if ref.values[0] in ['S', 'W']:
                    deg = -deg
                return deg
            lat = _dms_to_deg(gps_lat, gps_lat_ref)
            lon = _dms_to_deg(gps_lon, gps_lon_ref)
            return lat, lon
    except Exception:
        pass
    return None

def reverse_geocode(lat, lon):
    try:
        geolocator = Nominatim(user_agent="photoportfolio")
        location = geolocator.reverse((lat, lon), language='en', timeout=10)
        return location.address if location else None
    except Exception:
        return None

def google_vision_landmark(image_bytes):
    try:
        client = vision.ImageAnnotatorClient()
        image = vision.Image(content=image_bytes)
        response = client.landmark_detection(image=image)
        landmarks = response.landmark_annotations
        if landmarks:
            return landmarks[0].description
    except Exception:
        pass
    return None

@app.route('/api/annotate-locations', methods=['POST'])
def annotate_locations():
    print(f"[PHOTO-PORTFOLIO] [annotate_locations] Using DB file: {os.path.abspath(DB_PATH)}")
    logging.info(f"[annotate_locations] Using DB file: {os.path.abspath(DB_PATH)}")
    """
    Batch annotate photos in the DB with location_tag using EXIF GPS (if available),
    else Google Vision landmark detection. Processes only a batch per call.
    Query params:
      - batch_size (default 10)
      - offset (default 0)
    Returns: progress info and how many annotated in this batch.
    """
    import tempfile, os, requests
    batch_size = int(request.args.get('batch_size', 10))
    offset = int(request.args.get('offset', 0))
    updated = 0
    with _db_lock:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        # Count total untagged
        c.execute('SELECT COUNT(*) FROM photos WHERE location_tag IS NULL OR location_tag = "" OR location_tag = "null"')
        total_untagged = c.fetchone()[0]
        # Get batch
        c.execute('SELECT id, url FROM photos WHERE location_tag IS NULL OR location_tag = "" OR location_tag = "null" LIMIT ? OFFSET ?', (batch_size, offset))
        photos = c.fetchall()
        for photo_id, url in photos:
            try:
                resp = requests.get(url, timeout=10)
                if resp.status_code != 200:
                    continue
                with tempfile.NamedTemporaryFile(delete=False) as tmp:
                    tmp.write(resp.content)
                    tmp_path = tmp.name
                # 1. Try EXIF GPS
                gps = extract_gps_from_exif(tmp_path)
                tag = None
                if gps:
                    lat, lon = gps
                    tag = reverse_geocode(lat, lon)
                # 2. If no GPS, try Vision API
                if not tag:
                    tag = google_vision_landmark(resp.content)
                # 3. If found, update DB
                if tag:
                    c.execute('UPDATE photos SET location_tag=? WHERE id=?', (tag, photo_id))
                    updated += 1
                os.remove(tmp_path)
            except Exception:
                continue
        # Count remaining after this batch
        c.execute('SELECT COUNT(*) FROM photos WHERE location_tag IS NULL OR location_tag = ""')
        remaining = c.fetchone()[0]
        conn.commit()
        conn.close()
    return jsonify({
        'status': 'ok',
        'batch_size': batch_size,
        'offset': offset,
        'updated_this_batch': updated,
        'remaining_untagged': remaining,
        'total_untagged': total_untagged
    })

@app.route('/api/reindex-gcs', methods=['POST'])
def reindex_gcs():
    print(f"[PHOTO-PORTFOLIO] [reindex_gcs] Using DB file: {os.path.abspath(DB_PATH)}")
    logging.info(f"[reindex_gcs] Using DB file: {os.path.abspath(DB_PATH)}")
    try:
        client = get_gcs_client()
        bucket = client.bucket(GCS_BUCKET)
        blobs = bucket.list_blobs(prefix='folders/')
        folders = set()
        file_count = 0
        for blob in blobs:
            # Skip the root 'folders/' blob if it exists
            if blob.name == 'folders/':
                continue
            # Parse folder and filename from blob name
            parts = blob.name.split('/')
            if len(parts) >= 2:
                folder = parts[1]
                if folder:
                    folders.add(folder)
                # If this is a file (not a directory marker), add photo
                if len(parts) >= 3 and not blob.name.endswith('/'):
                    filename = '/'.join(parts[2:])  # Support nested files
                    url = f'https://storage.googleapis.com/{bucket.name}/{blob.name}'
                    mimetype = blob.content_type or 'image/jpeg'
                    add_folder_to_db(folder)
                    add_photo_to_db(folder, filename, url, mimetype, blob.name)
                    file_count += 1
        # Add all folders found, even if empty
        for folder in folders:
            add_folder_to_db(folder)
        return jsonify({'status': 'ok', 'folders': list(folders), 'indexed_files': file_count}), 200
    except Exception as e:
        import traceback
        return jsonify({'error': str(e), 'trace': traceback.format_exc()}), 500

# Set your GCS bucket name
GCS_BUCKET = 'photoportfolio-uploads'

# SQLite setup
_db_lock = threading.Lock()

def init_db():
    print(f"[PHOTO-PORTFOLIO] [init_db] Using DB file: {os.path.abspath(DB_PATH)}")
    logging.info(f"[init_db] Using DB file: {os.path.abspath(DB_PATH)}")
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
        # Migration: add location_tag if not exists
        c.execute("PRAGMA table_info(photos)")
        columns = [row[1] for row in c.fetchall()]
        if 'location_tag' not in columns:
            c.execute('ALTER TABLE photos ADD COLUMN location_tag TEXT')
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
    print(f"[PHOTO-PORTFOLIO] [add_folder_to_db] Using DB file: {os.path.abspath(DB_PATH)}")
    logging.info(f"[add_folder_to_db] Using DB file: {os.path.abspath(DB_PATH)}")
    with _db_lock:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('INSERT OR IGNORE INTO folders (name) VALUES (?)', (folder,))
        conn.commit()
        conn.close()

def add_photo_to_db(folder, name, url, mimetype, gcs_path, location_tag=None):
    print(f"[PHOTO-PORTFOLIO] [add_photo_to_db] Using DB file: {os.path.abspath(DB_PATH)}")
    logging.info(f"[add_photo_to_db] Using DB file: {os.path.abspath(DB_PATH)}")
    with _db_lock:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        # Insert with location_tag if provided
        if location_tag is not None:
            c.execute('''INSERT INTO photos (folder, name, url, mimetype, gcs_path, location_tag) VALUES (?, ?, ?, ?, ?, ?)''',
                      (folder, name, url, mimetype, gcs_path, location_tag))
        else:
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
        c.execute('SELECT folder, name, url, mimetype, location_tag FROM photos')
        photos = c.fetchall()
        conn.close()
        folder_dict = {}
        for folder, name, url, mimetype, location_tag in photos:
            folder_dict.setdefault(folder, []).append({
                'name': name,
                'url': url,
                'mimetype': mimetype,
                'location_tag': location_tag
            })
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

from flask import make_response

@app.errorhandler(413)
def handle_413(e):
    response = make_response(jsonify({'error': 'Request too large. Each batch must be under 32MB.'}), 413)
    response.headers['Access-Control-Allow-Origin'] = get_cors_origin()
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    response.headers['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
    return response

@app.route('/api/upload', methods=['POST'])
def upload_photos():
    import traceback
    folder = request.form.get('folder')
    files = request.files.getlist('images')
    if not folder or not files:
        resp = make_response(jsonify({'error': 'Folder name and images are required.'}), 400)
        resp.headers['Access-Control-Allow-Origin'] = get_cors_origin()
        resp.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS, DELETE'
        resp.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
        return resp
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
            # Continue uploading other files, but log error
    resp = make_response(jsonify({'folder': folder, 'uploaded': uploaded, 'folders': get_all_folders()}), 201)
    resp.headers['Access-Control-Allow-Origin'] = get_cors_origin()
    resp.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS, DELETE'
    resp.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
    return resp

@app.route('/api/folders', methods=['GET', 'OPTIONS'])
def get_folders():
    if request.method == 'OPTIONS':
        # Preflight CORS
        resp = make_response('', 204)
        resp.headers['Access-Control-Allow-Origin'] = get_cors_origin()
        resp.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS, DELETE'
        resp.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
        return resp
    try:
        resp = make_response(jsonify(get_photos_by_folder()))
        resp.headers['Access-Control-Allow-Origin'] = get_cors_origin()
        resp.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS, DELETE'
        resp.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
        return resp
    except Exception as e:
        resp = make_response(jsonify({'error': str(e)}), 500)
        resp.headers['Access-Control-Allow-Origin'] = get_cors_origin()
        resp.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS, DELETE'
        resp.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
        return resp

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

# --- Direct-to-GCS Upload Endpoints ---
from flask import make_response

@app.route('/api/signed-url', methods=['POST', 'OPTIONS'])
def get_signed_url():
    if request.method == 'OPTIONS':
        # CORS preflight request
        return '', 200
    import traceback
    try:
        data = request.get_json()
        filename = data.get('filename')
        content_type = data.get('contentType')
        folder = secure_filename(data.get('folder', 'uploads'))
        if not filename or not content_type or not folder:
            resp = make_response(jsonify({'error': 'filename, contentType, and folder are required'}), 400)
            resp.headers['Access-Control-Allow-Origin'] = get_cors_origin()
            resp.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS, DELETE'
            resp.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
            return resp
        unique_name = f"{uuid.uuid4().hex}_{secure_filename(filename)}"
        gcs_path = f"folders/{folder}/{unique_name}"
        client = get_gcs_client()
        bucket = client.bucket(GCS_BUCKET)
        blob = bucket.blob(gcs_path)
        url = blob.generate_signed_url(
            version="v4",
            expiration=datetime.timedelta(minutes=15),
            method="PUT",
            content_type=content_type,
        )
        public_url = f"https://storage.googleapis.com/{GCS_BUCKET}/{gcs_path}"
        resp = make_response(jsonify({'url': url, 'publicUrl': public_url, 'gcsPath': gcs_path}), 200)
        resp.headers['Access-Control-Allow-Origin'] = get_cors_origin()
        resp.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS, DELETE'
        resp.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
        return resp
    except Exception as e:
        print('Error in /api/signed-url:', str(e))
        traceback.print_exc()
        resp = make_response(jsonify({'error': str(e), 'trace': traceback.format_exc()}), 500)
        resp.headers['Access-Control-Allow-Origin'] = get_cors_origin()
        resp.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS, DELETE'
        resp.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
        return resp

@app.route('/api/register-upload', methods=['POST'])
def register_upload():
    data = request.get_json()
    filename = data.get('filename')
    content_type = data.get('contentType')
    folder = secure_filename(data.get('folder', 'uploads'))
    public_url = data.get('publicUrl')
    gcs_path = data.get('gcsPath')
    if not filename or not content_type or not folder or not public_url:
        resp = make_response(jsonify({'error': 'filename, contentType, folder, and publicUrl are required'}), 400)
        resp.headers['Access-Control-Allow-Origin'] = get_cors_origin()
        resp.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS, DELETE'
        resp.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
        return resp
    add_folder_to_db(folder)
    add_photo_to_db(folder, filename, public_url, content_type, gcs_path or '')
    resp = make_response(jsonify({'ok': True}), 200)
    resp.headers['Access-Control-Allow-Origin'] = get_cors_origin()
    resp.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS, DELETE'
    resp.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
    return resp

import os
# --- AI-powered Semantic Search Endpoint ---
# Model is loaded at module level to avoid reloading on every request
_semantic_model = SentenceTransformer('all-MiniLM-L6-v2')

@app.route('/api/photos/semantic-search', methods=['GET'])
def semantic_search_photos():
    query = request.args.get('q', '').strip()
    if not query:
        return jsonify({'error': 'Missing query'}), 400
    # Fetch all photo metadata from DB
    with _db_lock:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('SELECT folder, name, url, mimetype, uploaded_at FROM photos')
        rows = c.fetchall()
        conn.close()
    if not rows:
        return jsonify([])
    # Prepare texts for embedding
    photo_texts = [f"{name} {folder} {mimetype}" for folder, name, url, mimetype, uploaded_at in rows]
    photo_embeddings = _semantic_model.encode(photo_texts)
    query_embedding = _semantic_model.encode([query])[0]
    # Compute cosine similarity
    similarities = np.dot(photo_embeddings, query_embedding) / (
        np.linalg.norm(photo_embeddings, axis=1) * np.linalg.norm(query_embedding) + 1e-8
    )
    top_indices = np.argsort(similarities)[::-1][:10]  # Top 10
    results = [
        {
            'folder': rows[i][0],
            'name': rows[i][1],
            'url': rows[i][2],
            'mimetype': rows[i][3],
            'uploaded_at': rows[i][4],
            'score': float(similarities[i])
        }
        for i in top_indices
    ]
    return jsonify(results)

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
