"""
ChatWindow - Yuki V3 UI (QTextBrowser Approach)
================================================

ARCHITECTURE:
- Uses QTextBrowser for chat display (HTML rendering)
- Avoids QWidget layout negotiation issues entirely
- V3 compatible: connects to response_ready(dict) signal

This approach is proven stable (user's original implementation).
"""
from PyQt5 import QtCore, QtGui, QtWidgets
import os

from .viewmodel import ChatViewModel
from ..config import MAX_HISTORY
from .components.context_pill import ContextPill
from .components.debug_drawer import DebugDrawer
from .components.notes_panel import NotesPanel


class SakuraChatWindow(QtWidgets.QWidget):
    """
    Main chat window for Yuki V3.
    Uses QTextBrowser with HTML-rendered bubbles for reliable layout.
    """
    
    # Style constants
    USER_BUBBLE_BG = "#873550"
    USER_BUBBLE_TEXT = "#FFFFFF"
    ASSISTANT_BUBBLE_BG = "#25673A"
    ASSISTANT_BUBBLE_TEXT = "#FFFFFF"
    FONT_FAMILY = "'Segoe UI', 'Helvetica Neue', 'Arial', sans-serif"
    FONT_SIZE = "12pt"  # Smaller font
    BUBBLE_PADDING = "10px 15px"

    def __init__(self, conversation_history=None, parent=None, assistant_ref=None):
        super().__init__(parent)
        self.setWindowTitle('Yuki - AI Personal Assistant')
        self.setGeometry(100, 100, 800, 1000)
        self.setWindowFlags(self.windowFlags() | QtCore.Qt.WindowStaysOnTopHint)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        
        # ViewModel
        self.vm = ChatViewModel()
        if conversation_history:
            self.vm.conversation_history = conversation_history
        self.assistant_ref = assistant_ref
        
        # Connect V3 signals
        self.vm.response_ready.connect(self._on_message_received)
        self.vm.status_changed.connect(self._on_status_changed)
        self.vm.listening_state_changed.connect(self._on_mic_state_changed)
        self.vm.error_occurred.connect(self._on_error)
        self.vm.chat_cleared.connect(self.refresh_chat_area)
        self.vm.notes_list_updated.connect(self._on_notes_updated)
        
        # Load styles
        self._load_stylesheet()
        
        # Build UI
        self._init_ui()
        
        # Fade in animation
        self._setup_fade_in()
        
        # Load notes
        self.notes_panel.update_notes(self.vm.get_notes())

    def _load_stylesheet(self):
        path = os.path.join(os.path.dirname(__file__), 'style_theme.qss')
        if os.path.exists(path):
            with open(path, 'r') as f:
                self.setStyleSheet(f.read())

    def _setup_fade_in(self):
        effect = QtWidgets.QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(effect)
        anim = QtCore.QPropertyAnimation(effect, b"opacity")
        anim.setDuration(300)
        anim.setStartValue(0)
        anim.setEndValue(1)
        anim.finished.connect(lambda: self.setGraphicsEffect(None))
        anim.start()
        self._fade_anim = anim

    def _init_ui(self):
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # Main card
        self.card = QtWidgets.QFrame(self)
        self.card.setObjectName("MainCard")
        self.card.setStyleSheet("#MainCard { background-color: #202225; border-radius: 12px; border: 1px solid #18191c; }")
        card_layout = QtWidgets.QVBoxLayout(self.card)
        card_layout.setContentsMargins(0, 0, 0, 0)
        card_layout.setSpacing(0)
        main_layout.addWidget(self.card)
        
        # Header
        self._build_header(card_layout)
        
        # Notes panel
        self._build_notes_panel(card_layout)
        
        # Toolbar
        self._build_toolbar(card_layout)
        
        # Debug drawer
        self._build_debug_drawer(card_layout)
        
        # Chat area (QTextBrowser - key difference!)
        self._build_chat_area(card_layout)
        
        # Input bar
        self._build_input_bar(card_layout)
        
        # Load history
        self.refresh_chat_area()

    def _build_header(self, parent_layout):
        header = QtWidgets.QFrame(self.card)
        header.setObjectName("Header")
        layout = QtWidgets.QHBoxLayout(header)
        layout.setContentsMargins(15, 10, 15, 10)
        
        # Avatar
        self.avatar = QtWidgets.QLabel(header)
        self.avatar.setFixedSize(64, 64)
        self.avatar.setStyleSheet("border-radius: 32px; background-color: #3D3DE3;")
        icon_path = "sakura_assistant/assets/Icon.jpeg"
        if os.path.exists(icon_path):
            pix = QtGui.QPixmap(icon_path)
            self.avatar.setPixmap(pix.scaled(64, 64, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation))
        layout.addWidget(self.avatar)
        
        # Title
        title = QtWidgets.QLabel("Yuki", header)
        title.setObjectName("HeaderTitle")
        layout.addWidget(title)
        
        # Mood dot
        self.mood_dot = QtWidgets.QLabel("●", header)
        self.mood_dot.setStyleSheet("color: #3D3DE3; font-size: 14px;")
        self.mood_dot.setToolTip("Neutral")
        layout.addWidget(self.mood_dot)
        
        layout.addStretch()
        
        # Pill
        self.pill = ContextPill(header)
        layout.addWidget(self.pill)
        
        parent_layout.addWidget(header)

    def _build_notes_panel(self, parent_layout):
        self.notes_panel = NotesPanel(self.card)
        self.notes_panel.note_selected.connect(lambda p: self.vm.read_note_to_chat(p))
        self.notes_panel.refresh_requested.connect(lambda: self.notes_panel.update_notes(self.vm.get_notes()))
        parent_layout.addWidget(self.notes_panel)

    def _build_toolbar(self, parent_layout):
        toolbar = QtWidgets.QFrame(self.card)
        layout = QtWidgets.QHBoxLayout(toolbar)
        layout.setContentsMargins(15, 5, 15, 5)
        layout.setSpacing(10)
        
        # Notes toggle
        self.btn_notes = QtWidgets.QPushButton("📝", toolbar)
        self.btn_notes.setToolTip("Toggle Notes")
        self.btn_notes.setCheckable(True)
        self.btn_notes.setObjectName("ToolbarBtn")
        self.btn_notes.toggled.connect(self.notes_panel.setVisible)
        layout.addWidget(self.btn_notes)
        
        # Debug toggle
        self.btn_debug = QtWidgets.QPushButton("🧠", toolbar)
        self.btn_debug.setToolTip("Toggle Logic")
        self.btn_debug.setCheckable(True)
        self.btn_debug.setObjectName("ToolbarBtn")
        layout.addWidget(self.btn_debug)
        
        # V4: Wake word recording button
        self.btn_wake = QtWidgets.QPushButton("🎙️", toolbar)
        self.btn_wake.setToolTip("Record Wake Word")
        self.btn_wake.setObjectName("ToolbarBtn")
        self.btn_wake.clicked.connect(self._on_record_wake_word)
        layout.addWidget(self.btn_wake)
        
        layout.addStretch()
        
        # V4: TTS Stop button (subtle, in toolbar)
        self.btn_stop_tts = QtWidgets.QPushButton("🔇", toolbar)
        self.btn_stop_tts.setToolTip("Stop voice")
        self.btn_stop_tts.setObjectName("ToolbarBtn")
        self.btn_stop_tts.clicked.connect(self._on_stop_tts)
        layout.addWidget(self.btn_stop_tts)
        
        # Clear button
        btn_clear = QtWidgets.QPushButton("🗑️", toolbar)
        btn_clear.setObjectName("ToolbarBtn")
        btn_clear.clicked.connect(self._on_clear_clicked)
        layout.addWidget(btn_clear)
        
        parent_layout.addWidget(toolbar)

    def _build_debug_drawer(self, parent_layout):
        self.debug_drawer = DebugDrawer(self.card)
        self.btn_debug.toggled.connect(self.debug_drawer.setVisible)
        parent_layout.addWidget(self.debug_drawer)

    def _build_chat_area(self, parent_layout):
        """Build chat area using QTextBrowser (HTML-based, no layout issues)."""
        self.chat_area = QtWidgets.QTextBrowser(self.card)
        self.chat_area.setReadOnly(True)
        self.chat_area.setObjectName("ChatArea")
        self.chat_area.setOpenExternalLinks(True)
        self.chat_area.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
        self.chat_area.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.chat_area.setStyleSheet("""
            QTextBrowser#ChatArea {
                background-color: transparent;
                border: none;
                padding: 10px;
            }
        """)
        
        # Enable custom context menu for right-click delete
        self.chat_area.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.chat_area.customContextMenuRequested.connect(self._show_message_context_menu)
        
        parent_layout.addWidget(self.chat_area, stretch=1)
        
        # Scroll-to-bottom button (floating, circular with arrow)
        self.scroll_btn = QtWidgets.QPushButton("▼", self.card)
        self.scroll_btn.setFixedSize(44, 44)
        self.scroll_btn.setStyleSheet("""
            QPushButton {
                background-color: #3D3DE3;
                color: white;
                border-radius: 22px;
                font-size: 18px;
                font-weight: bold;
                border: 2px solid rgba(255,255,255,0.2);
            }
            QPushButton:hover {
                background-color: #5555FF;
                border: 2px solid rgba(255,255,255,0.4);
            }
            QPushButton:pressed {
                background-color: #2D2DC3;
            }
        """)
        self.scroll_btn.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
        self.scroll_btn.clicked.connect(self._scroll_to_bottom)
        self.scroll_btn.hide()  # Hidden by default
        
        # Connect scroll bar to show/hide button
        self.chat_area.verticalScrollBar().valueChanged.connect(self._on_scroll_changed)

    def _build_input_bar(self, parent_layout):
        self.input_bar = QtWidgets.QFrame(self.card)
        self.input_bar.setObjectName("InputBar")
        layout = QtWidgets.QHBoxLayout(self.input_bar)
        layout.setContentsMargins(15, 12, 15, 12)
        layout.setSpacing(10)
        
        # Upload button (for RAG ingestion)
        self.btn_upload = QtWidgets.QPushButton("📎", self.input_bar)
        self.btn_upload.setObjectName("UploadBtn")
        self.btn_upload.setFixedSize(44, 44)
        self.btn_upload.setToolTip("Upload file for RAG")
        self.btn_upload.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
        self.btn_upload.clicked.connect(self._on_upload_file)
        layout.addWidget(self.btn_upload)
        
        # Text input
        self.textbox = QtWidgets.QLineEdit(self.input_bar)
        self.textbox.setPlaceholderText('Type a message...')
        self.textbox.setObjectName("MessageInput")
        self.textbox.returnPressed.connect(self._on_send)
        layout.addWidget(self.textbox)
        
        # Send button
        btn_send = QtWidgets.QPushButton("➤", self.input_bar)
        btn_send.setObjectName("SendBtn")
        btn_send.setFixedSize(48, 48)
        btn_send.clicked.connect(self._on_send)
        layout.addWidget(btn_send)
        
        # Mic button
        self.btn_mic = QtWidgets.QPushButton("🎤", self.input_bar)
        self.btn_mic.setObjectName("MicBtn")
        self.btn_mic.setFixedSize(48, 48)
        self.btn_mic.clicked.connect(self.vm.toggle_listening)
        layout.addWidget(self.btn_mic)
        
        parent_layout.addWidget(self.input_bar)

    # --- Message Handling ---

    def _on_message_received(self, payload):
        """Handle V3 message payload."""
        metadata = payload.get("metadata", {})
        if metadata:
            self._update_metadata_ui(metadata)
        
        # Refresh the entire chat (simple, reliable)
        self.refresh_chat_area()

    def refresh_chat_area(self):
        """Rebuild chat HTML from history."""
        html_output = ""
        
        try:
            history = self.vm.conversation_history[-MAX_HISTORY:]
        except:
            history = self.vm.conversation_history[-100:]
        
        # Store displayed messages for right-click reference
        self._displayed_messages = list(history)
        
        for idx, msg in enumerate(history):
            role = msg.get('role', 'user')
            raw_content = msg.get('content', '')
            if not isinstance(raw_content, str):
                raw_content = str(raw_content)
            content = raw_content.replace('\n', '<br>')
            
            if role == 'user':
                # User: right-aligned bubble
                html_output += f'''
                    <table width="100%" cellspacing="0" cellpadding="0" style="margin: 4px 0;">
                        <tr>
                            <td width="30%"></td>
                            <td align="right">
                                <a name="msg_{idx}"></a>
                                <table cellspacing="0" cellpadding="0">
                                    <tr><td style="background-color: {self.USER_BUBBLE_BG}; color: {self.USER_BUBBLE_TEXT}; padding: {self.BUBBLE_PADDING}; border-radius: 18px 18px 4px 18px; font-family: {self.FONT_FAMILY}; font-size: {self.FONT_SIZE};">{content}</td></tr>
                                </table>
                            </td>
                        </tr>
                    </table>
                '''
            else:
                # Assistant: left-aligned bubble
                html_output += f'''
                    <table width="100%" cellspacing="0" cellpadding="0" style="margin: 4px 0;">
                        <tr>
                            <td align="left">
                                <a name="msg_{idx}"></a>
                                <table cellspacing="0" cellpadding="0">
                                    <tr><td style="background-color: {self.ASSISTANT_BUBBLE_BG}; color: {self.ASSISTANT_BUBBLE_TEXT}; padding: {self.BUBBLE_PADDING}; border-radius: 18px 18px 18px 4px; font-family: {self.FONT_FAMILY}; font-size: {self.FONT_SIZE};">{content}</td></tr>
                                </table>
                            </td>
                            <td width="30%"></td>
                        </tr>
                    </table>
                '''
        
        self.chat_area.setHtml(html_output)
        
        # Scroll to bottom
        scrollbar = self.chat_area.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def _show_message_context_menu(self, pos):
        """Show context menu for right-click on messages."""
        # Get cursor position
        cursor = self.chat_area.cursorForPosition(pos)
        
        # Find which message was clicked by searching nearby anchors
        cursor.movePosition(cursor.StartOfBlock)
        block_text = cursor.block().text()
        
        # Find message index by checking HTML around cursor
        html = self.chat_area.toHtml()
        cursor_pos = cursor.position()
        
        # Simple approach: check which message block we're in by position ratio
        if not hasattr(self, '_displayed_messages') or not self._displayed_messages:
            return
        
        total_messages = len(self._displayed_messages)
        if total_messages == 0:
            return
        
        # Estimate which message was clicked based on document position
        doc = self.chat_area.document()
        doc_height = doc.size().height()
        cursor_y = self.chat_area.cursorRect(cursor).y() + self.chat_area.verticalScrollBar().value()
        
        # Rough estimate of message index
        msg_idx = min(int((cursor_y / max(doc_height, 1)) * total_messages), total_messages - 1)
        msg_idx = max(0, msg_idx)
        
        # Create context menu
        menu = QtWidgets.QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #2b2b2b;
                border: 1px solid #404040;
                border-radius: 8px;
                padding: 5px;
            }
            QMenu::item {
                padding: 8px 20px;
                color: #ffffff;
            }
            QMenu::item:selected {
                background-color: #3d3de3;
                border-radius: 4px;
            }
        """)
        
        msg = self._displayed_messages[msg_idx]
        preview = msg.get('content', '')[:50] + ('...' if len(msg.get('content', '')) > 50 else '')
        role = msg.get('role', 'user')
        
        # Header showing which message
        header = menu.addAction(f"📝 {role.title()}: {preview}")
        header.setEnabled(False)
        menu.addSeparator()
        
        # Delete from chat only
        delete_chat_action = menu.addAction("🗑️ Delete from Chat")
        delete_chat_action.triggered.connect(lambda: self._delete_message(msg_idx, from_memory=False))
        
        # Delete from chat AND memory
        delete_memory_action = menu.addAction("🧠 Delete from Chat & Memory")
        delete_memory_action.triggered.connect(lambda: self._delete_message(msg_idx, from_memory=True))
        
        menu.addSeparator()
        
        # Cancel
        cancel_action = menu.addAction("❌ Cancel")
        
        # Show menu
        menu.exec_(self.chat_area.mapToGlobal(pos))

    def _delete_message(self, idx, from_memory=False):
        """Delete a message by index."""
        if not hasattr(self, '_displayed_messages') or idx >= len(self._displayed_messages):
            return
        
        msg = self._displayed_messages[idx]
        content = msg.get('content', '')
        role = msg.get('role', '')
        
        # Delete from ViewModel
        self.vm.delete_message(content, role, delete_from_memory=from_memory, save_immediate=True)
        
        # Refresh
        self.refresh_chat_area()

    # --- UI Event Handlers ---

    def _on_send(self):
        text = self.textbox.text().strip()
        if text:
            self.textbox.clear()
            self.vm.send_message(text)
    
    def _on_stop_tts(self):
        """V4: Stop TTS playback immediately."""
        try:
            from ..utils.tts import stop_speaking
            stop_speaking()
            print("🔇 TTS stopped by user")
        except Exception as e:
            print(f"⚠️ TTS stop failed: {e}")

    def _on_upload_file(self):
        """Open file dialog and ingest selected file for RAG."""
        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, 
            "Select File for RAG",
            "",
            "Documents (*.pdf *.txt *.md *.docx);;All Files (*.*)"
        )
        if file_path:
            self.vm.ingest_file(file_path)

    def _on_clear_clicked(self):
        reply = QtWidgets.QMessageBox.question(
            self, 'Clear History',
            "Delete all conversation history?\nThis cannot be undone.",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
        )
        if reply == QtWidgets.QMessageBox.Yes:
            self.vm.clear_history()
    
    def _on_record_wake_word(self):
        """V4: Record wake word sample UI flow."""
        try:
            from ..utils.wake_word import (
                record_wake_template, save_template, get_template_count,
                pause_wake_detection, resume_wake_detection
            )
            
            # Pause detection during recording
            pause_wake_detection()
            
            current_count = get_template_count()
            
            # Inform user
            QtWidgets.QMessageBox.information(
                self,
                "Record Wake Word",
                f"You have {current_count} sample(s) recorded.\n\n"
                f"Say 'Yuki' when prompted.\n"
                f"Recording 3–5 samples improves accuracy."
            )
            
            # Record sample
            self.btn_wake.setText("🔴")
            self.btn_wake.setEnabled(False)
            QtWidgets.QApplication.processEvents()
            
            mfcc = record_wake_template(duration=1.5)
            
            self.btn_wake.setText("🎙️")
            self.btn_wake.setEnabled(True)
            
            if mfcc is not None:
                save_template(mfcc)
                new_count = get_template_count()
                QtWidgets.QMessageBox.information(
                    self,
                    "Saved",
                    f"✅ Sample recorded! ({new_count} total)\n\n"
                    f"Set ENABLE_WAKE_WORD=True in config to activate."
                )
            else:
                QtWidgets.QMessageBox.warning(
                    self,
                    "Recording Failed",
                    "Could not record sample. Check microphone."
                )
            
            # Resume detection
            resume_wake_detection()
            
        except Exception as e:
            QtWidgets.QMessageBox.warning(
                self,
                "Error",
                f"Wake word recording failed: {e}"
            )
            self.btn_wake.setText("🎙️")
            self.btn_wake.setEnabled(True)

    def _on_status_changed(self, text):
        pass

    def _on_mic_state_changed(self, is_listening):
        self.btn_mic.setProperty("listening", is_listening)
        self.btn_mic.style().unpolish(self.btn_mic)
        self.btn_mic.style().polish(self.btn_mic)

    def _on_error(self, msg):
        QtWidgets.QMessageBox.warning(self, "Error", str(msg))

    def _on_notes_updated(self):
        self.notes_panel.update_notes(self.vm.get_notes())

    def _update_metadata_ui(self, metadata):
        self.pill.update_state(
            metadata.get("mode", "STD"),
            metadata.get("confidence", 0.0),
            metadata.get("tool_used", "")
        )
        self.debug_drawer.add_log(metadata)
        
        mood = metadata.get("mood", "Neutral")
        colors = {"Neutral": "#3D3DE3", "Happy": "#43b581", "Focused": "#f1c40f", "Annoyed": "#ed4245"}
        self.mood_dot.setStyleSheet(f"color: {colors.get(mood, '#3D3DE3')}; font-size: 14px;")
        self.mood_dot.setToolTip(mood)

    def closeEvent(self, event):
        self.hide()
        event.ignore()

    def resizeEvent(self, event):
        """Reposition scroll button on window resize."""
        super().resizeEvent(event)
        self._position_scroll_btn()

    def _position_scroll_btn(self):
        """Position scroll button at bottom-right of chat area."""
        if hasattr(self, 'scroll_btn') and hasattr(self, 'chat_area'):
            # Get chat area geometry relative to card
            chat_geo = self.chat_area.geometry()
            btn_x = chat_geo.right() - self.scroll_btn.width() - 20
            btn_y = chat_geo.bottom() - self.scroll_btn.height() - 20
            self.scroll_btn.move(btn_x, btn_y)
            self.scroll_btn.raise_()

    def _on_scroll_changed(self, value):
        """Show/hide scroll button based on scroll position."""
        scrollbar = self.chat_area.verticalScrollBar()
        dist_from_bottom = scrollbar.maximum() - value
        
        if dist_from_bottom > 100:  # More than 100px from bottom
            self.scroll_btn.show()
            self._position_scroll_btn()
        else:
            self.scroll_btn.hide()

    def _scroll_to_bottom(self):
        """Scroll chat to bottom."""
        scrollbar = self.chat_area.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
        self.scroll_btn.hide()
