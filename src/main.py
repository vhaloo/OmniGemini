import sys
import asyncio
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from qasync import QEventLoop
from src.config import load_config
from src.agent import OmniAgent
from src.gui import MainWindow

def run():
    # Enable High DPI scaling for 4K and Full HD screens
    QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    
    app = QApplication(sys.argv)
    loop = QEventLoop(app)
    asyncio.set_event_loop(loop)
    
    config = load_config()
    
    # We define a dummy logger before GUI is loaded, though GUI overrides it immediately
    agent = OmniAgent(config, print)
    window = MainWindow(agent)
    window.show()
    
    with loop:
        loop.run_forever()

if __name__ == "__main__":
    run()
