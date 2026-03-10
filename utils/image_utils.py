"""Image conversion utilities."""

import io
import cv2
import numpy as np
from PIL import Image
from PyQt6.QtGui import QImage, QPixmap


def qimage_to_bytes(qt_image: QImage, quality: int = 85) -> bytes:
    """
    Convert QImage to JPEG bytes for transmission.
    
    Args:
        qt_image: Source QImage
        quality: JPEG quality (0-100)
        
    Returns:
        JPEG encoded bytes
    """
    try:
        buffer = io.BytesIO()
        pil_image = Image.fromqimage(qt_image)
        pil_image.save(buffer, format='JPEG', quality=quality)
        return buffer.getvalue()
    except Exception as e:
        raise ValueError(f"Failed to convert image: {e}")


def bytes_to_qimage(frame_bytes: bytes) -> QImage:
    """
    Convert JPEG bytes to QImage.
    
    Args:
        frame_bytes: JPEG encoded bytes
        
    Returns:
        QImage object
    """
    try:
        nparr = np.frombuffer(frame_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is None:
            raise ValueError("Failed to decode image")
            
        rgb_img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_img.shape
        bytes_per_line = ch * w
        return QImage(rgb_img.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
    except Exception as e:
        raise ValueError(f"Failed to convert bytes to image: {e}")


def scale_pixmap(pixmap: QPixmap, target_size, keep_aspect: bool = True) -> QPixmap:
    """
    Scale pixmap to fit target size.
    
    Args:
        pixmap: Source pixmap
        target_size: Target QSize or tuple (width, height)
        keep_aspect: Maintain aspect ratio
        
    Returns:
        Scaled QPixmap
    """
    from PyQt6.QtCore import Qt
    
    aspect_mode = Qt.AspectRatioMode.KeepAspectRatio if keep_aspect else Qt.AspectRatioMode.IgnoreAspectRatio
    transform_mode = Qt.TransformationMode.SmoothTransformation
    
    return pixmap.scaled(target_size, aspect_mode, transform_mode)


def create_thumbnail(image: Image.Image, max_size: tuple = (300, 300)) -> Image.Image:
    """Create a thumbnail maintaining aspect ratio."""
    thumb = image.copy()
    thumb.thumbnail(max_size)
    return thumb