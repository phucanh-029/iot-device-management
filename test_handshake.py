"""
Test suite for handshake functionality (SCRUM-55)

Tests cover:
- Handshake message structure validation
- Default handshake generation
- WebSocket auto-handshake on connection
- Handshake response logging
"""

import json
import unittest
from unittest.mock import Mock, patch, MagicMock, call
from datetime import datetime

from utilities import HandshakeValidator, DEFAULT_COMMANDS, AppLogger
from ws_client import WebSocketManager


class TestHandshakeValidator(unittest.TestCase):
    """Tests for HandshakeValidator class."""

    def test_valid_handshake(self):
        """Test validation of a valid handshake payload."""
        payload = {
            "action": "handshake",
            "clientId": "test-client-001",
            "token": "valid-token-123",
            "version": "1.0",
            "timestamp": "2026-03-27T12:00:00Z"
        }
        is_valid, error_msg = HandshakeValidator.validate(payload)
        self.assertTrue(is_valid)
        self.assertIsNone(error_msg)

    def test_missing_action(self):
        """Test validation fails when action field is missing."""
        payload = {
            "clientId": "test-client-001",
            "token": "valid-token-123",
        }
        is_valid, error_msg = HandshakeValidator.validate(payload)
        self.assertFalse(is_valid)
        self.assertIn("action", error_msg.lower())

    def test_wrong_action(self):
        """Test validation fails when action is not 'handshake'."""
        payload = {
            "action": "ping",
            "clientId": "test-client-001",
            "token": "valid-token-123",
        }
        is_valid, error_msg = HandshakeValidator.validate(payload)
        self.assertFalse(is_valid)
        self.assertIn("handshake", error_msg.lower())

    def test_missing_clientId(self):
        """Test validation fails when clientId is missing."""
        payload = {
            "action": "handshake",
            "token": "valid-token-123",
        }
        is_valid, error_msg = HandshakeValidator.validate(payload)
        self.assertFalse(is_valid)
        self.assertIn("clientId", error_msg)

    def test_missing_token(self):
        """Test validation fails when token is missing."""
        payload = {
            "action": "handshake",
            "clientId": "test-client-001",
        }
        is_valid, error_msg = HandshakeValidator.validate(payload)
        self.assertFalse(is_valid)
        self.assertIn("token", error_msg)

    def test_empty_clientId(self):
        """Test validation fails when clientId is empty."""
        payload = {
            "action": "handshake",
            "clientId": "",
            "token": "valid-token-123",
        }
        is_valid, error_msg = HandshakeValidator.validate(payload)
        self.assertFalse(is_valid)
        self.assertIn("clientId", error_msg)

    def test_short_clientId(self):
        """Test validation fails when clientId is too short."""
        payload = {
            "action": "handshake",
            "clientId": "ab",  # Less than 3 chars
            "token": "valid-token-123",
        }
        is_valid, error_msg = HandshakeValidator.validate(payload)
        self.assertFalse(is_valid)
        self.assertIn("clientId", error_msg)

    def test_placeholder_token(self):
        """Test validation fails when token is 'replace-me' placeholder."""
        payload = {
            "action": "handshake",
            "clientId": "test-client-001",
            "token": "replace-me",
        }
        is_valid, error_msg = HandshakeValidator.validate(payload)
        self.assertFalse(is_valid)
        self.assertIn("configured", error_msg.lower())

    def test_non_dict_payload(self):
        """Test validation fails when payload is not a dict."""
        payload = "not a dict"
        is_valid, error_msg = HandshakeValidator.validate(payload)
        self.assertFalse(is_valid)
        self.assertIn("dictionary", error_msg)

    def test_get_default_handshake(self):
        """Test generating default handshake payload."""
        handshake = HandshakeValidator.get_default_handshake(
            client_id="my-client",
            token="my-token"
        )
        self.assertEqual(handshake["action"], "handshake")
        self.assertEqual(handshake["clientId"], "my-client")
        self.assertEqual(handshake["token"], "my-token")
        self.assertEqual(handshake["version"], "1.0")
        self.assertIn("timestamp", handshake)

    def test_get_default_handshake_custom_args(self):
        """Test default handshake with custom client ID."""
        handshake = HandshakeValidator.get_default_handshake(
            client_id="custom-device-123"
        )
        self.assertEqual(handshake["clientId"], "custom-device-123")


class TestDefaultCommandsHandshake(unittest.TestCase):
    """Tests for handshake in DEFAULT_COMMANDS."""

    def test_handshake_in_defaults(self):
        """Test that handshake is in DEFAULT_COMMANDS."""
        handshake_cmd = DEFAULT_COMMANDS[0]
        self.assertEqual(handshake_cmd["name"], "Handshake")
        self.assertEqual(handshake_cmd["payload"]["action"], "handshake")

    def test_handshake_has_required_fields(self):
        """Test that default handshake has all required fields."""
        payload = DEFAULT_COMMANDS[0]["payload"]
        required_fields = ["action", "clientId", "token"]
        for field in required_fields:
            self.assertIn(field, payload)

    def test_handshake_is_first_command(self):
        """Test that handshake is the first default command."""
        self.assertEqual(DEFAULT_COMMANDS[0]["name"], "Handshake")


class TestWebSocketHandshakeIntegration(unittest.TestCase):
    """Tests for WebSocket manager handshake integration."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_logger = Mock()
        self.messages = []

    def test_websocket_manager_initialization(self):
        """Test WebSocketManager initializes with auto_handshake enabled."""
        manager = WebSocketManager(
            logger=self.mock_logger,
            auto_handshake=True
        )
        self.assertTrue(manager.auto_handshake)
        self.assertIsNone(manager.handshake_payload)

    def test_websocket_manager_can_disable_auto_handshake(self):
        """Test WebSocketManager can disable auto_handshake."""
        manager = WebSocketManager(
            logger=self.mock_logger,
            auto_handshake=False
        )
        self.assertFalse(manager.auto_handshake)

    def test_handshake_sent_on_connection(self):
        """Test that handshake is sent when WebSocket opens."""
        mock_logger = Mock()
        manager = WebSocketManager(
            logger=mock_logger,
            auto_handshake=True
        )
        
        # Manually trigger the on_open callback
        manager.connected = False
        manager.ws_app = MagicMock()
        manager._on_open(None)
        
        # Verify the state changed
        self.assertTrue(manager.connected)
        # Logger should have been called
        self.assertGreater(mock_logger.log.call_count, 0)

    def test_handshake_validation_before_send(self):
        """Test that handshake is validated before sending."""
        logger_callback = Mock()
        app_logger = AppLogger(logger_callback)
        manager = WebSocketManager(
            logger=app_logger,
            auto_handshake=True
        )
        
        # Set invalid handshake payload (replace-me token)
        manager.handshake_payload = {
            "action": "handshake",
            "clientId": "test-client",
            "token": "replace-me"
        }
        
        manager.connected = True
        manager.ws_app = MagicMock()
        
        # Try to send invalid handshake
        manager._send_handshake()
        
        # Should log validation error
        self.assertGreater(logger_callback.call_count, 0)

    def test_handshake_response_logging(self):
        """Test that handshake responses are logged."""
        logger_callback = Mock()
        app_logger = AppLogger(logger_callback)
        manager = WebSocketManager(logger=app_logger)
        
        # Simulate receiving a handshake response
        response_msg = json.dumps({
            "action": "handshake",
            "status": "accepted",
            "sessionId": "sess-123"
        })
        
        manager._on_message(None, response_msg)
        
        # Should log handshake response
        self.assertGreater(logger_callback.call_count, 0)

    def test_send_json_with_valid_connection(self):
        """Test sending JSON message via WebSocket."""
        manager = WebSocketManager(logger=self.mock_logger)
        manager.connected = True
        manager.ws_app = MagicMock()
        
        payload = {"action": "ping"}
        manager.send_json(payload)
        
        # Verify send was called
        manager.ws_app.send.assert_called_once()

    def test_default_handshake_generated_on_open(self):
        """Test default handshake is generated if not provided."""
        logger_callback = Mock()
        app_logger = AppLogger(logger_callback)
        manager = WebSocketManager(
            logger=app_logger,
            auto_handshake=True
        )
        
        manager.connected = False
        manager.ws_app = MagicMock()
        manager.auto_handshake = True
        manager.handshake_payload = None
        
        manager._on_open(None)
        
        # Check that handshake_payload was generated
        self.assertIsNotNone(manager.handshake_payload)
        self.assertEqual(manager.handshake_payload["action"], "handshake")


class TestHandshakeMessageStructure(unittest.TestCase):
    """Tests for handshake message structure."""

    def test_handshake_json_structure(self):
        """Test that handshake message is valid JSON."""
        handshake = HandshakeValidator.get_default_handshake(
            client_id="test-device",
            token="test-token"
        )
        # Should be serializable to JSON
        json_str = json.dumps(handshake)
        # Should be deserializable from JSON
        parsed = json.loads(json_str)
        self.assertEqual(parsed["action"], "handshake")

    def test_handshake_timestamp_format(self):
        """Test that handshake includes ISO format timestamp."""
        handshake = HandshakeValidator.get_default_handshake(
            client_id="test",
            token="test"
        )
        timestamp = handshake.get("timestamp")
        self.assertIsNotNone(timestamp)
        # Should end with Z (ISO format)
        self.assertTrue(timestamp.endswith("Z"))


if __name__ == "__main__":
    unittest.main()
