import cv2
import mss
import numpy as np
import time

class VisionController:
    def __init__(self, config):
        self.config = config
        self.cap = None
        self.sct = mss.mss()
        self.last_cam_frame = None
        self.last_screen_frame = None
        self.cam_last_time = 0
        self.screen_last_time = 0

    def start_camera(self):
        if self.cap is None:
            idx = int(self.config.get("camera_index", 0))
            self.cap = cv2.VideoCapture(idx)

    def stop_camera(self):
        if self.cap:
            self.cap.release()
            self.cap = None

    def get_camera_frame_bytes(self, force=False):
        if not self.cap or not self.cap.isOpened():
            return None
        ret, frame = self.cap.read()
        if not ret:
            return None
        
        frame = cv2.resize(frame, (640, 480))
        
        # Simple delta detection
        now = time.time()
        if not force and self.last_cam_frame is not None and (now - self.cam_last_time) < 10.0:
            diff = cv2.absdiff(frame, self.last_cam_frame)
            if np.mean(diff) < 2.0:
                return None # No significant change

        self.last_cam_frame = frame.copy()
        self.cam_last_time = now

        ret, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
        if ret:
            return buffer.tobytes()
        return None

    def get_screen_frame_bytes(self, monitor_index=0, force=False):
        try:
            if monitor_index >= len(self.sct.monitors) or monitor_index < 0:
                monitor_index = 0
                
            monitor = self.sct.monitors[monitor_index]
            sct_img = self.sct.grab(monitor)
            
            img = np.array(sct_img)
            img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
            img = cv2.resize(img, (1280, 720))
            
            now = time.time()
            if not force and self.last_screen_frame is not None and (now - self.screen_last_time) < 10.0:
                diff = cv2.absdiff(img, self.last_screen_frame)
                if np.mean(diff) < 1.0:
                    return None # No significant change

            self.last_screen_frame = img.copy()
            self.screen_last_time = now

            ret, buffer = cv2.imencode('.jpg', img, [cv2.IMWRITE_JPEG_QUALITY, 80])
            if ret:
                return buffer.tobytes()
        except Exception:
            pass
        return None
