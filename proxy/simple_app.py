from flask import Flask, request, Response, jsonify
import requests
import logging
import os
import json
from flask_cors import CORS

app = Flask(__name__)

# Enable CORS for all routes
CORS(app, resources={r"/*": {"origins": "*"}})

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Target backend
TARGET_BACKEND = "https://simplified-backend-839093975626.us-central1.run.app"

# Routes for the proxy service

@app.route('/api/folders/', methods=['GET', 'OPTIONS'])
def get_folders():
    """Handle API requests for folders"""
    logger.info("Folders request received")
    
    try:
        # Forward to the simplified backend
        target_url = f"{TARGET_BACKEND}/api/folders/"
        
        # Make the request to the backend
        response = requests.get(target_url)
        
        if response.status_code == 200:
            logger.info("Successfully fetched folders")
            return jsonify(response.json())
        else:
            logger.error(f"Failed to fetch folders: {response.status_code}")
            return jsonify({"success": False, "message": "Failed to fetch folders"}), response.status_code
    except Exception as e:
        logger.error(f"Error fetching folders: {str(e)}")
        return jsonify({"success": False, "message": "Error fetching folders"}), 500

@app.route('/api/annotate-image/', methods=['POST', 'OPTIONS'])
def annotate_image():
    """Handle image annotation requests"""
    logger.info("Annotation request received")
    
    try:
        # Forward to the simplified backend
        target_url = f"{TARGET_BACKEND}/api/annotate-image/"
        
        # Get the request data
        data = request.get_json()
        
        # Make the request to the backend
        response = requests.post(
            target_url,
            json=data,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            logger.info("Successfully annotated image")
            return jsonify(response.json())
        else:
            logger.error(f"Failed to annotate image: {response.status_code}")
            return jsonify({"success": False, "message": "Failed to annotate image"}), response.status_code
    except Exception as e:
        logger.error(f"Error annotating image: {str(e)}")
        return jsonify({"success": False, "message": "Error annotating image"}), 500

@app.route('/api/delete-image/', methods=['POST', 'OPTIONS'])
def delete_image():
    """Handle image deletion requests"""
    logger.info("Delete image request received")
    
    try:
        # Forward to the simplified backend
        target_url = f"{TARGET_BACKEND}/api/delete-image/"
        
        # Get the request data
        data = request.get_json()
        
        # Make the request to the backend
        response = requests.post(
            target_url,
            json=data,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            logger.info("Successfully deleted image")
            return jsonify(response.json())
        else:
            logger.error(f"Failed to delete image: {response.status_code}")
            return jsonify({"success": False, "message": "Failed to delete image"}), response.status_code
    except Exception as e:
        logger.error(f"Error deleting image: {str(e)}")
        return jsonify({"success": False, "message": "Error deleting image"}), 500

@app.route('/uploads/<path:filename>', methods=['GET'])
def serve_uploads(filename):
    """Serve uploaded files from the backend"""
    logger.info(f"Uploads request received for: {filename}")
    
    try:
        # Forward to the simplified backend
        target_url = f"{TARGET_BACKEND}/uploads/{filename}"
        
        # Make the request to the backend
        response = requests.get(target_url, stream=True)
        
        if response.status_code == 200:
            # Get the content type from the response
            content_type = response.headers.get('Content-Type', 'image/jpeg')
            
            # Create a streaming response
            def generate():
                for chunk in response.iter_content(chunk_size=8192):
                    yield chunk
            
            # Return the streaming response
            return Response(
                generate(),
                status=200,
                content_type=content_type,
                headers={'Cache-Control': 'max-age=86400'}
            )
        else:
            logger.error(f"Failed to fetch upload: {response.status_code}")
            return jsonify({"success": False, "message": "Failed to fetch upload"}), response.status_code
    except Exception as e:
        logger.error(f"Error fetching upload: {str(e)}")
        return jsonify({"success": False, "message": "Error fetching upload"}), 500

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'])
def proxy(path):
    """General proxy handler for all other routes"""
    # Skip specific endpoints that have dedicated handlers
    if path in ['api/folders/', 'api/annotate-image/', 'api/delete-image/'] or path.startswith('uploads/'):
        return jsonify({"error": "This endpoint has a dedicated handler"}), 400

    # Log request
    logger.info(f"Proxying {request.method} request to {TARGET_BACKEND}/{path}")
    
    # Forward the request
    url = f"{TARGET_BACKEND}/{path}"
    try:
        # Create headers dictionary
        headers = {}
        for name, value in request.headers.items():
            if name.lower() != 'host':
                headers[name] = value
        
        # Get request data
        data = request.get_data()
        
        # Make the request
        response = requests.request(
            method=request.method,
            url=url,
            headers=headers,
            data=data,
            cookies=request.cookies,
            allow_redirects=False,
            timeout=30
        )
        
        # Create response
        headers = {}
        for name, value in response.headers.items():
            if name.lower() not in ['content-encoding', 'content-length', 'transfer-encoding', 'connection']:
                headers[name] = value
        
        # Always add CORS headers
        headers['Access-Control-Allow-Origin'] = '*'
        headers['Access-Control-Allow-Headers'] = 'Content-Type,Authorization'
        headers['Access-Control-Allow-Methods'] = 'GET,PUT,POST,DELETE,OPTIONS'
        
        return Response(response.content, response.status_code, headers)
        
    except Exception as e:
        logger.error(f"Error in proxy: {str(e)}")
        return jsonify({"error": f"Proxy error: {str(e)}"}), 500

# Run the app
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=False)
