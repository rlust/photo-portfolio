"""Tests for the API endpoints."""

def test_endpoints_list(client):
    """Test that the endpoints list endpoint returns a 200 status code and the expected response."""
    response = client.get('/api/endpoints')
    assert response.status_code == 200
    data = response.json()
    assert 'endpoints' in data
    assert isinstance(data['endpoints'], list)
    
    # Check that some expected endpoints are present
    endpoints = {item['path'] for item in data['endpoints']}
    assert '/api/health' in endpoints
    assert '/api/endpoints' in endpoints
