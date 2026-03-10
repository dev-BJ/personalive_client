"""
WebSocket client for server communication.
Handles connection, reconnection, and message protocol.
"""

import json
import asyncio
import websockets
import threading
import queue
import time
import uuid
from typing import Optional, Dict, Any

from PyQt6.QtCore import QThread, pyqtSignal, QMutex, QMutexLocker

from personalive_client.config import ClientConfig
from personalive_client.enums import ConnectionStatus, LCMLiveStatus


class WebSocketClient(QThread):
    """
    Asynchronous WebSocket client running in separate thread.
    
    Signals:
        connection_status_changed: Emitted when connection state changes (status, color)
        frame_received: Emitted when binary frame received (bytes)
        log_message: Emitted for log messages (str)
        error_occurred: Emitted on errors (str)
        client_id_received: Emitted when client ID confirmed (str)
        stats_updated: Emitted with statistics dict (dict)
    """
    
    # Signals
    connection_status_changed = pyqtSignal(str, str)
    retry_failed = pyqtSignal()  # Emitted when reconnection attempts are exhausted
    # lcm_status_changed = pyqtSignal(str)
    frame_received = pyqtSignal(bytes)
    log_message = pyqtSignal(str)
    error_occurred = pyqtSignal(str)
    client_id_received = pyqtSignal(str)
    stats_updated = pyqtSignal(dict)
    
    def __init__(self, config: ClientConfig):
        super().__init__()
        self.config = config
        self.client_id = str(uuid.uuid4())
        
        # Connection objects
        self.websocket: Optional[websockets.WebSocketClientProtocol] = None
        self.loop: Optional[asyncio.AbstractEventLoop] = None
        
        # State
        self._running = False
        self._status = ConnectionStatus.DISCONNECTED
        self._lcm_status = LCMLiveStatus.WAIT
        self._mutex = QMutex()
        self.reconnect_count = 0
        
        # Frame queue for sending
        self.frame_queue = queue.Queue(maxsize=config.max_frame_queue_size)
        
        # Statistics
        self.stats = {
            'frames_sent': 0,
            'frames_received': 0,
            'bytes_sent': 0,
            'bytes_received': 0,
            'latency_ms': 0
        }
        
    @property
    def running(self) -> bool:
        with QMutexLocker(self._mutex):
            return self._running
            
    @running.setter
    def running(self, value: bool):
        with QMutexLocker(self._mutex):
            self._running = value
            
    @property
    def status(self) -> ConnectionStatus:
        with QMutexLocker(self._mutex):
            return self._status
            
    def set_status(self, status: ConnectionStatus):
        """Update status and emit signal with appropriate color."""
        with QMutexLocker(self._mutex):
            self._status = status
            
        color_map = {
            ConnectionStatus.CONNECTED: "#4CAF50",
            ConnectionStatus.CONNECTING: "#FFC107",
            ConnectionStatus.DISCONNECTED: "#F44336",
            ConnectionStatus.ERROR: "#F44336",
            ConnectionStatus.RECONNECTING: "#FF9800",
            ConnectionStatus.PAUSED: "#2196F3"
        }
        color = color_map.get(status, "#000000")
        self.connection_status_changed.emit(status.value, color)

    @property
    def lcm_status(self) -> LCMLiveStatus:
        with QMutexLocker(self._mutex):
            return self._lcm_status
            
    def set_lcm_status(self, status: LCMLiveStatus):
        """Update status and emit signal with appropriate color."""
        with QMutexLocker(self._mutex):
            self._lcm_status = status
            
        # color_map = {
        #     LCMLiveStatus.WAIT: "#4CAF50",
        #     LCMLiveStatus.SEND_FRAME: "#FFC107",
        #     LCMLiveStatus.PAUSED: "#F44336"
        # }
        # color = color_map.get(status, "#000000")
        # self.lcm_status_changed.emit(status.value)
        
    async def connect(self):
        """Main connection loop with reconnection support."""
        uri = None
        if self.config.switch:
            uri = f"{self.config.server_url}/api/ws/{self.client_id}"
        else:
            uri = f"{self.config.server_url}/ws/{self.client_id}"
        self.set_status(ConnectionStatus.CONNECTING)
        self.log_message.emit(f"Connecting to {uri}...")
        
        try:
            self.websocket = await websockets.connect(
                uri,
                ping_interval=20,
                ping_timeout=60,
                max_queue=32,
                write_limit=2**20
            )
            self.reconnect_count = 0
            self.set_status(ConnectionStatus.CONNECTED)
            self.client_id_received.emit(self.client_id)
            self.log_message.emit(f"Connected with ID: {self.client_id[:8]}...")
            
            # Start sender and receiver tasks
            sender_task = asyncio.create_task(self._send_frames_loop())
            receiver_task = asyncio.create_task(self._receive_loop())
            
            # await asyncio.gather(sender_task, receiver_task)
            done, pending = await asyncio.wait(
                [sender_task, receiver_task],
                return_when=asyncio.FIRST_EXCEPTION
            )

            for task in pending:
                task.cancel()
            
        except Exception as e:
            self.handle_error(f"Connection failed: {str(e)}")
            await self._handle_reconnection()
            
    async def _handle_reconnection(self):
        """Handle reconnection logic."""
        if (self.config.enable_auto_reconnect and 
            self.reconnect_count < self.config.max_reconnect_attempts):
            self.reconnect_count += 1
            self.set_status(ConnectionStatus.RECONNECTING)
            self.log_message.emit(
                f"Reconnecting in {self.config.reconnect_delay}s... "
                f"(attempt {self.reconnect_count}/{self.config.max_reconnect_attempts})"
            )
            await asyncio.sleep(self.config.reconnect_delay)
            if self.running:
                await self.connect()
        else:
            self.set_status(ConnectionStatus.ERROR)
            self.retry_failed.emit()
            
    async def _send_frames_loop(self):
        while self.running and self.websocket:
            try:
                frame_data = None

                try:
                    frame_data = self.frame_queue.get_nowait()
                except queue.Empty:
                    await asyncio.sleep(0.002)
                    continue

                start_time = time.time()

                await self.websocket.send(frame_data)

                self.stats['frames_sent'] += 1
                self.stats['bytes_sent'] += len(frame_data)
                self.stats['latency_ms'] = (time.time() - start_time) * 1000
                self.stats_updated.emit(self.stats.copy())

                # IMPORTANT: yield to event loop
                await asyncio.sleep(0)

            except Exception as e:
                self.handle_error(f"Send error: {str(e)}")
                break
                
    async def _receive_loop(self):
        """Background loop to receive messages."""
        while self.running and self.websocket:
            try:
                message = await self.websocket.recv()
                
                if isinstance(message, str):
                    # print(f"Received text message: {message[:100]}...")
                    await self._handle_text_message(message)
                else:
                    self.stats['frames_received'] += 1
                    self.stats['bytes_received'] += len(message)
                    self.frame_received.emit(message)
                    self.stats_updated.emit(self.stats.copy())
                    
            except websockets.exceptions.ConnectionClosed:
                self.log_message.emit("Connection closed by server")
                self.set_status(ConnectionStatus.DISCONNECTED)
                break
            except Exception as e:
                self.handle_error(f"Receive error: {str(e)}")
                break
                
    async def _handle_text_message(self, message: str):
        """Parse and handle text control messages."""
        try:
            data = json.loads(message)
            status = None
            if self.config.switch:
                status = data.get('status')
            else:
                status = data.get('type')
            
            handlers = {
                'connected': lambda: self._handle_connect_handler(),
                'send_frame': lambda: self.set_lcm_status(LCMLiveStatus.SEND_FRAME),
                'wait': lambda: self.set_lcm_status(LCMLiveStatus.WAIT),
                'timeout': lambda: self.handle_error("Server timeout"),
                'error': lambda: self.handle_error(f"Server error: {data.get('message') or data.get('msg') }"),
                'pause': lambda: self.set_lcm_status(LCMLiveStatus.PAUSED),
                'ready': lambda: self.set_lcm_status(LCMLiveStatus.SEND_FRAME),
                'reset': lambda: self.set_lcm_status(LCMLiveStatus.WAIT),
                'ping': lambda: self.send_cmd({"type": "pong"})
            }
            
            handler = handlers.get(status)
            if handler:
                handler()
            else:
                self.log_message.emit(f"Unknown status: {status}")
                
        except json.JSONDecodeError:
            self.log_message.emit(f"Received text: {message}")

    def _handle_connect_handler(self):
        """Handle server 'connected' status."""
        self.set_status(ConnectionStatus.CONNECTED)
        self.log_message.emit("Connection confirmed by server")
            
    def handle_error(self, message: str):
        """Log error and emit signal."""
        self.log_message.emit(f"ERROR: {message}")
        self.error_occurred.emit(message)
        
    def send_frame(self, frame_bytes: bytes):
        """
        Queue frame for sending (thread-safe).
        Drops oldest frame if queue is full.
        """
        try:
            if self.frame_queue.full():
                self.frame_queue.get_nowait()
            self.frame_queue.put_nowait(frame_bytes)
        except queue.Full:
            pass
            
    async def _send_control(self, command: Dict[str, Any]):
        """Send control message to server."""
        if self.websocket:
            try:
                await self.websocket.send(json.dumps(command))
            except Exception as e:
                self.handle_error(f"Control send failed: {str(e)}")

    def send_cmd(self, cmd: Dict[str, Any]):
        """Send ref image."""
        if self.loop and not self.loop.is_closed():
            asyncio.run_coroutine_threadsafe(
                self._send_control(cmd), 
                self.loop
            )
                
    def send_pause(self):
        """Send pause command."""
        if self.loop and not self.loop.is_closed():
            asyncio.run_coroutine_threadsafe(
                self._send_control({"status": "pause"}), 
                self.loop
            )
            
    def send_resume(self):
        """Send resume command."""
        if self.loop and not self.loop.is_closed():
            asyncio.run_coroutine_threadsafe(
                self._send_control({"status": "resume"}), 
                self.loop
            )
            
    def run(self):
        """Thread entry point."""
        self.running = True
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        
        try:
            self.loop.run_until_complete(self.connect())
        finally:
            self.loop.close()
            self.running = False
            
    def stop(self):
        """Stop the client gracefully."""
        self.running = False
        if self.loop and not self.loop.is_closed() and self.websocket:
            asyncio.run_coroutine_threadsafe(self.websocket.close(), self.loop)
        self.wait(2000)