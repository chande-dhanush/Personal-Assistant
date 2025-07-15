import sys
import os
from PyQt5 import QtWidgets
from .ui.bubble import SakuraBubble
from .config import SYSTEM_NAME

def main():
    # Create application
    app = QtWidgets.QApplication(sys.argv)
    app.setApplicationName(SYSTEM_NAME)
    
    # Set application style
    app.setStyle("Fusion")
    app.setStyleSheet("""
        QToolTip {
            background-color: #333;
            color: #fff;
            border: 1px solid #555;
        }
    """)
    
    # Create and show bubble
    bubble = SakuraBubble()
    bubble.show()
    
    # Run application
    sys.exit(app.exec_())

if __name__ == '__main__':
    main() 