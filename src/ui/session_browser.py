import os
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QListWidget, QPushButton, QLabel

class SessionBrowser(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("OmniGemini Session Manager")
        self.setMinimumWidth(600)
        self.setMinimumHeight(450)
        self.setStyleSheet(
            """
            QDialog { background-color: #1E1E2E; color: #CDD6F4; font-family: 'Segoe UI', sans-serif; }
            QListWidget { background-color: #181825; color: #CDD6F4; border: 1px solid #313244; border-radius: 8px; padding: 10px; font-size: 13px; }
            QListWidget::item { padding: 8px; border-bottom: 1px solid #313244; }
            QListWidget::item:selected { background-color: #313244; color: #89B4FA; font-weight: bold; }
            QPushButton { background-color: #313244; color: #CDD6F4; border-radius: 6px; padding: 12px; font-weight: bold; border: 1px solid #45475A; }
            QPushButton:hover { background-color: #45475A; border: 1px solid #89B4FA; }
            QLabel { font-weight: bold; color: #89B4FA; margin-bottom: 5px; }
            """)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Select a previous session log to reload into current memory:"))

        self.list_widget = QListWidget()
        layout.addWidget(self.list_widget)

        self.load_logs()

        btn_layout = QHBoxLayout()
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        self.load_btn = QPushButton("🚀 RELOAD CONVERSATION")
        self.load_btn.setStyleSheet("background-color: #89B4FA; color: #11111B;")
        self.load_btn.clicked.connect(self.accept)

        btn_layout.addWidget(self.cancel_btn)
        btn_layout.addWidget(self.load_btn)
        layout.addLayout(btn_layout)

    def load_logs(self):
        log_dir = "logs"
        if not os.path.exists(log_dir):
            return
        # Get all md files, excluding the latest_webcam one if it exists
        files = sorted([f for f in os.listdir(log_dir) if f.endswith(".md") and not f.startswith("latest")], reverse=True)
        for f in files:
            self.list_widget.addItem(f)

    def get_selected_file(self):
        item = self.list_widget.currentItem()
        return item.text() if item else None
