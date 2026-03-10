"""Webcam control panel."""

from PyQt6.QtWidgets import (
    QWidget, QGroupBox, QGridLayout, 
    QLabel, QComboBox, QSpinBox, QPushButton
)
from PyQt6.QtCore import pyqtSignal

from personalive_client.config import ClientConfig


class WebcamPanel(QGroupBox):
    """Panel for webcam controls."""
    
    start_clicked = pyqtSignal(bool)  # True = start, False = stop
    device_changed = pyqtSignal(int)
    fps_changed = pyqtSignal(int)
    
    def __init__(self, parent=None):
        super().__init__("Webcam", parent)
        self.config = ClientConfig()
        self._setup_ui()
        
    def _setup_ui(self):
        layout = QGridLayout(self)
        
        # Device selection
        layout.addWidget(QLabel("Device:"), 0, 0)
        self.device_combo = QComboBox()
        self.device_combo.addItems([f"Camera {i}" for i in range(5)])
        self.device_combo.currentIndexChanged.connect(self.device_changed.emit)
        layout.addWidget(self.device_combo, 0, 1)
        
        # FPS selection
        layout.addWidget(QLabel("FPS:"), 1, 0)
        self.fps_spin = QSpinBox()
        self.fps_spin.setRange(1, 60)
        self.fps_spin.setValue(self.config.frame_rate)
        self.fps_spin.valueChanged.connect(self.fps_changed.emit)
        layout.addWidget(self.fps_spin, 1, 1)
        
        # Start button
        self.start_btn = QPushButton("Start Webcam")
        self.start_btn.setCheckable(True)
        self.start_btn.clicked.connect(
            lambda: self.start_clicked.emit(self.start_btn.isChecked())
        )
        self.start_btn.setEnabled(False)  # Initially disabled until connection is established
        layout.addWidget(self.start_btn, 2, 0, 1, 2)
        
        # FPS display
        self.fps_label = QLabel("Capture FPS: 0")
        layout.addWidget(self.fps_label, 3, 0, 1, 2)
        
    def set_running(self, running: bool):
        """Update UI for running state."""
        self.start_btn.setChecked(running)
        self.start_btn.setText("Stop Webcam" if running else "Start Webcam")

    def enable_start_btn(self, enabled: bool):
        """Enable or disable the start button."""
        self.start_btn.setEnabled(enabled)
        
    def update_fps(self, fps: float):
        """Update FPS display."""
        self.fps_label.setText(f"Capture FPS: {fps:.1f}")
        
    def get_device_id(self) -> int:
        """Get selected device ID."""
        return self.device_combo.currentIndex()
        
    def get_fps(self) -> int:
        """Get selected FPS."""
        return self.fps_spin.value()