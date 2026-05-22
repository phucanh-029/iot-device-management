import json
import socket
import threading
from datetime import datetime, timezone
from typing import Callable, Optional

from websocket import WebSocketApp


class WebSocketManager:
    def __init__(
        self,
        logger,
        on_message: Optional[Callable[[str], None]] = None,
        on_status_change: Optional[Callable[[bool], None]] = None,
    ) -> None:
        self.logger = logger
        self.on_message = on_message
        self.on_status_change = on_status_change
        self.ws_app = None
        self.ws_thread = None
        self.connected = False

    def connect(self, ws_url: str) -> None:
        if self.connected:
            self.logger.log("WebSocket is already connected.")
            return

        if not ws_url:
            self.logger.log("WebSocket URL is empty.")
            return

        self.logger.log(f"Connecting to WebSocket: {ws_url}")

        def run_ws() -> None:
            self.ws_app = WebSocketApp(
                ws_url,
                on_open=self._on_open,
                on_message=self._on_message,
                on_error=self._on_error,
                on_close=self._on_close,
            )
            try:
                self.ws_app.run_forever()
            except Exception as exc:
                self.logger.log(f"WebSocket run_forever exception: {exc}")

        self.ws_thread = threading.Thread(target=run_ws, daemon=True)
        self.ws_thread.start()

    def disconnect(self) -> None:
        if self.ws_app is None:
            self.logger.log("No active WebSocket connection.")
            return

        self.logger.log("Disconnecting WebSocket...")
        try:
            self.ws_app.close()
        except Exception as exc:
            self.logger.log(f"Disconnect error: {exc}")

    def send_json(self, payload: dict) -> None:
        if not self.connected or self.ws_app is None:
            self.logger.log("Cannot send via WebSocket: not connected.")
            return

        try:
            raw_payload = json.dumps(payload)
            self.ws_app.send(raw_payload)
            self.logger.log(f"Sent WebSocket message: {raw_payload}")
        except Exception as exc:
            self.logger.log(f"WebSocket send error: {exc}")

    def _set_connected(self, value: bool) -> None:
        self.connected = value
        if self.on_status_change:
            self.on_status_change(value)

    def _build_handshake_payload(self) -> dict:
        """Build a handshake payload with device metadata."""
        return {
            "message_type": "handshake",
            "client_id": socket.gethostname(),
            "protocol_version": "1.0",
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "") + "Z",
            "device_name": "IoT-Device-Client",
            "capabilities": ["ping", "login", "subscribe", "echo"],
        }

    def _validate_handshake_response(self, payload: dict) -> bool:
        """Validate incoming handshake response from server."""
        required_fields = ["message_type", "timestamp"]
        if not all(field in payload for field in required_fields):
            self.logger.log("Handshake response validation failed: missing fields")
            return False
        if payload.get("message_type") != "handshake_response":
            return False
        self.logger.log(f"Handshake response validated: {payload}")
        return True

    def _on_open(self, _ws) -> None:
        self._set_connected(True)
        self.logger.log("WebSocket connected.")

        # Send handshake after 100ms delay in a daemon thread
        def send_handshake_delayed() -> None:
            threading.Event().wait(0.1)
            handshake_payload = self._build_handshake_payload()
            self.send_json(handshake_payload)
            self.logger.log(f"Handshake message sent: {json.dumps(handshake_payload)}")

        handshake_thread = threading.Thread(target=send_handshake_delayed, daemon=True)
        handshake_thread.start()

    def _on_message(self, _ws, message: str) -> None:
        # Detect and validate handshake responses
        try:
            msg_obj = json.loads(message)
            if msg_obj.get("message_type") == "handshake_response":
                if self._validate_handshake_response(msg_obj):
                    if self.on_message:
                        self.on_message(message)
                else:
                    self.logger.log("Handshake response validation failed")
                return
        except (json.JSONDecodeError, AttributeError, TypeError):
            pass

        # Handle regular messages
        if self.on_message:
            self.on_message(message)
        else:
            self.logger.log(f"WebSocket received: {message}")

    def _on_error(self, _ws, error) -> None:
        self.logger.log(f"WebSocket error: {error}")

    def _on_close(self, _ws, close_status_code, close_msg) -> None:
        self._set_connected(False)
        self.logger.log(f"WebSocket closed. code={close_status_code}, message={close_msg}")
