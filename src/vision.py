import cv2
import mss
import numpy as np

class VisionController:
    def __init__(self, config):
        self.config = config
        self.cap = None
        self.sct = mss.mss()

    def start_camera(self):
        if self.cap is None:
            idx = int(self.config.get("camera_index", 0))
            self.cap = cv2.VideoCapture(idx)

    def stop_camera(self):
        if self.cap:
            self.cap.release()
            self.cap = None

    def get_camera_frame_bytes(self):
        if not self.cap or not self.cap.isOpened():
            return None
        ret, frame = self.cap.read()
        if not ret:
            return None
        
        # Resize to save bandwidth / tokens (Max recommended is 640x480 for streaming)
        frame = cv2.resize(frame, (640, 480))
        ret, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
        if ret:
            return buffer.tobytes()
        return None

    def get_screen_frame_bytes(self, monitor_index=0):
        try:
            # mss monitors[0] is all screens combined. [1] is primary, etc.
            if monitor_index >= len(self.sct.monitors) or monitor_index < 0:
                monitor_index = 0
                
            monitor = self.sct.monitors[monitor_index]
            sct_img = self.sct.grab(monitor)
            
            # Convert mss image to numpy array
            img = np.array(sct_img)
            
            # Drop alpha channel
            img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
            
            # Resize for bandwidth constraints (maintaining roughly 720p scale)
            img = cv2.resize(img, (1280, 720))
            ret, buffer = cv2.imencode('.jpg', img, [cv2.IMWRITE_JPEG_QUALITY, 80])
            if ret:
                return buffer.tobytes()
        except Exception:
            pass
        return None
