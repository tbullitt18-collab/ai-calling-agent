"""
Tests for Rain Check webhook and API endpoints.
Production-ready test suite covering webhooks, auth-gated API routes, and scheduling.
"""

import pytest
from unittest.mock import patch, MagicMock


@pytest.fixture
def app():
    """Create and configure test application."""
    from app import create_app
    app = create_app()
    app.config['TESTING'] = True
    return app


@pytest.fixture
def client(app):
    """Unauthenticated test client — for public endpoints (health, webhooks)."""
    with app.test_client() as c:
        yield c


@pytest.fixture
def auth_client(app):
    """Authenticated test client — for routes behind the auth gate."""
    with app.test_client() as c:
        with c.session_transaction() as sess:
            sess['authenticated'] = True
            sess['user'] = 'test-user@test.com'
        yield c


# ── Public Endpoints (no auth required) ─────────────────────────────

def test_health_check(client):
    """Health check returns 200 with status ok."""
    response = client.get('/health')
    assert response.status_code == 200
    assert response.json['status'] == 'ok'


def test_webhook_answer_returns_ncco(client):
    """Vonage answer webhook returns valid NCCO with talk + WebSocket connect."""
    response = client.get('/webhook/answer?uuid=test-call-123&from=+15550001234')

    assert response.status_code == 200
    ncco = response.get_json()
    assert isinstance(ncco, list)
    assert len(ncco) >= 2
    assert ncco[0]['action'] == 'talk'
    assert ncco[1]['action'] == 'connect'
    assert ncco[1]['endpoint'][0]['type'] == 'websocket'
    assert 'ws/audio/test-call-123' in ncco[1]['endpoint'][0]['uri']


def test_webhook_events_accepts_post(client):
    """Vonage event webhook accepts POST and returns 204."""
    response = client.post('/webhook/events', json={
        'uuid': 'test-call-123',
        'status': 'ringing'
    })
    assert response.status_code == 204


# ── Auth Gate Verification ──────────────────────────────────────────

def test_unauthenticated_api_redirects(client):
    """Unauthenticated requests to protected routes get 302 redirect."""
    response = client.post('/api/call/initiate', json={'to': '+15551234567'})
    assert response.status_code == 302

def test_unauthenticated_session_redirects(client):
    """Unauthenticated requests to session routes get 302 redirect."""
    response = client.post('/session/call-now', json={'to_number': '+15551234567'})
    assert response.status_code == 302


# ── Authenticated API Endpoints ─────────────────────────────────────

def test_api_initiate_call_requires_number(auth_client):
    """POST /api/call/initiate rejects missing phone number with 400."""
    response = auth_client.post('/api/call/initiate', json={})
    assert response.status_code == 400
    assert 'error' in response.json


@patch('app.routes.api.initiate_outbound_call')
def test_api_initiate_call_success(mock_call, auth_client):
    """POST /api/call/initiate succeeds with valid number."""
    mock_call.return_value = {"uuid": "vonage-uuid-456"}

    response = auth_client.post('/api/call/initiate', json={
        'to': '+15559998888',
        'reason': 'Sick Day'
    })

    assert response.status_code == 200
    assert response.json['status'] == 'initiated'
    assert response.json['call_uuid'] == 'vonage-uuid-456'
    mock_call.assert_called_once()


# ── Authenticated Session Endpoints ─────────────────────────────────

def test_session_schedule_requires_fields(auth_client):
    """POST /session/schedule rejects missing to_number or time with 400."""
    response = auth_client.post('/session/schedule', json={})
    assert response.status_code == 400


@patch('app.routes.session.scheduler')
def test_session_call_now_requires_number(mock_scheduler, auth_client):
    """POST /session/call-now rejects missing to_number with 400."""
    response = auth_client.post('/session/call-now', json={})
    assert response.status_code == 400
