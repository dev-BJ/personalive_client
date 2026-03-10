"""Logging utilities for Qt integration."""

import logging
from PyQt6.QtCore import pyqtSignal, QObject


class LogEmitter(QObject):
    """Emits log messages to Qt thread."""
    log_message = pyqtSignal(str)


class QtLogHandler(logging.Handler):
    """Custom logging handler that emits Qt signals."""
    
    def __init__(self, emitter: LogEmitter):
        super().__init__()
        self.emitter = emitter
        
    def emit(self, record):
        msg = self.format(record)
        self.emitter.log_message.emit(msg)