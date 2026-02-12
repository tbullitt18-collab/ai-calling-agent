"""
Tests for session management and AI modules (Claude).
"""

import pytest
from unittest.mock import MagicMock, patch

class TestSessionManager:
    """Test session manager functionality."""
    
    @pytest.fixture
    def mock_redis(self):
        """Create mock Redis client."""
        with patch('modules.session_manager.redis') as mock:
            mock_client = MagicMock()
            mock.from_url.return_value = mock_client
            yield mock_client
            
    @pytest.fixture
    def session_manager(self, mock_redis):
        """Create session manager with mocked Redis."""
        from modules.session_manager import SessionManager
        return SessionManager()
        
    def test_create_session(self, session_manager, mock_redis):
        """Test session creation."""
        session = session_manager.create_session(
            call_uuid="test-123",
            caller_number="+12025551234"
        )
        assert session.call_uuid == "test-123"
        
class TestIntentDetector:
    """Test intent detection functionality with Claude."""
    
    @pytest.fixture
    def mock_anthropic(self):
        """Create mock Anthropic client."""
        with patch('modules.intent_detector.client') as mock:
            yield mock
            
    def test_detect_intent(self, mock_anthropic):
        """Test intent detection."""
        # Mock Claude response
        mock_msg = MagicMock()
        mock_msg.content = [MagicMock(text='{"intent": "inquiry", "confidence": 0.9}')]
        mock_anthropic.messages.create.return_value = mock_msg
        
        from modules.intent_detector import detect_intent
        result = detect_intent("What are your hours?")
        
        assert result.intent == "inquiry"
        assert result.confidence == 0.9

class TestConversationEngine:
    """Test conversation engine functionality with Claude."""
    
    @pytest.fixture
    def mock_anthropic(self):
        """Create mock Anthropic client."""
        with patch('modules.conversation_engine.client') as mock:
            yield mock
            
    def test_generate_response(self, mock_anthropic):
        """Test response generation."""
        mock_msg = MagicMock()
        mock_msg.content = [MagicMock(text="I'd be happy to help you with that!")]
        mock_anthropic.messages.create.return_value = mock_msg
        
        from modules.conversation_engine import ConversationEngine
        engine = ConversationEngine()
        
        response = engine.generate_response("I need help with something")
        assert response == "I'd be happy to help you with that!"
