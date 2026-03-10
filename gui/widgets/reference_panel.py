"""Reference image panel widget."""

from PyQt6.QtWidgets import (
    QWidget, QGroupBox, QVBoxLayout, 
    QHBoxLayout, QPushButton, QLabel, QFileDialog
)
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QPixmap, QImage
from PIL import Image


class ReferencePanel(QGroupBox):
    """Panel for reference image selection."""
    
    image_loaded = pyqtSignal(str)  # filepath
    image_cleared = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__("Reference Image", parent)
        self._current_image = None
        self._setup_ui()
        
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Image display
        self.image_label = QLabel("No image selected")
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setMinimumHeight(200)
        self.image_label.setStyleSheet("""
            QLabel {
                background-color: #f0f0f0;
                border: 2px dashed #ccc;
                border-radius: 8px;
            }
        """)
        layout.addWidget(self.image_label)
        
        # Buttons
        btn_layout = QHBoxLayout()
        
        self.load_btn = QPushButton("Load Image")
        self.load_btn.clicked.connect(self._load_image)
        self.load_btn.setEnabled(False)
        btn_layout.addWidget(self.load_btn)
        
        self.clear_btn = QPushButton("Clear")
        self.clear_btn.clicked.connect(self._clear_image)
        self.clear_btn.setEnabled(False)
        btn_layout.addWidget(self.clear_btn)
        
        layout.addLayout(btn_layout)
        
    def _load_image(self):
        """Open file dialog and load image."""
        filename, _ = QFileDialog.getOpenFileName(
            self, "Select Reference Image", "", 
            "Images (*.png *.jpg *.jpeg *.bmp *.webp)"
        )
        if filename:
            try:
                self._display_image(filename)
                self.image_loaded.emit(filename)
            except Exception as e:
                self.image_label.setText(f"Error: {str(e)}")
                
    def _display_image(self, filepath: str):
        """Load and display image thumbnail."""
        image = Image.open(filepath)
        self._current_image = image
        
        # Create thumbnail
        thumb = image.copy()
        thumb.thumbnail((300, 300))
        
        # Convert to QPixmap
        if thumb.mode != 'RGB':
            thumb = thumb.convert('RGB')
            
        data = thumb.tobytes()
        qimage = QImage(data, thumb.width, thumb.height, QImage.Format.Format_RGB888)
        pixmap = QPixmap.fromImage(qimage)
        
        self.image_label.setPixmap(pixmap.scaled(self.image_label.width(), self.image_label.height(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        self.image_label.setText("")
        
    def _clear_image(self):
        """Clear current image."""
        self._current_image = None
        self.image_label.setPixmap(QPixmap())
        self.image_label.setText("No image selected")
        self.image_cleared.emit()
        
    def get_current_image(self):
        """Return current PIL Image."""
        return self._current_image
    
    def enable_load_btn(self, enabled: bool):
        """Enable or disable the load button."""
        self.load_btn.setEnabled(enabled)

    def enable_clear_btn(self, enabled: bool):
        """Enable or disable the clear button."""
        self.clear_btn.setEnabled(enabled)