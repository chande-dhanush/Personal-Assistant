from PyQt5 import QtCore, QtGui, QtWidgets

class NotesPanel(QtWidgets.QFrame):
    note_selected = QtCore.pyqtSignal(str) # Emits path
    refresh_requested = QtCore.pyqtSignal() 
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("NotesPanel")
        self.setVisible(False)
        self.initUI()
        
    def initUI(self):
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)
        
        # Header Row
        header_layout = QtWidgets.QHBoxLayout()
        title = QtWidgets.QLabel("📝 Saved Notes")
        title.setStyleSheet("color: #b9bbbe; font-weight: bold; font-size: 13px;")
        header_layout.addWidget(title)
        
        header_layout.addStretch()
        
        self.refresh_btn = QtWidgets.QPushButton("🔄")
        self.refresh_btn.setFixedSize(24, 24)
        self.refresh_btn.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
        self.refresh_btn.setStyleSheet("background: transparent; color: #b9bbbe; border: none;")
        self.refresh_btn.clicked.connect(self.refresh_requested.emit)
        header_layout.addWidget(self.refresh_btn)
        
        layout.addLayout(header_layout)
        
        # List
        self.notes_list = QtWidgets.QListWidget(self)
        self.notes_list.setObjectName("NotesList") # Styled by QSS
        self.notes_list.setFixedHeight(150)
        self.notes_list.itemClicked.connect(self._on_item_clicked)
        layout.addWidget(self.notes_list)
        
    def update_notes(self, notes_data):
        self.notes_list.clear()
        for n in notes_data:
            # n = {title, folder, path}
            display_text = f"{n['folder']}  /  {n['title']}"
            item = QtWidgets.QListWidgetItem(display_text)
            item.setData(QtCore.Qt.UserRole, n['path'])
            item.setToolTip(n['path'])
            self.notes_list.addItem(item)
            
    def _on_item_clicked(self, item):
        path = item.data(QtCore.Qt.UserRole)
        self.note_selected.emit(path)

    def toggle(self):
        self.setVisible(not self.isVisible())
