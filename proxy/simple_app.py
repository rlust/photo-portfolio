from flask import Flask, request, Response, jsonify
import requests
import logging
import os

app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Target backend
TARGET_BACKEND = "https://simplified-backend-839093975626.us-central1.run.app"

@app.after_request
def after_request(response):
    """Add CORS headers to every response"""
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    return response

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'])
def proxy(path):
    """Simple proxy that adds CORS headers"""
    if request.method == 'OPTIONS':
        # Just return headers for preflight requests
        return ''

    # Log request
    logger.info(f"Proxying {request.method} request to {TARGET_BACKEND}/{path}")
    
    # Forward the request
    url = f"{TARGET_BACKEND}/{path}"
    try:
        resp = requests.request(
            method=request.method,
            url=url,
            headers={key: value for key, value in request.headers if key != 'Host'},
            data=request.get_data(),
            cookies=request.cookies,
            allow_redirects=False,
            verify=True
        )
        
        # Create response
        excluded_headers = ['content-encoding', 'content-length', 'transfer-encoding', 'connection']
        headers = [(name, value) for name, value in resp.raw.headers.items()
                  if name.lower() not in excluded_headers]
                  
        response = Response(resp.content, resp.status_code, headers)
        return response
        
    except Exception as e:
        logger.error(f"Error in proxy: {str(e)}")
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)
