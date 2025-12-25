from PyQt5 import QtCore, QtWidgets

class DebugDrawer(QtWidgets.QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("DebugDrawer")
        self.setVisible(False)
        self.initUI()
        
    def initUI(self):
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Header (Optional, mostly controlled by button)
        # self.header = QtWidgets.QLabel("🧠 Subconscious Log", self)
        # self.header.setStyleSheet("color: #72767d; font-weight: bold; padding: 5px;")
        # layout.addWidget(self.header)
        
        # Log Area
        self.log_area = QtWidgets.QTextBrowser(self)
        self.log_area.setObjectName("DebugLog") # Styled by QSS
        self.log_area.setFixedHeight(120)
        layout.addWidget(self.log_area)
        
    def add_log(self, metadata: dict):
        time_str = QtCore.QTime.currentTime().toString("HH:mm:ss")
        mode = metadata.get("mode", "STD")
        conf = metadata.get("confidence", 0.0)
        tool = metadata.get("tool_used", "-")
        mood = metadata.get("mood", "-")
        
        # Color coding for HTML
        color_conf = "#43b581" if conf > 0.7 else "#f1c40f" if conf > 0.4 else "#f04747"
        
        html = (
            f"<div style='margin-bottom: 2px;'>"
            f"<span style='color: #72767d;'>[{time_str}]</span> "
            f"<span style='color: #ffffff; font-weight: bold;'>{mode}</span> | "
            f"Conf: <span style='color: {color_conf};'>{conf:.2f}</span> | "
            f"Tool: <span style='color: #5865F2;'>{tool}</span> | "
            f"Mood: <span style='color: #faa61a;'>{mood}</span>"
            f"</div>"
        )
        
        if "reason" in metadata and metadata["reason"]:
            html += f"<div style='color: #b9bbbe; margin-left: 20px; font-style: italic;'>&gt; {metadata['reason']}</div>"
            
        self.log_area.append(html)
        
        # Auto Scroll
        scrollbar = self.log_area.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def toggle(self):
        self.setVisible(not self.isVisible())
