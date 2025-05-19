"""Tests for the health check endpoint."""

def test_health_check(client):
    """Test that the health check endpoint returns a 200 status code and the expected response."""
    response = client.get('/api/health')
    assert response.status_code == 200
    data = response.json()
    assert data['status'] == 'healthy'  # Should be 'healthy' in test environment
    assert 'database' in data
