
"""BrainSprinkles desktop application entry point."""

import threading

import webview
from werkzeug.serving import make_server

from app import app


HOST = "127.0.0.1"


def main():
    # Start Flask using a local WSGI server on an available port.
    server = make_server(HOST, 0, app, threaded=True)

    server_thread = threading.Thread(
        target=server.serve_forever,
        daemon=True
    )
    server_thread.start()

    url = f"http://{HOST}:{server.server_port}"

    print("Starting BrainSprinkles Desktop...")
    print(f"Local application server: {url}")

    # Create the native desktop window.
    webview.create_window(
        title="BrainSprinkles 🌈",
        url=url,
        width=1200,
        height=800,
        min_size=(850, 600)
    )

    try:
        # This runs the native macOS application window.
        webview.start(gui="cocoa")
    finally:
        # When the application window closes, stop Flask.
        print("Closing BrainSprinkles...")
        server.shutdown()
        server.server_close()
        server_thread.join(timeout=3)
        print("BrainSprinkles has shut down.")


if __name__ == "__main__":
    main()
