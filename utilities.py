from datetime import datetime
import json
from typing import Optional, Dict, Any


DEFAULT_COMMANDS = [
    {
        "name": "Handshake",
        "payload": {
            "action": "handshake",
            "clientId": "tkinter-client-001",
            "token": "replace-me",
            "version": "1.0",
            "timestamp": "2026-03-27T12:00:00Z"
        },
    },
    {
        "name": "Ping",
        "payload": {
            "action": "ping",
            "timestamp": "2026-03-27T12:00:00Z",
        },
    },
    {
        "name": "Login",
        "payload": {
            "action": "login",
            "username": "demo_user",
            "token": "replace-me",
        },
    },
    {
        "name": "Subscribe",
        "payload": {
            "action": "subscribe",
            "channel": "events",
        },
    },
    {
        "name": "Echo",
        "payload": {
            "action": "echo",
            "message": "hello from tkinter client",
        },
    },
    {
        "name": "HTTP POST sample",
        "payload": {
            "method": "POST",
            "path": "/api/commands",
            "headers": {
                "Content-Type": "application/json",
            },
            "body": {
                "action": "status",
            },
            "timeout": 10,
        },
    },
]


class AppLogger:
    def __init__(self, callback) -> None:
        self.callback = callback

    def log(self, message: str) -> None:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.callback(f"[{timestamp}] {message}\n")


class HandshakeValidator:
    """Validates handshake messages before sending."""
    
    REQUIRED_FIELDS = ["action", "clientId", "token"]
    OPTIONAL_FIELDS = ["version", "timestamp"]
    
    @classmethod
    def validate(cls, payload: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """
        Validate handshake payload.
        
        Args:
            payload: The handshake message payload
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not isinstance(payload, dict):
            return False, "Payload must be a dictionary"
        
        # Check action field
        if payload.get("action") != "handshake":
            return False, "Action must be 'handshake'"
        
        # Check required fields
        for field in cls.REQUIRED_FIELDS:
            if field not in payload:
                return False, f"Missing required field: {field}"
            if not payload[field]:
                return False, f"Required field '{field}' cannot be empty"
        
        # Validate clientId format (simple alphanumeric and dash check)
        client_id = payload.get("clientId", "")
        if not isinstance(client_id, str) or len(client_id) < 3:
            return False, "clientId must be a non-empty string (min 3 chars)"
        
        # Validate token format (should not be 'replace-me' placeholder)
        token = payload.get("token", "")
        if token == "replace-me":
            return False, "token field must be configured (not 'replace-me')"
        
        return True, None
    
    @classmethod
    def get_default_handshake(cls, client_id: str = "tkinter-client-001", 
                             token: str = "") -> Dict[str, Any]:
        """
        Generate a default handshake payload.
        
        Args:
            client_id: Client identifier
            token: Authentication token
            
        Returns:
            A handshake payload dict
        """
        return {
            "action": "handshake",
            "clientId": client_id,
            "token": token,
            "version": "1.0",
            "timestamp": datetime.now().isoformat() + "Z"
        }
