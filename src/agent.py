import asyncio
import subprocess
import os
from datetime import datetime
from google import genai
from google.genai import types
from src.audio import AudioController
from src.vision import VisionController

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
                    "model": {"type": "STRING", "description": "Choose 'gemini-2.5-pro' for complex reasoning/coding/MCPs, or 'gemini-2.5-flash' for simple tasks.", "enum": ["gemini-2.5-pro", "gemini-2.5-flash"]}
                },
                "required": ["prompt", "model"]
            }
        }
        
        self.base_instruction = (
            "You are OmniGemini, the ultimate Live Desktop Assistant. "
            "You have direct access to the user's system via two tools:\n"
            "1. 'run_powershell': For immediate, tiny system checks.\n"
            "2. 'delegate_gemini': The heavy lifter. The Gemini CLI has all the Model Context Protocol (MCP) servers, full file system access, and system mastery. "
            "IMPORTANT: If the user asks you to modify files, write code, browse the web, or do anything complex, YOU MUST use 'delegate_gemini' and select the appropriate model. "
            "Be friendly, conversational, and highly capable. "
            "You can also see the user's screen and webcam if they explicitly push a frame to you."
        )
        self.steering_prompt = ""
        self.on_frame_captured = None 
        self.on_disconnect = None # Callback for GUI to reset state

    def _get_current_instruction(self):
        instr = self.base_instruction
        if self.steering_prompt:
            instr += f"\n\nUSER STEERING DIRECTIVES:\n{self.steering_prompt}"
        return instr

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

    async def connect(self):
        api_key = self.config.get("api_key")
        if not api_key:
            self.logger("[bold red]ERROR:[/bold red] API Key is missing. Click Settings to add it.")
            return False
            
        self._init_log()
        self.client = genai.Client(api_key=api_key)
        tools = [{"function_declarations": [self.run_powershell, self.delegate_gemini]}]
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
                    # Termination error?
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
                            # Do NOT 'continue'. Let tools execute if they were part of the payload.
                        
                        if server_content.input_transcription:
                            text = server_content.input_transcription.text
                            self.logger(f"[bold white]You:[/bold white] {text}")
                            self._append_log("User", text)
                        
                        if server_content.output_transcription:
                            text = server_content.output_transcription.text
                            self.logger(f"[bold blue]Omni:[/bold blue] {text}")
                            self._append_log("Omni", text)

                        model_turn = server_content.model_turn
                        if model_turn:
                            for part in model_turn.parts:
                                if part.inline_data and isinstance(part.inline_data.data, bytes):
                                    self.audio.speaker_queue.put_nowait(part.inline_data.data)

                    if response.tool_call:
                        func_responses = []
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
                                model_choice = args.get("model", "gemini-2.5-pro") if isinstance(args, dict) else getattr(args, "model", "gemini-2.5-pro")
                                
                                self.logger(f"[bold magenta]Tool:[/bold magenta] delegate_gemini\n[dim]Model: {model_choice}\nPrompt: {prompt}[/dim]")
                                self._append_log("Tool Call", f"delegate_gemini [{model_choice}]: {prompt}")
                                
                                cli_path = self.config.get("gemini_cli_path", "gemini")
                                try:
                                    self.logger(f"[dim]Gemini CLI is running synchronously with {model_choice}...[/dim]")
                                    process = await asyncio.create_subprocess_shell(
                                        f'"{cli_path}" --yolo --model "{model_choice}" "{prompt}"',
                                        stdout=asyncio.subprocess.PIPE,
                                        stderr=asyncio.subprocess.PIPE
                                    )
                                    stdout, stderr = await process.communicate()
                                    out = (stdout + stderr).decode('utf-8', errors='replace')
                                    self.logger(f"[green]Gemini CLI Finished.[/green] Output length: {len(out)} chars.")
                                except Exception as e:
                                    out = f"Failed to run Gemini CLI: {e}"
                                    self.logger(f"[red]{out}[/red]")
                                    
                            out = out[:2000] + "\n... (truncated)" if len(out) > 2000 else out
                            self._append_log("Tool Result", out)
                            func_responses.append(types.FunctionResponse(id=fc.id, name=fc.name, response={"result": out}))
                            
                        if func_responses:
                            if self.session and self.running:
                                try:
                                    self.logger("[dim]Sending tool result back to Live API...[/dim]")
                                    await self.session.send_tool_response(function_responses=func_responses)
                                except Exception as e:
                                    self.logger(f"[red]Failed to send tool response: {e}[/red]")
                
                # Async loop exit naturally
                await asyncio.sleep(0.1)
                    
            except Exception as e:
                if self.running:
                    self.logger(f"[red]Connection lost: {e}[/red]")
                break
                
        # Clean shutdown
        if self.running:
            await self.disconnect()

    async def send_text(self, text):
        if not self.session:
            self.logger("[yellow]Cannot send text: Not connected.[/yellow]")
            return
            
        self.logger(f"[bold white]You (Text):[/bold white] {text}")
        self._append_log("User (Text)", text)
        try:
            await self.session.send_client_content(
                turns=[{"role": "user", "parts": [{"text": text}]}],
                turn_complete=True
            )
        except Exception as e:
            self.logger(f"[red]Failed to send text: {e}[/red]")

    async def send_vision_frame(self, source="webcam"):
        if not self.session:
            self.logger("[yellow]Cannot send frame: Not connected.[/yellow]")
            return
            
        frame_bytes = None
        if source == "webcam":
            await asyncio.to_thread(self.vision.start_camera)
            frame_bytes = await asyncio.to_thread(self.vision.get_camera_frame_bytes)
        elif source == "screen":
            frame_bytes = await asyncio.to_thread(self.vision.get_screen_frame_bytes)
            
        if frame_bytes:
            if self.on_frame_captured:
                self.on_frame_captured(frame_bytes)
                
            self.logger(f"[bold blue]Sending {source.capitalize()} frame[/bold blue] ({len(frame_bytes)} bytes) as context...")
            self._append_log("Vision", f"Sent {source} frame context.")
            try:
                await self.session.send_client_content(
                    turns=[{"role": "user", "parts": [{"inline_data": {"mime_type": "image/jpeg", "data": frame_bytes}}]}],
                    turn_complete=True
                )
                self.logger("[green]Frame sent successfully.[/green]")
            except Exception as e:
                self.logger(f"[red]Failed to send frame: {e}[/red]")
        else:
            self.logger(f"[red]Failed to capture from {source}.[/red]")
