"""Tests for the health check endpoint."""

def test_health_check(client):
    """Test that the health check endpoint returns a 200 status code and the expected response."""
    response = client.get('/health')
    assert response.status_code == 200
    data = response.get_json()
    assert data['status'] == 'healthy' or data['status'] == 'unhealthy'  # Depending on GCS connectivity
    assert 'timestamp' in data
    assert 'services' in data
    assert 'database' in data['services']
    assert 'storage' in data['services']
    assert 'version' in data
    assert 'environment' in data
