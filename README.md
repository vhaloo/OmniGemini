# OmniGemini

![OmniGemini Logo](https://img.shields.io/badge/OmniGemini-v0.0.4-blue?style=for-the-badge&logo=google)

The Ultimate Live Desktop Assistant powered by Google's **Gemini 2.5 Flash Native Audio Preview** and **Gemini 3.1 Pro/Flash**.

OmniGemini blends the incredible low-latency, real-time voice conversational capabilities of the **Gemini Live API** with the deep system-level integration of the **Gemini CLI**. Talk naturally, share your screen or webcam, and let OmniGemini control your computer, write code, or use Model Context Protocol (MCP) servers on your behalf.

---

## 💾 Download Installers (Recommended)

The easiest way to get started is to download the auto-installer bundle for your operating system.

**[👉 Download OmniGemini for Windows & macOS/Linux from the Releases Page](https://github.com/vhaloo/OmniGemini/releases/latest)**

1. Download the `.zip` file for your OS.
2. Extract the folder to your desktop or desired location.
3. Run the `install_windows.bat` (Windows) or `install_unix.sh` (Mac/Linux) script inside the folder. It will automatically set up Python, install the required libraries, and launch the assistant.

---

## 🌟 Key Features

- 🎙️ **Real-Time Voice Chat:** Talk naturally to the AI without needing to press keys or wait for text to generate. The connection remains open and responsive.
- 👁️ **Vision Context (Webcam & Screen):** Push frames from your webcam or your screen to let the AI see exactly what you are talking about.
  - **Auto-Vision Streaming:** Enable the "👁️ Auto-Vision" toggle to have your screen continuously streamed to the AI in the background.
  - **Autonomous Self-Capture:** The AI is equipped with tools to "look" at your screen or your webcam on its own whenever you ask it a question about your visual context!
- ⚡ **Deep System Control & MCP Delegation:** 
  - **Lightweight Tasks:** OmniGemini can run short PowerShell commands instantly to check system state.
  - **Heavyweight Tasks:** For complex coding, refactoring, or using MCP tools (like GitHub, Google Workspace, File System), OmniGemini autonomously delegates the work to your local [Gemini CLI](https://github.com/google/gemini-cli) using the powerful **Gemini 3.1 Pro** or **Gemini 3.1 Flash** models.
- 🔇 **Perfect Echo Cancellation (Hard Ducking):** OmniGemini mutes your microphone transparently when the AI is speaking by sending pure silence streams, preventing annoying feedback loops and ensuring rock-solid API connection stability.
- 🧠 **Dynamic AI Steering:** Adjust the AI's personality, tone, or constraints on the fly using the GUI Steering input.
- 💻 **Cross-Platform PyQt6 GUI:** A high-verbosity, terminal-like interface showing you exactly what the AI is thinking, what tools it is triggering, the microphone volume levels, and the results it gets.
- 📝 **Persistent Local Logging:** Every session is automatically saved as a Markdown file in the `logs/` directory, keeping a full history of your conversations, tool calls, and system actions.

---

## 🚀 Installation

We provide robust auto-install scripts to get you up and running in seconds on any platform.

### Windows
Double-click the `install_windows.bat` file, or run it from your terminal:
```cmd
.\install_windows.bat
```
This will automatically create a Python virtual environment, install all dependencies, and launch the application. Future launches can be done using the `Launch OmniGemini.bat` file.

### macOS & Linux
Run the provided shell script:
```bash
chmod +x install_unix.sh
./install_unix.sh
```
*(On macOS, ensure you have Python 3.10+ installed via Homebrew or official installers. You may need to grant Terminal permission to access the Camera/Microphone in System Settings).*

---

## 🛠️ Manual Setup

If you prefer to set up the environment manually:

1. Clone this repository:
```bash
git clone https://github.com/vhaloo/OmniGemini.git
cd OmniGemini
```

2. Create a virtual environment and activate it:
```bash
python -m venv venv
# On Windows:
venv\Scripts\activate
# On Linux/Mac:
source venv/bin/activate
```

3. Install dependencies:
```bash
pip install google-genai sounddevice numpy opencv-python mss Pillow PyQt6 qasync rich
```

4. Run the application:
```bash
python -m src.main
```

---

## 🎮 Usage Guide

1. **Configure API Key:** On first launch, click **⚙ Settings** and paste your `GEMINI_API_KEY`. (Get one from [Google AI Studio](https://aistudio.google.com/app/apikey)).
2. **Connect:** Click the **Connect** button. The AI will start listening.
3. **Talk & Type:** Speak directly into your microphone, or use the text input bar at the bottom for precise prompts (like URLs or code snippets).
4. **Share Vision:** Click **📸 Share Webcam** or **🖥️ Share Screen** right before asking a question about your visual context (e.g., *"What error is shown on my screen right now?"*).
5. **System Control:** Ask the AI to *"Create a folder on my desktop"* or *"Use Gemini CLI to write a Python script that plays Tetris"*. Watch the high-verbosity logs as it executes your commands!

## 🔗 Integration with Gemini CLI
OmniGemini acts as an intelligent voice frontend for the [Gemini CLI](https://github.com/google/gemini-cli). It expects the command `gemini` to be available in your system's PATH. 
Whenever you ask for complex operations, OmniGemini runs `gemini --yolo --model gemini-3.1-pro-preview "your task"` autonomously, utilizing all your loaded extensions and MCPs safely.

## ⚠️ Requirements
- Python 3.10 or higher
- A working Microphone and Speakers/Headphones
- A valid Gemini API Key

## License
MIT License
