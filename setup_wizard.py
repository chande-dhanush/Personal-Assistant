import sys
import os
from PyQt5 import QtWidgets, QtCore, QtGui

class SetupWizard(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Sakura Assistant Setup")
        self.setGeometry(100, 100, 500, 400)
        self.setStyleSheet("""
            QWidget {
                background-color: #1e1e2e;
                color: #cdd6f4;
                font-family: 'Segoe UI', sans-serif;
            }
            QLineEdit {
                background-color: #313244;
                border: 1px solid #45475a;
                border-radius: 5px;
                padding: 8px;
                color: #ffffff;
            }
            QLabel {
                font-size: 14px;
                margin-bottom: 5px;
            }
            QPushButton {
                background-color: #89b4fa;
                color: #1e1e2e;
                border: none;
                border-radius: 5px;
                padding: 10px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #b4befe;
            }
        """)
        self.init_ui()

    def init_ui(self):
        layout = QtWidgets.QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(30, 30, 30, 30)

        # Title
        title = QtWidgets.QLabel("🌸 Sakura Assistant Setup")
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: #f5c2e7; margin-bottom: 20px;")
        title.setAlignment(QtCore.Qt.AlignCenter)
        layout.addWidget(title)

        # Form Layout
        form_layout = QtWidgets.QFormLayout()
        form_layout.setSpacing(10)

        self.inputs = {}
        fields = [
            ("GOOGLE_API_KEY", "Google Gemini API Key"),
            ("GROQ_API_KEY", "Groq API Key"),
            ("SPOTIFY_CLIENT_ID", "Spotify Client ID"),
            ("SPOTIFY_CLIENT_SECRET", "Spotify Client Secret"),
            ("TAVILY_API_KEY", "Tavily Search API Key")
        ]

        for key, label_text in fields:
            label = QtWidgets.QLabel(label_text)
            input_field = QtWidgets.QLineEdit()
            input_field.setPlaceholderText(f"Enter {label_text}...")
            
            # Pre-fill if exists
            current_val = os.getenv(key, "")
            if current_val:
                input_field.setText(current_val)
                
            self.inputs[key] = input_field
            form_layout.addRow(label, input_field)

        layout.addLayout(form_layout)

        # Save Button
        save_btn = QtWidgets.QPushButton("Save Configuration")
        save_btn.setCursor(QtCore.Qt.PointingHandCursor)
        save_btn.clicked.connect(self.save_config)
        layout.addWidget(save_btn)

        self.setLayout(layout)

    def save_config(self):
        env_content = []
        for key, input_field in self.inputs.items():
            value = input_field.text().strip()
            if value:
                env_content.append(f"{key}={value}")
        
        # Add default language if missing
        env_content.append("LANGUAGE=en")

        try:
            with open(".env", "w", encoding="utf-8") as f:
                f.write("\n".join(env_content))
            
            QtWidgets.QMessageBox.information(self, "Success", "Configuration saved successfully!\nYou can now run Sakura Assistant.")
            self.close()
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Error", f"Failed to save config: {e}")

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    
    # Check if .env exists, if not create empty
    if not os.path.exists(".env"):
        with open(".env", "w") as f:
            f.write("")
            
    # Load existing env for pre-filling
    from dotenv import load_dotenv
    load_dotenv()

    window = SetupWizard()
    window.show()
    sys.exit(app.exec_())
