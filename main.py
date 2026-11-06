"""Entry point for SpeakThat Windows Text Reader."""

import sys
import os

# Add local directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from speak_that.app import SpeakThatApp

def main():
    app = SpeakThatApp()
    app.start()

if __name__ == "__main__":
    main()

