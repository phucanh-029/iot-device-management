"""
Test suite for handshake functionality (SCRUM-55)

Tests cover:
- Handshake message structure validation
- Handshake payload building
- WebSocket auto-handshake on connection
- Handshake response validation and logging
"""

import json
import socket
import unittest
from unittest.mock import Mock, patch, MagicMock, call
from datetime import datetime, timezone

from utilities import DEFAULT_COMMANDS
from ws_client import WebSocketManager


class TestHandshakePayloadBuilder(unittest.TestCase):
    """Tests for handshake payload building."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_logger = Mock()
        self.ws_manager = WebSocketManager(logger=self.mock_logger)

    def test_build_handshake_payload_structure(self):
        """Test that handshake payload has all required fields."""
        payload = self.ws_manager._build_handshake_payload()
        
        required_fields = [
            "message_type",
            "client_id", 
            "protocol_version",
            "timestamp",
            "device_name",
            "capabilities",
        ]
        for field in required_fields:
            self.assertIn(field, payload, f"Field '{field}' missing from handshake payload")

    def test_handshake_message_type(self):
        """Test that message_type is 'handshake'."""
        payload = self.ws_manager._build_handshake_payload()
        self.assertEqual(payload["message_type"], "handshake")

    def test_handshake_client_id_from_hostname(self):
        """Test that client_id uses socket.gethostname()."""
        payload = self.ws_manager._build_handshake_payload()
        self.assertEqual(payload["client_id"], socket.gethostname())

    def test_handshake_protocol_version(self):
        """Test that protocol_version is '1.0'."""
        payload = self.ws_manager._build_handshake_payload()
        self.assertEqual(payload["protocol_version"], "1.0")

    def test_handshake_device_name(self):
        """Test that device_name is correct."""
        payload = self.ws_manager._build_handshake_payload()
        self.assertEqual(payload["device_name"], "IoT-Device-Client")

    def test_handshake_capabilities_list(self):
        """Test that capabilities is a list with expected commands."""
        payload = self.ws_manager._build_handshake_payload()
        expected_capabilities = ["ping", "login", "subscribe", "echo"]
        self.assertEqual(payload["capabilities"], expected_capabilities)

    def test_handshake_timestamp_format(self):
        """Test that timestamp is ISO 8601 format with 'Z' suffix."""
        payload = self.ws_manager._build_handshake_payload()
        timestamp = payload["timestamp"]
        
        # Should end with 'Z'
        self.assertTrue(timestamp.endswith("Z"), f"Timestamp should end with 'Z': {timestamp}")
        
        # Should be parseable as ISO 8601
        try:
            # Remove 'Z' and parse
            datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        except ValueError:
            self.fail(f"Timestamp is not valid ISO 8601: {timestamp}")


class TestHandshakeResponseValidation(unittest.TestCase):
    """Tests for handshake response validation."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_logger = Mock()
        self.ws_manager = WebSocketManager(logger=self.mock_logger)

    def test_valid_handshake_response(self):
        """Test validation of a valid handshake response."""
        payload = {
            "message_type": "handshake_response",
            "timestamp": "2026-05-21T14:32:10Z",
            "status": "ok"
        }
        result = self.ws_manager._validate_handshake_response(payload)
        self.assertTrue(result)
        self.mock_logger.log.assert_called()

    def test_invalid_response_missing_message_type(self):
        """Test validation fails when message_type is missing."""
        payload = {
            "timestamp": "2026-05-21T14:32:10Z",
            "status": "ok"
        }
        result = self.ws_manager._validate_handshake_response(payload)
        self.assertFalse(result)

    def test_invalid_response_missing_timestamp(self):
        """Test validation fails when timestamp is missing."""
        payload = {
            "message_type": "handshake_response",
            "status": "ok"
        }
        result = self.ws_manager._validate_handshake_response(payload)
        self.assertFalse(result)

    def test_invalid_response_wrong_message_type(self):
        """Test validation fails when message_type is not 'handshake_response'."""
        payload = {
            "message_type": "ping_response",
            "timestamp": "2026-05-21T14:32:10Z",
            "status": "ok"
        }
        result = self.ws_manager._validate_handshake_response(payload)
        self.assertFalse(result)

    def test_validation_logs_success(self):
        """Test that successful validation is logged."""
        payload = {
            "message_type": "handshake_response",
            "timestamp": "2026-05-21T14:32:10Z"
        }
        self.ws_manager._validate_handshake_response(payload)
        
        # Check that logger was called
        calls = self.mock_logger.log.call_args_list
        self.assertTrue(any("validated" in str(call) for call in calls))

    def test_validation_logs_failure(self):
        """Test that failed validation is logged."""
        payload = {
            "timestamp": "2026-05-21T14:32:10Z"
        }
        self.ws_manager._validate_handshake_response(payload)
        
        # Check that logger was called with failure message
        calls = self.mock_logger.log.call_args_list
        self.assertTrue(
            any("validation failed" in str(call).lower() for call in calls),
            f"Expected validation failure log, got: {calls}"
        )


class TestHandshakeInDefaultCommands(unittest.TestCase):
    """Tests for handshake in default commands list."""

    def test_handshake_in_default_commands(self):
        """Test that 'Handshake' appears in DEFAULT_COMMANDS."""
        handshake_cmd = None
        for cmd in DEFAULT_COMMANDS:
            if cmd.get("name") == "Handshake":
                handshake_cmd = cmd
                break
        
        self.assertIsNotNone(handshake_cmd, "Handshake not found in DEFAULT_COMMANDS")

    def test_handshake_command_structure(self):
        """Test that handshake command has correct structure."""
        handshake_cmd = None
        for cmd in DEFAULT_COMMANDS:
            if cmd.get("name") == "Handshake":
                handshake_cmd = cmd
                break
        
        self.assertIn("payload", handshake_cmd)
        payload = handshake_cmd["payload"]
        
        expected_fields = [
            "message_type",
            "client_id",
            "protocol_version",
            "device_name",
            "capabilities",
        ]
        for field in expected_fields:
            self.assertIn(field, payload, f"Field '{field}' missing from handshake command payload")

    def test_handshake_command_message_type(self):
        """Test that handshake command has message_type='handshake'."""
        handshake_cmd = None
        for cmd in DEFAULT_COMMANDS:
            if cmd.get("name") == "Handshake":
                handshake_cmd = cmd
                break
        
        self.assertEqual(handshake_cmd["payload"]["message_type"], "handshake")


class TestWebSocketHandshakeIntegration(unittest.TestCase):
    """Integration tests for WebSocket handshake behavior."""

    def test_handshake_builder_creates_valid_structure(self):
        """Test that handshake payload builder creates valid structure."""
        mock_logger = Mock()
        ws_manager = WebSocketManager(logger=mock_logger)
        
        # Build and verify handshake can be created
        handshake = ws_manager._build_handshake_payload()
        self.assertIsNotNone(handshake)
        self.assertEqual(handshake["message_type"], "handshake")

    def test_handshake_send_json_integration(self):
        """Test that handshake can be sent via send_json()."""
        mock_logger = Mock()
        ws_manager = WebSocketManager(logger=mock_logger)
        
        # Simulate connected state
        ws_manager._set_connected(True)
        
        # Mock the websocket app
        ws_manager.ws_app = Mock()
        
        # Build and send handshake
        handshake = ws_manager._build_handshake_payload()
        ws_manager.send_json(handshake)
        
        # Verify send was called
        ws_manager.ws_app.send.assert_called_once()


if __name__ == "__main__":
    unittest.main()
