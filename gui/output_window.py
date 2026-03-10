"""
Dedicated output window for OBS capture.
Clean, minimal UI showing only the processed video.
"""

import time
import numpy as np
import cv2

from PyQt6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QLabel
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QImage, QPixmap, QFont


class OutputWindow(QMainWindow):
    """
    Clean output window designed for OBS screen capture.
    Features:
    - Always on top option
    - FPS counter
    - Resolution display
    - Dark background for better visibility
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("PersonaLive Output - OBS Source")
        self.setGeometry(100, 100, 640, 480)
        self.setMinimumSize(320, 240)
        
        # Setup UI
        self._setup_ui()
        
        # Statistics
        self.frame_count = 0
        self.last_time = time.time()
        self.current_fps = 0
        
        # Window flags for OBS capture
        self.setWindowFlags(
            self.windowFlags() | 
            Qt.WindowType.WindowStaysOnTopHint
        )
        # Hint that the window paints its own contents (may help Xwayland/Wayland capture)
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, True)
        
    def _setup_ui(self):
        """Create window layout."""
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Main image display
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        # make sure the widget is fully opaque and forces paint events
        self.image_label.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, True)
        self.image_label.setStyleSheet("background-color: #1a1a1a; color: #666;")
        self.image_label.setText("Waiting for processed frames...")
        self.image_label.setFont(QFont("Arial", 14))
        layout.addWidget(self.image_label, stretch=1)
        
        # Info bar at bottom
        self.info_bar = QLabel("FPS: 0 | Resolution: -")
        self.info_bar.setStyleSheet("""
            QLabel {
                background-color: rgba(0, 0, 0, 180);
                color: white;
                padding: 5px 10px;
                font-family: monospace;
                font-size: 12px;
            }
        """)
        layout.addWidget(self.info_bar)
        
    def update_frame(self, image_bytes: bytes):
        """
        Update displayed frame from JPEG bytes.
        
        Args:
            image_bytes: JPEG encoded image data
        """
        try:
            # Decode JPEG
            nparr = np.frombuffer(image_bytes, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            if img is None:
                return
                
            # Convert to QImage
            rgb_img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb_img.shape
            bytes_per_line = ch * w
            qt_image = QImage(rgb_img.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
            pixmap = QPixmap.fromImage(qt_image)
            
            # Scale to fit window
            scaled = pixmap.scaled(
                self.image_label.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            # clear previous content and force repaint/commit so compositor sees each frame
            self.image_label.clear()
            self.image_label.setPixmap(scaled)
            self.image_label.repaint()
            self.update()
            
            # Update statistics
            self._update_stats(w, h)
        except Exception as e:
            print(f"Frame display error: {e}")
            
    def _update_stats(self, width: int, height: int):
        """Update FPS and resolution display."""
        self.frame_count += 1
        current_time = time.time()
        
        if current_time - self.last_time >= 1.0:
            self.current_fps = self.frame_count
            self.frame_count = 0
            self.last_time = current_time
            
        self.info_bar.setText(
            f"FPS: {self.current_fps} | Resolution: {width}x{height} | "
            f"Window: {self.width()}x{self.height()}"
        )
        
    def resizeEvent(self, event):
        """Handle window resize."""
        super().resizeEvent(event)
        # Update window size in info bar
        text = self.info_bar.text()
        if "Window:" in text:
            base = text.split(" | Window:")[0]
            self.info_bar.setText(f"{base} | Window: {self.width()}x{self.height()}")