"""
Webcam capture thread using OpenCV.
"""

import time
import cv2
import numpy as np
from PyQt6.QtCore import QThread, pyqtSignal, QMutex, QMutexLocker
from PyQt6.QtGui import QImage


class WebcamCapture(QThread):
    """
    Captures video from webcam in separate thread.
    
    Signals:
        frame_captured: Emitted when new frame available (QImage)
        error_occurred: Emitted on errors (str)
        fps_updated: Emitted every second with FPS count (float)
    """
    
    frame_captured = pyqtSignal(QImage, np.ndarray)
    error_occurred = pyqtSignal(str)
    fps_updated = pyqtSignal(float)
    
    def __init__(self, device_id: int = 0, target_fps: int = 15):
        super().__init__()
        self.device_id = device_id
        self.target_fps = target_fps
        self._running = False
        self._mutex = QMutex()
        self.cap = None
        self._frame_interval = 1.0 / target_fps
        
    @property
    def running(self) -> bool:
        with QMutexLocker(self._mutex):
            return self._running
            
    @running.setter
    def running(self, value: bool):
        with QMutexLocker(self._mutex):
            self._running = value
            
    def run(self):
        """Main capture loop."""
        self.running = True
        self.cap = cv2.VideoCapture(self.device_id)
        
        if not self.cap.isOpened():
            self.error_occurred.emit(f"Failed to open webcam {self.device_id}")
            self.running = False
            return
            
        # Configure camera
        self._configure_camera()
        
        # FPS calculation
        frame_time = time.time()
        fps_counter = 0
        fps_time = time.time()
        
        while self.running:
            ret, frame = self.cap.read()
            if not ret:
                continue
                
            # Frame rate limiting
            current_time = time.time()
            elapsed = current_time - frame_time
            if elapsed < self._frame_interval:
                time.sleep(self._frame_interval - elapsed)
            frame_time = time.time()

            qt_frame = frame.copy()  # Make a copy for conversion to avoid modifying original

            if frame.shape[1] > 256 or frame.shape[0] > 256:
                frame = cv2.resize(frame, (256, 256), interpolation=cv2.INTER_AREA)
            
            # Convert to QImage
            qt_image = self._convert_frame(qt_frame)
            if qt_image:
                self.frame_captured.emit(qt_image, frame)
                
            # Update FPS
            fps_counter += 1
            if current_time - fps_time >= 1.0:
                self.fps_updated.emit(fps_counter)
                fps_counter = 0
                fps_time = current_time
                
        self._cleanup()
        
    def _configure_camera(self):
        """Set camera properties."""
        self.cap.set(cv2.CAP_PROP_FPS, self.target_fps)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 512)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 512)
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Minimize latency
        
    def _convert_frame(self, frame: np.ndarray) -> QImage:
        """Convert OpenCV frame to QImage.

        Handles variety of input formats (BGR, BGRA, grayscale) so the
        resulting Qt image is always RGB888.  Some capture backends return
        unexpected channel counts which previously resulted in blue/green
        swapped or entirely wrong-looking feeds.
        """
        try:
            # make sure we have a 3‑channel RGB image regardless of what
            # the camera backend gave us
            if frame is None:
                raise ValueError("empty frame")

            if frame.ndim == 2:
                # grayscale -> convert to RGB
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2RGB)
            elif frame.shape[2] == 4:
                # BGRA -> RGB
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2RGB)
            else:
                # assume BGR (the common OpenCV format)
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            h, w, ch = rgb_frame.shape
            bytes_per_line = ch * w
            return QImage(rgb_frame.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
        except Exception as e:
            self.error_occurred.emit(f"Frame conversion error: {e}")
            return None
            
    def _cleanup(self):
        """Release resources."""
        if self.cap:
            self.cap.release()
            self.cap = None
            
    def stop(self):
        """Stop capture."""
        self.running = False
        self.wait(1000)