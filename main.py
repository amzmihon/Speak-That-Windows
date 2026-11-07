"""Entry point for SpeakThat Windows Text Reader."""

import sys
import os

# Add local directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from speak_that.app import SpeakThatApp, notify_existing_instance

def main():
    # If SpeakThat is already running, activate the existing window and exit
    if notify_existing_instance():
        print("[+] SpeakThat is already running. Existing window activated.")
        return

    app = SpeakThatApp()
    app.start()

if __name__ == "__main__":
    main()

