# OmniGemini

![OmniGemini Logo](https://img.shields.io/badge/OmniGemini-v0.5.0-blue?style=for-the-badge&logo=google)

The Ultimate Live Desktop Assistant powered by Google's **Gemini Live API** and **Gemini CLI**.

OmniGemini blends the incredible low-latency, real-time voice conversational capabilities of the **Gemini Live API** with the deep system-level integration of the **Gemini CLI**. Talk naturally, share your screen or webcam, and let OmniGemini control your computer, manage your emails, or use Model Context Protocol (MCP) servers on your behalf.

---

## 💾 Download Installers (Recommended)

The easiest way to get started is to download the auto-installer bundle for your operating system.

**[👉 Download OmniGemini for Windows & macOS/Linux from the Releases Page](https://github.com/vhaloo/OmniGemini/releases/latest)**

---

## 🌟 Key Features (v0.5.0 Major Overhaul)

- 🎙️ **Real-Time Voice Chat:** Talk naturally without waiting for text generation. Powered by `gemini-2.5-flash-native-audio-preview-12-2025`.
- 👁️ **Vision Context:** High-speed capture of webcam and multi-monitor setups.
- ⚡ **Deep CLI Delegation:** Background tasks (coding, emails, browsing) are delegated to the **Gemini CLI** using **Gemini 3.1 Pro** for massive reasoning power.
- 🧠 **Session Manager:** Reload any previous conversation from your local logs into current memory to continue where you left off.
- 📺 **4K/High-DPI Support:** Crisp text and beautiful multicolored animated indicators.
- 🔇 **Robust Stability:** Sanitized WebSocket payloads prevent disconnects during complex task reporting.
- 🔍 **Dev Verbosity Toggle:** Hide technical system noise with one click.
- 📝 **Persistent Local Logging:** Full conversation history preserved in `logs/`.

---

## 🚀 Quick Start (Development)

1. **Clone & Install:**
   ```bash
   git clone https://github.com/vhaloo/OmniGemini.git
   cd OmniGemini
   install_windows.bat
   ```
2. **Setup:** Open the **Settings** menu in the app and paste your **Gemini API Key**.
3. **Connect:** Click **Connect Live API** and start talking!

Whenever you ask for complex operations, OmniGemini runs `gemini --yolo --model gemini-3.1-pro-preview "your task"` autonomously, utilizing all your loaded extensions and MCPs safely.

## ⚠️ Requirements
- Python 3.10+
- A working Microphone and Speakers
- A valid Gemini API Key (from Google AI Studio)

## License
MIT License
