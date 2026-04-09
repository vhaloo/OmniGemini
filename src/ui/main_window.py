import asyncio
import ctypes
import os
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QTextEdit, QLineEdit, QCheckBox, 
                             QLabel, QSplitter, QProgressBar, QFrame, QDialog)
from PyQt6.QtGui import QPixmap
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from src.config import save_config
from src.ui.utils import rich_to_html
from src.ui.settings import SettingsDialog
from src.ui.session_browser import SessionBrowser

class MainWindow(QMainWindow):
    log_signal = pyqtSignal(str)
    frame_signal = pyqtSignal(bytes)
    volume_signal = pyqtSignal(int)
    disconnect_signal = pyqtSignal()
    working_signal = pyqtSignal(bool)

    def __init__(self, agent):
        super().__init__()
        self.agent = agent
        self.setWindowTitle("OmniGemini - Live Desktop Assistant v0.5.0")
        self.resize(1400, 950)
        
        self.current_font_size = 10
        
        self.setStyleSheet(
            """
            QMainWindow { background-color: #11111B; color: #CDD6F4; font-family: 'Segoe UI', sans-serif; }
            QWidget#mainContainer { background-color: #11111B; }
            QWidget#headerBar { background-color: #181825; border-bottom: 1px solid #313244; }
            QWidget#leftPanel, QWidget#rightPanel { background-color: #1E1E2E; border-radius: 8px; }
            QPushButton { background-color: #313244; color: #CDD6F4; border-radius: 6px; padding: 8px 16px; font-weight: bold; border: 1px solid #45475A; }
            QPushButton:hover { background-color: #45475A; border: 1px solid #89B4FA; }
            QPushButton:pressed { background-color: #585B70; }
            QTextEdit { background-color: #181825; color: #CDD6F4; border-radius: 6px; border: 1px solid #313244; padding: 12px; font-family: 'Consolas', monospace; }
            QLineEdit { background-color: #181825; color: #CDD6F4; border-radius: 6px; border: 1px solid #313244; padding: 12px 15px; font-size: 14px; }
            QLineEdit:focus { border: 1px solid #89B4FA; }
            QLabel { color: #CDD6F4; }
            QProgressBar { border: none; border-radius: 3px; background-color: #181825; text-align: center; }
            QProgressBar::chunk { background-color: #A6E3A1; border-radius: 3px; }
            QScrollBar:vertical { border: none; background: #181825; width: 10px; border-radius: 5px; }
            QScrollBar::handle:vertical { background: #313244; min-height: 20px; border-radius: 5px; }
            """)
        
        self.log_signal.connect(self.append_log)
        self.frame_signal.connect(self.update_vision_preview)
        self.volume_signal.connect(self.update_volume_meter)
        self.disconnect_signal.connect(self.handle_agent_disconnect)
        self.working_signal.connect(self.toggle_working_indicator)
        
        self.agent.on_frame_captured = self.frame_signal.emit
        self.agent.audio.on_volume_changed = self.volume_signal.emit
        self.agent.on_disconnect = self.disconnect_signal.emit
        self.agent.on_working_state_changed = self.working_signal.emit
        
        self.working_timer = QTimer()
        self.working_timer.timeout.connect(self.animate_working)
        self.working_dots = 0
        
        main_widget = QWidget()
        main_widget.setObjectName("mainContainer")
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # --- HEADER ---
        header_bar = QWidget()
        header_bar.setObjectName("headerBar")
        header_bar.setFixedHeight(60)
        header_layout = QHBoxLayout(header_bar)
        
        header_title = QLabel("OmniGemini")
        header_title.setStyleSheet("font-size: 22px; font-weight: 900; color: #89B4FA; margin-left: 10px;")
        header_layout.addWidget(header_title)
        
        version_lbl = QLabel("v0.5.0")
        version_lbl.setStyleSheet("color: #6C7086; font-size: 12px; font-weight: bold; margin-top: 8px;")
        header_layout.addWidget(version_lbl)
        
        header_layout.addSpacing(40)
        self.mcp_lbl = QLabel("🔌 Warming up...")
        self.mcp_lbl.setStyleSheet("color: #A6ADC8; font-size: 13px; background-color: #313244; padding: 5px 15px; border-radius: 15px;")
        header_layout.addWidget(self.mcp_lbl)
        
        header_layout.addStretch()
        
        self.working_lbl = QLabel("⚙️ STANDBY")
        self.working_lbl.setStyleSheet("color: #A6ADC8; font-weight: bold; font-size: 13px; background-color: #313244; padding: 6px 16px; border-radius: 12px; border: 1px solid #45475A;")
        header_layout.addWidget(self.working_lbl)
        
        header_layout.addSpacing(10)
        
        try:
            is_admin = ctypes.windll.shell32.IsUserAnAdmin() != 0 if os.name == 'nt' else os.getuid() == 0
        except: is_admin = False
        power_lbl = QLabel(f"⚡ {'ADMIN' if is_admin else 'USER'}")
        power_lbl.setStyleSheet(f"font-weight: 900; color: {'#11111B' if is_admin else '#CDD6F4'}; background-color: {'#F38BA8' if is_admin else '#45475A'}; padding: 5px 15px; border-radius: 15px; font-size: 12px;")
        header_layout.addWidget(power_lbl)
        
        main_layout.addWidget(header_bar)
        
        # --- BODY ---
        content_wrapper = QWidget()
        content_layout = QVBoxLayout(content_wrapper)
        content_layout.setContentsMargins(15, 15, 15, 15)
        
        splitter = QSplitter(Qt.Orientation.Horizontal)
        content_layout.addWidget(splitter)
        main_layout.addWidget(content_wrapper)
        
        # LEFT PANEL
        left_panel = QWidget()
        left_panel.setObjectName("leftPanel")
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(20, 20, 20, 20)
        
        action_toolbar = QHBoxLayout()
        action_toolbar.setSpacing(10)
        
        self.connect_btn = QPushButton("Connect Live API")
        self.connect_btn.setStyleSheet("background-color: #A6E3A1; color: #11111B; font-size: 14px; padding: 8px 24px;")
        self.connect_btn.clicked.connect(self.toggle_connection)
        self.connect_btn.setToolTip("Start or stop the real-time voice and vision session.")
        
        self.memory_btn = QPushButton("🧠 Sessions")
        self.memory_btn.clicked.connect(self.open_memory_manager)
        self.memory_btn.setToolTip("RELOAD a previous conversation log or fetch saved facts.")
        
        self.settings_btn = QPushButton("⚙ Settings")
        self.settings_btn.clicked.connect(self.open_settings)
        
        self.clear_log_btn = QPushButton("🗑 Clear")
        self.clear_log_btn.clicked.connect(self.clear_logger)
        
        self.verbose_checkbox = QCheckBox("Dev Log")
        self.verbose_checkbox.setChecked(self.agent.config.get("verbose_logging", True))
        self.verbose_checkbox.setToolTip("Uncheck to hide system JSON and tool calls, showing only the clean chat.")
        self.verbose_checkbox.stateChanged.connect(self.toggle_verbose_logging)
        self.verbose_checkbox.setStyleSheet("color: #BAC2DE; font-weight: bold; margin-left: 10px;")

        action_toolbar.addWidget(self.connect_btn)
        action_toolbar.addWidget(self.memory_btn)
        action_toolbar.addWidget(self.settings_btn)
        action_toolbar.addWidget(self.clear_log_btn)
        action_toolbar.addWidget(self.verbose_checkbox)
        action_toolbar.addStretch()
        
        self.zoom_out_btn = QPushButton("A-")
        self.zoom_out_btn.clicked.connect(self.zoom_out_log)
        self.zoom_in_btn = QPushButton("A+")
        self.zoom_in_btn.clicked.connect(self.zoom_in_log)
        action_toolbar.addWidget(self.zoom_out_btn)
        action_toolbar.addWidget(self.zoom_in_btn)
        
        action_toolbar.addSpacing(15)
        self.vol_meter = QProgressBar()
        self.vol_meter.setRange(0, 10000)
        self.vol_meter.setFixedSize(80, 6)
        action_toolbar.addWidget(self.vol_meter)
        
        left_layout.addLayout(action_toolbar)
        
        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        self._apply_log_font()
        left_layout.addWidget(self.log_area)
        
        quick_prompts = QHBoxLayout()
        quick_prompts.setSpacing(8)
        btns = [
            ("👀 Explain Screen", "Look at my screen and explain what's going on."),
            ("📅 Summary", "Fetch my last 5 emails and summary my upcoming calendar events."),
            ("💻 Code Helper", "Help me with a programming task. Use gemini-3.1-pro-preview.")
        ]
        for label, prompt in btns:
            b = QPushButton(label)
            b.setToolTip(f"Send: {prompt}")
            b.clicked.connect(lambda checked, p=prompt: self.insert_prompt(p))
            quick_prompts.addWidget(b)
        quick_prompts.addStretch()
        left_layout.addLayout(quick_prompts)

        input_layout = QHBoxLayout()
        self.text_input = QLineEdit()
        self.text_input.setPlaceholderText("Message OmniGemini... (Press Enter)")
        self.text_input.returnPressed.connect(self.handle_text_submit)
        self.send_btn = QPushButton("Send")
        self.send_btn.setStyleSheet("background-color: #89B4FA; color: #11111B; padding: 12px 24px; font-size: 14px;")
        self.send_btn.clicked.connect(self.handle_text_submit)
        input_layout.addWidget(self.text_input)
        input_layout.addWidget(self.send_btn)
        left_layout.addLayout(input_layout)
        
        splitter.addWidget(left_panel)
        
        # RIGHT PANEL
        right_panel = QWidget()
        right_panel.setObjectName("rightPanel")
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(20, 20, 20, 20)
        
        vision_title = QLabel("LIVE CONTEXT")
        vision_title.setStyleSheet("font-weight: 800; color: #BAC2DE; font-size: 11px; letter-spacing: 2px;")
        right_layout.addWidget(vision_title)
        
        self.vision_preview = QLabel("No visual context.")
        self.vision_preview.setStyleSheet("background-color: #11111B; border: 1px solid #313244; color: #6C7086; border-radius: 8px;")
        self.vision_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.vision_preview.setFixedHeight(240)
        right_layout.addWidget(self.vision_preview)
        
        vision_tools = QHBoxLayout()
        self.send_cam_btn = QPushButton("📸 CAM")
        self.send_cam_btn.clicked.connect(lambda: asyncio.create_task(self.agent.send_vision_frame("webcam", force=True)))
        self.send_screen_btn = QPushButton("🖥️ SCREEN")
        self.send_screen_btn.clicked.connect(lambda: asyncio.create_task(self.agent.send_vision_frame("screen", force=True)))
        self.auto_vision_btn = QPushButton("👁️ AUTO: OFF")
        self.auto_vision_btn.setCheckable(True)
        self.auto_vision_btn.clicked.connect(self.toggle_auto_vision)
        vision_tools.addWidget(self.send_cam_btn)
        vision_tools.addWidget(self.send_screen_btn)
        vision_tools.addWidget(self.auto_vision_btn)
        right_layout.addLayout(vision_tools)
        
        line = QFrame(); line.setFrameShape(QFrame.Shape.HLine); line.setStyleSheet("color: #313244;")
        right_layout.addWidget(line)
        
        steering_title = QLabel("AI STEERING")
        steering_title.setStyleSheet("font-weight: 800; color: #BAC2DE; font-size: 11px; letter-spacing: 2px;")
        right_layout.addWidget(steering_title)
        self.steering_text = QTextEdit()
        self.steering_text.setPlaceholderText("Instructions (e.g. Speak French)...")
        self.steering_text.textChanged.connect(self.update_steering)
        right_layout.addWidget(self.steering_text)
        
        splitter.addWidget(right_panel)
        splitter.setSizes([950, 350])
        
        self.agent.logger = self.log_message
        self.log_message("[dim]Welcome to OmniGemini. Fetching system readiness...[/dim]")
        # Use QTimer to start the warmup task once the event loop is actually running
        QTimer.singleShot(0, lambda: asyncio.create_task(self.fetch_mcps_and_warmup()))

    def toggle_verbose_logging(self, state):
        self.agent.config["verbose_logging"] = bool(state)
        save_config(self.agent.config)

    def zoom_in_log(self):
        self.current_font_size += 1
        self._apply_log_font()

    def zoom_out_log(self):
        self.current_font_size = max(6, self.current_font_size - 1)
        self._apply_log_font()
        
    def _apply_log_font(self):
        font = self.log_area.font()
        font.setPointSize(self.current_font_size)
        self.log_area.setFont(font)
        self.log_area.document().setDefaultFont(font)
        
    def clear_logger(self):
        self.log_area.clear()

    def animate_working(self):
        import time
        self.working_dots = (self.working_dots + 1) % 4
        colors = ["#89B4FA", "#CBA6F7", "#F38BA8", "#F9E2AF", "#A6E3A1", "#89DCEB"]
        color = colors[int(time.time() * 3) % len(colors)]
        self.working_lbl.setStyleSheet(f"color: {color}; font-weight: 900; font-size: 13px; background-color: #313244; padding: 6px 16px; border-radius: 12px; border: 1px solid {color};")
        self.working_lbl.setText(f"⚙️ WORKING{'.' * self.working_dots}")

    async def fetch_mcps_and_warmup(self):
        try:
            cli_path = self.agent.config.get("gemini_cli_path", "gemini")
            import subprocess, shutil
            res = await asyncio.to_thread(subprocess.run, [shutil.which(cli_path) or cli_path, "mcp", "list"], capture_output=True, text=True, shell=True)
            mcps = [line.split(' ')[1] for line in res.stdout.strip().split('\n') if line.startswith('- ')]
            if mcps: self.mcp_lbl.setText(f"🔌 MCPs: {', '.join(mcps)}")
            else: self.mcp_lbl.setText("🔌 No MCPs detected.")
            self.log_message("[green]Gemini CLI linkage verified.[/green]")
        except:
            self.mcp_lbl.setText("🔌 Failed to load MCPs.")

    def log_message(self, msg): self.log_signal.emit(msg)

    def append_log(self, msg):
        if not self.agent.config.get("verbose_logging", True):
            if not ("[bold white]You" in msg or "[bold blue]Omni" in msg or "Reloading session" in msg):
                return
        self.log_area.append(rich_to_html(msg))
        self.log_area.verticalScrollBar().setValue(self.log_area.verticalScrollBar().maximum())

    def handle_text_submit(self):
        text = self.text_input.text().strip()
        if text:
            asyncio.create_task(self.agent.send_text(text))
            self.text_input.clear()

    def insert_prompt(self, text):
        self.text_input.setText(text)
        self.text_input.setFocus()

    def toggle_auto_vision(self, checked):
        if checked:
            self.auto_vision_btn.setText("👁️ AUTO: ON")
            self.auto_vision_btn.setStyleSheet("background-color: #A6E3A1; color: #11111B;")
            asyncio.create_task(self.agent.toggle_auto_vision(True, "screen"))
        else:
            self.auto_vision_btn.setText("👁️ AUTO: OFF")
            self.auto_vision_btn.setStyleSheet("background-color: #313244; color: #CDD6F4;")
            asyncio.create_task(self.agent.toggle_auto_vision(False))

    def update_vision_preview(self, b):
        pix = QPixmap(); pix.loadFromData(b)
        self.vision_preview.setPixmap(pix.scaled(self.vision_preview.width(), self.vision_preview.height(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))

    def update_volume_meter(self, v): self.vol_meter.setValue(v)
    def update_steering(self): self.agent.steering_prompt = self.steering_text.toPlainText()

    def handle_agent_disconnect(self):
        self.connect_btn.setText("Connect Live API")
        self.connect_btn.setStyleSheet("background-color: #A6E3A1; color: #11111B; font-size: 14px; padding: 8px 24px;")
        self.connect_btn.setEnabled(True)
        self.auto_vision_btn.setChecked(False)
        self.toggle_auto_vision(False)
            
    def toggle_working_indicator(self, is_working):
        if is_working: self.working_timer.start(300)
        else:
            self.working_timer.stop()
            self.working_lbl.setStyleSheet("color: #A6ADC8; font-weight: bold; font-size: 13px; background-color: #313244; padding: 6px 16px; border-radius: 12px; border: 1px solid #45475A;")
            self.working_lbl.setText("⚙️ STANDBY")

    def open_settings(self):
        SettingsDialog(self.agent.config, self).exec()
        
    def open_memory_manager(self):
        dlg = SessionBrowser(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            file = dlg.get_selected_file()
            if file:
                self.log_message(f"[bold blue]Omni:[/bold blue] Reloading history from {file}...")
                self.load_session(file)

    def load_session(self, filename):
        path = os.path.join("logs", filename)
        if not os.path.exists(path): return
        self.agent.chat_history = []
        self.log_area.clear()
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith("You: "):
                    t = line[5:]; self.agent.chat_history.append(f"You: {t}"); self.append_log(f"[bold white]You:[/bold white] {t}")
                elif line.startswith("Omni: "):
                    t = line[6:]; self.agent.chat_history.append(f"Omni: {t}"); self.append_log(f"[bold blue]Omni:[/bold blue] {t}")
        self.log_message("[green]Session reloaded. You can now reconnect to continue.")

    def toggle_connection(self):
        if not self.agent.running:
            self.connect_btn.setText("Connecting...")
            self.connect_btn.setStyleSheet("background-color: #F9E2AF; color: #11111B; font-size: 14px; padding: 8px 24px;")
            self.connect_btn.setEnabled(False)
            asyncio.create_task(self.start_agent())
        else:
            asyncio.create_task(self.agent.disconnect())

    async def start_agent(self):
        if await self.agent.connect():
            self.connect_btn.setText("Disconnect")
            self.connect_btn.setStyleSheet("background-color: #F38BA8; color: #11111B; font-size: 14px; padding: 8px 24px;")
            self.connect_btn.setEnabled(True)
            asyncio.gather(self.agent.send_audio_loop(), self.agent.receive_loop(), self.agent.audio.mic_loop(), self.agent.audio.speaker_loop())
        else: self.handle_agent_disconnect()

    def closeEvent(self, event):
        if self.agent.running:
            try: asyncio.get_event_loop().create_task(self.agent.disconnect())
            except: pass
        event.accept()
