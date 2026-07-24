"""
Launch the Dash Market Terminal in a native desktop window.
"""
import threading
import time
import webview
from dash_app import app

def run_dash():
    app.run(debug=False, port=8050)

if __name__ == "__main__":
    # Start Dash in background thread
    t = threading.Thread(target=run_dash, daemon=True)
    t.start()
    
    # Wait for server to start
    time.sleep(2)
    
    # Open in native window
    webview.create_window(
        "Market Terminal",
        "http://127.0.0.1:8050",
        width=1400,
        height=900,
        resizable=True,
    )
    webview.start()
