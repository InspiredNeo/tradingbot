import subprocess
import time
import webview
import atexit
import os


streamlit_process = subprocess.Popen(
    [
         "streamlit", "run",
         os.path.expanduser("~/tradingbot/dashboard/app.py"),
         "--server.headless=true",
         "--server.port=8501",
         "--browser.gatherUsageStats=false"
    ],
    stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL
)


def cleanup():
    streamlit_process.terminate()
    streamlit_process.wait()
    
    
atexit.register(cleanup)


time.sleep(3)


webview.create_window(
    "Market Terminal",
    "http://localhost:8501",
    width=1400,
    height=900,
    min_size=(900, 600)
)
webview.start()
    


