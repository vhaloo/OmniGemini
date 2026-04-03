# OmniGemini

The Ultimate Live Desktop Assistant powered by Google's Gemini 2.5 Flash Native Audio Preview.

OmniGemini blends the incredible low-latency, real-time voice conversational capabilities of the **Gemini Live API** with the deep system-level integration of the **Gemini CLI**.

## Features
- 🎙️ **Real-Time Voice Chat:** Talk naturally to the AI without needing to press keys.
- 👁️ **Vision Context:** Push frames from your webcam or your screen to let the AI see what you are talking about.
- ⚡ **CLI Delegation:** OmniGemini can run PowerShell commands instantly, or delegate complex coding/system tasks to the Gemini CLI (which manages your MCP servers, git workflows, and deeper autonomous tasks).
- 🔇 **Echo Cancellation (Ducking):** Mutes your microphone transparently when the AI is speaking, preventing annoying feedback loops.
- 💻 **Cross-Platform PyQt6 GUI:** A high-verbosity terminal-like interface showing you exactly what the AI is thinking, what tools it is triggering, and the results it gets.

## Installation

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

## Usage

1. Run the application:
```bash
python -m src.main
```
Or use the provided `Launch OmniGemini.bat` file on Windows.

2. Click **⚙ Settings** and paste your `GEMINI_API_KEY`.
3. Click **Connect** and start talking!
4. Use the Vision buttons (**Share Webcam**, **Share Screen**) to send a visual context frame to the AI right before you ask it a question about it.

## Integration with Gemini CLI
OmniGemini works seamlessly with [Gemini CLI](https://github.com/google/gemini-cli). It expects the command `gemini` to be available in your PATH. If your installation is located elsewhere, update the path in the Settings dialog.

Whenever you ask for complex operations like "Create a React App" or "Analyze this codebase", OmniGemini runs `gemini --yolo "your task"` in the background, utilizing all your loaded extensions and MCPs automatically.

## Requirements
- Python 3.10+
- Microphone and Speakers
- A valid Gemini API Key

## License
MIT License
