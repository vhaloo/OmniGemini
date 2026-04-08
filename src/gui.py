import asyncio
import ctypes
import os
import re
import sounddevice as sd
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QTextEdit, QLineEdit, QCheckBox, 
                             QFormLayout, QDialog, QDialogButtonBox, QLabel, QSplitter, QProgressBar, QComboBox, QFrame)
from PyQt6.QtGui import QPixmap, QImage, QFont, QIcon, QColor, QPalette
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QSize
from rich.console import Console
from src.config import save_config

console = Console(force_terminal=False)

def rich_to_html(rich_text):
    text = rich_text.replace("[bold green]", "<b style='color: #A6E3A1'>").replace("[/bold green]", "</b>")
    text = text.replace("[green]", "<span style='color: #A6E3A1'>").replace("[/green]", "</span>")
    text = text.replace("[bold red]", "<b style='color: #F38BA8'>").replace("[/bold red]", "</b>")
    text = text.replace("[red]", "<span style='color: #F38BA8'>").replace("[/red]", "</span>")
    text = text.replace("[bold blue]", "<b style='color: #89B4FA'>").replace("[/bold blue]", "</b>")
    text = text.replace("[bold cyan]", "<b style='color: #89DCEB'>").replace("[/bold cyan]", "</b>")
    text = text.replace("[bold magenta]", "<b style='color: #CBA6F7'>").replace("[/bold magenta]", "</b>")
    text = text.replace("[bold white]", "<b style='color: #CDD6F4'>").replace("[/bold white]", "</b>")
    text = text.replace("[yellow]", "<span style='color: #F9E2AF'>").replace("[/yellow]", "</span>")
    text = text.replace("[dim]", "<span style='color: #6C7086'>").replace("[/dim]", "</span>")
    
    text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text)
    text = re.sub(r'\*(.+?)\*', r'<i>\1</i>', text)
    text = re.sub(r'`(.+?)`', r'<code style="background-color:#313244; padding:2px 4px; border-radius:4px;">\1</code>', text)
    
    return text.replace("\n", "<br>")

class SettingsDialog(QDialog):
    def __init__(self, config, parent=None):
        super().__init__(parent)
        self.setWindowTitle("OmniGemini Settings")
        self.setMinimumWidth(500)
        self.config = config
        self.setStyleSheet("""
            QDialog { background-color: #1E1E2E; color: #CDD6F4; font-family: 'Segoe UI', sans-serif; }
            QLineEdit { background-color: #181825; color: #CDD6F4; border: 1px solid #313244; border-radius: 6px; padding: 6px; }
            QComboBox { background-color: #181825; color: #CDD6F4; border: 1px solid #313244; border-radius: 6px; padding: 6px; }
            QPushButton { background-color: #313244; color: #CDD6F4; border-radius: 6px; padding: 8px 16px; border: none; font-weight: bold;}
            QPushButton:hover { background-color: #45475A; }
            QLabel { color: #CDD6F4; font-weight: 500;}
        """)
        
        layout = QFormLayout(self)
        layout.setSpacing(15)
        
        self.api_key_input = QLineEdit(self.config.get("api_key", ""))
        self.api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.api_key_input.setToolTip("Your Gemini API key from Google AI Studio.")
        layout.addRow("Gemini API Key:", self.api_key_input)
        
        self.cli_path_input = QLineEdit(self.config.get("gemini_cli_path", "gemini"))
        self.cli_path_input.setToolTip("Path to the Gemini CLI executable. Leave as 'gemini' if it is in your system PATH.")
        layout.addRow("Gemini CLI Path:", self.cli_path_input)
        
        self.camera_idx_input = QLineEdit(str(self.config.get("camera_index", 0)))
        self.camera_idx_input.setToolTip("The index of your webcam (0 is usually the default, 1 is an external or secondary camera).")
        layout.addRow("Camera Index:", self.camera_idx_input)
        
        self.loudness_input = QLineEdit(str(self.config.get("loudness_threshold", 8000)))
        self.loudness_input.setToolTip("Set the volume level required to trigger the microphone. Lower means more sensitive (picks up quiet sounds), higher means less sensitive (ignores background noise). Default is 8000.")
        layout.addRow("Loudness Threshold:", self.loudness_input)
        
        self.in_device_combo = QComboBox()
        self.in_device_combo.setToolTip("Select your microphone.")
        self.in_device_combo.addItem("Default", None)
        self.out_device_combo = QComboBox()
        self.out_device_combo.setToolTip("Select your speakers or headphones.")
        self.out_device_combo.addItem("Default", None)
        
        devices = sd.query_devices()
        current_in = self.config.get("input_device")
        current_out = self.config.get("output_device")
        
        for i, dev in enumerate(devices):
            if dev['max_input_channels'] > 0:
                self.in_device_combo.addItem(f"{i}: {dev['name']}", i)
                if current_in == i:
                    self.in_device_combo.setCurrentIndex(self.in_device_combo.count() - 1)
            if dev['max_output_channels'] > 0:
                self.out_device_combo.addItem(f"{i}: {dev['name']}", i)
                if current_out == i:
                    self.out_device_combo.setCurrentIndex(self.out_device_combo.count() - 1)
                    
        layout.addRow("Input Device (Mic):", self.in_device_combo)
        layout.addRow("Output Device:", self.out_device_combo)
        
        self.ducking_checkbox = QCheckBox("Enable Speaker Ducking (Echo Cancellation)")
        self.ducking_checkbox.setToolTip("Echo Cancellation: Mutes the microphone feed momentarily while the AI is speaking so it doesn't hear itself and loop. Essential if not using headphones.")
        self.ducking_checkbox.setChecked(self.config.get("ducking_enabled", True))
        layout.addRow("", self.ducking_checkbox)
        
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def accept(self):
        self.config["api_key"] = self.api_key_input.text()
        self.config["gemini_cli_path"] = self.cli_path_input.text()
        try:
            self.config["camera_index"] = int(self.camera_idx_input.text())
        except ValueError:
            pass
        try:
            self.config["loudness_threshold"] = int(self.loudness_input.text())
        except ValueError:
            pass
            
        in_data = self.in_device_combo.currentData()
        out_data = self.out_device_combo.currentData()
        self.config["input_device"] = in_data
        self.config["output_device"] = out_data
        
        self.config["ducking_enabled"] = self.ducking_checkbox.isChecked()
        save_config(self.config)
        super().accept()

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
        self.resize(1400, 900)
        self.setStyleSheet("""
            QMainWindow { background-color: #11111B; color: #CDD6F4; font-family: 'Segoe UI', sans-serif; }
            QWidget#mainContainer { background-color: #11111B; }
            QWidget#headerBar { background-color: #181825; border-bottom: 1px solid #313244; }
            QWidget#leftPanel, QWidget#rightPanel { background-color: #1E1E2E; border-radius: 8px; }
            QPushButton { background-color: #313244; color: #CDD6F4; border-radius: 6px; padding: 8px 16px; font-weight: bold; border: 1px solid #45475A; }
            QPushButton:hover { background-color: #45475A; }
            QPushButton:pressed { background-color: #585B70; }
            QPushButton:disabled { background-color: #181825; color: #6C7086; border: 1px solid #313244; }
            QTextEdit { background-color: #181825; color: #CDD6F4; border-radius: 6px; border: 1px solid #313244; padding: 12px; font-family: 'Consolas', monospace; font-size: 13px; }
            QLineEdit { background-color: #181825; color: #CDD6F4; border-radius: 6px; border: 1px solid #313244; padding: 12px 15px; font-size: 14px; }
            QLineEdit:focus { border: 1px solid #89B4FA; }
            QLabel { color: #CDD6F4; }
            QProgressBar { border: none; border-radius: 3px; background-color: #181825; text-align: center; }
            QProgressBar::chunk { background-color: #A6E3A1; border-radius: 3px; }
            QSplitter::handle { background-color: transparent; }
            QScrollBar:vertical { border: none; background: #181825; width: 10px; border-radius: 5px; }
            QScrollBar::handle:vertical { background: #313244; min-height: 20px; border-radius: 5px; }
            QScrollBar::handle:vertical:hover { background: #45475A; }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { border: none; background: none; }
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
        
        # --- HEADER BAR ---
        header_bar = QWidget()
        header_bar.setObjectName("headerBar")
        header_bar.setFixedHeight(56)
        header_layout = QHBoxLayout(header_bar)
        header_layout.setContentsMargins(20, 0, 20, 0)
        
        header_title = QLabel("OmniGemini")
        header_title.setStyleSheet("font-size: 20px; font-weight: 800; color: #89B4FA; letter-spacing: 0.5px;")
        header_layout.addWidget(header_title)
        
        version_lbl = QLabel("v0.4.0")
        version_lbl.setStyleSheet("color: #6C7086; font-size: 12px; font-weight: bold; margin-top: 6px; margin-left: 5px;")
        header_layout.addWidget(version_lbl)
        
        header_layout.addSpacing(30)
        
        self.mcp_lbl = QLabel("🔌 Detecting capabilities...")
        self.mcp_lbl.setStyleSheet("color: #A6ADC8; font-size: 13px; background-color: #313244; padding: 4px 12px; border-radius: 12px;")
        header_layout.addWidget(self.mcp_lbl)
        
        header_layout.addStretch()
        
        self.working_lbl = QLabel("⚙️ STANDBY")
        self.working_lbl.setStyleSheet("color: #A6ADC8; font-weight: bold; font-size: 13px; background-color: #313244; padding: 6px 16px; border-radius: 12px; margin-right: 15px; border: 1px solid #45475A;")
        header_layout.addWidget(self.working_lbl)
        
        try:
            is_admin = ctypes.windll.shell32.IsUserAnAdmin() != 0 if os.name == 'nt' else os.getuid() == 0
        except Exception:
            is_admin = False
            
        power_lbl = QLabel(f"⚡ {'ADMIN' if is_admin else 'USER'}")
        power_lbl.setStyleSheet(f"font-weight: bold; color: {'#11111B' if is_admin else '#CDD6F4'}; background-color: {'#F38BA8' if is_admin else '#45475A'}; padding: 4px 12px; border-radius: 12px; font-size: 12px;")
        header_layout.addWidget(power_lbl)
        
        main_layout.addWidget(header_bar)
        
        # --- SPLITTER AREA ---
        content_wrapper = QWidget()
        content_layout = QVBoxLayout(content_wrapper)
        content_layout.setContentsMargins(15, 15, 15, 15)
        
        splitter = QSplitter(Qt.Orientation.Horizontal)
        content_layout.addWidget(splitter)
        main_layout.addWidget(content_wrapper)
        
        # --- LEFT PANEL (CHAT & LOGS) ---
        left_panel = QWidget()
        left_panel.setObjectName("leftPanel")
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(20, 20, 20, 20)
        left_layout.setSpacing(15)
        
        # Action Toolbar
        action_toolbar = QHBoxLayout()
        action_toolbar.setSpacing(10)
        
        self.connect_btn = QPushButton("Connect Live API")
        self.connect_btn.setStyleSheet("background-color: #A6E3A1; color: #11111B; font-size: 14px; padding: 8px 24px;")
        self.connect_btn.clicked.connect(self.toggle_connection)
        
        self.memory_btn = QPushButton("🧠 Memory")
        self.memory_btn.clicked.connect(self.open_memory_manager)
        
        self.settings_btn = QPushButton("⚙ Settings")
        self.settings_btn.clicked.connect(self.open_settings)
        
        self.clear_log_btn = QPushButton("🗑 Clear Log")
        self.clear_log_btn.clicked.connect(self.clear_logger)
        
        self.verbose_checkbox = QCheckBox("Dev Verbose")
        self.verbose_checkbox.setChecked(self.agent.config.get("verbose_logging", True))
        self.verbose_checkbox.setToolTip("Toggle super verbose system logs. If off, only shows oral input and output.")
        self.verbose_checkbox.setStyleSheet("color: #BAC2DE; font-weight: bold; margin-left: 10px;")
        self.verbose_checkbox.stateChanged.connect(self.toggle_verbose_logging)

        action_toolbar.addWidget(self.connect_btn)
        action_toolbar.addWidget(self.memory_btn)
        action_toolbar.addWidget(self.settings_btn)
        action_toolbar.addWidget(self.clear_log_btn)
        action_toolbar.addWidget(self.verbose_checkbox)
        action_toolbar.addStretch()
        
        self.zoom_out_btn = QPushButton("A-")
        self.zoom_out_btn.setToolTip("Decrease Log Font Size")
        self.zoom_out_btn.setStyleSheet("padding: 4px 10px; font-weight: bold;")
        self.zoom_out_btn.clicked.connect(self.zoom_out_log)
        
        self.zoom_in_btn = QPushButton("A+")
        self.zoom_in_btn.setToolTip("Increase Log Font Size")
        self.zoom_in_btn.setStyleSheet("padding: 4px 10px; font-weight: bold;")
        self.zoom_in_btn.clicked.connect(self.zoom_in_log)
        
        action_toolbar.addWidget(self.zoom_out_btn)
        action_toolbar.addWidget(self.zoom_in_btn)
        
        action_toolbar.addSpacing(15)
        
        mic_lbl = QLabel("🎤 Mic:")
        mic_lbl.setStyleSheet("color: #A6ADC8; font-weight: bold; font-size: 12px;")
        action_toolbar.addWidget(mic_lbl)
        
        self.vol_meter = QProgressBar()
        self.vol_meter.setRange(0, 10000) 
        self.vol_meter.setTextVisible(False)
        self.vol_meter.setFixedSize(100, 6)
        action_toolbar.addWidget(self.vol_meter)
        
        left_layout.addLayout(action_toolbar)
        
        # Log Area
        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        self.log_area.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
        # default font for log area
        log_font = self.log_area.font()
        log_font.setPointSize(10)
        self.log_area.setFont(log_font)
        left_layout.addWidget(self.log_area)
        
        # Shortcuts for quick instructions
        quick_prompt_layout = QHBoxLayout()
        quick_prompt_layout.setSpacing(10)
        explain_screen_btn = QPushButton("👀 Explain my Screen")
        explain_screen_btn.setToolTip("Quickly ask OmniGemini to look at your screen and explain what's happening.")
        explain_screen_btn.clicked.connect(lambda: self.insert_prompt("Look at my screen and explain what's going on or what I'm working on."))
        summarize_day_btn = QPushButton("📅 Summarize Day")
        summarize_day_btn.setToolTip("Quickly ask OmniGemini to summarize your emails and calendar events.")
        summarize_day_btn.clicked.connect(lambda: self.insert_prompt("Can you fetch my recent emails and calendar events and summarize my day?"))
        quick_prompt_layout.addWidget(explain_screen_btn)
        quick_prompt_layout.addWidget(summarize_day_btn)
        quick_prompt_layout.addStretch()
        left_layout.addLayout(quick_prompt_layout)

        # Input Area
        input_layout = QHBoxLayout()
        input_layout.setSpacing(10)
        self.text_input = QLineEdit()
        self.text_input.setPlaceholderText("Message OmniGemini... (Press Enter to send)")
        self.text_input.returnPressed.connect(self.handle_text_submit)
        
        self.send_btn = QPushButton("Send")
        self.send_btn.setToolTip("Send the typed message to OmniGemini.")
        self.send_btn.setStyleSheet("background-color: #89B4FA; color: #11111B; padding: 12px 24px; font-size: 14px;")
        self.send_btn.clicked.connect(self.handle_text_submit)
        
        input_layout.addWidget(self.text_input)
        input_layout.addWidget(self.send_btn)
        left_layout.addLayout(input_layout)
        
        splitter.addWidget(left_panel)
        
        # --- RIGHT PANEL (VISION & CONTEXT) ---
        right_panel = QWidget()
        right_panel.setObjectName("rightPanel")
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(20, 20, 20, 20)
        right_layout.setSpacing(15)
        
        vision_title = QLabel("VISUAL CONTEXT")
        vision_title.setStyleSheet("font-weight: 800; color: #BAC2DE; font-size: 12px; letter-spacing: 1.5px;")
        right_layout.addWidget(vision_title)
        
        self.vision_preview = QLabel("No context shared yet.\nWebcam and Screen captures will appear here.")
        self.vision_preview.setStyleSheet("background-color: #11111B; border: 1px solid #313244; color: #6C7086; border-radius: 8px;")
        self.vision_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.vision_preview.setFixedHeight(220)
        self.vision_preview.setScaledContents(False) # We will manually scale in update_vision_preview
        right_layout.addWidget(self.vision_preview)
        
        vision_tools = QHBoxLayout()
        vision_tools.setSpacing(8)
        
        self.send_cam_btn = QPushButton("📸 Webcam")
        self.send_cam_btn.setStyleSheet("background-color: #89DCEB; color: #11111B;")
        self.send_cam_btn.clicked.connect(lambda: asyncio.create_task(self.agent.send_vision_frame("webcam", force=True)))
        
        self.send_screen_btn = QPushButton("🖥️ Screen")
        self.send_screen_btn.setStyleSheet("background-color: #F5C2E7; color: #11111B;")
        self.send_screen_btn.clicked.connect(lambda: asyncio.create_task(self.agent.send_vision_frame("screen", force=True)))
        
        self.auto_vision_btn = QPushButton("👁️ Auto: OFF")
        self.auto_vision_btn.setCheckable(True)
        self.auto_vision_btn.clicked.connect(self.toggle_auto_vision)
        
        vision_tools.addWidget(self.send_cam_btn)
        vision_tools.addWidget(self.send_screen_btn)
        vision_tools.addWidget(self.auto_vision_btn)
        right_layout.addLayout(vision_tools)
        
        # Divider
        divider = QFrame()
        divider.setFrameShape(QFrame.Shape.HLine)
        divider.setStyleSheet("background-color: #313244; margin: 10px 0px;")
        right_layout.addWidget(divider)
        
        steering_title = QLabel("AI STEERING DIRECTIVES")
        steering_title.setStyleSheet("font-weight: 800; color: #BAC2DE; font-size: 12px; letter-spacing: 1.5px;")
        right_layout.addWidget(steering_title)
        
        self.steering_text = QTextEdit()
        self.steering_text.setPlaceholderText("Enter overriding instructions or personality traits here...\nExample: \"You are a grumpy robot. Only speak French.\"")
        self.steering_text.setStyleSheet("border: 1px solid #45475A;")
        self.steering_text.textChanged.connect(self.update_steering)
        right_layout.addWidget(self.steering_text)
        
        steering_help = QLabel("Changes to directives apply immediately on next message.")
        steering_help.setStyleSheet("color: #6C7086; font-size: 11px; font-style: italic;")
        right_layout.addWidget(steering_help)
        
        splitter.addWidget(right_panel)
        splitter.setSizes([900, 350]) # Give more space to the left side
        
        self.agent.logger = self.log_message
        self.log_message("[dim]Welcome to OmniGemini. Fetching system readiness...[/dim]")
        
        try:
            loop = asyncio.get_event_loop()
            loop.create_task(self.fetch_mcps_and_warmup())
        except RuntimeError:
            pass

    def insert_prompt(self, text):
        self.text_input.setText(text)
        self.text_input.setFocus()

    def toggle_verbose_logging(self, state):
        self.agent.config["verbose_logging"] = bool(state)
        save_config(self.agent.config)

    def zoom_in_log(self):
        if not hasattr(self, 'current_font_size'):
            self.current_font_size = 10
        self.current_font_size += 1
        self._apply_log_font()

    def zoom_out_log(self):
        if not hasattr(self, 'current_font_size'):
            self.current_font_size = 10
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
        self.working_dots = (self.working_dots + 1) % 4
        color = "#F9E2AF" if self.working_dots % 2 == 0 else "#F38BA8"
        bg_color = "#45475A" if self.working_dots % 2 == 0 else "#585B70"
        self.working_lbl.setStyleSheet(f"color: {color}; font-weight: 900; font-size: 14px; background-color: {bg_color}; padding: 6px 16px; border-radius: 12px; margin-right: 15px; border: 1px solid {color};")
        self.working_lbl.setText(f"⚙️ WORKING{'.' * self.working_dots}")

    async def fetch_mcps_and_warmup(self):
        try:
            cli_path = self.agent.config.get("gemini_cli_path", "gemini")
            import subprocess
            import shutil
            resolved_path = shutil.which(cli_path)
            if not resolved_path:
                resolved_path = cli_path
            
            # WARM UP: Check version
            self.log_message("[dim]Warming up Gemini CLI...[/dim]")
            version_res = await asyncio.to_thread(subprocess.run, [resolved_path, "--version"], capture_output=True, text=True, shell=True)
            if version_res.returncode == 0:
                v = version_res.stdout.strip()
                self.log_message(f"[green]Gemini CLI is ready![/green] [dim]({v})[/dim]")
            else:
                self.log_message("[red]Failed to warm up Gemini CLI. Is it in your PATH?[/red]")

            res = await asyncio.to_thread(subprocess.run, [resolved_path, "mcp", "list"], capture_output=True, text=True, shell=True)
            output = res.stdout.strip()
            mcps = []
            for line in output.split('\n'):
                if line.startswith('- '):
                    parts = line.split(' ')
                    if len(parts) >= 2:
                        mcps.append(parts[1])
            if mcps:
                self.mcp_lbl.setText(f"🔌 MCPs: {', '.join(mcps)}")
            else:
                self.mcp_lbl.setText("🔌 No MCPs detected or CLI error.")
        except Exception:
            self.mcp_lbl.setText("🔌 Failed to load MCPs.")

    def log_message(self, msg):
        self.log_signal.emit(msg)

    def append_log(self, msg):
        if not self.agent.config.get("verbose_logging", True):
            if not ("[bold white]You" in msg or "[bold blue]Omni" in msg):
                return
                
        html_msg = rich_to_html(msg)
        self.log_area.append(html_msg)
        scrollbar = self.log_area.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def handle_text_submit(self):
        text = self.text_input.text().strip()
        if text:
            asyncio.create_task(self.agent.send_text(text))
            self.text_input.clear()

    def toggle_auto_vision(self, checked):
        if checked:
            self.auto_vision_btn.setText("👁️ Auto: ON")
            self.auto_vision_btn.setStyleSheet("background-color: #A6E3A1; color: #11111B;")
            asyncio.create_task(self.agent.toggle_auto_vision(True, "screen"))
        else:
            self.auto_vision_btn.setText("👁️ Auto: OFF")
            self.auto_vision_btn.setStyleSheet("background-color: #313244; color: #CDD6F4;")
            asyncio.create_task(self.agent.toggle_auto_vision(False))

    def update_vision_preview(self, frame_bytes):
        pixmap = QPixmap()
        pixmap.loadFromData(frame_bytes)
        # Scale to fit while keeping aspect ratio
        scaled_pixmap = pixmap.scaled(self.vision_preview.width(), self.vision_preview.height(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        self.vision_preview.setPixmap(scaled_pixmap)

    def update_volume_meter(self, value):
        self.vol_meter.setValue(value)

    def update_steering(self):
        self.agent.steering_prompt = self.steering_text.toPlainText()

    def handle_agent_disconnect(self):
        self.connect_btn.setText("Connect Live API")
        self.connect_btn.setStyleSheet("background-color: #A6E3A1; color: #11111B; font-size: 14px; padding: 8px 24px;")
        self.connect_btn.setEnabled(True)
        if hasattr(self, 'auto_vision_btn'):
            self.auto_vision_btn.setChecked(False)
            self.auto_vision_btn.setText("👁️ Auto: OFF")
            self.auto_vision_btn.setStyleSheet("background-color: #313244; color: #CDD6F4;")
            asyncio.create_task(self.agent.toggle_auto_vision(False))
            
    def toggle_working_indicator(self, is_working):
        if is_working:
            self.working_timer.start(300)
            self.working_lbl.setVisible(True)
        else:
            self.working_timer.stop()
            self.working_lbl.setStyleSheet("color: #A6ADC8; font-weight: bold; font-size: 13px; background-color: #313244; padding: 6px 16px; border-radius: 12px; margin-right: 15px; border: 1px solid #45475A;")
            self.working_lbl.setText("⚙️ STANDBY")

    def open_settings(self):
        dlg = SettingsDialog(self.agent.config, self)
        dlg.exec()
        
    def open_memory_manager(self):
        asyncio.create_task(self.agent.send_text("Fetch all my memories using save_memory tool and read them out loud to me."))

    def toggle_connection(self):
        if not self.agent.running:
            self.connect_btn.setText("Connecting...")
            self.connect_btn.setStyleSheet("background-color: #F9E2AF; color: #11111B; font-size: 14px; padding: 8px 24px;")
            self.connect_btn.setEnabled(False)
            asyncio.create_task(self.start_agent())
        else:
            asyncio.create_task(self.stop_agent())

    async def start_agent(self):
        success = await self.agent.connect()
        if success:
            self.connect_btn.setText("Disconnect")
            self.connect_btn.setStyleSheet("background-color: #F38BA8; color: #11111B; font-size: 14px; padding: 8px 24px;")
            self.connect_btn.setEnabled(True)
            asyncio.create_task(self.agent.send_audio_loop())
            asyncio.create_task(self.agent.receive_loop())
            asyncio.create_task(self.agent.audio.mic_loop())
            asyncio.create_task(self.agent.audio.speaker_loop())
        else:
            self.connect_btn.setText("Connect Live API")
            self.connect_btn.setStyleSheet("background-color: #A6E3A1; color: #11111B; font-size: 14px; padding: 8px 24px;")
            self.connect_btn.setEnabled(True)

    async def stop_agent(self):
        await self.agent.disconnect()
        
    def closeEvent(self, event):
        if self.agent.running:
            try:
                loop = asyncio.get_event_loop()
                loop.create_task(self.agent.disconnect())
            except Exception:
                pass
        event.accept()
