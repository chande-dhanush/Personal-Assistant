from PyQt5 import QtCore, QtGui, QtWidgets
import os
import pyautogui
from .viewmodel import ChatViewModel
from ..config import MAX_HISTORY



class SakuraChatWindow(QtWidgets.QWidget):
    def __init__(self, conversation_history=None, parent=None, assistant_ref=None):
        super().__init__(parent)
        self.setWindowTitle('Sakura - AI Personal Assistant')
        self.setGeometry(100, 100, 400, 600)
        self.setWindowFlags(self.windowFlags() | QtCore.Qt.WindowStaysOnTopHint)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.setStyleSheet('QWidget { border-radius: 18px; background: transparent; }')
        
        # Initialize ViewModel
        self.vm = ChatViewModel()
        if conversation_history:
            self.vm.conversation_history = conversation_history
            
        self.assistant_ref = assistant_ref
        
        # Connect ViewModel Signals
        self.vm.message_received.connect(self.on_message_received)
        self.vm.status_changed.connect(self.update_status)
        self.vm.listening_state_changed.connect(self.update_mic_state)
        self.vm.error_occurred.connect(self.show_error)
        self.vm.file_list_updated.connect(self.refresh_file_list)
        self.vm.ingestion_status_changed.connect(self.update_ingest_indicator)
        self.vm.chat_cleared.connect(self.refresh_chat_area)
        
        # UI Setup
        self.opacity_effect = QtWidgets.QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.opacity_effect)
        self.opacity_anim = QtCore.QPropertyAnimation(self.opacity_effect, b"opacity")
        self.opacity_anim.setDuration(400)
        self.opacity_anim.setStartValue(0)
        self.opacity_anim.setEndValue(1)
        self.opacity_anim.start()
        
        # Load External Stylesheet
        self.load_stylesheet()
        
        self.initUI()
        self.refresh_file_list()

    def load_stylesheet(self):
        try:
            style_path = os.path.join(os.path.dirname(__file__), '..', 'assets', 'styles.qss')
            if os.path.exists(style_path):
                with open(style_path, "r") as f:
                    self.setStyleSheet(f.read())
            else:
                print(f"⚠️ Stylesheet not found at: {style_path}")
        except Exception as e:
            print(f"❌ Error loading stylesheet: {e}")

    def initUI(self):
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Icon handling
        icon_path = "sakura_assistant/assets/Icon.jpeg"
        if os.path.exists(icon_path):
            self.setWindowIcon(QtGui.QIcon(icon_path))

        card = QtWidgets.QFrame(self)
        card.setObjectName("MainCard")
        card_layout = QtWidgets.QVBoxLayout(card)
        card_layout.setContentsMargins(0, 0, 0, 0)
        card_layout.setSpacing(0)
        main_layout.addWidget(card, alignment=QtCore.Qt.AlignCenter)

        # Header
        header = QtWidgets.QFrame(card)
        header.setObjectName("Header")
        header_layout = QtWidgets.QHBoxLayout(header)
        header_layout.setContentsMargins(20, 15, 20, 15)
        header_layout.setSpacing(15)

        avatar = QtWidgets.QLabel(header)
        avatar.setFixedSize(48, 48)
        avatar.setStyleSheet("border-radius: 24px; background-color: #3D3DE3;")
        if os.path.exists(icon_path):
            avatar_pixmap = QtGui.QPixmap(icon_path)
            avatar.setPixmap(avatar_pixmap.scaled(48, 48, QtCore.Qt.KeepAspectRatioByExpanding, QtCore.Qt.SmoothTransformation))
        avatar.setScaledContents(True)
        header_layout.addWidget(avatar)

        name_label = QtWidgets.QLabel("Sakura", header)
        name_label.setObjectName("HeaderTitle")
        header_layout.addWidget(name_label)
        header_layout.addStretch()
        
        self.memory_status_label = QtWidgets.QLabel("🧠 Memory: Initializing...", header)
        self.memory_status_label.setObjectName("MemoryStatus")
        header_layout.addWidget(self.memory_status_label)
        
        self.ingest_status_label = QtWidgets.QLabel("📄 Ingestion: Idle", header)
        self.ingest_status_label.setObjectName("IngestStatus")
        header_layout.addWidget(self.ingest_status_label)
        
        card_layout.addWidget(header)

        # Files Section (Collapsible)
        self.files_frame = QtWidgets.QFrame(card)
        self.files_frame.setObjectName("FilesFrame")
        self.files_frame.setVisible(False)
        files_layout = QtWidgets.QVBoxLayout(self.files_frame)
        files_layout.setContentsMargins(10, 10, 10, 10)
        
        files_header = QtWidgets.QLabel("📂 Uploaded Files", self.files_frame)
        files_header.setObjectName("FilesHeader")
        files_layout.addWidget(files_header)
        
        self.files_list_widget = QtWidgets.QListWidget(self.files_frame)
        self.files_list_widget.setObjectName("FilesList")
        self.files_list_widget.setFixedHeight(100)
        files_layout.addWidget(self.files_list_widget)
        
        card_layout.addWidget(self.files_frame)

        # Toolbar
        toolbar = QtWidgets.QFrame(card)
        toolbar_layout = QtWidgets.QHBoxLayout(toolbar)
        toolbar_layout.setContentsMargins(20, 5, 20, 5)
        
        self.toggle_files_btn = QtWidgets.QPushButton("📂 Files", toolbar)
        self.toggle_files_btn.setObjectName("ToolbarBtn")
        self.toggle_files_btn.clicked.connect(self.toggle_files_visibility)
        toolbar_layout.addWidget(self.toggle_files_btn)
        
        toolbar_layout.addStretch()
        
        delete_all_chats_btn = QtWidgets.QPushButton("🗑️ Clear Chat", toolbar)
        delete_all_chats_btn.setObjectName("ClearChatBtn")
        delete_all_chats_btn.clicked.connect(self.clear_chat)
        toolbar_layout.addWidget(delete_all_chats_btn)
        
        card_layout.addWidget(toolbar)

        # Chat Area
        self.chat_area = QtWidgets.QTextBrowser(card)
        self.chat_area.setReadOnly(True)
        self.chat_area.setObjectName("ChatArea")
        self.chat_area.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
        card_layout.addWidget(self.chat_area, stretch=1)

        # Input Bar
        input_bar = QtWidgets.QFrame(card)
        input_bar.setObjectName("InputBar")
        input_layout = QtWidgets.QHBoxLayout(input_bar)
        input_layout.setContentsMargins(15, 12, 15, 12)
        input_layout.setSpacing(10)

        # Upload Button
        self.upload_btn = QtWidgets.QPushButton("📎", input_bar)
        self.upload_btn.setFixedSize(40, 40)
        self.upload_btn.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
        self.upload_btn.setObjectName("UploadBtn")
        self.upload_btn.clicked.connect(self.upload_file)
        input_layout.addWidget(self.upload_btn)

        self.textbox = QtWidgets.QLineEdit(input_bar)
        self.textbox.setPlaceholderText('Type your message here...')
        self.textbox.setObjectName("MessageInput")
        self.textbox.returnPressed.connect(self.handle_input)
        input_layout.addWidget(self.textbox, stretch=1)

        self.send_btn = QtWidgets.QPushButton("➤")
        self.send_btn.setFixedSize(44, 44)
        self.send_btn.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
        self.send_btn.setObjectName("SendBtn")
        self.send_btn.clicked.connect(self.handle_input)
        input_layout.addWidget(self.send_btn)

        self.mic_btn = QtWidgets.QPushButton('🎤', input_bar)
        self.mic_btn.setObjectName("MicBtn")
        self.mic_btn.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
        self.mic_btn.clicked.connect(self.on_mic_button_clicked)
        input_layout.addWidget(self.mic_btn)

        card_layout.addWidget(input_bar)
        card.setFixedWidth(600)
        card.setFixedHeight(800)

        self.refresh_chat_area()

    # --- Event Handlers ---

    def handle_input(self):
        text = self.textbox.text()
        if text.strip():
            self.textbox.clear()
            self.vm.send_message(text)

    def on_message_received(self, role, content):
        self.refresh_chat_area()

    def update_status(self, text):
        if "Memory" in text:
            self.memory_status_label.setText(text)
        elif "Ingestion" in text:
            self.ingest_status_label.setText(text)

    def update_ingest_indicator(self, is_ingesting):
        if is_ingesting:
            self.ingest_status_label.setText("📄 Ingestion: Processing...")
            self.ingest_status_label.setStyleSheet("color: #f1c40f;")
        else:
            self.ingest_status_label.setText("📄 Ingestion: Idle")
            self.ingest_status_label.setStyleSheet("color: #FFFFFF;")

    def show_error(self, message):
        QtWidgets.QMessageBox.critical(self, "Error", message)

    def upload_file(self):
        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Select File", "", "All Files (*.*)")
        if file_path:
            self.vm.ingest_file(file_path)

    def refresh_file_list(self):
        self.files_list_widget.clear()
        files = self.vm.get_files()
        
        for f in files:
            item_widget = QtWidgets.QWidget()
            item_layout = QtWidgets.QHBoxLayout(item_widget)
            item_layout.setContentsMargins(5, 2, 5, 2)
            
            info_text = f"{f['filename']} (ID: {f['file_id'][:8]}...)"
            label = QtWidgets.QLabel(info_text)
            label.setStyleSheet(f"color: #FFFFFF;")
            item_layout.addWidget(label)
            
            del_btn = QtWidgets.QPushButton("🗑️")
            del_btn.setFixedSize(24, 24)
            del_btn.setStyleSheet("background: #e74c3c; border-radius: 12px; color: white; border: none;")
            del_btn.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
            del_btn.clicked.connect(lambda checked, fid=f['file_id']: self.vm.delete_file(fid))
            item_layout.addWidget(del_btn)
            
            item = QtWidgets.QListWidgetItem(self.files_list_widget)
            item.setSizeHint(item_widget.sizeHint())
            self.files_list_widget.addItem(item)
            self.files_list_widget.setItemWidget(item, item_widget)

    def toggle_files_visibility(self):
        self.files_frame.setVisible(not self.files_frame.isVisible())

    def clear_chat(self):
        # Create a custom dialog for full control
        dialog = QtWidgets.QDialog(self)
        dialog.setWindowTitle("Clear Chat History")
        dialog.setWindowFlags(dialog.windowFlags() | QtCore.Qt.WindowStaysOnTopHint | QtCore.Qt.FramelessWindowHint)
        dialog.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        dialog.setFixedSize(300, 150)
        
        # Layout
        layout = QtWidgets.QVBoxLayout(dialog)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Background Frame
        frame = QtWidgets.QFrame(dialog)
        frame.setStyleSheet("""
            QFrame {
                background-color: #2b2b2b;
                border: 1px solid #4a4a4a;
                border-radius: 10px;
            }
        """)
        frame_layout = QtWidgets.QVBoxLayout(frame)
        frame_layout.setContentsMargins(20, 20, 20, 20)
        layout.addWidget(frame)
        
        # Message
        label = QtWidgets.QLabel("Are you sure you want to clear the chat history?", frame)
        label.setWordWrap(True)
        label.setStyleSheet("color: #ffffff; font-size: 14px; border: none;")
        label.setAlignment(QtCore.Qt.AlignCenter)
        frame_layout.addWidget(label)
        
        frame_layout.addSpacing(20)
        
        # Buttons
        btn_layout = QtWidgets.QHBoxLayout()
        btn_layout.setSpacing(10)
        
        yes_btn = QtWidgets.QPushButton("Yes, Clear")
        yes_btn.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
        yes_btn.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                color: white;
                border: none;
                padding: 8px 15px;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #c0392b; }
        """)
        yes_btn.clicked.connect(dialog.accept)
        
        no_btn = QtWidgets.QPushButton("Cancel")
        no_btn.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
        no_btn.setStyleSheet("""
            QPushButton {
                background-color: #3b3b3b;
                color: white;
                border: 1px solid #555;
                padding: 8px 15px;
                border-radius: 5px;
            }
            QPushButton:hover { background-color: #4b4b4b; }
        """)
        no_btn.clicked.connect(dialog.reject)
        
        btn_layout.addWidget(no_btn)
        btn_layout.addWidget(yes_btn)
        frame_layout.addLayout(btn_layout)
        
        # Center on screen or parent
        dialog.move(self.geometry().center() - dialog.rect().center())
        
        if dialog.exec_() == QtWidgets.QDialog.Accepted:
            self.vm.clear_history()

    def update_mic_state(self, is_listening):
        if is_listening:
            self.mic_btn.setStyleSheet(self.mic_listening_style())
        else:
            self.mic_btn.setStyleSheet(self.mic_idle_style())

    def on_mic_button_clicked(self):
        self.vm.toggle_listening()

    def refresh_chat_area(self):
        USER_BUBBLE_BG = "#707CFE"
        USER_BUBBLE_TEXT = "#FFFFFF"
        BOT_BUBBLE_BG = "#36393F"
        BOT_BUBBLE_TEXT = "#DCDDDE"
        CHAT_FONT_FAMILY = "'Segoe UI', 'Helvetica Neue', 'Arial', sans-serif"
        CHAT_FONT_SIZE = "12pt"
        BUBBLE_PADDING = "10px 15px"
        
        self.chat_area.clear()
        html_output = ""
        
        try:
            history_to_display = self.vm.conversation_history[-MAX_HISTORY:]
        except:
            history_to_display = self.vm.conversation_history[-100:]

        for msg_data in history_to_display:
            role = msg_data.get('role', 'user')
            raw_content = msg_data.get('content', '')
            if not isinstance(raw_content, str):
                raw_content = str(raw_content)
            content = raw_content.replace('\n', '<br>')
            
            if role == 'user':
                bubble_style = f"background: {USER_BUBBLE_BG}; color: {USER_BUBBLE_TEXT}; padding: {BUBBLE_PADDING}; border-radius: 18px 18px 0 18px; max-width: 75%; font-family: {CHAT_FONT_FAMILY}; font-size: {CHAT_FONT_SIZE};"
                html_output += f'<div style="display: flex; justify-content: flex-end; margin: 8px 0;"><div style="{bubble_style}">{content}</div></div>'
            else:
                bubble_style = f"background: {BOT_BUBBLE_BG}; color: {BOT_BUBBLE_TEXT}; padding: {BUBBLE_PADDING}; border-radius: 18px 18px 18px 0; max-width: 75%; font-family: {CHAT_FONT_FAMILY}; font-size: {CHAT_FONT_SIZE};"
                html_output += f'<div style="display: flex; justify-content: flex-start; margin: 8px 0;"><div style="{bubble_style}">{content}</div></div>'
                
        self.chat_area.setHtml(html_output)
        scrollbar = self.chat_area.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def mic_idle_style(self):
        return "QPushButton { background-color: #4fc08d; border: 2px solid white; border-radius: 20px; font-size: 16px; min-width: 40px; min-height: 40px; } QPushButton:hover { background-color: #4fb08d; }"

    def mic_listening_style(self):
        return "QPushButton { background-color: #f04747; border: 2px solid white; border-radius: 20px; font-size: 16px; min-width: 40px; min-height: 40px; } QPushButton:hover { background-color: #f04500; }"

    def closeEvent(self, event):
        self.hide()
        event.ignore()
