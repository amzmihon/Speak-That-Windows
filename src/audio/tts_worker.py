"""High-Performance IPC Worker for Paradee 8M TTS Audio Playback."""

import json
import os
import sys

# Ensure repository root is on sys.path
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

# Save IPC stdout and redirect general stdout to stderr to protect JSON IPC protocol
ipc_stdout = sys.stdout
sys.stdout = sys.stderr

try:
    sys.stdin.reconfigure(line_buffering=True)
except Exception:
    pass

from speak_that.engine import TTSEngine

def main():
    engine = TTSEngine(voice="bf_isabella", speed=1.05, volume=1.0)

    def on_status_change(status):
        try:
            ipc_stdout.write(json.dumps({"event": "status", "data": status}) + "\n")
            ipc_stdout.flush()
        except Exception:
            pass

    def on_sentence(sentence):
        try:
            ipc_stdout.write(json.dumps({"event": "sentence", "data": sentence}) + "\n")
            ipc_stdout.flush()
        except Exception:
            pass

    def on_complete():
        try:
            ipc_stdout.write(json.dumps({"event": "complete"}) + "\n")
            ipc_stdout.flush()
        except Exception:
            pass

    engine.on_status_change = on_status_change
    engine.on_sentence = on_sentence
    engine.on_complete = on_complete

    # Wait until engine model is loaded
    while not engine.is_ready():
        import time
        time.sleep(0.05)

    try:
        ipc_stdout.write(json.dumps({"event": "ready", "voices": engine.get_voices()}) + "\n")
        ipc_stdout.flush()
    except Exception:
        pass

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
            cmd = req.get("cmd")

            if cmd == "speak":
                text = req.get("text", "")
                if "voice" in req:
                    engine.set_voice(req["voice"])
                if "speed" in req:
                    engine.set_speed(float(req["speed"]))
                if "volume" in req:
                    engine.set_volume(float(req["volume"]))
                engine.speak(text)
            elif cmd == "stop":
                engine.stop()
            elif cmd == "pause":
                engine.pause()
            elif cmd == "resume":
                engine.resume()
            elif cmd == "set_voice":
                engine.set_voice(req.get("voice", "bf_isabella"))
            elif cmd == "set_speed":
                engine.set_speed(float(req.get("speed", 1.05)))
            elif cmd == "set_volume":
                engine.set_volume(float(req.get("volume", 1.0)))
            elif cmd == "ping":
                ipc_stdout.write(json.dumps({"event": "pong"}) + "\n")
                ipc_stdout.flush()
        except Exception as e:
            try:
                ipc_stdout.write(json.dumps({"event": "error", "error": str(e)}) + "\n")
                ipc_stdout.flush()
            except Exception:
                pass

if __name__ == "__main__":
    main()
    main()
