"""Status enumerations for the application."""

from enum import Enum


class ConnectionStatus(Enum):
    """WebSocket connection states."""
    DISCONNECTED = "Disconnected"
    CONNECTING = "Connecting..."
    CONNECTED = "Connected"
    PAUSED = "Paused"
    ERROR = "Error"
    RECONNECTING = "Reconnecting..."


class StreamStatus(Enum):
    """Video streaming states."""
    STOPPED = "Stopped"
    STREAMING = "Streaming"
    BUFFERING = "Buffering"


class LCMLiveStatus:
    """Status constants matching server protocol."""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    SEND_FRAME = "send_frame"
    WAIT = "wait"
    TIMEOUT = "timeout"
    PAUSED = "paused"
    ERROR = "error"