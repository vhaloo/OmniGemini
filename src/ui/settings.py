import sounddevice as sd
from PyQt6.QtWidgets import QDialog, QFormLayout, QLineEdit, QComboBox, QCheckBox, QDialogButtonBox
from src.config import save_config

class SettingsDialog(QDialog):
    def __init__(self, config, parent=None):
        super().__init__(parent)
        self.setWindowTitle("OmniGemini Settings")
        self.setMinimumWidth(550)
        self.config = config
        self.setStyleSheet(
            """
            QDialog { background-color: #1E1E2E; color: #CDD6F4; font-family: 'Segoe UI', sans-serif; }
            QLineEdit { background-color: #181825; color: #CDD6F4; border: 1px solid #313244; border-radius: 6px; padding: 8px; }
            QComboBox { background-color: #181825; color: #CDD6F4; border: 1px solid #313244; border-radius: 6px; padding: 8px; }
            QPushButton { background-color: #313244; color: #CDD6F4; border-radius: 6px; padding: 10px 20px; border: none; font-weight: bold;}
            QPushButton:hover { background-color: #45475A; }
            QLabel { color: #CDD6F4; font-weight: 500;}
            """)

        layout = QFormLayout(self)
        layout.setSpacing(15)

        self.api_key_input = QLineEdit(self.config.get("api_key", ""))
        self.api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.api_key_input.setToolTip("Your Gemini API key from Google AI Studio. Required for the Live API.")
        layout.addRow("Gemini API Key:", self.api_key_input)

        self.cli_path_input = QLineEdit(self.config.get("gemini_cli_path", "gemini"))
        self.cli_path_input.setToolTip("Path to the Gemini CLI executable. Use 'gemini' if installed globally via npm.")
        layout.addRow("Gemini CLI Path:", self.cli_path_input)

        self.camera_idx_input = QLineEdit(str(self.config.get("camera_index", 0)))
        self.camera_idx_input.setToolTip("Webcam index. 0 is usually integrated, 1+ for external.")
        layout.addRow("Camera Index:", self.camera_idx_input)

        self.loudness_input = QLineEdit(str(self.config.get("loudness_threshold", 8000)))
        self.loudness_input.setToolTip("Sensitivity threshold for the mic. Lower = More sensitive. 8000 is standard.")
        layout.addRow("Loudness Threshold:", self.loudness_input)

        self.in_device_combo = QComboBox()
        self.in_device_combo.setToolTip("Choose your microphone input.")
        self.in_device_combo.addItem("Default System Input", None)
        self.out_device_combo = QComboBox()
        self.out_device_combo.setToolTip("Choose your audio output (speakers/headphones).")
        self.out_device_combo.addItem("Default System Output", None)

        try:
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
        except Exception:
            pass

        layout.addRow("Mic Input:", self.in_device_combo)
        layout.addRow("Speaker Output:", self.out_device_combo)

        self.ducking_checkbox = QCheckBox("Enable Speaker Ducking (Echo Cancellation)")
        self.ducking_checkbox.setToolTip("Prevents the AI from hearing itself through your speakers. Highly recommended.")
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
        except ValueError: pass
        try:
            self.config["loudness_threshold"] = int(self.loudness_input.text())
        except ValueError: pass

        self.config["input_device"] = self.in_device_combo.currentData()
        self.config["output_device"] = self.out_device_combo.currentData()
        self.config["ducking_enabled"] = self.ducking_checkbox.isChecked()

        save_config(self.config)
        super().accept()
