"""Log and error display panel."""

from PyQt6.QtWidgets import (
    QWidget, QGroupBox, QVBoxLayout, QHBoxLayout,
    QTextEdit, QPushButton, QCheckBox, QFileDialog
)
from PyQt6.QtGui import QFont, QTextCursor
from PyQt6.QtCore import pyqtSignal


class LogPanel(QWidget):
    """Panel for logs and errors."""
    
    save_logs_clicked = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Logs group
        log_group = QGroupBox("Server Logs")
        log_layout = QVBoxLayout(log_group)
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("Consolas", 9))
        log_layout.addWidget(self.log_text)
        
        # Log controls
        log_controls = QHBoxLayout()
        
        self.clear_btn = QPushButton("Clear")
        self.clear_btn.clicked.connect(self.log_text.clear)
        log_controls.addWidget(self.clear_btn)
        
        self.save_btn = QPushButton("Save Logs")
        self.save_btn.clicked.connect(self._save_logs)
        log_controls.addWidget(self.save_btn)
        
        self.auto_scroll = QCheckBox("Auto-scroll")
        self.auto_scroll.setChecked(True)
        log_controls.addWidget(self.auto_scroll)
        
        log_layout.addLayout(log_controls)
        layout.addWidget(log_group)
        
        # Errors group
        error_group = QGroupBox("Errors")
        error_layout = QVBoxLayout(error_group)
        
        self.error_text = QTextEdit()
        self.error_text.setReadOnly(True)
        self.error_text.setMaximumHeight(150)
        self.error_text.setStyleSheet("""
            QTextEdit {
                background-color: #ffebee;
                color: #c62828;
                border: 1px solid #ef5350;
            }
        """)
        error_layout.addWidget(self.error_text)
        
        self.clear_error_btn = QPushButton("Clear Errors")
        self.clear_error_btn.clicked.connect(self.error_text.clear)
        error_layout.addWidget(self.clear_error_btn)
        
        layout.addWidget(error_group)
        
    def append_log(self, message: str):
        """Append message to log."""
        self.log_text.append(message)
        if self.auto_scroll.isChecked():
            self.log_text.verticalScrollBar().setValue(
                self.log_text.verticalScrollBar().maximum()
            )
            
    def append_error(self, message: str):
        """Append error message."""
        import time
        timestamp = time.strftime("%H:%M:%S")
        self.error_text.append(f"[{timestamp}] {message}")
        
    def get_logs(self) -> str:
        """Get all log text."""
        return self.log_text.toPlainText()
        
    def _save_logs(self):
        """Save logs to file."""
        filename, _ = QFileDialog.getSaveFileName(
            self, "Save Logs", "personalive_logs.txt", "Text Files (*.txt)"
        )
        if filename:
            with open(filename, 'w') as f:
                f.write(self.get_logs())