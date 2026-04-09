import asyncio
import subprocess
import os
import shutil
import re
from datetime import datetime
from google import genai
from google.genai import types
from src.audio import AudioController
from src.vision import VisionController

# Stable Multimodal Live API model
MODEL = "gemini-2.5-flash-native-audio-preview-12-2025"

class OmniAgent:
    def __init__(self, config, logger):
        self.config = config
        self.logger = logger
        self.client = None
        self.session = None
        self.audio = AudioController(config)
        self.vision = VisionController(config)
        self.running = False
        self.log_path = None
        self._session_cm = None
        
        # Callbacks for GUI
        self.on_frame_captured = None 
        self.on_disconnect = None
        self.on_working_state_changed = None
        
        # State
        self.chat_history = []
        self.active_background_tasks = 0
        self.steering_prompt = ""
        self.auto_vision_active = False
        
        # Tool Definitions
        self.run_powershell = {
            "name": "run_powershell",
            "description": "Executes a short PowerShell command on the user's Windows machine. Good for quick system checks, opening folders, moving files, checking IP, etc.",
            "parameters": {
                "type": "OBJECT",
                "properties": {
                    "command": {"type": "STRING"}
                },
                "required": ["command"]
            }
        }
        self.delegate_gemini = {
            "name": "delegate_gemini",
            "description": "Delegates a task to the local Gemini CLI agent. Use this for ANYTHING that requires Model Context Protocol (MCP) servers, like reading files, browsing the web, deep coding, or computer use. You MUST tell the user out loud that you are starting it.",
            "parameters": {
                "type": "OBJECT",
                "properties": {
                    "prompt": {"type": "STRING", "description": "The exact instruction for the Gemini CLI.",},
                    "model": {"type": "STRING", "description": "Choose 'pro' for programming, complex tasks, or deep research. Choose 'flash' for quick file operations or simple queries.", "enum": ["pro", "flash"]}
                },
                "required": ["prompt", "model"]
            }
        }
        self.capture_screen = {
            "name": "capture_screen",
            "description": "Captures a current image of the user's computer screen and adds it to your visual context. Use this whenever the user asks you to look at their screen or read something.",
            "parameters": {
                "type": "OBJECT", 
                "properties": {
                    "monitor_index": {"type": "INTEGER", "description": "Optional. 0 for all monitors combined (default), 1 for primary, 2 for secondary, etc."}
                }
            }
        }
        self.capture_webcam = {
            "name": "capture_webcam",
            "description": "Captures a current image from the user's webcam and adds it to your visual context. Use this to look at the user or their physical environment.",
            "parameters": {"type": "OBJECT", "properties": {}}
        }
        
        self.base_instruction = (
            "You are OmniGemini, the ultimate Live Desktop Assistant. "
            "You have direct access to the user's system via powerful tools:\n"
            "1. 'run_powershell': For immediate, tiny system checks or opening files (e.g., 'Invoke-Item path\to\file').\n"
            "2. 'delegate_gemini': The heavy lifter. The Gemini CLI has all the Model Context Protocol (MCP) servers, full file system access, and system mastery.\n"
            "3. 'capture_screen' & 'capture_webcam': Use these tools AT ANY TIME to take a picture and see what the user is doing or looking at.\n"
            "IMPORTANT: If the user asks you to modify files, browse the web, or use MCPs (like Google Workspace for GMAIL/Calendar/Docs), YOU MUST use 'delegate_gemini'.\n"
            "VERBOSITY: When you receive the result from 'delegate_gemini', you MUST give a highly detailed, verbose verbal summary of exactly what the CLI did. Explain the details."
        )

    def _get_current_instruction(self):
        instr = self.base_instruction
        if self.steering_prompt:
            instr += f"\n\nUSER STEERING DIRECTIVES:\n{self.steering_prompt}"
        if self.chat_history:
            # We provide the last 30 turns to ensure continuity after reconnect
            history_text = "\n".join(self.chat_history[-30:])
            instr += f"\n\nCONVERSATION CONTINUITY (You just reconnected or resumed. Here is what was discussed so far):\n{history_text}\n\nResume naturally based on this context."
        return instr

    async def _run_background_cli(self, task_id, actual_model, prompt):
        self.active_background_tasks += 1
        if self.on_working_state_changed:
            self.on_working_state_changed(True)
            
        self.logger(f"[bold magenta]Background Task [{task_id}]:[/bold magenta] Starting {actual_model}\n[dim]Prompt: {prompt}[/dim]")
        self._append_log("Background Task", f"Started {task_id} [{actual_model}]: {prompt}")
        
        cli_path = self.config.get("gemini_cli_path", "gemini")
        try:
            import shutil
            resolved_path = shutil.which(cli_path) or cli_path
                
            args_list = [resolved_path, "--yolo", "--model", actual_model, "--include-directories", "C:\\", "-p", prompt]
            cmd_str = subprocess.list2cmdline(args_list)
            
            process = await asyncio.create_subprocess_shell(
                cmd_str,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
                stdin=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
            
            out_chunks = []
            while True:
                line = await process.stdout.readline()
                if not line: break
                decoded_line = line.decode('utf-8', errors='replace')
                out_chunks.append(decoded_line)
                self.logger(f"[dim][CLI {task_id}][/dim] {decoded_line.strip()}")
                if len(out_chunks) > 2000:
                    process.terminate()
                    break
                
            await process.wait()
            out = "".join(out_chunks)
            
            if process.returncode != 0:
                self.logger(f"[red]Task {task_id} Failed (Code {process.returncode}).[/red]")
            else:
                self.logger(f"[green]Task {task_id} Finished.[/green]")
                
            if self.session and self.running:
                self.logger(f"[dim]Injecting Task {task_id} results into Live API context...[/dim]")
                
                # Sanitize for WebSocket safety
                clean_out = re.sub(r'[^\x20-\x7E\n\r\t]', '', out)
                if len(clean_out) > 800:
                    clean_out = "...(truncated)...\n" + clean_out[-800:]
                    
                notification = f"Background Task {task_id} completed. Terminal output:\n{clean_out}\n\nPlease review and summarize the final outcome to the user out loud."
                self.chat_history.append(f"System: Task {task_id} completed.")
                try:
                    await self.session.send_client_content(turns={"role": "user", "parts": [{"text": notification}]}, turn_complete=True)
                except Exception as e:
                    self.logger(f"[red]Failed to send task result to session: {e}[/red]")
                    
        except Exception as e:
            self.logger(f"[red]Failed to run Gemini CLI: {e}[/red]")
            if self.session and self.running:
                try:
                    await self.session.send_client_content(turns={"role": "user", "parts": [{"text": f"[SYSTEM: Background Task {task_id} FAILED: {e}]"}]}, turn_complete=True)
                except Exception as ex:
                    self.logger(f"[red]Failed to send error fallback to session: {ex}[/red]")
        finally:
            self.active_background_tasks -= 1
            if self.on_working_state_changed and self.active_background_tasks <= 0:
                self.on_working_state_changed(False)

    def _init_log(self):
        if not os.path.exists("logs"):
            os.makedirs("logs")
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        self.log_path = os.path.join("logs", f"session_{timestamp}.md")
        with open(self.log_path, "w", encoding="utf-8") as f:
            f.write(f"# OmniGemini Session Log - {timestamp}\n\n")

    def _append_log(self, role, text):
        if self.log_path:
            try:
                with open(self.log_path, "a", encoding="utf-8") as f:
                    f.write(f"{role}: {text}\n\n")
            except Exception as e:
                self.logger(f"[red]Log append failed: {e}[/red]")

    async def toggle_auto_vision(self, state, source="webcam"):
        self.auto_vision_active = state
        if state: asyncio.create_task(self._auto_vision_task(source))
            
    async def _auto_vision_task(self, source):
        self.logger(f"[dim]Auto-Vision ({source}) started...[/dim]")
        while self.running and self.session and self.auto_vision_active:
            await self.send_vision_frame(source, silent=True, force=False)
            await asyncio.sleep(2.5)

    async def connect(self):
        api_key = self.config.get("api_key")
        if not api_key:
            self.logger("[bold red]ERROR:[/bold red] API Key missing in Settings.")
            return False
            
        if not self.log_path: self._init_log()
        self.client = genai.Client(api_key=api_key)
        
        tools = [{"function_declarations": [self.run_powershell, self.delegate_gemini, self.capture_screen, self.capture_webcam]}]
        cfg = {
            "response_modalities": ["AUDIO"],
            "tools": tools,
            "system_instruction": {"parts": [{"text": self._get_current_instruction()}]}
        }
        
        try:
            self._session_cm = self.client.aio.live.connect(model=MODEL, config=cfg)
            self.session = await self._session_cm.__aenter__()
            self.running = True
            self.audio.start()
            self.logger("[bold green]Connected to OmniGemini Live API![/bold green] Listening...")
            self._append_log("System", "Connected to API.")
            return True
        except Exception as e:
            self.logger(f"[bold red]Connection Failed:[/bold red] {e}")
            return False

    async def disconnect(self):
        if not self.running and not self.session: return
        self.running = False
        if self._session_cm:
            try: await self._session_cm.__aexit__(None, None, None)
            except Exception as e:
                self.logger(f"[red]Session exit error: {e}[/red]")
        self.session = None
        self._session_cm = None
        self.audio.stop()
        self.vision.stop_camera()
        self._append_log("System", "Disconnected.")
        self.logger("[bold yellow]Disconnected.[/bold yellow]")
        if self.on_disconnect: self.on_disconnect()

    async def send_audio_loop(self):
        while self.running and self.session:
            try:
                msg = await asyncio.wait_for(self.audio.mic_queue.get(), timeout=0.5)
                if self.running and self.session: await self.session.send_realtime_input(audio=msg)
            except asyncio.TimeoutError: continue
            except Exception as e:
                if self.running:
                    self.logger(f"[yellow]Audio send error: {e}[/yellow]")
                    if "timeout" in str(e).lower() or "close" in str(e).lower():
                        await self.disconnect(); break
                await asyncio.sleep(0.1)

    async def receive_loop(self):
        if not self.session: return
        while self.running and self.session:
            try:
                async for response in self.session.receive():
                    if not self.running: break
                    server_content = response.server_content
                    if server_content:
                        if server_content.interrupted:
                            self.logger("[yellow][User Interrupted][/yellow]")
                            self.audio.clear_speaker_queue()
                        if server_content.input_transcription:
                            t = server_content.input_transcription.text
                            self.logger(f"[bold white]You:[/bold white] {t}"); self._append_log("You", t); self.chat_history.append(f"User: {t}")
                        if server_content.output_transcription:
                            t = server_content.output_transcription.text
                            self.logger(f"[bold blue]Omni:[/bold blue] {t}"); self._append_log("Omni", t); self.chat_history.append(f"OmniGemini: {t}")
                        if server_content.model_turn:
                            for part in server_content.model_turn.parts:
                                if part.inline_data: self.audio.speaker_queue.put_nowait(part.inline_data.data)

                    if response.tool_call:
                        func_responses = []
                        frames_to_send = []
                        for fc in response.tool_call.function_calls:
                            args = fc.args
                            if fc.name == "run_powershell":
                                cmd = args.get("command", "")
                                self.logger(f"[bold cyan]Tool:[/bold cyan] powershell: {cmd}")
                                self._append_log("Tool", f"powershell: {cmd}")
                                try:
                                    process = await asyncio.create_subprocess_shell(f"powershell.exe -NoProfile -Command \"{cmd}\"", stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
                                    stdout, stderr = await process.communicate()
                                    out = (stdout + stderr).decode('utf-8', errors='replace') or "Success."
                                except Exception as e: out = f"Error: {e}"
                                self.logger(f"[green]Result:[/green] {out[:200]}...")
                            elif fc.name == "delegate_gemini":
                                prompt = args.get("prompt", ""); model_choice = args.get("model", "flash")
                                actual_model = "gemini-3.1-pro-preview" if "pro" in model_choice.lower() else "gemini-2.5-flash"
                                
                                # Strict non-interactive constraint
                                p = prompt + "\n\nCRITICAL: RUN HEADLESSLY. DO NOT STALL. USE NON-INTERACTIVE FLAGS."
                                task_id = f"task_{int(datetime.now().timestamp())}"
                                asyncio.create_task(self._run_background_cli(task_id, actual_model, p))
                                out = f"Background task {task_id} started on {actual_model}. Tell the user you're on it."
                                self.logger(f"[bold magenta]Delegated:[/bold magenta] {actual_model}")
                                self._append_log("Delegation", f"{actual_model}: {prompt}")
                            elif fc.name == "capture_screen":
                                m = args.get("monitor_index", 0)
                                self.logger(f"[bold cyan]Tool:[/bold cyan] screen capture ({m})")
                                frames_to_send.append(("screen", m))
                                out = "Screen captured context sent."
                            elif fc.name == "capture_webcam":
                                self.logger("[bold cyan]Tool:[/bold cyan] webcam capture")
                                frames_to_send.append(("webcam", 0))
                                out = "Webcam frame context sent."
                                    
                            func_responses.append(types.FunctionResponse(id=fc.id, name=fc.name, response={"result": out}))
                            
                        if func_responses and self.session and self.running:
                            try:
                                await self.session.send_tool_response(function_responses=func_responses)
                                for s, m in frames_to_send: await self.send_vision_frame(s, monitor_index=m, silent=True, force=True)
                            except Exception as e: self.logger(f"[red]Tool send error: {e}[/red]")
                await asyncio.sleep(0.1)
            except Exception as e:
                if self.running: self.logger(f"[red]Lost connection: {e}[/red]")
                break
        if self.running: await self.disconnect()

    async def send_text(self, text):
        if not self.session:
            self.logger(f"[bold white]You (Internal):[/bold white] {text}")
            self.chat_history.append(f"User: {text}")
            return
        self.logger(f"[bold white]You:[/bold white] {text}")
        self._append_log("You", text)
        self.chat_history.append(f"User: {text}")
        try: await self.session.send_client_content(turns={"role": "user", "parts": [{"text": text}]}, turn_complete=True)
        except Exception as e: self.logger(f"[red]Send error: {e}[/red]")

    async def send_vision_frame(self, source="webcam", monitor_index=0, silent=False, force=False):
        if not self.session: return
        frame_bytes = None
        if source == "webcam":
            await asyncio.to_thread(self.vision.start_camera)
            frame_bytes = await asyncio.to_thread(self.vision.get_camera_frame_bytes, force)
        elif source == "screen":
            frame_bytes = await asyncio.to_thread(self.vision.get_screen_frame_bytes, monitor_index, force)
            
        if frame_bytes:
            if self.on_frame_captured: self.on_frame_captured(frame_bytes)
            try:
                with open(os.path.join("logs", f"latest_{source}.jpg"), "wb") as f: f.write(frame_bytes)
            except Exception as e:
                self.logger(f"[red]Vision frame save failed: {e}[/red]")
            if not silent: self.logger(f"[bold blue]Context:[/bold blue] Sent {source} frame.")
            self._append_log("Vision", f"Sent {source}")
            try:
                part = types.Part.from_bytes(data=frame_bytes, mime_type="image/jpeg")
                await self.session.send_client_content(turns={"role": "user", "parts": [part]}, turn_complete=True)
            except Exception as e:
                if not silent: self.logger(f"[red]Vision error: {e}[/red]")
