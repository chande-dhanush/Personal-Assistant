# Yuki V3 UI Components
## ChatWindow + MessageBubble Architecture

This document explains the layout decisions and best practices for the Yuki V3 chat UI.

---

## Architecture Overview

```
SakuraChatWindow (QWidget)
└── QVBoxLayout
    └── card (QFrame)
        ├── header
        ├── notes_panel
        ├── toolbar
        ├── debug_drawer
        ├── scroll_area (QScrollArea) ← stretch=1
        │   └── chat_container (QWidget)
        │       └── chat_layout (QVBoxLayout)
        │           └── MessageBubble[] (QWidget)
        │               └── bubble_frame (QFrame)
        │                   └── label (QLabel / TypewriterLabel)
        ├── selection_bar
        └── input_bar
```

---

## Key Design Decisions

### 1. SizePolicy Configuration

| Component | Horizontal | Vertical | Rationale |
|-----------|------------|----------|-----------|
| `chat_container` | Preferred | Minimum | Grows with content, no stretch |
| `MessageBubble` | Preferred | Maximum | Shrinks to content height |
| `bubble_frame` | Preferred | Maximum | Matches bubble sizing |
| `label` | Preferred | Maximum | Text determines height |

### 2. Why No sizeHint Override

Qt's default `sizeHint()` for QLabel with `wordWrap=True` is width-dependent. Custom overrides caused:
- Width-dependent height collapse
- Short messages disappearing at wide window widths
- Resize feedback loops

**Solution**: Let Qt handle sizing naturally with proper SizePolicy.

### 3. MinimumWidth on bubble_frame

When a QHBoxLayout has alignment set (AlignLeft/AlignRight), child widgets can shrink to 0px width. Setting `bubble_frame.setMinimumWidth(100)` prevents this collapse.

### 4. Autoscroll Behavior

```python
dist = scrollbar.maximum() - scrollbar.value()
if dist < THRESHOLD or role == 'user':
    scroll_to_bottom()
```

- Only auto-scroll when near bottom (< 100px)
- Always scroll for user's own messages
- Use `QTimer.singleShot(0, ...)` to let layout settle

### 5. Layout Constraints

```python
chat_layout.setAlignment(QtCore.Qt.AlignTop)
chat_layout.setSizeConstraint(QtWidgets.QLayout.SetMinAndMaxSize)
```

- `AlignTop` stacks bubbles from top without filling gaps
- `SetMinAndMaxSize` helps Qt bound the layout correctly

---

## V3 Signal Contract

The ViewModel emits a single signal for all messages:

```python
# ViewModel
response_ready = pyqtSignal(dict)

# Payload format
{
    "role": "user" | "assistant",
    "content": "message text",
    "metadata": {
        "mode": "...",
        "tool_used": "...",
        "confidence": 0.0,
        "mood": "..."
    }
}
```

ChatWindow connects to this signal:
```python
self.vm.response_ready.connect(self._on_message_received)
```

---

## Tunable Parameters

| Parameter | Location | Default | Purpose |
|-----------|----------|---------|---------|
| `SCROLL_THRESHOLD` | ChatWindow | 100px | Distance from bottom for autoscroll |
| `MIN_WIDTH` | MessageBubble | 100px | Minimum bubble width |
| `FONT_SIZE` | MessageBubble | 26 | Text font size |
| `speed_ms` | TypewriterLabel | 20ms | Typing animation speed |

---

## Performance Notes

- Bubbles are created once and added to layout
- No virtualization (all bubbles in DOM)
- For very long histories (>1000), consider:
  - Implementing virtual scrolling
  - Pagination / lazy loading
  - Removing old bubbles from layout

---

## Testing

Run smoke tests:
```bash
python tests/ui_smoke.py
```

Run stress test:
```bash
python ui_test_runner.py
```
