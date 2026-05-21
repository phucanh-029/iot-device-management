import json
import threading
from typing import Callable, Optional

from websocket import WebSocketApp

from utilities import HandshakeValidator


class WebSocketManager:
    def __init__(
        self,
        logger,
        on_message: Optional[Callable[[str], None]] = None,
        on_status_change: Optional[Callable[[bool], None]] = None,
        auto_handshake: bool = True,
    ) -> None:
        self.logger = logger
        self.on_message = on_message
        self.on_status_change = on_status_change
        self.ws_app = None
        self.ws_thread = None
        self.connected = False
        self.auto_handshake = auto_handshake
        self.handshake_payload: Optional[dict] = None

    def connect(self, ws_url: str, handshake_payload: Optional[dict] = None) -> None:
        """
        Connect to WebSocket server.
        
        Args:
            ws_url: WebSocket URL to connect to
            handshake_payload: Optional handshake payload to send on connection.
                              If None and auto_handshake=True, default handshake is used.
        """
        if self.connected:
            self.logger.log("WebSocket is already connected.")
            return

        if not ws_url:
            self.logger.log("WebSocket URL is empty.")
            return

        self.handshake_payload = handshake_payload
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

    def _on_open(self, _ws) -> None:
        self._set_connected(True)
        self.logger.log("WebSocket connected.")
        
        # Auto-send handshake if enabled
        if self.auto_handshake:
            self._send_handshake()

    def _send_handshake(self) -> None:
        """Send handshake message after successful connection."""
        if self.handshake_payload is None:
            # Use default handshake
            self.handshake_payload = HandshakeValidator.get_default_handshake()
        
        # Validate handshake payload
        is_valid, error_msg = HandshakeValidator.validate(self.handshake_payload)
        if not is_valid:
            self.logger.log(f"Handshake validation failed: {error_msg}")
            return
        
        # Send the handshake
        self.logger.log(f"Sending handshake message: {json.dumps(self.handshake_payload)}")
        self.send_json(self.handshake_payload)

    def _on_message(self, _ws, message: str) -> None:
        # Log handshake responses specially
        try:
            msg_obj = json.loads(message)
            if msg_obj.get("action") == "handshake" or "handshake" in message.lower():
                self.logger.log(f"Handshake response received: {message}")
            elif self.on_message:
                self.on_message(message)
            else:
                self.logger.log(f"WebSocket received: {message}")
        except (json.JSONDecodeError, AttributeError):
            # Not JSON or can't parse, use default handler
            if self.on_message:
                self.on_message(message)
            else:
                self.logger.log(f"WebSocket received: {message}")

    def _on_error(self, _ws, error) -> None:
        self.logger.log(f"WebSocket error: {error}")

    def _on_close(self, _ws, close_status_code, close_msg) -> None:
        self._set_connected(False)
        self.logger.log(f"WebSocket closed. code={close_status_code}, message={close_msg}")
