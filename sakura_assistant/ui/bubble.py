import os
from PyQt5 import QtCore, QtGui, QtWidgets
from datetime import datetime, timedelta, timezone
from sakura_assistant.utils.tts import text_to_speech
from ..memory.faiss_store import load_conversation, save_conversation, clear_conversation_history
from .chat_window import SakuraChatWindow
import random
import json
import threading
import time

class SakuraBubble(QtWidgets.QWidget):

    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            QtCore.Qt.FramelessWindowHint |
            QtCore.Qt.WindowStaysOnTopHint |
            QtCore.Qt.Tool # Ensures it doesn't show in taskbar, typically
        )
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.setFixedSize(70, 70)

        # --- Configuration and State ---
        self.expanded = False # Currently not used, but good for future features
        self.conversation_history = load_conversation()
        # self.pending_action = None # Not used in provided snippet
        # self.pending_whatsapp_contact = None # Not used in provided snippet
        
        self._pulse_scale = 1.0
        self.listening_glow_intensity = 0.0 # 0.0 to 1.0 for smooth transitions
        self.hover_glow_intensity = 0.0 # 0.0 to 1.0 for smooth transitions

        self.idle_animation_speed = 3000  # ms for one pulse cycle
        self.active_animation_speed = 2000  # ms for one pulse cycle

        self.is_dragging = False
        self.drag_position = None
        self.is_hovered = False # Track hover state for paintEvent
        self.last_message_time = None  # in __init__

        # --- UI Colors & Style ---
        self.ICON_SIZE = 56 # Slightly smaller than bubble for padding
        self.BASE_BUBBLE_COLOR_START = QtGui.QColor("#360000") # Dark muted purple/blue
        self.BASE_BUBBLE_COLOR_END = QtGui.QColor("#000033")   # Deeper shade
        self.BORDER_COLOR_IDLE = QtGui.QColor("#6B728E") # Slightly lighter border
        self.BORDER_COLOR_HOVER = QtGui.QColor("#9A8C98") # Muted pink/lavender for hover
        self.BORDER_COLOR_ACTIVE = QtGui.QColor("#C9ADA7") # Soft pink for active listening
        
        self.SHADOW_COLOR = QtGui.QColor(0, 0, 0, 50)
        
        self.GLOW_COLOR_HOVER = QtGui.QColor(220, 200, 220, 100) # Soft lavender glow
        self.GLOW_COLOR_LISTENING = QtGui.QColor(240, 180, 180, 150) # Soft pink glow

        self.EMOJI_FONT_SIZE = 28
        self.EMOJI_COLOR = QtGui.QColor("#F2E9E4") # Off-white for emoji

        # Find and set application icon
        self.icon_pixmap = None # Store loaded pixmap
        self.load_icon()
        
        # Setup UI components
        self.initUI()
        self.installEventFilter(self) # For hover effects
        self.move_to_corner()
        
        self.chat_window = None
        
        self.setup_animations()
        self.setup_context_menu()
        
        # Wake word listener removed - user requested removal

    def load_icon(self):
        icon_paths_to_check = ['sakura_assistant\\assets']
        # Prefer PNG for transparency
        preferred_extensions = ["png", "svg"] # SVG might need QSvgRenderer
        other_extensions = ["jpeg", "jpg"]
        
        base_filenames = ["Icon", "app_icon","icon"] # Common names
        
        # Check in current directory and an 'assets' subdirectory
        possible_dirs = [os.getcwd()] + icon_paths_to_check

        for dirname in possible_dirs:
            if os.path.exists(dirname):
                for fname_base in base_filenames:
                    for ext in preferred_extensions + other_extensions:
                        candidate = os.path.join(dirname, f"{fname_base}.{ext}")
                        if os.path.exists(candidate):
                            icon_paths_to_check.append(candidate)

        # Use the first valid path
        loaded_icon_path = None
        for path in icon_paths_to_check:
            pixmap = QtGui.QPixmap(path)
            if not pixmap.isNull():
                self.icon_pixmap = pixmap.scaled(self.ICON_SIZE, self.ICON_SIZE,
                                                 QtCore.Qt.KeepAspectRatio,
                                                 QtCore.Qt.SmoothTransformation)
                loaded_icon_path = path
                self.setWindowIcon(QtGui.QIcon(path)) # Set window icon for OS
                break
        
        if not loaded_icon_path:
            print(f"Warning: Icon not found. Searched in: {possible_dirs} for {base_filenames} with extensions {preferred_extensions + other_extensions}")

    def initUI(self):
        # Main container for icon or emoji - no explicit QLabel needed if drawing in paintEvent
        # However, QLabels are easier for simple image/text. We'll draw icon in paintEvent for smoothness.
        # The emoji will also be drawn in paintEvent.
        self.setToolTip('Sakura Assistant\nClick to open chat\nRight-click for options\n(Ctrl+Right-click to drag)')

    def setup_animations(self):
        # Pulse animation for the bubble scale
        self.pulse_anim = QtCore.QPropertyAnimation(self, b"pulse_scale_prop") # Use property name
        self.pulse_anim.setDuration(self.idle_animation_speed)
        self.pulse_anim.setStartValue(1.0)
        self.pulse_anim.setKeyValueAt(0.5, 1.05) # More natural pulse
        self.pulse_anim.setEndValue(1.0)
        self.pulse_anim.setEasingCurve(QtCore.QEasingCurve.InOutSine)
        self.pulse_anim.setLoopCount(-1)
        self.pulse_anim.start()

        # Smooth transition for listening glow
        self.listening_glow_anim = QtCore.QPropertyAnimation(self, b"listening_glow_prop")
        self.listening_glow_anim.setDuration(300) # Quick transition
        self.listening_glow_anim.setEasingCurve(QtCore.QEasingCurve.InOutQuad)

        # Smooth transition for hover glow
        self.hover_glow_anim = QtCore.QPropertyAnimation(self, b"hover_glow_prop")
        self.hover_glow_anim.setDuration(200)
        self.hover_glow_anim.setEasingCurve(QtCore.QEasingCurve.InOutQuad)

    def setup_context_menu(self):
        self.context_menu = QtWidgets.QMenu(self)
        
        open_action = self.context_menu.addAction("Open Chat")
        open_action.triggered.connect(self.open_chat_window)
        
        # self.toggle_listen_action = self.context_menu.addAction("Enable Voice Wake") # Original
        # ... (rest of wake listener setup)

        self.context_menu.addSeparator()
        settings_action = self.context_menu.addAction("Commands/Keywords")
        settings_action.triggered.connect(self.open_settings)
        self.context_menu.addSeparator()
        quit_action = self.context_menu.addAction("Quit")
        quit_action.triggered.connect(self.close_application)

        # Style the context menu for a more professional look
        self.context_menu.setStyleSheet(f"""
            QMenu {{
                background-color: #2B2D31; /* Dark background */
                color: #D1D0C5; /* Light grey text */
                border: 1px solid #404348;
                border-radius: 5px;
                padding: 5px;
            }}
            QMenu::item {{
                padding: 8px 20px 8px 20px;
                margin: 2px 0px; /* Spacing between items */
                border-radius: 4px; /* Rounded corners for items */
            }}
            QMenu::item:selected {{
                background-color: #5865F2; /* Accent color for selection */
                color: #FFFFFF;
            }}
            QMenu::separator {{
                height: 1px;
                background-color: #404348;
                margin-left: 10px;
                margin-right: 10px;
                margin-top: 4px;
                margin-bottom: 4px;
            }}
        """)
    # --- Properties for animations ---
    def get_pulse_scale(self):
        return self._pulse_scale

    def set_pulse_scale(self, value):
        if self._pulse_scale != value:
            self._pulse_scale = value
            self.update() # Trigger repaint
    
    pulse_scale_prop = QtCore.pyqtProperty(float, fget=get_pulse_scale, fset=set_pulse_scale)

    def get_listening_glow_intensity(self):
        return self.listening_glow_intensity

    def set_listening_glow_intensity(self, value):
        if self.listening_glow_intensity != value:
            self.listening_glow_intensity = value
            self.update()

    listening_glow_prop = QtCore.pyqtProperty(float, fget=get_listening_glow_intensity, fset=set_listening_glow_intensity)

    def get_hover_glow_intensity(self):
        return self.hover_glow_intensity

    def set_hover_glow_intensity(self, value):
        if self.hover_glow_intensity != value:
            self.hover_glow_intensity = value
            self.update()
    hover_glow_prop = QtCore.pyqtProperty(float, fget=get_hover_glow_intensity, fset=set_hover_glow_intensity)
    # --- Paint Event ---
    # This is where we draw the bubble, shadows, glows, and icon/emoji
    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        
        rect = self.rect() # Full widget rect
        center_x, center_y = rect.width() / 2, rect.height() / 2
        
        # Effective radius, considering padding for shadow and glow
        bubble_radius = min(rect.width(), rect.height()) / 2 

        # --- 1. Draw Shadow ---
        painter.save()
        shadow_offset_y = bubble_radius * 0.6
        shadow_ellipse_rect = QtCore.QRectF(
            center_x - bubble_radius * 0.9, center_y + shadow_offset_y - (bubble_radius * 0.15), # Y pos slightly higher
            bubble_radius * 1.8, bubble_radius * 0.3 # Wider, flatter shadow
        )
        painter.setBrush(self.SHADOW_COLOR)
        painter.setPen(QtCore.Qt.NoPen)
        painter.drawEllipse(shadow_ellipse_rect)
        painter.restore()

        # --- Apply pulse scaling for bubble and content ---
        painter.save()
        painter.translate(center_x, center_y)
        painter.scale(self._pulse_scale, self._pulse_scale)
        painter.translate(-center_x, -center_y)

        # --- 2. Draw Outer Glows (Listening and Hover) ---
        # These glows are drawn first so the main bubble is on top
        current_glow_radius = bubble_radius + 3 # Glow slightly larger than bubble
        
        if self.listening_glow_intensity > 0:
            painter.save()
            glow_color_listening = QtGui.QColor(self.GLOW_COLOR_LISTENING)
            glow_color_listening.setAlphaF(self.listening_glow_intensity * (self.GLOW_COLOR_LISTENING.alphaF())) # Modulate alpha
            painter.setBrush(glow_color_listening)
            painter.setPen(QtCore.Qt.NoPen)
            painter.drawEllipse(QtCore.QPointF(center_x, center_y), current_glow_radius, current_glow_radius)
            painter.restore()

        if self.hover_glow_intensity > 0 and not self.listening_glow_intensity > 0.5 : # Don't overdo glow if already listening
            painter.save()
            glow_color_hover = QtGui.QColor(self.GLOW_COLOR_HOVER)
            glow_color_hover.setAlphaF(self.hover_glow_intensity * (self.GLOW_COLOR_HOVER.alphaF()))
            painter.setBrush(glow_color_hover)
            painter.setPen(QtCore.Qt.NoPen)
            painter.drawEllipse(QtCore.QPointF(center_x, center_y), current_glow_radius, current_glow_radius)
            painter.restore()
        # --- 3. Draw Main Bubble ---
        gradient = QtGui.QRadialGradient(center_x, center_y - bubble_radius * 0.2, bubble_radius * 1.5) # Offset for highlight
        gradient.setColorAt(0, self.BASE_BUBBLE_COLOR_START.lighter(120))
        gradient.setColorAt(0.5, self.BASE_BUBBLE_COLOR_START)
        gradient.setColorAt(1, self.BASE_BUBBLE_COLOR_END)
        painter.setBrush(QtGui.QBrush(gradient))
        current_border_color = self.BORDER_COLOR_IDLE
        if self.listening_glow_intensity > 0.5: # Prioritize active color
            current_border_color = self.BORDER_COLOR_ACTIVE
        elif self.is_hovered:
            current_border_color = self.BORDER_COLOR_HOVER
        # Draw the main bubble
        pen = QtGui.QPen(current_border_color, 6) # Border thickness
        painter.setPen(pen)
        painter.drawEllipse(QtCore.QPointF(center_x, center_y), bubble_radius, bubble_radius)

        # --- 4. Draw Icon or Emoji ---
        if self.icon_pixmap:
            icon_rect = QtCore.QRectF(0, 0, self.ICON_SIZE, self.ICON_SIZE)
            icon_rect.moveCenter(QtCore.QPointF(center_x, center_y))
            painter.drawPixmap(icon_rect.topLeft(), self.icon_pixmap)
        else:
            # Fallback to emoji
            font = painter.font()
            font.setPointSize(self.EMOJI_FONT_SIZE)
            # Try to use a font that supports emojis well, e.g., Segoe UI Emoji
            font.setFamily("Segoe UI Emoji, Noto Color Emoji, Apple Color Emoji, sans-serif")
            painter.setFont(font)
            painter.setPen(self.EMOJI_COLOR)
            painter.drawText(QtCore.QRectF(center_x - bubble_radius, center_y - bubble_radius, 
                                           bubble_radius*2, bubble_radius*2), 
                             QtCore.Qt.AlignCenter, '🌸')
        
        painter.restore() # Restore from pulse scaling
        painter.end()
        # super().paintEvent(event) # Not needed if we paint everything and widget is WA_TranslucentBackground

    
    def update_visual_state(self, is_listening=None, is_hovered=None):
        if is_listening is not None:
            target_glow = 1.0 if is_listening else 0.0
            if self.listening_glow_anim.state() == QtCore.QAbstractAnimation.Running:
                self.listening_glow_anim.stop()
            self.listening_glow_anim.setStartValue(self.listening_glow_intensity)
            self.listening_glow_anim.setEndValue(target_glow)
            self.listening_glow_anim.start()
            
            # Adjust pulse animation speed
            new_duration = self.active_animation_speed if is_listening else self.idle_animation_speed
            if self.pulse_anim.duration() != new_duration:
                self.pulse_anim.stop()
                self.pulse_anim.setDuration(new_duration)
                self.pulse_anim.start()

        if is_hovered is not None:
            self.is_hovered = is_hovered # Store direct state for border in paintEvent
            target_hover_glow = 1.0 if is_hovered else 0.0
            if self.hover_glow_anim.state() == QtCore.QAbstractAnimation.Running:
                self.hover_glow_anim.stop()
            self.hover_glow_anim.setStartValue(self.hover_glow_intensity)
            self.hover_glow_anim.setEndValue(target_hover_glow)
            self.hover_glow_anim.start()
        
        self.update() # Trigger repaint

    def move_to_corner(self):
        # Using QGuiApplication.primaryScreen() for multi-monitor awareness if available
        screen_geometry = QtWidgets.QApplication.primaryScreen().availableGeometry()
        padding = 30 # Padding from screen edges
        x = padding
        y = padding + 30 # A bit down from the very top
        self.move(x, y)

    def eventFilter(self, obj, event):
        if obj is self: # Ensure we are filtering events for this widget
            if event.type() == QtCore.QEvent.Enter:
                self.setCursor(QtCore.Qt.PointingHandCursor)
                self.update_visual_state(is_hovered=True)
                return True # Event handled
            elif event.type() == QtCore.QEvent.Leave:
                self.setCursor(QtCore.Qt.ArrowCursor)
                self.update_visual_state(is_hovered=False)
                return True # Event handled
        return super().eventFilter(obj, event)

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            # Simple: left click opens chat
            self.open_chat_window()
        elif event.button() == QtCore.Qt.RightButton:
            if QtWidgets.QApplication.keyboardModifiers() & QtCore.Qt.ControlModifier:
                self.is_dragging = True
                self.drag_position = event.globalPos() - self.frameGeometry().topLeft()
            else:
                self.context_menu.popup(event.globalPos())
            event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() == QtCore.Qt.RightButton and self.is_dragging:
            self.is_dragging = False
        super().mouseReleaseEvent(event)

    def should_greet(self):
        if self.last_message_time is None:
            self.last_message_time = datetime.now()
            return True  # First time opening, greet
        now = datetime.now()
        should_greet = (now - self.last_message_time) > timedelta(hours=3)
        self.last_message_time = now
        return should_greet

    def mouseMoveEvent(self, event):
        if self.is_dragging and event.buttons() == QtCore.Qt.RightButton:
            self.move(event.globalPos() - self.drag_position)
            event.accept()

    def get_greeting(self):
        hour = datetime.now().hour

        base = (
            "Good morning" if 5 <= hour < 12 else
            "Good afternoon" if 12 <= hour < 17 else
            "Good evening" if 17 <= hour < 22 else
            "You're still awake? Bold of you."
        )

        snarks = [
            "what's up?"
        ]

        return f"{base}, {random.choice(snarks)}"

    def open_chat_window(self):
        print("DEBUG: open_chat_window called")
        if self.chat_window is None:
            # CRITICAL: Do NOT set parent=self. This makes it a top-level window.
            # If parent is set to the bubble (which is a tool window/overlay), 
            # the chat window might get hidden or behave weirdly.
            self.chat_window = SakuraChatWindow(self.conversation_history, parent=None)
        
        # Ensure window is normal (not minimized)
        if self.chat_window.isMinimized():
            self.chat_window.showNormal()
            
        # Position logic - simplified to center of screen if off-screen
        screen_geo = QtWidgets.QApplication.primaryScreen().availableGeometry()
        
        # If window is not visible or first time, position it near bubble
        if not self.chat_window.isVisible():
            bubble_rect = self.geometry()
            chat_width = 500
            chat_height = 700
            self.chat_window.resize(chat_width, chat_height)
            
            # Default to right of bubble
            x = bubble_rect.right() + 20
            y = bubble_rect.top()
            
            # If off screen, center it
            if x + chat_width > screen_geo.right():
                x = screen_geo.center().x() - (chat_width // 2)
                y = screen_geo.center().y() - (chat_height // 2)
                
            self.chat_window.move(x, y)

        self.chat_window.show()
        self.chat_window.raise_()
        self.chat_window.activateWindow()

        if self.should_greet():
            greeting = self.get_greeting()
            print(f"Greeting: {greeting}")
            self.conversation_history.append({'role': 'assistant', 'content': greeting})
            if hasattr(self.chat_window, 'refresh_chat_area'):
                self.chat_window.refresh_chat_area()
            text_to_speech(greeting)
        
        self.last_message_time = datetime.now()

    def check_listening_status_after_wake(self):
        """Resets glow if chat window is not actively listening."""
        if self.chat_window and self.chat_window.isVisible() and hasattr(self.chat_window, 'listening'):
            if not self.chat_window.listening:
                self.update_visual_state(is_listening=False)
        else: # No chat window or it doesn't support 'listening' attribute
            self.update_visual_state(is_listening=False)

    def open_settings(self):
        # Using a more modern styled message box if possible, or just QMessageBox
        msg_box = QtWidgets.QMessageBox(self)
        msg_box.setWindowTitle("Settings")
        msg_box.setTextFormat(QtCore.Qt.RichText) # Allows basic HTML
        msg_box.setText("Sakura Assistant Settings")
        msg_box.setInformativeText(
            "Right now these are the commands you can use:<ul>, but you can add more in the tools file.<br>"
            "<b>🎵 Spotify & Media:</b><ul>"
            "<li><i>Plays a song via Spotify</li>"
            "<li><i>Controls spotify playback</li>"
            "<li><i>Plays a video via YouTube</li></ul>"
            "<b>💬 Chat, Info & Fun:</b><ul>"
            "<li>Info via Wikipedia (sometimes chaotic)</li>"
            "<li>Tech joke from pyjokes</li>"
            "<li>Shows system info</li>"
            "<li>Current time</li>"
            "<li>Today’s date</li></ul>"
            "<b>🌐 Browsing & Tools:</b><ul>"
            "<li> Opens any site in your browser</li>"
            "<li> Instant answers via DuckDuckGo</li>"
            "<li> Weather using OpenWeatherMap</li>"
            "<li> Opens your default mail client</li></ul>"
            "<b>🧠 Messaging & Personalization:</b><ul>"
            "<li><i>send a message to [contact] saying [message]</i> — WhatsApp it</li>"
            "<li><i>add contact [name, number]</i> — Adds contact to your list</li></ul>"
            "<b>🍿 Anime:</b><ul>"
            "<li><i>/anime</i> — Opens HiAnime homepage</li>"
            "<li> Searches anime</li></ul>"
            "<b>🤖 Fun & Random:</b><ul>"
            "<li> Drops random wisdom</li></ul>"
        )

        msg_box.setIcon(QtWidgets.QMessageBox.Information)
        msg_box.setStandardButtons(QtWidgets.QMessageBox.Ok)
        # Apply some basic styling to the QMessageBox
        msg_box.setStyleSheet("""
            QMessageBox {
                background-color: #2B2D31;
                color: #D1D0C5;
                font-size: 10pt;
            }
            QLabel#qt_msgbox_label { /* Title */
                color: #FFFFFF;
                font-size: 12pt;
                font-weight: bold;
            }
            QLabel#qt_msgbox_informativelabel { /* Main text */
                color: #B9BBBE;
            }
            QPushButton {
                background-color: #5865F2;
                color: white;
                padding: 8px 16px;
                border-radius: 4px;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #4754C7;
            }
        """)
        msg_box.exec_()
    
    def close_application(self):
        if self.chat_window:
            # save_conversation(self.conversation_history) # Assuming history is updated by chat_window
            self.chat_window.close()
        QtWidgets.QApplication.quit()
        
    def closeEvent(self, event):
        self.close_application()
        event.accept()
