# OmniGemini Project History

## v0.5.0 Stable Release
- **Session Manager:** Overhauled the "Memory" feature. It now opens a `Session Manager` dialog that lists all Markdown logs in the `logs/` directory. Selecting a log reloads the conversation history into the agent's memory, allowing the user to resume any previous session naturally.
- **Connection Stability:** Fixed the persistent `1007 Invalid Argument` WebSocket disconnects by implementing strict ASCII regex sanitization and hard payload truncation (800 chars) for background task results.
- **Deprecated API Fix:** Purged the deprecated `.send()` method from the `google-genai` SDK and replaced it with the modern `send_client_content()` using the required `{"role": "user", "parts": [...]}` dictionary schema.
- **Model Realignment:** Reverted the Live API to `gemini-2.5-flash-native-audio-preview-12-2025` (the only stable model for the Multimodal Live WebSocket) while keeping the background CLI agent on **Gemini 3.1 Pro** for complex tasks.
- **DPI & UI:** Fully enabled High-DPI support and fixed the `A+` / `A-` zoom buttons by overriding the document's default font size, ensuring rich HTML formatting is preserved during scaling.
- **Error Handling:** Added non-interactive safety constraints to all background CLI prompts to prevent the agent from stalling on interactive shells.
