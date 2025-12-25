from PyQt5 import QtCore, QtWidgets

class ContextPill(QtWidgets.QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("ContextPill")
        self.setText("Ready")
        self.setAlignment(QtCore.Qt.AlignCenter)
        
    def update_state(self, mode: str, confidence: float, tool: str):
        # Determine Color
        # Green (>0.7), Yellow (0.4-0.7), Red (<0.4)
        if confidence >= 0.7:
            bg_color = "#3ba55c" # Green
            text_color = "#ffffff"
        elif confidence >= 0.4:
            bg_color = "#faa61a" # Yellow/Orange
            text_color = "#000000"
        else:
            bg_color = "#ed4245" # Red
            text_color = "#ffffff"
            
        tool_icon = f" 🔧 {tool}" if tool and tool != "None" else ""
        
        self.setText(f"{mode} | {confidence:.2f}{tool_icon}")
        
        # We set style dynamically because QSS handles static props, 
        # but color is data-driven here.
        self.setStyleSheet(f"""
            QLabel#ContextPill {{
                background-color: {bg_color};
                color: {text_color};
                border-radius: 12px;
                padding: 4px 10px;
                font-family: 'Consolas', monospace;
                font-size: 11px;
                font-weight: bold;
            }}
        """)
