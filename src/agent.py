import asyncio
import subprocess
import os
import shutil
from datetime import datetime
from google import genai
from google.genai import types
from src.audio import AudioController
from src.vision import VisionController

MODEL = "gemini-3.1-flash-live-preview"

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
        
        # Tools
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
                    "prompt": {"type": "STRING", "description": "The exact instruction for the Gemini CLI."},
                    "model": {"type": "STRING", "description": "Choose 'flash' as the default for most tasks including MCP usage, file operations, and general coding. Only use 'pro' for extremely complex reasoning or massive refactoring.", "enum": ["pro", "flash"]}
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
            "1. 'run_powershell': For immediate, tiny system checks or opening files (e.g., 'Invoke-Item path\\to\\file').\n"
            "2. 'delegate_gemini': The heavy lifter. The Gemini CLI has all the Model Context Protocol (MCP) servers, full file system access, and system mastery. 'gemini-3.1-flash-preview' is fully capable of using MCPs and should be your default choice.\n"
            "3. 'capture_screen' & 'capture_webcam': Use these tools AT ANY TIME to take a picture and see what the user is doing or looking at.\n"
            "IMPORTANT: If the user asks you to modify files, browse the web, or use MCPs (like Google Workspace for GMAIL/Calendar/Docs), YOU MUST use 'delegate_gemini'.\n"
            "PROACTIVE MANDATE: You are extremely PROACTIVE. Do not just wait for commands. Anticipate the user's needs. Offer to automatically fix issues, suggest the next logical step, or take initiative to use your tools to improve their workflow. If they are stuck, immediately offer a concrete action you can take to help.\n"
            "GMAIL DELEGATION: You have full access to the user's emails via the Google Workspace MCP. If the user asks 'read my emails', 'what is my last email', or 'send an email', use 'delegate_gemini' and ask the CLI to fetch or send the emails. \n"
            "VISION DELEGATION: If the user asks you to create a file (like an Excel sheet) based on what you see in the webcam or screen, YOU must first capture the image, analyze it yourself, and EXTRACT all the relevant data into raw text. Then, pass that extracted raw text inside the prompt to 'delegate_gemini' so the background CLI can write the file, because the background CLI CANNOT see your live camera feed! Always ask the CLI to open the file when it is done.\n"
            "VERBOSITY MANDATE: When you receive the result from 'delegate_gemini', you MUST give a highly detailed, verbose verbal summary of exactly what the CLI did, what files it touched, or the contents of the emails it fetched. Do not just say 'it is done'. Explain the details."
        )
        self.steering_prompt = ""
        self.chat_history = []
        self.active_background_tasks = 0
        self.on_frame_captured = None 

    def _get_current_instruction(self):
        instr = self.base_instruction
        if self.steering_prompt:
            instr += f"\n\nUSER STEERING DIRECTIVES:\n{self.steering_prompt}"
        if self.chat_history:
            history_text = "\n".join(self.chat_history[-20:])
            instr += f"\n\nPREVIOUS CONVERSATION HISTORY (You just reconnected. Resume naturally from here):\n{history_text}"
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
            import time
            resolved_path = shutil.which(cli_path)
            if not resolved_path:
                resolved_path = cli_path
                
            args_list = [resolved_path, "--yolo", "--model", actual_model, "--include-directories", "C:\\", "-p", prompt]
            cmd_str = subprocess.list2cmdline(args_list)
            
            creation_flags = 0
            if os.name == 'nt':
                creation_flags = subprocess.CREATE_NO_WINDOW
                
            process = await asyncio.create_subprocess_shell(
                cmd_str,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
                stdin=subprocess.DEVNULL,
                creationflags=creation_flags
            )
            
            out_chunks = []
            while True:
                line = await process.stdout.readline()
                if not line:
                    break
                decoded_line = line.decode('utf-8', errors='replace')
                out_chunks.append(decoded_line)
                self.logger(f"[dim][CLI {task_id}][/dim] {decoded_line.strip()}")
                
                # Prevent memory explosion if output is insane
                if len(out_chunks) > 2000:
                    out_chunks.append("\n...[OUTPUT TRUNCATED]...")
                    process.terminate()
                    break
                
            await process.wait()
            out = "".join(out_chunks)
            
            if process.returncode != 0:
                self.logger(f"[red]Task {task_id} Failed (Code {process.returncode}).[/red]")
            else:
                self.logger(f"[green]Task {task_id} Finished.[/green]")
                
            # Send notification back to the Live Session
            if self.session and self.running:
                self.logger(f"[dim]Injecting Task {task_id} results into Live API context...[/dim]")
                
                # Safeguard against huge payloads and weird control characters causing WebSocket disconnects
                import re
                # Only keep basic ASCII printable characters, newlines, and tabs
                clean_out = re.sub(r'[^\x20-\x7E\n\r\t]', '', out)
                if len(clean_out) > 600:
                    clean_out = "...(truncated)...\n" + clean_out[-600:]
                    
                notification = f"Background Task {task_id} completed. Terminal output:\n{clean_out}\n\nPlease review and summarize the final outcome to the user out loud."
                self.chat_history.append(f"System: Task {task_id} completed.")
                try:
                    await self.session.send(input=notification, end_of_turn=True)
                except Exception as e:
                    self.logger(f"[red]Failed to send task result to session: {e}[/red]")
                    
        except Exception as e:
            out = f"Failed to run Gemini CLI: {e}"
            self.logger(f"[red]{out}[/red]")
            if self.session and self.running:
                try:
                    await self.session.send(input=f"[SYSTEM NOTIFICATION: Background Task {task_id} FAILED]\nError: {e}", end_of_turn=True)
                except:
                    pass
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
                    f.write(f"**{role}:** {text}\n\n")
            except Exception:
                pass

    async def toggle_auto_vision(self, state, source="screen"):
        self.auto_vision_active = state
        if state:
            asyncio.create_task(self._auto_vision_task(source))
            
    async def _auto_vision_task(self, source):
        self.logger(f"[dim]Auto-Vision ({source}) started. Sending frames every 2 seconds...[/dim]")
        while self.running and self.session and self.auto_vision_active:
            await self.send_vision_frame(source, silent=True, force=False)
            await asyncio.sleep(2.0)
        self.logger(f"[dim]Auto-Vision stopped.[/dim]")

    async def connect(self):
        api_key = self.config.get("api_key")
        if not api_key:
            self.logger("[bold red]ERROR:[/bold red] API Key is missing. Click Settings to add it.")
            return False
            
        self._init_log()
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
        if not self.running and not self.session:
            return
            
        self.running = False
        if self._session_cm:
            try:
                await self._session_cm.__aexit__(None, None, None)
            except Exception:
                pass
        self.session = None
        self._session_cm = None
        self.audio.stop()
        self.vision.stop_camera()
        self._append_log("System", "Disconnected.")
        self.logger("[bold yellow]Disconnected.[/bold yellow]")
        if self.on_disconnect:
            self.on_disconnect()

    async def send_audio_loop(self):
        while self.running and self.session:
            try:
                msg = await asyncio.wait_for(self.audio.mic_queue.get(), timeout=0.5)
                if self.running and self.session:
                    await self.session.send_realtime_input(audio=msg)
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                if self.running:
                    self.logger(f"[yellow]Audio send error: {e}[/yellow]")
                    if "timeout" in str(e).lower() or "close" in str(e).lower() or "1011" in str(e).lower():
                        await self.disconnect()
                        break
                await asyncio.sleep(0.1)

    async def receive_loop(self):
        if not self.session:
            return
            
        while self.running and self.session:
            try:
                async for response in self.session.receive():
                    if not self.running:
                        break
                    
                    server_content = response.server_content
                    if server_content:
                        if server_content.interrupted:
                            self.logger("[yellow][User Interrupted AI generation][/yellow]")
                            self._append_log("System", "User Interrupted AI generation.")
                            self.audio.clear_speaker_queue()
                        
                        if server_content.input_transcription:
                            text = server_content.input_transcription.text
                            self.logger(f"[bold white]You:[/bold white] {text}")
                            self._append_log("User", text)
                            self.chat_history.append(f"User: {text}")
                        
                        if server_content.output_transcription:
                            text = server_content.output_transcription.text
                            self.logger(f"[bold blue]Omni:[/bold blue] {text}")
                            self._append_log("Omni", text)
                            self.chat_history.append(f"OmniGemini: {text}")

                        model_turn = server_content.model_turn
                        if model_turn:
                            for part in model_turn.parts:
                                if part.inline_data and isinstance(part.inline_data.data, bytes):
                                    self.audio.speaker_queue.put_nowait(part.inline_data.data)

                    if response.tool_call:
                        func_responses = []
                        frames_to_send = []
                        for fc in response.tool_call.function_calls:
                            args = fc.args
                            
                            if fc.name == "run_powershell":
                                cmd = args.get("command") if isinstance(args, dict) else getattr(args, "command", str(args))
                                self.logger(f"[bold cyan]Tool:[/bold cyan] run_powershell\n[dim]Command: {cmd}[/dim]")
                                self._append_log("Tool Call", f"run_powershell: {cmd}")
                                
                                robust_cmd = f"Try {{ {cmd} }} Catch {{ Write-Error $_.Exception.Message }}"
                                try:
                                    process = await asyncio.create_subprocess_shell(
                                        f"powershell.exe -NoProfile -ExecutionPolicy Bypass -Command \"{robust_cmd}\"",
                                        stdout=asyncio.subprocess.PIPE,
                                        stderr=asyncio.subprocess.PIPE
                                    )
                                    stdout, stderr = await process.communicate()
                                    out = (stdout + stderr).decode('utf-8', errors='replace')
                                    if not out.strip(): out = "Success (No output)."
                                    self.logger(f"[green]Result:[/green] {out[:500]}...")
                                except Exception as e:
                                    out = f"Error: {e}"
                                    self.logger(f"[red]Result:[/red] {out}")
                                    
                            elif fc.name == "delegate_gemini":
                                prompt = args.get("prompt") if isinstance(args, dict) else getattr(args, "prompt", str(args))
                                model_choice = args.get("model", "gemini-3.1-flash-preview") if isinstance(args, dict) else getattr(args, "model", "gemini-3.1-flash-preview")
                                
                                # Add non-interactive safety constraint to the prompt
                                prompt += "\n\nCRITICAL CONSTRAINTS FOR YOU (THE BACKGROUND AGENT): You are running headlessly in YOLO mode. DO NOT use interactive shell commands that wait for input (e.g., vim, ssh, or interactive node/python scripts). NEVER stall by opening a shell you don't act upon. Use non-interactive flags."
                                
                                if "pro" in model_choice.lower():
                                    actual_model = "gemini-3.1-pro-preview"
                                else:
                                    actual_model = "gemini-2.5-flash"
                                
                                task_id = f"task_{int(datetime.now().timestamp())}"
                                
                                # Start the background task without blocking the receive loop
                                asyncio.create_task(self._run_background_cli(task_id, actual_model, prompt))
                                
                                out = f"Background task {task_id} started successfully. You MUST now continue conversing with the user while it runs. Tell them you are working on it and explain what's happening technically. Do not wait in silence."
                                self.logger(f"[bold magenta]Tool:[/bold magenta] delegate_gemini\n[dim]Model: {actual_model}\nPrompt: {prompt}\nStatus: Pushed to background.[/dim]")
                                self._append_log("Tool Call", f"delegate_gemini [{actual_model}]: {prompt}")
                                    
                            elif fc.name == "capture_screen":
                                monitor_idx = args.get("monitor_index", 0) if isinstance(args, dict) else getattr(args, "monitor_index", 0)
                                self.logger(f"[bold cyan]Tool:[/bold cyan] capture_screen (monitor {monitor_idx})")
                                self._append_log("Tool Call", f"capture_screen (monitor {monitor_idx})")
                                frames_to_send.append(("screen", monitor_idx))
                                out = f"Screen {monitor_idx} captured successfully. The image will be sent to your visual context immediately after this response."
                                
                            elif fc.name == "capture_webcam":
                                self.logger("[bold cyan]Tool:[/bold cyan] capture_webcam")
                                self._append_log("Tool Call", "capture_webcam")
                                frames_to_send.append(("webcam", 0))
                                out = "Webcam captured successfully. The image will be sent to your visual context immediately after this response."
                                    
                            out = out[:10000] + "\n... (truncated)" if len(out) > 10000 else out
                            self._append_log("Tool Result", out)
                            func_responses.append(types.FunctionResponse(id=fc.id, name=fc.name, response={"result": out}))
                            
                        if func_responses:
                            if self.session and self.running:
                                try:
                                    self.logger("[dim]Sending tool result back to Live API...[/dim]")
                                    await self.session.send_tool_response(function_responses=func_responses)
                                    
                                    for source, monitor_idx in frames_to_send:
                                        await self.send_vision_frame(source, monitor_index=monitor_idx, silent=True, force=True)
                                except Exception as e:
                                    self.logger(f"[red]Failed to send tool response or frame: {e}[/red]")
                
                await asyncio.sleep(0.1)
                    
            except Exception as e:
                if self.running:
                    self.logger(f"[red]Connection lost: {e}[/red]")
                break
                
        if self.running:
            await self.disconnect()

    async def send_text(self, text):
        if not self.session:
            self.logger("[yellow]Cannot send text: Not connected.[/yellow]")
            return
            
        self.logger(f"[bold white]You (Text):[/bold white] {text}")
        self._append_log("User (Text)", text)
        self.chat_history.append(f"User: {text}")
        try:
            await self.session.send(input=text, end_of_turn=True)
        except Exception as e:
            self.logger(f"[red]Failed to send text: {e}[/red]")

    async def send_vision_frame(self, source="webcam", monitor_index=0, silent=False, force=False):
        if not self.session:
            if not silent:
                self.logger("[yellow]Cannot send frame: Not connected.[/yellow]")
            return
            
        frame_bytes = None
        if source == "webcam":
            await asyncio.to_thread(self.vision.start_camera)
            frame_bytes = await asyncio.to_thread(self.vision.get_camera_frame_bytes, force)
        elif source == "screen":
            frame_bytes = await asyncio.to_thread(self.vision.get_screen_frame_bytes, monitor_index, force)
            
        if frame_bytes:
            if self.on_frame_captured:
                self.on_frame_captured(frame_bytes)
                
            latest_frame_path = os.path.abspath(os.path.join("logs", f"latest_{source}.jpg"))
            try:
                with open(latest_frame_path, "wb") as f:
                    f.write(frame_bytes)
            except Exception:
                pass

            if not silent:
                self.logger(f"[bold blue]Sending {source.capitalize()} frame[/bold blue] ({len(frame_bytes)} bytes) as context...")
            self._append_log("Vision", f"Sent {source} frame context.")
            try:
                part = types.Part.from_bytes(data=frame_bytes, mime_type="image/jpeg")
                await self.session.send(input=part, end_of_turn=True)
                if not silent:
                    self.logger("[green]Frame sent successfully.[/green]")
            except Exception as e:
                if not silent:
                    self.logger(f"[red]Failed to send frame: {e}[/red]")
        else:
            if not silent:
                # self.logger(f"[dim]Frame from {source} skipped (no significant change or capture failed).[/dim]")
                pass
