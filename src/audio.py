import asyncio
import sounddevice as sd
import numpy as np

SEND_SAMPLE_RATE = 16000
RECEIVE_SAMPLE_RATE = 24000
CHUNK_SIZE = 1024

class AudioController:
    def __init__(self, config):
        self.config = config
        self.mic_queue = asyncio.Queue(maxsize=50)
        self.speaker_queue = asyncio.Queue()
        self.stream_in = None
        self.stream_out = None
        self.running = False
        self.loudness_threshold = int(self.config.get("loudness_threshold", 8000))
        self.on_volume_changed = None 
        self.is_playing = False

    def start(self):
        self.running = True
        in_dev = self.config.get("input_device")
        out_dev = self.config.get("output_device")
        
        self.stream_in = sd.RawInputStream(
            samplerate=SEND_SAMPLE_RATE, channels=1, dtype='int16', blocksize=CHUNK_SIZE,
            device=in_dev if in_dev is not None else None
        )
        self.stream_out = sd.RawOutputStream(
            samplerate=RECEIVE_SAMPLE_RATE, channels=1, dtype='int16',
            device=out_dev if out_dev is not None else None
        )
        self.stream_in.start()
        self.stream_out.start()

    def stop(self):
        self.running = False
        if self.stream_in:
            try:
                self.stream_in.stop()
                self.stream_in.close()
            except Exception: pass
            self.stream_in = None
        if self.stream_out:
            try:
                self.stream_out.stop()
                self.stream_out.close()
            except Exception: pass
            self.stream_out = None

    async def mic_loop(self):
        while self.running and self.stream_in:
            try:
                data, overflowed = await asyncio.to_thread(self.stream_in.read, CHUNK_SIZE)
                
                audio_array = np.frombuffer(data, dtype=np.int16)
                if audio_array.size > 0:
                    mean_sq = np.mean(audio_array.astype(np.float32)**2)
                    amplitude = np.sqrt(max(0, mean_sq))
                else:
                    amplitude = 0
                
                if self.on_volume_changed:
                    self.on_volume_changed(int(amplitude))
                
                if self.is_playing and self.config.get("ducking_enabled", True):
                    # Hard Ducking: Send pure silence to prevent echo but keep stream alive
                    send_data = bytes(bytearray(len(data))) 
                else:
                    # Open Mic: Send actual audio
                    send_data = bytes(data)

                self.mic_queue.put_nowait({"data": send_data, "mime_type": "audio/pcm;rate=16000"})
            except asyncio.QueueFull:
                pass
            except Exception:
                await asyncio.sleep(0.01)

    async def speaker_loop(self):
        while self.running and self.stream_out:
            try:
                bytestream = await asyncio.wait_for(self.speaker_queue.get(), timeout=0.1)
                self.is_playing = True
                await asyncio.to_thread(self.stream_out.write, bytestream)
            except asyncio.TimeoutError:
                if self.is_playing:
                    # Add a padding before releasing the ducking to avoid trailing echo
                    await asyncio.sleep(0.3)
                    if self.speaker_queue.empty():
                        self.is_playing = False
            except Exception:
                self.is_playing = False
                await asyncio.sleep(0.01)

    def clear_speaker_queue(self):
        while not self.speaker_queue.empty():
            try:
                self.speaker_queue.get_nowait()
            except Exception:
                break
