# OmniGemini

![OmniGemini Logo](https://img.shields.io/badge/OmniGemini-v0.1.3-blue?style=for-the-badge&logo=google)

The Ultimate Live Desktop Assistant powered by Google's **Gemini 3.1 Flash Live Preview** and **Gemini 3.1 Pro/Flash**.

OmniGemini blends the incredible low-latency, real-time voice conversational capabilities of the **Gemini Live API** with the deep system-level integration of the **Gemini CLI**. Talk naturally, share your screen or webcam, and let OmniGemini control your computer, manage your emails, or use Model Context Protocol (MCP) servers on your behalf.

---

## 💾 Download Installers (Recommended)

The easiest way to get started is to download the auto-installer bundle for your operating system.

**[👉 Download OmniGemini for Windows & macOS/Linux from the Releases Page](https://github.com/vhaloo/OmniGemini/releases/latest)**

1. Download the `.zip` file for your OS.
2. Extract the folder to your desktop or desired location.
3. Run the `install_windows.bat` (Windows) or `install_unix.sh` (Mac/Linux) script inside the folder. It will automatically set up Python, install the required libraries, and launch the assistant.

---

## 🌟 Key Features

- 🎙️ **Real-Time Voice Chat:** Talk naturally to the AI without needing to press keys or wait for text to generate.
  - **Audio Device Selection:** Choose your preferred input (mic) and output (speaker) devices directly from the settings menu.
- 👁️ **Vision Context (Webcam & Screen):** Push frames from your webcam or your screens.
  - **Multi-Monitor Support:** OmniGemini captures all your monitors by default, or you can ask it to focus on a specific monitor.
  - **Auto-Vision Streaming:** Continuous background screen streaming.
  - **Autonomous Self-Capture:** The AI can pull frames itself using tools.
- ⚡ **Deep System Control & MCP Delegation:** 
  - **Gmail & Workspace:** Ask OmniGemini to "read my last 5 emails" or "send an email to boss@example.com". It will delegate the task to the Google Workspace MCP securely.
  - **File Operations:** Create, modify, or analyze files (including Excel, PDF, code) based on voice or vision.
  - **Model Choice:** Automatically uses **Gemini 3.1 Flash** for speed or **Gemini 3.1 Pro** for deep reasoning.
- 🔇 **Perfect Echo Cancellation (Hard Ducking):** Zero-feedback audio stream stability.
- 🧠 **Dynamic AI Steering & Memory:** Adjust AI personality on the fly, or use the **Memory Manager** button to recall and summarize all your persistently saved preferences and workflows.
- 💻 **High Verbosity GUI:** See exactly what the AI is thinking and doing in the PyQt6 terminal logs, complete with an **Active MCPs** loaded list and a background task spinner.
- 📝 **Persistent Local Logging:** Full Markdown conversation history in `logs/`.

---

## 🚀 Installation

We provide robust auto-install scripts to get you up and running in seconds on any platform.

### Windows
Double-click the `install_windows.bat` file, or run it from your terminal:
```cmd
.\install_windows.bat
```

### macOS & Linux
Run the provided shell script:
```bash
chmod +x install_unix.sh
./install_unix.sh
```

---

## 🔗 Integration with Gemini CLI
OmniGemini acts as an intelligent voice frontend for the [Gemini CLI](https://github.com/google/gemini-cli). It expects the command `gemini` to be available in your system's PATH. 
Whenever you ask for complex operations, OmniGemini runs `gemini --yolo --model gemini-3.1-flash-preview "your task"` autonomously, utilizing all your loaded extensions and MCPs safely.

## ⚠️ Requirements
- Python 3.10 or higher
- A working Microphone and Speakers/Headphones
- A valid Gemini API Key

## License
MIT License
