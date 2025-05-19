import os
import requests
from flask import Blueprint, request, jsonify

search_bp = Blueprint('search', __name__)

GOOGLE_API_KEY = os.environ.get('GOOGLE_CUSTOM_SEARCH_API_KEY')
GOOGLE_CSE_ID = os.environ.get('GOOGLE_CUSTOM_SEARCH_CX')

@search_bp.route('/api/web-search', methods=['GET'])
def web_search():
    query = request.args.get('q')
    if not query:
        return jsonify({'error': 'Missing query parameter'}), 400
    if not GOOGLE_API_KEY or not GOOGLE_CSE_ID:
        return jsonify({'error': 'API key or CSE ID not set'}), 500
    url = 'https://www.googleapis.com/customsearch/v1'
    params = {
        'key': GOOGLE_API_KEY,
        'cx': GOOGLE_CSE_ID,
        'q': query
    }
    resp = requests.get(url, params=params)
    if resp.status_code != 200:
        return jsonify({'error': 'Google API error', 'details': resp.text}), 502
    return jsonify(resp.json())
