"""Tests for the root endpoint."""

def test_root_endpoint(client):
    """Test that the root endpoint returns a 200 status code and the expected response."""
    response = client.get('/')
    assert response.status_code == 200
    data = response.get_json()
    assert data['service'] == 'Photo Portfolio Backend'
    assert data['status'] == 'running'
    assert 'timestamp' in data
    assert 'environment' in data
