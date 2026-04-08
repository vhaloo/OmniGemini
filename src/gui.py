import asyncio
import ctypes
import os
import re
import sounddevice as sd
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QTextEdit, QLineEdit, QCheckBox, 
                             QFormLayout, QDialog, QDialogButtonBox, QLabel, QSplitter, QProgressBar, QComboBox)
from PyQt6.QtGui import QPixmap, QImage, QFont
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
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
    
    # Basic Markdown
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
            QLineEdit { background-color: #181825; color: #CDD6F4; border: 1px solid #313244; border-radius: 4px; padding: 5px; }
            QComboBox { background-color: #181825; color: #CDD6F4; border: 1px solid #313244; border-radius: 4px; padding: 5px; }
            QPushButton { background-color: #313244; color: #CDD6F4; border-radius: 4px; padding: 6px 12px; border: none; }
            QPushButton:hover { background-color: #45475A; }
            QLabel { color: #CDD6F4; }
        """)
        
        layout = QFormLayout(self)
        
        self.api_key_input = QLineEdit(self.config.get("api_key", ""))
        self.api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addRow("Gemini API Key:", self.api_key_input)
        
        self.cli_path_input = QLineEdit(self.config.get("gemini_cli_path", "gemini"))
        layout.addRow("Gemini CLI Path:", self.cli_path_input)
        
        self.camera_idx_input = QLineEdit(str(self.config.get("camera_index", 0)))
        layout.addRow("Camera Index:", self.camera_idx_input)
        
        self.loudness_input = QLineEdit(str(self.config.get("loudness_threshold", 8000)))
        layout.addRow("Interruption Loudness Threshold:", self.loudness_input)
        
        self.in_device_combo = QComboBox()
        self.in_device_combo.addItem("Default", None)
        self.out_device_combo = QComboBox()
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
        layout.addRow("Output Device (Speaker):", self.out_device_combo)
        
        self.ducking_checkbox = QCheckBox("Enable Speaker Ducking (Echo Cancellation)")
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
        self.setWindowTitle("OmniGemini - Live Desktop Assistant v0.1.9")
        self.resize(1300, 850)
        self.setStyleSheet("""
            QMainWindow { background-color: #1E1E2E; color: #CDD6F4; font-family: 'Segoe UI', sans-serif; }
            QPushButton { background-color: #313244; color: #CDD6F4; border-radius: 6px; padding: 10px; font-weight: bold; border: 1px solid #45475A; }
            QPushButton:hover { background-color: #45475A; }
            QPushButton:pressed { background-color: #585B70; }
            QTextEdit, QLineEdit { background-color: #181825; color: #CDD6F4; border-radius: 6px; border: 1px solid #313244; padding: 10px; font-family: 'Consolas', monospace; font-size: 13px; }
            QLabel { color: #CDD6F4; }
            QProgressBar { border: 1px solid #313244; border-radius: 4px; background-color: #181825; text-align: center; }
            QProgressBar::chunk { background-color: #A6E3A1; border-radius: 3px; }
            QSplitter::handle { background-color: #313244; width: 2px; }
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
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget)
        
        header_layout = QHBoxLayout()
        header = QLabel("OmniGemini")
        header.setStyleSheet("font-size: 24px; font-weight: bold; color: #89B4FA;")
        header_layout.addWidget(header)
        
        self.working_lbl = QLabel("⚙️ WORKING")
        self.working_lbl.setStyleSheet("color: #F9E2AF; font-weight: bold; font-size: 14px;")
        self.working_lbl.setVisible(False)
        header_layout.addWidget(self.working_lbl)
        header_layout.addStretch()
        
        try:
            is_admin = ctypes.windll.shell32.IsUserAnAdmin() != 0 if os.name == 'nt' else os.getuid() == 0
        except Exception:
            is_admin = False
            
        power_lbl = QLabel(f"⚡ POWER LEVEL: {'ADMIN' if is_admin else 'USER'}")
        power_lbl.setStyleSheet(f"font-weight: bold; color: {'#F38BA8' if is_admin else '#FAB387'}; padding: 5px; border: 1px solid {'#F38BA8' if is_admin else '#FAB387'}; border-radius: 4px;")
        header_layout.addWidget(power_lbl)
        main_layout.addLayout(header_layout)
        
        self.mcp_lbl = QLabel("🔌 Loaded MCPs: Waiting for CLI...")
        self.mcp_lbl.setStyleSheet("color: #89DCEB; font-size: 12px; font-style: italic; margin-bottom: 5px;")
        main_layout.addWidget(self.mcp_lbl)
        
        splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(splitter)
        
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 10, 0)
        
        top_layout = QHBoxLayout()
        self.connect_btn = QPushButton("Connect")
        self.connect_btn.setStyleSheet("background-color: #A6E3A1; color: #11111B; padding: 10px; font-weight: bold; border: none;")
        self.connect_btn.clicked.connect(self.toggle_connection)
        
        self.memory_btn = QPushButton("🧠 Memory Manager")
        self.memory_btn.setStyleSheet("background-color: #CBA6F7; color: #11111B; padding: 10px; font-weight: bold; border: none;")
        self.memory_btn.clicked.connect(self.open_memory_manager)
        
        self.settings_btn = QPushButton("⚙ Settings")
        self.settings_btn.clicked.connect(self.open_settings)
        
        top_layout.addWidget(self.connect_btn)
        top_layout.addWidget(self.memory_btn)
        top_layout.addWidget(self.settings_btn)
        left_layout.addLayout(top_layout)
        
        meter_layout = QHBoxLayout()
        meter_layout.addWidget(QLabel("🎤 MIC:"))
        self.vol_meter = QProgressBar()
        self.vol_meter.setRange(0, 10000) 
        self.vol_meter.setTextVisible(False)
        self.vol_meter.setFixedHeight(8)
        meter_layout.addWidget(self.vol_meter)
        left_layout.addLayout(meter_layout)
        
        vision_layout = QHBoxLayout()
        self.send_cam_btn = QPushButton("📸 Share Webcam")
        self.send_cam_btn.setStyleSheet("background-color: #89DCEB; color: #11111B; font-weight: bold;")
        self.send_cam_btn.clicked.connect(lambda: asyncio.create_task(self.agent.send_vision_frame("webcam", force=True)))
        
        self.send_screen_btn = QPushButton("🖥️ Share Screen")
        self.send_screen_btn.setStyleSheet("background-color: #F5C2E7; color: #11111B; font-weight: bold;")
        self.send_screen_btn.clicked.connect(lambda: asyncio.create_task(self.agent.send_vision_frame("screen", force=True)))
        
        self.auto_vision_btn = QPushButton("👁️ Auto-Vision: OFF")
        self.auto_vision_btn.setCheckable(True)
        self.auto_vision_btn.clicked.connect(self.toggle_auto_vision)
        
        vision_layout.addWidget(self.send_cam_btn)
        vision_layout.addWidget(self.send_screen_btn)
        vision_layout.addWidget(self.auto_vision_btn)
        left_layout.addLayout(vision_layout)
        
        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        left_layout.addWidget(self.log_area)
        
        input_layout = QHBoxLayout()
        self.text_input = QLineEdit()
        self.text_input.setPlaceholderText("Type a prompt and press Enter...")
        self.text_input.returnPressed.connect(self.handle_text_submit)
        
        self.send_btn = QPushButton("Send")
        self.send_btn.setStyleSheet("background-color: #89B4FA; color: #11111B; padding: 10px; font-weight: bold;")
        self.send_btn.clicked.connect(self.handle_text_submit)
        
        input_layout.addWidget(self.text_input)
        input_layout.addWidget(self.send_btn)
        left_layout.addLayout(input_layout)
        
        splitter.addWidget(left_panel)
        
        right_panel = QWidget()
        right_panel.setFixedWidth(350)
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(10, 0, 0, 0)
        
        preview_label = QLabel("VISUAL CONTEXT")
        preview_label.setStyleSheet("font-weight: bold; color: #6C7086; font-size: 11px; letter-spacing: 1px;")
        preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        right_layout.addWidget(preview_label)
        
        self.vision_preview = QLabel("No context shared yet.")
        self.vision_preview.setStyleSheet("background-color: #11111B; border: 1px solid #313244; color: #6C7086; border-radius: 6px;")
        self.vision_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.vision_preview.setMinimumHeight(200)
        self.vision_preview.setScaledContents(True)
        right_layout.addWidget(self.vision_preview)
        
        steering_label = QLabel("🧠 AI STEERING (DIRECTIVES)")
        steering_label.setStyleSheet("font-weight: bold; color: #89B4FA; font-size: 11px; margin-top: 20px; letter-spacing: 1px;")
        right_layout.addWidget(steering_label)
        
        self.steering_text = QTextEdit()
        self.steering_text.setPlaceholderText("Enter personality instructions here...")
        self.steering_text.setStyleSheet("border: 1px solid #89B4FA;")
        self.steering_text.textChanged.connect(self.update_steering)
        right_layout.addWidget(self.steering_text)
        
        help_txt = QLabel("Changes apply on next connection.")
        help_txt.setStyleSheet("color: #6C7086; font-size: 11px; font-style: italic;")
        right_layout.addWidget(help_txt)
        
        right_layout.addStretch()
        splitter.addWidget(right_panel)
        
        self.agent.logger = self.log_message
        self.log_message("[dim]Welcome to OmniGemini. Fetching system readiness...[/dim]")
        
        try:
            loop = asyncio.get_event_loop()
            loop.create_task(self.fetch_mcps_and_warmup())
        except RuntimeError:
            pass

    def animate_working(self):
        self.working_dots = (self.working_dots + 1) % 4
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
                self.mcp_lbl.setText(f"🔌 Loaded MCPs: {', '.join(mcps)}")
            else:
                self.mcp_lbl.setText("🔌 No MCPs detected or CLI error.")
        except Exception:
            self.mcp_lbl.setText("🔌 Failed to load MCPs.")

    def log_message(self, msg):
        self.log_signal.emit(msg)

    def append_log(self, msg):
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
            self.auto_vision_btn.setText("👁️ Auto-Vision: ON")
            self.auto_vision_btn.setStyleSheet("background-color: #A6E3A1; color: #11111B; font-weight: bold;")
            asyncio.create_task(self.agent.toggle_auto_vision(True, "screen"))
        else:
            self.auto_vision_btn.setText("👁️ Auto-Vision: OFF")
            self.auto_vision_btn.setStyleSheet("")
            asyncio.create_task(self.agent.toggle_auto_vision(False))

    def update_vision_preview(self, frame_bytes):
        pixmap = QPixmap()
        pixmap.loadFromData(frame_bytes)
        self.vision_preview.setPixmap(pixmap)

    def update_volume_meter(self, value):
        self.vol_meter.setValue(value)

    def update_steering(self):
        self.agent.steering_prompt = self.steering_text.toPlainText()

    def handle_agent_disconnect(self):
        self.connect_btn.setText("Connect")
        self.connect_btn.setStyleSheet("background-color: #A6E3A1; color: #11111B; padding: 10px; font-weight: bold; border: none;")
        self.connect_btn.setEnabled(True)
        if hasattr(self, 'auto_vision_btn'):
            self.auto_vision_btn.setChecked(False)
            self.auto_vision_btn.setText("👁️ Auto-Vision: OFF")
            self.auto_vision_btn.setStyleSheet("")
            asyncio.create_task(self.agent.toggle_auto_vision(False))
            
    def toggle_working_indicator(self, is_working):
        if is_working:
            self.working_lbl.setText("⚙️ WORKING")
            self.working_lbl.setVisible(True)
            self.working_timer.start(400)
        else:
            self.working_timer.stop()
            self.working_lbl.setVisible(False)

    def open_settings(self):
        dlg = SettingsDialog(self.agent.config, self)
        dlg.exec()
        
    def open_memory_manager(self):
        asyncio.create_task(self.agent.send_text("Fetch all my memories using save_memory tool and read them out loud to me."))

    def toggle_connection(self):
        if not self.agent.running:
            self.connect_btn.setText("Connecting...")
            self.connect_btn.setStyleSheet("background-color: #F9E2AF; color: #11111B; padding: 10px; font-weight: bold; border: none;")
            self.connect_btn.setEnabled(False)
            asyncio.create_task(self.start_agent())
        else:
            asyncio.create_task(self.stop_agent())

    async def start_agent(self):
        success = await self.agent.connect()
        if success:
            self.connect_btn.setText("Disconnect")
            self.connect_btn.setStyleSheet("background-color: #F38BA8; color: #11111B; padding: 10px; font-weight: bold; border: none;")
            self.connect_btn.setEnabled(True)
            asyncio.create_task(self.agent.send_audio_loop())
            asyncio.create_task(self.agent.receive_loop())
            asyncio.create_task(self.agent.audio.mic_loop())
            asyncio.create_task(self.agent.audio.speaker_loop())
        else:
            self.connect_btn.setText("Connect")
            self.connect_btn.setStyleSheet("background-color: #A6E3A1; color: #11111B; padding: 10px; font-weight: bold; border: none;")
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
