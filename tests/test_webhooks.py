"""
Tests for Rain Check Twilio endpoints.
"""

import pytest
from app import app
from unittest.mock import patch, MagicMock

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_health_check(client):
    """Test health check endpoint."""
    response = client.get('/')
    assert response.status_code == 200
    assert response.json['status'] == 'operational'

@patch('modules.twilio_api.generate_answer_twiml')
@patch('modules.session_manager.SessionManager.create_session')
def test_webhook_answer(mock_create_session, mock_twiml, client):
    """Test Twilio answer webhook."""
    # Mock TwiML generation
    mock_twiml.return_value = "<Response><Say>Test</Say></Response>"
    
    # Twilio sends form data
    response = client.post('/webhook/answer', data={
        'CallSid': 'CA12345',
        'From': '+15550001234'
    })
    
    assert response.status_code == 200
    assert response.mimetype == 'text/xml'
    assert b'<Response><Say>Test</Say></Response>' in response.data
    
    # Verify session creation
    mock_create_session.assert_called_with('CA12345', '+15550001234')

@patch('modules.twilio_api.initiate_outbound_call')
def test_api_initiate_call(mock_initiate, client):
    """Test outbound call API."""
    mock_initiate.return_value = {"uuid": "CA99999"}
    
    response = client.post('/api/call/initiate', json={
        'to': '+15550009999'
    })
    
    assert response.status_code == 200
    assert response.json['status'] == 'initiated'
    assert response.json['call_uuid'] == 'CA99999'
