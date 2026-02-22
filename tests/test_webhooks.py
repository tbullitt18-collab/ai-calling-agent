"""
Tests for Rain Check webhook endpoints (Vonage-based).
"""

import pytest
from unittest.mock import patch, MagicMock


@pytest.fixture
def client():
    from app import create_app
    app = create_app()
    app.config['TESTING'] = True
    with app.test_client() as c:
        yield c


def test_health_check(client):
    """Test health check endpoint returns correct provider info."""
    response = client.get('/health')
    assert response.status_code == 200
    assert response.json['status'] == 'ok'


def test_webhook_answer_returns_ncco(client):
    """Test Vonage answer webhook returns valid NCCO JSON."""
    response = client.get('/webhook/answer?uuid=test-call-123&from=+15550001234')
    
    assert response.status_code == 200
    ncco = response.get_json()
    assert isinstance(ncco, list)
    assert len(ncco) >= 1
    # First action should be a talk greeting
    assert ncco[0]['action'] == 'talk'
    # Second action should connect to WebSocket
    assert ncco[1]['action'] == 'connect'
    assert ncco[1]['endpoint'][0]['type'] == 'websocket'
    assert 'ws/audio/test-call-123' in ncco[1]['endpoint'][0]['uri']


def test_webhook_events_accepts_post(client):
    """Test Vonage event webhook accepts POST and returns 204."""
    response = client.post('/webhook/events', json={
        'uuid': 'test-call-123',
        'status': 'ringing'
    })
    assert response.status_code == 204


def test_api_initiate_call_requires_number(client):
    """Test that /api/call/initiate rejects missing phone number."""
    response = client.post('/api/call/initiate', json={})
    assert response.status_code == 400
    assert 'error' in response.json


@patch('app.services.vonage_service.initiate_outbound_call')
def test_api_initiate_call_success(mock_call, client):
    """Test successful call initiation via API."""
    mock_call.return_value = {"uuid": "vonage-uuid-456"}
    
    response = client.post('/api/call/initiate', json={
        'to': '+15559998888',
        'reason': 'Sick Day'
    })
    
    assert response.status_code == 200
    assert response.json['status'] == 'initiated'
    assert response.json['call_uuid'] == 'vonage-uuid-456'
    mock_call.assert_called_once()


def test_session_schedule_requires_fields(client):
    """Test that scheduling requires number and time."""
    response = client.post('/session/schedule', json={})
    assert response.status_code == 400


def test_session_call_now_requires_number(client):
    """Test that call-now requires a phone number."""
    response = client.post('/session/call-now', json={})
    assert response.status_code == 400
