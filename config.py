"""Application configuration settings."""

from dataclasses import dataclass


@dataclass
class ClientConfig:
    """Client configuration settings."""
    server_url: str = "ws://localhost:8765"
    client_id: str | None = None
    max_reconnect_attempts: int = 5
    reconnect_delay: float = 3.0
    frame_rate: int = 15
    jpeg_quality: int = 65
    enable_auto_reconnect: bool = True
    max_frame_queue_size: int = 3
    switch = False