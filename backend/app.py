from flask import Flask, jsonify, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

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

@app.route('/api/upload', methods=['POST'])
def upload_photos():
    folder = request.form.get('folder')
    files = request.files.getlist('images')
    if not folder or not files:
        return jsonify({'error': 'Folder name and images are required.'}), 400
    folder = secure_filename(folder)
    if folder not in photo_folders:
        photo_folders[folder] = []
    uploaded = []
    for file in files:
        filename = secure_filename(file.filename)
        # For demo: store as base64 string in memory (not for production!)
        import base64
        img_bytes = file.read()
        img_b64 = base64.b64encode(img_bytes).decode('utf-8')
        photo_info = {'name': filename, 'data': img_b64, 'mimetype': file.mimetype}
        photo_folders[folder].append(photo_info)
        uploaded.append({'name': filename, 'mimetype': file.mimetype})
    return jsonify({'folder': folder, 'uploaded': uploaded, 'folders': list(photo_folders.keys())}), 201

@app.route('/api/folders', methods=['GET'])
def get_folders():
    # Return folder names and photo metadata (not image data)
    return jsonify({folder: [{'name': p['name'], 'mimetype': p['mimetype']} for p in photos] for folder, photos in photo_folders.items()})

@app.route('/api/folder/<folder>/<filename>', methods=['GET'])
def get_photo(folder, filename):
    folder = secure_filename(folder)
    filename = secure_filename(filename)
    if folder not in photo_folders:
        return jsonify({'error': 'Folder not found'}), 404
    for photo in photo_folders[folder]:
        if photo['name'] == filename:
            import base64
            from flask import Response
            img_bytes = base64.b64decode(photo['data'])
            return Response(img_bytes, mimetype=photo['mimetype'])
    return jsonify({'error': 'Photo not found'}), 404

import os
port = int(os.environ.get('PORT', 8080))
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=port)
