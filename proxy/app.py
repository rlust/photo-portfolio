from flask import Flask, request, Response, jsonify, make_response
import requests
import logging
import os

app = Flask(__name__)

# Frontend origin that needs access
ALLOWED_ORIGINS = [
    'https://photoportfolio-frontend-839093975626.us-central1.run.app',
    'http://localhost:3000',
    'http://localhost:8080'
]

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# The target backend URL that we want to proxy to
TARGET_BACKEND = "https://simplified-backend-839093975626.us-central1.run.app"

# Special route for OPTIONS preflight requests
@app.route('/', defaults={'path': ''}, methods=['OPTIONS'])
@app.route('/<path:path>', methods=['OPTIONS'])
def options_handler(path):
    origin = request.headers.get('Origin', '')
    logger.info(f"Handling OPTIONS request for {path} from origin: {origin}")
    
    response = make_response()
    response.headers["Access-Control-Allow-Origin"] = origin if origin in ALLOWED_ORIGINS else ALLOWED_ORIGINS[0]
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, X-Requested-With"
    response.headers["Access-Control-Allow-Credentials"] = "true"
    response.headers["Access-Control-Max-Age"] = "3600"
    return response

# Main proxy route for all other methods
@app.route('/', defaults={'path': ''}, methods=['GET', 'POST', 'PUT', 'DELETE'])
@app.route('/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE'])
def proxy(path):
    """
    Proxy all requests to the backend with HTTPS enforced
    """
    # Get the origin for CORS
    origin = request.headers.get('Origin', '')
    
    # Log the request
    logger.info(f"Received request: {request.method} /{path} from {origin}")
    
    # Construct the target URL with HTTPS
    url = f"{TARGET_BACKEND}/{path}"
    logger.info(f"Proxying to: {url}")
    
    try:
        # Copy headers without Host header
        headers = {}
        for key, value in request.headers:
            if key.lower() != 'host':
                headers[key] = value
        
        # Make the request to the backend
        resp = requests.request(
            method=request.method,
            url=url,
            headers=headers,
            data=request.get_data(),
            cookies=request.cookies,
            allow_redirects=False,
            verify=True  # Verify SSL certificates
        )
        
        # Log the success
        logger.info(f"Received response from backend: {resp.status_code}")
        
        # Create a Flask response with the backend content
        response = Response(resp.content)
        
        # Copy relevant headers from the backend response
        excluded_headers = ['content-encoding', 'content-length', 'transfer-encoding', 'connection']
        for name, value in resp.raw.headers.items():
            if name.lower() not in excluded_headers:
                response.headers[name] = value
        
        # Add CORS headers
        response.headers["Access-Control-Allow-Origin"] = origin if origin in ALLOWED_ORIGINS else ALLOWED_ORIGINS[0]
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, X-Requested-With"
        response.headers["Access-Control-Allow-Credentials"] = "true"
        
        # Set status code
        response.status_code = resp.status_code
        return response
        
    except Exception as e:
        logger.error(f"Error during proxy request: {str(e)}")
        
        # Create error response with CORS headers
        response = jsonify({'error': str(e)})
        response.headers["Access-Control-Allow-Origin"] = origin if origin in ALLOWED_ORIGINS else ALLOWED_ORIGINS[0]
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, X-Requested-With"
        response.headers["Access-Control-Allow-Credentials"] = "true"
        response.status_code = 500
        return response

@app.route('/health')
def health():
    """Health check endpoint"""
    origin = request.headers.get('Origin', '')
    response = jsonify({"status": "healthy", "service": "https-proxy", "cors": "enabled"})
    
    # Add CORS headers
    response.headers["Access-Control-Allow-Origin"] = '*'  # Allow all origins for diagnostic endpoint
    response.headers["Access-Control-Allow-Methods"] = "GET, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    return response

# Root endpoint that confirms the service is running
@app.route('/')
def root():
    origin = request.headers.get('Origin', '')
    response = jsonify({
        "message": "HTTPS Proxy is running",
        "target": TARGET_BACKEND,
        "service": "https-proxy",
        "cors": "enabled"
    })
    
    # Add CORS headers
    response.headers["Access-Control-Allow-Origin"] = '*'  # Allow all origins for diagnostic endpoint
    response.headers["Access-Control-Allow-Methods"] = "GET, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    return response

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port, debug=False)
