"""
MessageBubble Component - Yuki V3 UI
=====================================

ARCHITECTURE DECISIONS:
-----------------------
1. SizePolicy: Preferred (H) / Maximum (V)
   - Preferred horizontal: grows to content, shrinks gracefully
   - Maximum vertical: never stretches beyond content height
   - This prevents bubbles from expanding to fill empty space

2. MinimumWidth: 100px on bubble_frame
   - Prevents Qt from collapsing short messages to 0px width
   - When HBoxLayout has alignment set, children can shrink arbitrarily
   - 100px floor ensures visibility without forcing fixed size

3. No sizeHint/minimumSizeHint overrides
   - Qt's default size hint calculation is sufficient
   - Custom overrides caused width-dependent collapse bugs

4. No resizeEvent width manipulation
   - Dynamic maxWidth changes during resize caused feedback loops
   - Parent layout handles width distribution naturally

5. WordWrap enabled on all labels
   - Text wraps within available width
   - Height adjusts automatically

USAGE:
------
    bubble = MessageBubble("user", "Hello!", typing_enabled=False)
    bubble.long_pressed.connect(on_long_press)
    bubble.clicked.connect(on_click)
    layout.addWidget(bubble)

"""
from PyQt5 import QtCore, QtGui, QtWidgets


class TypewriterLabel(QtWidgets.QLabel):
    """
    QLabel with character-by-character typing animation.
    Emits finished_typing when animation completes.
    """
    finished_typing = QtCore.pyqtSignal()

    def __init__(self, text, speed_ms=20, parent=None):
        super().__init__(parent)
        self.full_content = text
        self.current_index = 0
        self.speed_ms = speed_ms
        
        # Timer for animation
        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self._step)
        
        # Label configuration
        self.setWordWrap(True)
        self.setTextFormat(QtCore.Qt.RichText)
        self.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
        self.setText("")

    def start_typing(self):
        """Begin the typing animation."""
        self.timer.start(self.speed_ms)

    def _step(self):
        """Advance one step in the animation."""
        if self.current_index < len(self.full_content):
            # Type 2 characters per step for better speed
            self.current_index = min(self.current_index + 2, len(self.full_content))
            visible = self.full_content[:self.current_index]
            self.setText(visible.replace('\n', '<br>'))
        else:
            self._finish()

    def _finish(self):
        """Complete the animation."""
        self.timer.stop()
        self.setText(self.full_content.replace('\n', '<br>'))
        self.finished_typing.emit()

    def set_immediate(self, text):
        """Skip animation and show full text."""
        self.timer.stop()
        self.full_content = text
        self.current_index = len(text)
        self.setText(text.replace('\n', '<br>'))


class MessageBubble(QtWidgets.QWidget):
    """
    Chat message bubble widget.
    
    Signals:
        long_pressed(self): Emitted on 800ms press-and-hold
        clicked(self): Emitted on tap/click
    
    Properties:
        role: 'user' or 'assistant'
        content: Message text
        is_selected: Selection state for multi-select
    """
    long_pressed = QtCore.pyqtSignal(object)
    clicked = QtCore.pyqtSignal(object)

    # Style constants
    USER_COLOR = "#273550"
    ASSISTANT_COLOR = "#1C273A"
    TEXT_COLOR = "#DCE7FF"
    SELECTED_BORDER = "#7AB8FF"
    FONT_SIZE = 26
    MIN_WIDTH = 100

    def __init__(self, role, content, typing_enabled=False, parent=None):
        super().__init__(parent)
        self.role = role
        self.content = content
        self.typing_enabled = typing_enabled
        self.is_selected = False
        
        # Long-press detection
        self._press_timer = QtCore.QTimer(self)
        self._press_timer.setInterval(800)
        self._press_timer.setSingleShot(True)
        self._press_timer.timeout.connect(lambda: self.long_pressed.emit(self))
        
        self._init_ui()

    def _init_ui(self):
        """Build the bubble UI."""
        # Outer horizontal layout - NO alignment, use spacers instead
        outer = QtWidgets.QHBoxLayout(self)
        outer.setContentsMargins(10, 5, 10, 5)
        outer.setSpacing(0)
        
        # Create spacer and bubble
        spacer = QtWidgets.QSpacerItem(0, 0, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        
        # Bubble frame with Expanding horizontal to prevent collapse
        self.bubble_frame = QtWidgets.QFrame()
        self.bubble_frame.setSizePolicy(
            QtWidgets.QSizePolicy.Expanding,  # Take available space
            QtWidgets.QSizePolicy.Preferred   # Natural height
        )
        self.bubble_frame.setMinimumWidth(self.MIN_WIDTH)
        self.bubble_frame.setMaximumWidth(600)  # Cap max width for readability
        
        # Bubble internal layout
        bubble_layout = QtWidgets.QVBoxLayout(self.bubble_frame)
        bubble_layout.setContentsMargins(15, 10, 15, 10)
        bubble_layout.setSpacing(0)
        
        # Create label
        if self.role == 'assistant' and self.typing_enabled:
            self.label = TypewriterLabel(self.content, speed_ms=20, parent=self.bubble_frame)
            self.label.start_typing()
        else:
            self.label = QtWidgets.QLabel(self.bubble_frame)
            self.label.setWordWrap(True)
            self.label.setTextFormat(QtCore.Qt.RichText)
            self.label.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
            self.label.setOpenExternalLinks(True)
            self.label.setText(self.content.replace('\n', '<br>'))
        
        # Label sizing - Preferred to wrap content
        self.label.setSizePolicy(
            QtWidgets.QSizePolicy.Preferred,
            QtWidgets.QSizePolicy.Preferred
        )
        
        # Font
        font = QtGui.QFont("Segoe UI", self.FONT_SIZE)
        self.label.setFont(font)
        
        # Add label to bubble
        bubble_layout.addWidget(self.label)
        
        # Add to outer layout with spacer for alignment
        if self.role == 'user':
            # User messages: spacer on LEFT, bubble on RIGHT
            outer.addItem(spacer)
            outer.addWidget(self.bubble_frame)
        else:
            # Assistant messages: bubble on LEFT, spacer on RIGHT
            outer.addWidget(self.bubble_frame)
            outer.addItem(spacer)
        
        # Apply styling
        self._apply_style()
        
        # Event filter for click detection on child widgets
        self.label.installEventFilter(self)
        self.bubble_frame.installEventFilter(self)

    def _apply_style(self):
        """Apply visual styling based on role and selection state."""
        if self.role == 'user':
            bg = self.USER_COLOR
            radius = "border-bottom-right-radius: 2px;"
        else:
            bg = self.ASSISTANT_COLOR
            radius = "border-bottom-left-radius: 2px;"
        
        border = f"border: 1px solid {self.SELECTED_BORDER};" if self.is_selected else "border: none;"
        
        self.bubble_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {bg};
                color: {self.TEXT_COLOR};
                border-radius: 18px;
                {radius}
                padding: 4px;
                {border}
            }}
        """)

    def set_selected(self, selected):
        """Toggle selection state."""
        self.is_selected = selected
        self._apply_style()

    # --- Event Handling ---
    
    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            self._press_timer.start()
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        if self._press_timer.isActive():
            self._press_timer.stop()
            self.clicked.emit(self)
        super().mouseReleaseEvent(event)

    def eventFilter(self, obj, event):
        """Handle events on child widgets."""
        if event.type() == QtCore.QEvent.MouseButtonPress:
            if event.button() == QtCore.Qt.LeftButton:
                self._press_timer.start()
        elif event.type() == QtCore.QEvent.MouseButtonRelease:
            if self._press_timer.isActive():
                self._press_timer.stop()
                self.clicked.emit(self)
        return super().eventFilter(obj, event)
