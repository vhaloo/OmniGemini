# OmniGemini Project History

## v0.5.0 Major Overhaul
- **DPI Scaling:** Added `QApplication.setHighDpiScaleFactorRoundingPolicy` to fix blurriness and spacing issues on Full HD and 4K displays.
- **Model Upgrades:** Successfully integrated `gemini-3.1-pro-preview` for complex delegations and `gemini-3.1-flash` for high-volume tasks, leveraging the latest AI documentation.
- **Dev Verbosity Toggle:** Solved the issue of overwhelming log output by implementing a "Dev Verbose" checkbox. It dynamically filters out `[dim]` system logs and JSON outputs from the GUI, retaining only the clean conversational transcripts when unchecked.
- **Working Animation:** Designed a colorful, time-based cycling hex-palette for the "⚙️ WORKING..." text to make it visually engaging without impacting performance.
- **Text Zooming Hurdle:** Previously, changing the font size broke rich text/HTML formats. Overcame this by using `QTextEdit`'s native `.zoomIn(1)` and `.zoomOut(1)` methods for robust scaling.
- **UX Tooltips:** Added comprehensive tooltips to all buttons and settings (e.g. explaining the echo-cancellation and noise threshold logic) to drastically improve usability.