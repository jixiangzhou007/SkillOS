"""SkillOS Desktop Application — pywebview-based native window.

Architecture:
  - Backend: FastAPI server runs in a background thread
  - Frontend: HTML/CSS/JS loaded in pywebview window
  - Communication: Frontend calls API via localhost:8765

Hermes integration:
  - Hermes Agent provides the desktop shell and execution runtime
  - SkillOS provides the knowledge pipeline and marketplace
  - Skills are stored in agentskills.io format for interoperability
"""

import logging
import threading

_log = logging.getLogger(__name__)


def start_backend(host: str = "127.0.0.1", port: int = 8765):
    """Start the FastAPI backend in a background thread."""
    from skillos.api.server import start
    t = threading.Thread(target=start, args=(host, port), daemon=True)
    t.start()
    return t


def start_desktop(host: str = "127.0.0.1", port: int = 8765):
    """Start the desktop application."""
    import webview

    # Start backend
    backend_thread = start_backend(host, port)

    # Create window
    window = webview.create_window(
        title="SkillOS — AI Skill Operating System",
        url=f"http://{host}:{port}",
        width=1400,
        height=900,
        min_size=(900, 600),
        confirm_close=True,
    )

    webview.start(debug=True)
    _log.info("Desktop app closed")


def main():
    """Entry point: `skillos` command."""
    import argparse
    parser = argparse.ArgumentParser(description="SkillOS — AI Skill Operating System")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--server-only", action="store_true", help="Run API server only (no GUI)")
    args = parser.parse_args()

    if args.server_only:
        from skillos.api.server import start
        start(args.host, args.port)
    else:
        start_desktop(args.host, args.port)


if __name__ == "__main__":
    main()
