from PyQt5 import QtCore, QtGui, QtWidgets
import speech_recognition as sr
import threading
from ..utils.tts import text_to_speech
from ..utils.storage import save_conversation
from ..core.commands import handle_command
from ..core.llm import sakura_llm_response
from ..config import MAX_HISTORY
import os
import time
import pyautogui
import json
tt = False
class WakeWordDetector:
    def __init__(self, app_instance, wake_words=None):
        """
        Initialize wake word detector
        
        Args:
            app_instance: The main application instance
            wake_words: List of wake words to detect (default: ["levos", "hey levos"])
        """
        self.app = app_instance
        self.wake_words = ["hey sakura", "sakura listen", "hello sakura", "ok sakura", "hey chakra", "chakra listen", "hello chakra", "ok chakra","hey levos", "levos listen", "hello levos", "ok levos"]
        self.recognizer = sr.Recognizer()
        self.is_running = False
        self.detector_thread = None
        
    def start_detection(self):
        """Start the wake word detection in a separate thread"""
        if self.is_running:
            return
            
        self.is_running = True
        self.detector_thread = threading.Thread(target=self._detection_loop)
        self.detector_thread.daemon = True
        self.detector_thread.start()
        print("Wake word detection started")
        
    def stop_detection(self):
        """Stop the wake word detection"""
        self.is_running = False
        if self.detector_thread:
            self.detector_thread = None
        print("Wake word detection stopped")
        
    def _detection_loop(self):
        """Main detection loop that runs in the background"""
        while self.is_running:
            try:
                with sr.Microphone() as source:
                    # Adjust for ambient noise
                    self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
                    # Listen for audio
                    audio = self.recognizer.listen(source, phrase_time_limit=3)
                    
                try:
                    # Try to recognize speech in the audio
                    text = self.recognizer.recognize_google(audio).lower()
                    
                    # Check if any wake word is in the recognized text
                    if any(wake_word in text for wake_word in self.wake_words):
                        print(f"Wake word detected: {text}")
                        # Trigger the listening function in the main app GUI thread
                        self.app.wake_word_activated()
                    
                except sr.UnknownValueError:
                    # Speech was unintelligible
                    pass
                except sr.RequestError:
                    # Could not request results from speech recognition service
                    print("Could not request results from speech recognition service")
                    time.sleep(2)  # Wait before retrying
                    
            except Exception as e:
                print(f"Error in wake word detection: {str(e)}")
                time.sleep(1)
                
            # Small delay between detection attempts
            time.sleep(0.1)

class AnimatedButton(QtWidgets.QPushButton):
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setStyleSheet("background: #3498db; color: white; border-radius: 8px; font-size: 12pt; transition: background 0.2s;")
        self.default_style = "background: #3498db; color: white; border-radius: 8px; font-size: 12pt;"
        self.hover_style = "background: #217dbb; color: white; border-radius: 8px; font-size: 13pt; box-shadow: 0 0 12px #2980b9;"
        self.shadow = QtWidgets.QGraphicsDropShadowEffect(self)
        self.shadow.setBlurRadius(5)
        self.shadow.setColor(QtGui.QColor(52, 152, 219, 120))
        self.shadow.setOffset(2, 2)
        self.setGraphicsEffect(self.shadow)

    def enterEvent(self, event):
        self.setStyleSheet(self.hover_style)
        self.shadow.setBlurRadius(18)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.setStyleSheet(self.default_style)
        self.shadow.setBlurRadius(0)
        super().leaveEvent(event)

class SakuraChatWindow(QtWidgets.QWidget):
    # Add signals for thread-safe UI updates
    update_mic_button = QtCore.pyqtSignal(str, str)  # text, style
    update_textbox = QtCore.pyqtSignal(str)
    update_chat_area = QtCore.pyqtSignal()
    trigger_handle_input = QtCore.pyqtSignal()
    def __init__(self, conversation_history, parent=None, assistant_ref=None):
        super().__init__(parent)
        self.setWindowTitle('Levos - AI Personal Assistant')
        self.setGeometry(100, 100, 400, 500)
        self.setWindowFlags(self.windowFlags() | QtCore.Qt.WindowStaysOnTopHint)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.setStyleSheet('QWidget { border-radius: 18px; background: transparent; }')
        self.conversation_history = conversation_history
        self.assistant_ref = assistant_ref
        self.opacity_effect = QtWidgets.QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.opacity_effect)
        self.opacity_anim = QtCore.QPropertyAnimation(self.opacity_effect, b"opacity")
        self.opacity_anim.setDuration(400)
        self.opacity_anim.setStartValue(2)
        self.opacity_anim.setEndValue(5)
        self.opacity_anim.start()
        self.trigger_handle_input.connect(self.handle_input)
        self.listening = True
        self.setup_wake_word_detection()
        
        # Connect signals
        self.update_mic_button.connect(self._update_mic_button)
        self.update_textbox.connect(self._update_textbox)
        self.update_chat_area.connect(self._update_chat_area)
        self.initUI()

    def _update_mic_button(self, text, style):
        self.mic_btn.setText(text)
        self.mic_btn.setStyleSheet(style)

    def _update_textbox(self, text):
        self.textbox.setText(text)

    def _update_chat_area(self):
        self.refresh_chat_area()

    def initUI(self):
        # --- Color Palette ---
        BG_COLOR = "#1E1F22"  # Darker, slightly desaturated background
        PRIMARY_CARD_COLOR = "#2B2D31" # Main content card background
        SECONDARY_CARD_COLOR = "#313338" # Slightly lighter for elements within the card
        TEXT_COLOR_PRIMARY = "#FFFFFF"
        TEXT_COLOR_SECONDARY = "#B9BBBE" # For placeholder text or less important info
        ACCENT_COLOR = "#5865F2" # A modern, clean accent (e.g., Discord-like blue/purple)
        INPUT_BG_COLOR = "#202225" # Darker input background
        BORDER_COLOR = "#404249" # Subtle border color

        # --- Font ---
        FONT_FAMILY = "Segoe UI, Arial, sans-serif" # Prioritize Segoe UI

        # Main layout
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        self.setStyleSheet(f"background: {BG_COLOR};")

        # Set window icon
        icon_path = "sakura_assistant/assets/Icon.jpeg" # Default to None
        base_icon_path_suggestion = 'sakura_assistant/assets/Icon.jpeg' # Keep your original suggestion
        # More robust icon finding (look in current script's directory if relative path fails)
        script_dir = os.path.dirname(__file__)
        possible_icon_paths = [
            base_icon_path_suggestion,
            os.path.join(script_dir, 'sakura_assistant', 'assets', 'Icon.jpeg'),
            os.path.join(script_dir, 'assets', 'Icon.jpeg'), # If assets is next to script
            os.path.join(script_dir, 'Icon.jpeg') # If icon is next to script
        ]
        for ext in ["png", "jpeg", "jpg", "ico"]: # Check common extensions
            for p_base in [os.path.join(script_dir, "Bg"), os.path.join(script_dir, "icon")]:
                 candidate = f"{p_base}.{ext}"
                 if os.path.exists(candidate):
                    icon_path = candidate
                    break
            if icon_path: break

        if not icon_path: # Fallback if Bg.ext not found
            for candidate_path in possible_icon_paths:
                if os.path.exists(candidate_path):
                    icon_path = candidate_path
                    break

        if icon_path:
            self.setWindowIcon(QtGui.QIcon(icon_path))
        else:
            print(f"Warning: Icon not found at specified paths. Searched near: {script_dir}")


        # Centered card container
        card = QtWidgets.QFrame(self)
        card.setStyleSheet(f"""
            QFrame {{
                background: {PRIMARY_CARD_COLOR};
                border-radius: 18px;
            }}
        """)
        card_layout = QtWidgets.QVBoxLayout(card)
        card_layout.setContentsMargins(0, 0, 0, 0) # Margins will be handled by inner elements
        card_layout.setSpacing(0) # Spacing will be handled by inner elements or specific margins
        main_layout.addWidget(card, alignment=QtCore.Qt.AlignCenter)

        # Header with Sakura's name and avatar
        header = QtWidgets.QFrame(card)
        header.setStyleSheet(f"""
            QFrame {{
                background: {PRIMARY_CARD_COLOR}; /* Same as card, or could be slightly different */
                border-top-left-radius: 18px;
                border-top-right-radius: 18px;
                border-bottom: 1px solid {BORDER_COLOR}; /* Subtle separator line */
            }}
        """)
        header_layout = QtWidgets.QHBoxLayout(header)
        header_layout.setContentsMargins(20, 15, 20, 15) # Slightly adjusted padding
        header_layout.setSpacing(15)

        avatar = QtWidgets.QLabel(header)
        avatar.setFixedSize(48, 48)
        # Use a transparent background for the avatar label itself if the pixmap has transparency
        # The border-radius will clip the pixmap.
        avatar.setStyleSheet(f"""
            QLabel {{
                border-radius: 24px; /* Half of size for circle */
                background-color: {ACCENT_COLOR}; /* Fallback color or slight border */
            }}
        """)
        if icon_path:
            avatar_pixmap = QtGui.QPixmap(icon_path)
        else: # Create a placeholder colored circle if no icon
            avatar_pixmap = QtGui.QPixmap(48,48)
            avatar_pixmap.fill(QtGui.QColor(ACCENT_COLOR)) # Fallback placeholder color

        avatar.setPixmap(avatar_pixmap.scaled(48, 48, QtCore.Qt.KeepAspectRatioByExpanding, QtCore.Qt.SmoothTransformation))
        avatar.setScaledContents(True) # Ensures pixmap scales to label size if not exact

        header_layout.addWidget(avatar)

        name_label = QtWidgets.QLabel("Sakura", header)
        name_label.setStyleSheet(f"""
            QLabel {{
                color: {TEXT_COLOR_PRIMARY};
                font-size: 24px; /* Slightly reduced for a cleaner look */
                font-weight: bold;
                font-family: '{FONT_FAMILY}';
            }}
        """)
        header_layout.addWidget(name_label)
        header_layout.addStretch()
        card_layout.addWidget(header)

        # Chat area
        self.chat_area = QtWidgets.QTextBrowser(card)
        self.chat_area.setReadOnly(True)
        self.chat_area.setStyleSheet(f"""
            QTextBrowser {{
                background: {PRIMARY_CARD_COLOR};
                color: {TEXT_COLOR_PRIMARY};
                border: none; /* No border, seamless with card */
                font-size: 14pt; /* Kept your font size */
                font-family: '{FONT_FAMILY}';
                padding: 20px; /* Uniform padding */
            }}
            QScrollBar:vertical {{
                border: none;
                background: {SECONDARY_CARD_COLOR};
                width: 10px;
                margin: 0px 0px 0px 0px;
            }}
            QScrollBar::handle:vertical {{
                background: {ACCENT_COLOR};
                min-height: 20px;
                border-radius: 5px;
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
            QScrollBar::up-arrow:vertical, QScrollBar::down-arrow:vertical {{
                width: 0px;
                height: 0px;
            }}
        """)
        # self.chat_area.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff) # Consider ScrollBarAsNeeded
        self.chat_area.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
        card_layout.addWidget(self.chat_area, stretch=1)

        # Input bar
        input_bar = QtWidgets.QFrame(card)
        input_bar.setStyleSheet(f"""
            QFrame {{
                background: {PRIMARY_CARD_COLOR};
                border-top: 1px solid {BORDER_COLOR}; /* Separator line */
                border-bottom-left-radius: 18px;
                border-bottom-right-radius: 18px;
            }}
        """)
        input_layout = QtWidgets.QHBoxLayout(input_bar)
        input_layout.setContentsMargins(15, 12, 15, 12) # Adjusted padding
        input_layout.setSpacing(10)

        self.textbox = QtWidgets.QLineEdit(input_bar)
        self.textbox.setPlaceholderText('Type your message here...') # More descriptive placeholder
        self.textbox.setStyleSheet(f"""
            QLineEdit {{
                background: {INPUT_BG_COLOR};
                color: {TEXT_COLOR_PRIMARY};
                border-radius: 8px;
                padding: 12px 15px; /* Increased padding for better feel */
                font-size: 13pt;
                font-family: '{FONT_FAMILY}';
                border: 1px solid {BORDER_COLOR}; /* Subtle border */
            }}
            QLineEdit:focus {{
                border: 1px solid {ACCENT_COLOR}; /* Highlight on focus */
            }}
        """)
        self.textbox.returnPressed.connect(self.handle_input)
        input_layout.addWidget(self.textbox, stretch=1)

        button_style = f"""
            QPushButton {{
                background: {ACCENT_COLOR};
                color: {TEXT_COLOR_PRIMARY};
                border-radius: 8px;
                font-size: 16pt; /* Adjusted for visual balance with icons */
                font-weight: bold;
                min-width: 44px; /* Adjusted for better click target */
                min-height: 44px;
                padding: 0px; /* Remove padding if icon is centered */
                font-family: '{FONT_FAMILY}';
            }}
            QPushButton:hover {{
                background: #4754c7; /* Slightly darker accent for hover */
            }}
            QPushButton:pressed {{
                background: #3f4baf; /* Even darker for pressed state */
            }}
        """

        self.send_btn = AnimatedButton('➤', input_bar) # Using a more common send icon
        self.send_btn.setStyleSheet(button_style)
        self.send_btn.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
        self.send_btn.clicked.connect(self.handle_input)
        input_layout.addWidget(self.send_btn)

        self.mic_btn = QtWidgets.QPushButton('🎤', input_bar)
        self.mic_btn.setStyleSheet(button_style)
        self.mic_btn.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
        self.mic_btn.clicked.connect(self.handle_voice_input)
        input_layout.addWidget(self.mic_btn)

        card_layout.addWidget(input_bar)

        # Set fixed size for the card (responsive look)
        card.setFixedWidth(600)
        card.setFixedHeight(800)

        self.refresh_chat_area = self.refresh_chat_area_bubble  # Use bubble style
        self.refresh_chat_area()

    
    def refresh_chat_area_bubble(self):
        """
        Refreshes the chat area with messages displayed as styled bubbles.
        'self' is assumed to be an instance of your chat window class, having:
        - self.chat_area: A QTextBrowser widget.
        - self.conversation_history: A list of message dictionaries.
        - MAX_HISTORY: A constant defining the max number of messages to show.
        """

        # --- Define Style Variables (local to this function for the example) ---
        # In a class, these would ideally be self.USER_BUBBLE_BG, etc. or constants.
        USER_BUBBLE_BG = "#5865F2"       # Accent blue/purple
        USER_BUBBLE_TEXT = "#FFFFFF"
        BOT_BUBBLE_BG = "#36393F"        # Dark grey
        BOT_BUBBLE_TEXT = "#DCDDDE"      # Off-white / Light grey
        
        CHAT_FONT_FAMILY = "'Segoe UI', 'Helvetica Neue', 'Arial', sans-serif"
        CHAT_FONT_SIZE = "12pt"          # Adjust as needed
        
        BUBBLE_PADDING = "10px 15px"     # Vertical Horizontal
        # Specific border-radius for "tail" effect
        # Format: top-left top-right bottom-right bottom-left
        USER_BUBBLE_BORDER_RADIUS = "18px 18px 0 18px" 
        BOT_BUBBLE_BORDER_RADIUS = "18px 18px 18px 0"
        
        MESSAGE_MARGIN = "8px 0"         # Margin between messages
        MAX_BUBBLE_WIDTH = "75%"         # Max width of a bubble relative to chat area
        LINE_HEIGHT = "1.4"              # For better text readability

        self.chat_area.clear()
        
        html_output = ""

        # Slice the conversation history to get the latest messages
        # Ensure MAX_HISTORY is defined in the scope (e.g., self.MAX_HISTORY or a global)
        try:
            # Try to access MAX_HISTORY as a class attribute if it exists
            history_to_display = self.conversation_history[-self.MAX_HISTORY:]
        except AttributeError:
            # Fallback to a global MAX_HISTORY or a default if not on self
            # This assumes MAX_HISTORY is defined globally or in the outer scope
            history_to_display = self.conversation_history[-MAX_HISTORY:]


        for msg_index, msg_data in enumerate(history_to_display):
            role = msg_data.get('role', 'user')
            raw_content = msg_data.get('content', '')
            
            # Basic HTML escaping: preserve newlines, escape essential characters
            # For more complex needs, a proper HTML sanitizer/escaper is recommended.
            content = raw_content.replace('&', '&amp;') \
                                .replace('<', '&lt;') \
                                .replace('>', '&gt;') \
                                .replace('"', '&quot;') \
                                .replace("'", '&#39;') \
                                .replace('\n', '<br>')

            is_first_message_in_sequence = True
            is_last_message_in_sequence = True

            # Determine if this message is part of a sequence from the same role
            if msg_index > 0:
                prev_msg_data = history_to_display[msg_index - 1]
                if prev_msg_data.get('role') == role:
                    is_first_message_in_sequence = False
            
            if msg_index < len(history_to_display) - 1:
                next_msg_data = history_to_display[msg_index + 1]
                if next_msg_data.get('role') == role:
                    is_last_message_in_sequence = False

            # Adjust border radius for message sequences
            current_user_radius = USER_BUBBLE_BORDER_RADIUS
            current_bot_radius = BOT_BUBBLE_BORDER_RADIUS

            if role == 'user':
                if not is_first_message_in_sequence and not is_last_message_in_sequence: # Middle
                    current_user_radius = "18px 0 0 18px"
                elif not is_first_message_in_sequence: # Last in sequence
                    current_user_radius = "18px 0 0 18px"
                elif not is_last_message_in_sequence: # First in sequence
                    current_user_radius = "18px 18px 0 18px"
                # else: it's a single message or default applies

                bubble_style = f"""
                    background: {USER_BUBBLE_BG};
                    color: {USER_BUBBLE_TEXT};
                    padding: {BUBBLE_PADDING};
                    border-radius: {current_user_radius};
                    max-width: {MAX_BUBBLE_WIDTH};
                    word-wrap: break-word; /* or overflow-wrap: break-word; */
                    text-align: left; /* Text inside bubble always left-aligned */
                    font-family: {CHAT_FONT_FAMILY};
                    font-size: {CHAT_FONT_SIZE};
                    line-height: {LINE_HEIGHT};
                    display: inline-block; /* Important for the bubble to size to content */
                """
                # Outer div for alignment
                html_output += f'''
                    <div style="display: flex; justify-content: flex-end; margin: {MESSAGE_MARGIN if is_first_message_in_sequence else "2px 0"}; clear: both;">
                        <div style="{bubble_style.strip()}">
                            {content}
                        </div>
                    </div>
                '''
            else: # 'assistant' or other roles
                if not is_first_message_in_sequence and not is_last_message_in_sequence: # Middle
                    current_bot_radius = "0 18px 18px 0"
                elif not is_first_message_in_sequence: # Last in sequence
                    current_bot_radius = "0 18px 18px 0"
                elif not is_last_message_in_sequence: # First in sequence
                    current_bot_radius = "18px 18px 18px 0"
                # else: it's a single message or default applies

                bubble_style = f"""
                    background: {BOT_BUBBLE_BG};
                    color: {BOT_BUBBLE_TEXT};
                    padding: {BUBBLE_PADDING};
                    border-radius: {current_bot_radius};
                    max-width: {MAX_BUBBLE_WIDTH};
                    word-wrap: break-word; /* or overflow-wrap: break-word; */
                    font-family: {CHAT_FONT_FAMILY};
                    font-size: {CHAT_FONT_SIZE};
                    line-height: {LINE_HEIGHT};
                    display: inline-block; /* Important for the bubble to size to content */
                """
                # Outer div for alignment
                html_output += f'''
                    <div style="display: flex; justify-content: flex-start; margin: {MESSAGE_MARGIN if is_first_message_in_sequence else "2px 0"}; clear: both;">
                        <div style="{bubble_style.strip()}">
                            {content}
                        </div>
                    </div>
                '''
                
        self.chat_area.setHtml(html_output)
        
    # Scroll to the bottom
        scrollbar = self.chat_area.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def handle_input(self):
        user_message = self.textbox.text()
        if not user_message.strip():
            return
        self.conversation_history.append({'role': 'user', 'content': user_message})
        self.append_chat_bubble(f"<b style='color:#8bc34a;'>You:</b> {user_message}")
        self.refresh_chat_area()
        self.textbox.clear()
        # WhatsApp pending message flow
        if self.assistant_ref and self.assistant_ref.pending_action == 'whatsapp_message':
            contact_name = self.assistant_ref.pending_whatsapp_contact
            message = user_message
            contacts = json.load(open('contacts.json'))
            if contact_name not in contacts:
                response = f"Contact {contact_name} not found."
            else:
                phone_number = contacts[contact_name]
                try:
                    pyautogui.sendwhatmsg_instantly(phone_number, message, wait_time=10, tab_close=True, close_time=5)
                    time.sleep(5)
                    pyautogui.press('enter')
                    text_to_speech(f"Message sent to {contact_name}", after_speech_callback=self.start_listening)
                    response = ""
                except Exception as e:
                    response = f"Failed to send message: {str(e)}"
            self.assistant_ref.pending_action = None
            self.assistant_ref.pending_whatsapp_contact = None
            self.conversation_history.append({'role': 'assistant', 'content': response})
            self.append_chat_bubble(f"<b style='color:#03a9f4;'>Levos:</b> {response}")
            self.refresh_chat_area()
            text_to_speech(response, after_speech_callback=self.start_listening)
            save_conversation(self.conversation_history)
            return
        # Always trigger LLM for user input
        command_keywords = ['play the song', 'play the video', 'send message to', 'whatsapp', 'joke', 'who is', 'status', 'time', 'date', 'open', 'add contact', 'spotify','anime','watch the anime']
        if any(kw in user_message.lower() for kw in command_keywords):
            response = handle_command(user_message, self.refresh_chat_area, assistant_ref=self.assistant_ref)
            if response:
                self.conversation_history.append({'role': 'assistant', 'content': response})
                self.refresh_chat_area()
                text_to_speech(response, after_speech_callback=None)
                save_conversation(self.conversation_history)
                return
        llm_response = sakura_llm_response(user_message, self.conversation_history)
        self.conversation_history.append({'role': 'assistant', 'content': llm_response})
        self.refresh_chat_area()
        text_to_speech(llm_response, after_speech_callback=self.start_listening)    
        save_conversation(self.conversation_history)


    # Add this to your main application class
    def setup_wake_word_detection(self):
        """Initialize and start the wake word detector"""
        self.wake_word_detector = WakeWordDetector(self)
        self.wake_word_detector.start_detection()

    def wake_word_activated(self):
        self.handle_voice_input()
        self.update_mic_button.emit('🔴', self.mic_listening_style())
        print("listening activated")

    def handle_voice_input(self):
        self.update_mic_button.emit('🔴', self.mic_listening_style())
        if not hasattr(self, 'listening') or not self.listening:
            self.update_mic_button.emit('🎤', self.mic_idle_style())
            return
            
        recognizer = sr.Recognizer()
        try:
            with sr.Microphone() as source:
                if not self.listening:
                    self.update_mic_button.emit('🎤', self.mic_idle_style())
                    return
                
                try:
                    recognizer.adjust_for_ambient_noise(source, duration=1)
                    if not self.listening:
                        self.update_mic_button.emit('🎤', self.mic_idle_style())
                        return
                    
                    audio = recognizer.listen(source, phrase_time_limit=5)
                    if not self.listening:
                        self.update_mic_button.emit('🎤', self.mic_idle_style())
                        return
                    
                    try:
                        text = recognizer.recognize_google(audio)
                        if not self.listening:
                            self.update_mic_button.emit('🎤', self.mic_idle_style())
                            return
                            
                        # Update textbox with recognized text and clear it immediately
                        self.update_textbox.emit(text)
                        QtCore.QTimer.singleShot(100, lambda: self.update_textbox.emit(""))
                        
                        # Handle commands directly without triggering handle_input
                        command_keywords = ['play the song', 'play the video', 'send message to', 'whatsapp', 'joke', 'who is', 'status', 'time', 'date', 'open', 'add contact', 'spotify','anime','watch the anime']
                        if any(kw in text.lower() for kw in command_keywords):
                            response = handle_command(text, self.refresh_chat_area, assistant_ref=self.assistant_ref)
                            if response:
                                self.conversation_history.append({'role': 'user', 'content': text})
                                self.conversation_history.append({'role': 'assistant', 'content': response})
                                self.update_chat_area.emit()
                                text_to_speech(response, after_speech_callback=self.start_listening)
                                save_conversation(self.conversation_history)
                        else:
                            # For non-command inputs, use the regular input handler
                            self.user_input = text
                            QtCore.QTimer.singleShot(0, self.handle_input)
                        
                    except sr.UnknownValueError:
                        if self.listening:
                            pass
                    except sr.RequestError as e:
                        if self.listening:
                            print(f'Could not request results; {e}')
                            
                except sr.WaitTimeoutError:
                    if self.listening:
                        print('Listening timed out. Try again.')
                        
        except Exception as e:
            print(f"Error in voice input: {str(e)}")
        finally:
            self.update_mic_button.emit('🎤', self.mic_idle_style())

    def start_listening(self):
        if hasattr(self, 'listening') and self.listening:
            self.update_mic_button.emit('🔴', self.mic_listening_style())
            return
        self.listening = True
        print("i'm listening")
        threading.Thread(target=self.handle_voice_input, daemon=True).start()

    def stop_listening(self):
        if not hasattr(self, 'listening') or not self.listening:
            self.update_mic_button.emit('🎤', self.mic_idle_style())
            return
        self.listening = False
        print("stopping listening")

    def append_chat_bubble(self, message):
        self.chat_area.append(f"<div style='margin: 10px 0;'>{message}</div>")

    def update_mic_ui(self, icon, style):
        self.mic_btn.setText(icon)
        self.mic_btn.setStyleSheet(style)

    def mic_idle_style(self):
        return """
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #ed4245, stop:1 #c73e3e);
                color: white;
                border-radius: 20px;
                font-size: 16px;
                min-width: 40px;
                min-height: 40px;
                border: none;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #f04747, stop:1 #d84545);
            }
            QPushButton:pressed {
                background: #c73e3e;
            }
        """

    def mic_listening_style(self):
        return """
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #43b581, stop:1 #3ca374);
                color: white;
                border-radius: 20px;
                font-size: 16px;
                min-width: 40px;
                min-height: 40px;
                border: none;
                animation: pulse 1s infinite;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #4fc08d, stop:1 #42a678);
            }
        """

    def update_status_bar(self, message):
        """Optional: Add a method for status updates"""
        if hasattr(self, 'statusBar'):
            self.statusBar().showMessage(message, 2000)