"""Connection control panel widget."""

from PyQt6.QtWidgets import (
    QWidget, QGroupBox, QGridLayout, QLineEdit, 
    QPushButton, QLabel
)
from PyQt6.QtCore import pyqtSignal

from personalive_client.config import ClientConfig


class ConnectionPanel(QGroupBox):
    """Panel for server connection controls."""
    
    connect_clicked = pyqtSignal(bool)  # True = connect, False = disconnect
    url_changed = pyqtSignal(str)
    # ref_img_uploaded = pyqtSignal(bool)
    
    def __init__(self, parent=None):
        super().__init__("Connection", parent)
        self._setup_ui()
        
    def _setup_ui(self):
        self.config = ClientConfig()
        layout = QGridLayout(self)
        
        # URL input
        layout.addWidget(QLabel("Server URL:"), 0, 0)
        self.url_input = QLineEdit(self.config.server_url)
        self.url_input.textChanged.connect(self._handle_url_change)
        layout.addWidget(self.url_input, 0, 1)
        
        # Connect button
        self.connect_btn = QPushButton("Connect")
        self.connect_btn.setCheckable(True)
        self.connect_btn.clicked.connect(
            lambda: self.connect_clicked.emit(self.connect_btn.isChecked())
        )
        # self.ref_img_uploaded.connect(lambda uploaded: self.connect_btn.setEnabled(uploaded))
        layout.addWidget(self.connect_btn, 1, 0, 1, 2)
        
        # Status indicator
        self.status_label = QLabel("● Disconnected")
        self.status_label.setStyleSheet("color: #F44336; font-weight: bold;")
        layout.addWidget(self.status_label, 2, 0, 1, 2)
        
        # Client ID display
        self.client_id_label = QLabel("Client ID: Not connected")
        self.client_id_label.setWordWrap(True)
        self.client_id_label.setStyleSheet("font-family: monospace; font-size: 10px; color: #666;")
        layout.addWidget(self.client_id_label, 3, 0, 1, 2)

    def _handle_url_change(self, url: str):
        """Handle user changing the server URL."""
        url = url.strip()
        if url.startswith("https://"):
            url = "wss://" + url[len("https://"):]
        url = url.rstrip('/')
        self.url_changed.emit(url)
        
    def set_connected(self, connected: bool):
        """Update UI for connection state."""
        self.connect_btn.setChecked(connected)
        self.connect_btn.setText("Disconnect" if connected else "Connect")
    
        
    def set_status(self, text: str, color: str):
        """Update status indicator."""
        self.status_label.setText(f"● {text}")
        self.status_label.setStyleSheet(f"color: {color}; font-weight: bold;")
        
    def set_client_id(self, client_id: str):
        """Display client ID."""
        self.config.client_id = client_id # Store client ID in config for access by UI
        short_id = client_id[:8] + "..." if len(client_id) > 8 else client_id
        self.client_id_label.setText(f"Client ID: {short_id}")
        self.client_id_label.setToolTip(f"Full ID: {client_id}")
        
    def get_url(self) -> str:
        """Get current server URL."""
        # return self.url_input.text()
        return self.config.server_url