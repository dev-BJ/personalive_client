"""Stream control panel."""

from PyQt6.QtWidgets import (
    QWidget, QGroupBox, QVBoxLayout, QPushButton
)
from PyQt6.QtCore import pyqtSignal

from personalive_client.config import ClientConfig


class StreamPanel(QGroupBox):
    """Panel for stream controls."""
    
    stream_toggled = pyqtSignal(bool)  # True = start, False = stop
    pause_toggled = pyqtSignal(bool)   # True = pause, False = resume
    open_output_clicked = pyqtSignal()
    reset_clicked = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__("Stream Control", parent)
        self._is_streaming = False
        self._is_paused = False
        self.config = ClientConfig()
        self._setup_ui()
        
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Main stream button
        self.stream_btn = QPushButton("▶ Start Streaming")
        self.stream_btn.setEnabled(False)
        self.stream_btn.setStyleSheet(self._get_stream_style(False))
        self.stream_btn.clicked.connect(self._on_stream_click)
        layout.addWidget(self.stream_btn)
        
        # Pause button
        self.pause_btn = QPushButton("⏸ Pause")
        self.pause_btn.setEnabled(False)
        self.pause_btn.clicked.connect(self._on_pause_click)
        layout.addWidget(self.pause_btn)
        
        # Open output window button
        # self.output_btn = QPushButton("Open Output Window")
        # self.output_btn.clicked.connect(self.open_output_clicked.emit)
        # layout.addWidget(self.output_btn)

        # Open output window button
        self.reset_btn = QPushButton("Reset Stream")
        self.reset_btn.setEnabled(False)
        self.reset_btn.clicked.connect(self.reset_clicked.emit)
        layout.addWidget(self.reset_btn)
        
    def _get_stream_style(self, streaming: bool) -> str:
        """Get style sheet for stream button."""
        if streaming:
            return """
                QPushButton {
                    background-color: #f44336;
                    color: white;
                    font-weight: bold;
                    padding: 10px;
                    font-size: 14px;
                }
            """
        else:
            return """
                QPushButton {
                    background-color: #4CAF50;
                    color: white;
                    font-weight: bold;
                    padding: 10px;
                    font-size: 14px;
                }
                QPushButton:disabled {
                    background-color: #ccc;
                }
            """
            
    def _on_stream_click(self):
        """Handle stream button click."""
        self._is_streaming = not self._is_streaming
        self.stream_btn.setText("⏹ Stop Streaming" if self._is_streaming else "▶ Start Streaming")
        self.stream_btn.setStyleSheet(self._get_stream_style(self._is_streaming))
        self.pause_btn.setEnabled(self._is_streaming)
        self.stream_toggled.emit(self._is_streaming)
        
    def _on_pause_click(self):
        """Handle pause button click."""
        self._is_paused = not self._is_paused
        self.pause_btn.setText("▶ Resume" if self._is_paused else "⏸ Pause")
        self.pause_toggled.emit(self._is_paused)
        
    def set_can_stream(self, can_stream: bool):
        """Enable/disable stream button."""
        self.stream_btn.setEnabled(can_stream)
        if self.config.switch:
            self.pause_btn.setEnabled(can_stream and self._is_streaming)
        self.reset_btn.setEnabled(can_stream)
        
    def reset(self):
        """Reset to stopped state."""
        self._is_streaming = False
        self._is_paused = False
        self.stream_btn.setText("▶ Start Streaming")
        self.stream_btn.setStyleSheet(self._get_stream_style(False))
        self.pause_btn.setEnabled(False)
        self.pause_btn.setText("⏸ Pause")
        self.reset_btn.setEnabled(True)