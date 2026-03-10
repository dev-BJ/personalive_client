"""Statistics display panel."""

from PyQt6.QtWidgets import QWidget, QGroupBox, QGridLayout, QLabel


class StatsPanel(QGroupBox):
    """Panel for displaying connection statistics."""
    
    def __init__(self, parent=None):
        super().__init__("Statistics", parent)
        self._setup_ui()
        
    def _setup_ui(self):
        layout = QGridLayout(self)
        
        self.labels = {}
        stats = [
            ('frames_sent', 'Frames Sent'),
            ('frames_received', 'Frames Received'),
            ('bytes_sent', 'Data Sent'),
            ('bytes_received', 'Data Received'),
            ('latency_ms', 'Latency')
        ]
        
        for i, (key, label) in enumerate(stats):
            layout.addWidget(QLabel(f"{label}:"), i, 0)
            self.labels[key] = QLabel("0")
            layout.addWidget(self.labels[key], i, 1)
            
    def update_stats(self, stats: dict):
        """Update displayed statistics."""
        self.labels['frames_sent'].setText(str(stats.get('frames_sent', 0)))
        self.labels['frames_received'].setText(str(stats.get('frames_received', 0)))
        
        # Format bytes to MB
        bytes_sent = stats.get('bytes_sent', 0) / 1024 / 1024
        bytes_recv = stats.get('bytes_received', 0) / 1024 / 1024
        self.labels['bytes_sent'].setText(f"{bytes_sent:.2f} MB")
        self.labels['bytes_received'].setText(f"{bytes_recv:.2f} MB")
        
        # Format latency
        latency = stats.get('latency_ms', 0)
        self.labels['latency_ms'].setText(f"{latency:.1f} ms")