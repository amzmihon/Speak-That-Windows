"""Entry point for SpeakThat Windows Text Reader."""

import sys
import os
import time

# Add local directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def setup_debug_logging():
    """Redirects stdout and stderr to a persistent log file for diagnostics."""
    try:
        log_dir = os.path.join(os.environ.get("LOCALAPPDATA", "."), "Programs", "SpeakThat")
        os.makedirs(log_dir, exist_ok=True)
        log_file = os.path.join(log_dir, "speakthat_debug.log")

        class MultiWriter:
            def __init__(self, filename):
                self.f = open(filename, "a", encoding="utf-8", buffering=1)
                self.term = sys.__stdout__

            def write(self, s):
                try:
                    self.f.write(s)
                    self.f.flush()
                except Exception:
                    pass
                try:
                    if self.term:
                        self.term.write(s)
                except Exception:
                    pass

            def flush(self):
                try:
                    self.f.flush()
                except Exception:
                    pass
                try:
                    if self.term:
                        self.term.flush()
                except Exception:
                    pass

        writer = MultiWriter(log_file)
        sys.stdout = writer
        sys.stderr = writer
        print(f"\n=======================================================", flush=True)
        print(f"[*] SpeakThat session started at {time.strftime('%Y-%m-%d %H:%M:%S')}", flush=True)
    except Exception:
        pass


from speak_that.app import SpeakThatApp, notify_existing_instance

def main():
    setup_debug_logging()

    # If SpeakThat is already running, activate the existing window and exit
    if notify_existing_instance():
        print("[+] SpeakThat is already running. Existing window activated.", flush=True)
        return

    app = SpeakThatApp()
    app.start()

if __name__ == "__main__":
    main()

