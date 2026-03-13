"""
Main application window.
Coordinates all components and handles business logic.
"""

from importlib.resources import files
import sys
import time
import logging
import mimetypes
import uuid
import base64
import os
from urllib.parse import urlparse

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QSplitter,
    QStatusBar, QApplication, QMessageBox, QSystemTrayIcon, QMenu
)
from PyQt6.QtCore import Qt, pyqtSlot
from PyQt6.QtGui import QKeySequence, QImage
from PyQt6.QtGui import QShortcut
from PyQt6.QtCore import pyqtSignal

import requests
import cv2
import numpy as np

from personalive_client.config import ClientConfig
from personalive_client.enums import ConnectionStatus, LCMLiveStatus
from personalive_client.utils.logging_utils import LogEmitter, QtLogHandler
from personalive_client.utils.image_utils import qimage_to_bytes, bytes_to_qimage, scale_pixmap
from personalive_client.core.websocket_client import WebSocketClient
from personalive_client.core.webcam_capture import WebcamCapture

try:
    import pyvirtualcam
except ImportError:
    pyvirtualcam = None

# from .output_window import OutputWindow
from .widgets.connection_panel import ConnectionPanel
from .widgets.reference_panel import ReferencePanel
from .widgets.webcam_panel import WebcamPanel
from .widgets.stream_panel import StreamPanel
from .widgets.stats_panel import StatsPanel
from .widgets.log_panel import LogPanel


class MainWindow(QMainWindow):
    """
    Main application window managing all components.
    """
    
    def __init__(self):
        super().__init__()
        self.config = ClientConfig()
        
        # Components
        self.ws_client: WebSocketClient = None
        self.webcam: WebcamCapture = None
        # self.output_window: OutputWindow = None
        self.virtual_camera = None  # pyvirtualcam camera instance
        
        # State
        self.is_streaming = False
        self.reference_image_path = None
        self.is_reset_done = False
        
        self._init_ui()
        self._setup_logging()
        self._apply_styles()
        self._setup_tray()
        self._connect_signals()
        
    def _init_ui(self):
        """Initialize user interface."""
        self.setWindowTitle("PersonaLive Python GUI Client - by Phreaker")
        self.setGeometry(100, 100, 1400, 900)
        
        # Central widget with splitter
        central = QWidget()
        self.setCentralWidget(central)
        layout = QHBoxLayout(central)
        
        splitter = QSplitter(Qt.Orientation.Horizontal)
        layout.addWidget(splitter)
        
        # Left panel - Controls
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setSpacing(10)
        
        self.connection_panel = ConnectionPanel()
        # self.connection_panel.ref_img_uploaded.emit(False)

        self.reference_panel = ReferencePanel()
        self.webcam_panel = WebcamPanel()
        self.stream_panel = StreamPanel()
        self.stats_panel = StatsPanel()
        
        left_layout.addWidget(self.connection_panel)
        left_layout.addWidget(self.reference_panel)
        left_layout.addWidget(self.webcam_panel)
        left_layout.addWidget(self.stream_panel)
        left_layout.addWidget(self.stats_panel)
        left_layout.addStretch()
        
        splitter.addWidget(left_widget)
        
        # Center panel - Video feeds (simplified for brevity)
        center_widget = QWidget()
        center_layout = QVBoxLayout(center_widget)
        from PyQt6.QtWidgets import QTabWidget, QLabel
        # self.view_tabs = QTabWidget()
        
        self.webcam_label = QLabel("Webcam feed will appear here")
        self.webcam_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        # self.webcam_label.setMinimumSize(640, 480)
        self.webcam_label.setMinimumSize(350, 480)
        self.webcam_label.setStyleSheet("background-color: #1a1a1a; color: #666;")
        # self.view_tabs.addTab(self.webcam_label, "Webcam")
        center_layout.addWidget(self.webcam_label)
        
        self.processed_label = QLabel("Processed output will appear here")
        self.processed_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        # self.processed_label.setMinimumSize(640, 480)
        self.processed_label.setMinimumSize(350, 480)
        self.processed_label.setStyleSheet("background-color: #1a1a1a; color: #666;")
        # self.view_tabs.addTab(self.processed_label, "Processed")
        center_layout.addWidget(self.processed_label)
        
        # center_layout.addWidget(self.view_tabs)
        splitter.addWidget(center_widget)
        
        # Right panel - Logs
        self.log_panel = LogPanel()
        splitter.addWidget(self.log_panel)
        
        # Set proportions
        splitter.setSizes([300, 700, 400])
        
        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")
        
        # Shortcuts
        QShortcut(QKeySequence("Ctrl+Q"), self, self.close)
        QShortcut(QKeySequence("Space"), self, self._toggle_stream_shortcut)
        
    def _connect_signals(self):
        """Connect widget signals to handlers."""
        # Connection panel
        self.connection_panel.connect_clicked.connect(self._handle_connection)
        self.connection_panel.url_changed.connect(lambda url: setattr(self.config, 'server_url', url))
        
        # Reference panel
        self.reference_panel.image_loaded.connect(self._handle_image_loaded)
        self.reference_panel.image_cleared.connect(self._handle_image_cleared)
        
        # Webcam panel
        self.webcam_panel.start_clicked.connect(self._handle_webcam)
        # update fps display when user changes desired capture rate
        self.webcam_panel.fps_changed.connect(self._handle_fps_changed)
        
        # Stream panel
        self.stream_panel.stream_toggled.connect(self._handle_stream_toggle)
        self.stream_panel.pause_toggled.connect(self._handle_pause_toggle)
        # self.stream_panel.open_output_clicked.connect(self._show_output_window)
        self.stream_panel.reset_clicked.connect(self._handle_stream_reset)  # reuse stream toggle for reset (stop streaming)
        
    def _setup_logging(self):
        """Setup logging to GUI."""
        self.log_emitter = LogEmitter()
        self.log_emitter.log_message.connect(self.log_panel.append_log)
        
        handler = QtLogHandler(self.log_emitter)
        handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%H:%M:%S'
        ))
        logging.getLogger().addHandler(handler)
        logging.getLogger().setLevel(logging.INFO)
        
    def _apply_styles(self):
        """Apply application styles."""
        self.setStyleSheet("""
            QMainWindow { background-color: #f5f5f5; }
            QGroupBox {
                font-weight: bold;
                border: 1px solid #ddd;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
            QPushButton {
                padding: 8px 16px;
                border-radius: 4px;
                background-color: #2196F3;
                color: white;
                border: none;
            }
            QPushButton:hover { background-color: #1976D2; }
            QPushButton:pressed { background-color: #0D47A1; }
            QPushButton:disabled { background-color: #ccc; color: #666; }
            QLineEdit, QSpinBox, QComboBox {
                padding: 6px;
                border: 1px solid #ddd;
                border-radius: 4px;
            }
            QTextEdit { border: 1px solid #ddd; border-radius: 4px; }
            QLabel { color: #333; }
        """)
        
    def _setup_tray(self):
        """Setup system tray icon."""
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(QApplication.style().standardIcon(
            QApplication.style().StandardPixmap.SP_ComputerIcon
        ))
        
        menu = QMenu()
        menu.addAction("Show", self.show)
        menu.addAction("Hide", self.hide)
        menu.addSeparator()
        menu.addAction("Quit", self.close)
        
        self.tray_icon.setContextMenu(menu)
        self.tray_icon.activated.connect(self._tray_activated)
        self.tray_icon.show()
        
    @pyqtSlot(QSystemTrayIcon.ActivationReason)
    def _tray_activated(self, reason: QSystemTrayIcon.ActivationReason):
        """Handle tray icon activation."""
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.show()
            
    # ===== Event Handlers =====
    
    def _handle_connection(self, connect: bool):
        """Handle connect/disconnect button."""
        if connect:
            self.config.server_url = self.connection_panel.get_url()
            self.ws_client = WebSocketClient(self.config)
            
            # Connect signals
            self.ws_client.connection_status_changed.connect(
                self.connection_panel.set_status
            )
            self.ws_client.connection_status_changed.connect(
                self._on_connection_status_changed
            )
            self.ws_client.retry_failed.connect(lambda: self.connection_panel.set_connected(False))
            self.ws_client.frame_received.connect(self._handle_processed_frame)
            self.ws_client.log_message.connect(self.log_panel.append_log)
            self.ws_client.error_occurred.connect(self._handle_error)
            self.ws_client.client_id_received.connect(
                self.connection_panel.set_client_id
            )
            self.ws_client.stats_updated.connect(self.stats_panel.update_stats)
            
            self.ws_client.start()
            self.connection_panel.set_connected(True)
        else:
            if self.ws_client:
                self.ws_client.stop()
                self.ws_client = None
            self.connection_panel.set_connected(False)
            self.connection_panel.set_status("Disconnected", "#F44336")
            self.stream_panel.set_can_stream(False)
            
    def _on_connection_status_changed(self, status: str, color: str):
        """Handle connection status changes."""
        if "Connected" in status and "Reconnecting" not in status:
            self.reference_panel.enable_load_btn(True)
            self.reference_panel.enable_clear_btn(True)
            self.stream_panel.set_can_stream(True)
            self.webcam_panel.enable_start_btn(True)
        else:
            self.stream_panel.reset()
            self.connection_panel.client_id_label.setText("Client ID: Not connected")
            self.reference_panel.enable_load_btn(False)
            self.reference_panel.enable_clear_btn(False)
            self._handle_webcam(False)
            from PyQt6.QtGui import QPixmap
            self.webcam_label.setPixmap(QPixmap())
            self.webcam_label.setText("Webcam feed will appear here")
            self._cleanup_virtual_camera()
            # self._hide_output_window()
            
    def _handle_webcam(self, start: bool):
        """Handle webcam start/stop."""
        if start:
            device_id = self.webcam_panel.get_device_id()
            fps = self.webcam_panel.get_fps()
            
            self.webcam = WebcamCapture(device_id, fps)
            self.webcam.frame_captured.connect(self._update_webcam_view)
            self.webcam.error_occurred.connect(self._handle_error)
            self.webcam.fps_updated.connect(self.webcam_panel.update_fps)
            self.webcam.start()
            
            self.webcam_panel.set_running(True)
            self.webcam_panel.enable_start_btn(True)
            self.log_panel.append_log(f"Webcam started (Device {device_id}, {fps} FPS)")
        else:
            if self.webcam:
                self.webcam.stop()
                self.webcam = None
            self.webcam_panel.set_running(False)
            self.webcam_panel.enable_start_btn(False)
            from PyQt6.QtGui import QPixmap
            self.webcam_label.setPixmap(QPixmap())
            self.webcam_label.setText("Webcam feed will appear here")
            
    def _handle_fps_changed(self, fps: int):
        """Handle user changing the desired capture FPS."""
        # update label immediately
        self.webcam_panel.update_fps(fps)
        self.config.frame_rate = fps
        # if webcam is running, update capture settings
        if self.webcam:
            self.webcam.target_fps = self.config.frame_rate
            # also adjust internal frame interval used for throttling
            self.webcam._frame_interval = 1.0 / fps

    def _update_webcam_view(self, qt_image, frame):
        """Update webcam display and send to server if streaming."""
        from PyQt6.QtGui import QPixmap
        pixmap = QPixmap.fromImage(qt_image)
        # scaled = scale_pixmap(pixmap, self.webcam_label.size())
        self.webcam_label.setPixmap(pixmap.scaled(
            self.webcam_label.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation
        ))
        self.webcam_label.setText("")
        
        if self.is_streaming and self.ws_client and self.ws_client.lcm_status == LCMLiveStatus.SEND_FRAME:
            try:
                # frame_bytes = qimage_to_bytes(qt_image, self.config.jpeg_quality)
                _, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, self.config.jpeg_quality])
                self.ws_client.send_frame(buf.tobytes())
            except Exception as e:
                self._handle_error(f"Frame send error: {e}")

    def _init_virtual_camera(self):
        # Initialize virtual camera for OBS if available
        if pyvirtualcam and not self.virtual_camera:
            try:
                # Use processed label size as virtual camera resolution
                width = max(640, self.processed_label.width())
                height = max(480, self.processed_label.height())
                self.virtual_camera = pyvirtualcam.Camera(width=width, height=height, fps=30)
                self.virtual_camera.__enter__()
                self.log_panel.append_log(f"Virtual camera started: {width}x{height} @ 30fps")
            except Exception as e:
                self.log_panel.append_error(f"Failed to start virtual camera: {e}")
                self.virtual_camera = None

    def _cleanup_virtual_camera(self):
        # Cleanup virtual camera
        if self.virtual_camera and pyvirtualcam:
            try:
                self.virtual_camera.__exit__(None, None, None)
                self.virtual_camera = None
                self.log_panel.append_log("Virtual camera stopped")
            except Exception as e:
                self.log_panel.append_error(f"Error stopping virtual camera: {e}")

    def _update_virtual_camera_frame(self, frame_bytes: bytes):
        # Send to virtual camera if OBS capture is enabled
        if self.virtual_camera and pyvirtualcam:
            try:
                nparr = np.frombuffer(frame_bytes, np.uint8)
                frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                if frame is not None:
                    if frame.shape[:2] != (self.virtual_camera.height, self.virtual_camera.width):
                        frame = cv2.resize(frame, (self.virtual_camera.width, self.virtual_camera.height))

                # Convert BGR → RGB for pyvirtualcam
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

                self.virtual_camera.send(frame_rgb)
            except Exception as e:
                # print(f"Virtual camera send error: {e}")
                self.log_panel.append_error(f"Virtual camera send error: {e}")
                
    def _handle_stream_toggle(self, start: bool):
        """Handle stream start/stop."""
        self.is_streaming = start
        if start:
            if not self.webcam or not self.webcam.isRunning():
                QMessageBox.warning(self, "Warning", "Please start webcam first!")
                self.stream_panel.reset()
                return
            if self.is_reset_done:
                self.ws_client.set_lcm_status(LCMLiveStatus.SEND_FRAME)
                self.is_reset_done = False
            
            self._init_virtual_camera()
                    
            self.log_panel.append_log("Streaming started")
        else:
            self._cleanup_virtual_camera()
                    
            self.log_panel.append_log("Streaming stopped")
            
    def _handle_pause_toggle(self, paused: bool):
        """Handle pause/resume."""
        if self.ws_client:
            if paused:
                self.ws_client.send_pause()
            else:
                self.ws_client.send_resume()
                
    def _toggle_stream_shortcut(self):
        """Handle spacebar shortcut."""
        if self.stream_panel.stream_btn.isEnabled():
            self.stream_panel.stream_btn.click()

    def _handle_stream_reset(self):
        """Handle stream reset."""
        try:
            if self.config.switch:
                server_url = self.config.server_url
                if server_url.startswith("ws://"):
                    base_url = "http://" + server_url[len("ws://"):]
                elif server_url.startswith("wss://"):
                    base_url = "https://" + server_url[len("wss://"):]
                else:
                    parsed = urlparse(server_url)
                    base_url = f"{parsed.scheme}://{parsed.netloc}" if parsed.netloc else server_url

                reset_url = f"{base_url.rstrip('/')}/api/reset"

                response = requests.post(reset_url)
                if response.status_code < 200 or response.status_code >= 300:
                    self.reference_panel._clear_image()
                    raise RuntimeError(f"Reset failed with status {response.status_code}")
                
                self.ws_client.set_lcm_status(LCMLiveStatus.WAIT)
            else:
                self.ws_client.send_cmd({"cmd": "reset"})

            if not self.is_reset_done:
                self.is_reset_done = True
            
            self.reference_panel._clear_image()
            self.stream_panel.reset()
        except Exception as e:
            self._handle_error(f"Stream reset error: {e}")

    def _handle_image_loaded(self, filepath: str):
        """Handle reference image selection."""
        self.reference_image_path = filepath
        self.log_panel.append_log(f"Loaded reference image: {filepath}")
        
        try:
            if self.config.switch:
                server_url = self.config.server_url
                if server_url.startswith("ws://"):
                    base_url = "http://" + server_url[len("ws://"):]
                elif server_url.startswith("wss://"):
                    base_url = "https://" + server_url[len("wss://"):]
                else:
                    parsed = urlparse(server_url)
                    base_url = f"{parsed.scheme}://{parsed.netloc}" if parsed.netloc else server_url

                client_id = self.config.client_id
                # upload_url = f"{base_url.rstrip('/')}/api/upload_reference_image/{client_id}"
                upload_url = f"{base_url.rstrip('/')}/api/upload_reference_image"
                filename = "reference.jpg"

                image_bytes = qimage_to_bytes(QImage(filepath), quality=95)

                files = {
                    "ref_image": (filename, image_bytes, "image/jpeg")
                }

                response = requests.post(upload_url, files=files)
                if response.status_code < 200 or response.status_code >= 300:
                    self.reference_panel._clear_image()
                    raise RuntimeError(f"Upload failed with status {response.status_code}: {response.text}")
            else:
                if filepath and os.path.exists(filepath):
                    # Load source image
                    source = cv2.imread(filepath)
                else:
                    print("Invalid source image path.")
                    return
                # Encode source image
                _, encoded = cv2.imencode('.jpg', source, [int(cv2.IMWRITE_JPEG_QUALITY), 95])
                b64 = base64.b64encode(encoded).decode('utf-8')
        
                self.ws_client.send_cmd({"cmd": "init", "image": b64})

            # self.connection_panel.ref_img_uploaded.emit(True)
            self.log_panel.append_log("Reference image uploaded to server")
        except Exception as e:
            self.reference_panel._clear_image()
            self._handle_error(f"Reference image upload failed: {e}")
        
    def _handle_image_cleared(self):
        """Handle reference image clear."""
        self.reference_image_path = None
        # self.connection_panel.ref_img_uploaded.emit(False)
        self.log_panel.append_log("Reference image cleared")
        
    def _handle_processed_frame(self, frame_bytes: bytes):
        """Handle incoming processed frame."""
        try:
            # Decode frame for display
            qt_image = bytes_to_qimage(frame_bytes)
            from PyQt6.QtGui import QPixmap
            pixmap = QPixmap.fromImage(qt_image)
            scaled = scale_pixmap(pixmap, self.processed_label.size())
            self.processed_label.setPixmap(scaled)
            
            self._update_virtual_camera_frame(frame_bytes)
                    
        except Exception as e:
            self._handle_error(f"Frame processing error: {e}")
            
    def _handle_error(self, message: str):
        """Handle error messages."""
        self.log_panel.append_error(message)
        self.status_bar.showMessage(f"Error: {message}", 5000)
        logging.error(message)
        
    def _show_output_window(self):
        """Show or create output window."""
        if not self.output_window:
            self.output_window = OutputWindow()
        self.output_window.show()
        self.output_window.raise_()
        self.output_window.activateWindow()

    def _hide_output_window(self):
        """Hide output window."""
        if self.output_window:
            self.output_window.hide()
        
    def closeEvent(self, event):
        """Cleanup on close."""
        if self.webcam:
            self.webcam.stop()
        if self.ws_client:
            self.ws_client.stop()
        # if self.output_window:
        #     self.output_window.close()
        if self.virtual_camera and pyvirtualcam:
            try:
                self.virtual_camera.__exit__(None, None, None)
            except Exception as e:
                print(f"Error closing virtual camera: {e}")
        self.tray_icon.hide()
        event.accept()
