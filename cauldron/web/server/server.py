from cauldron.core.cauldron import Cauldron
from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_socketio import SocketIO, emit
from cauldron.core.led_strip import UdpStreamStrip
import cauldron.config.config as config
import queue

app = Flask(__name__)
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

# Configurable for deployment
cauldron: Cauldron = None
NUM_PIXELS = getattr(config, "NUM_PIXELS", 50)
HOST = getattr(config, "LED_HOST", "192.168.0.4")
PORT = getattr(config, "LED_PORT", 5456)
strip = UdpStreamStrip(NUM_PIXELS, HOST, PORT, 0.2)
INPUT = getattr(config, "CAULDRON_INPUT_DEVICE", "")
OUTPUT = getattr(config, "CAULDRON_OUTPUT_DEVICE", "")
cauldron = Cauldron(strip, INPUT, OUTPUT)
audio_queue = queue.Queue(maxsize=20)


@app.route("/health")
def health():
    return jsonify({"status": "ok"})


@app.route("/effect/cauldron/play", methods=["POST"])
def cauldron_effect_start():
    global cauldron
    if cauldron is None:
        cauldron = Cauldron(strip, INPUT, OUTPUT)
    cauldron.start()
    return jsonify({"result": "success"})


@app.route("/effect/cauldron/stop", methods=["POST"])
def cauldron_effect_stop():
    global cauldron
    if cauldron is None:
        return jsonify({"result": "success"})
    cauldron.stop()
    return jsonify({"result": "success"})


@app.route("/effect/cauldron/explode", methods=["POST"])
def cauldron_effect_explode():
    global cauldron
    if cauldron is None:
        return jsonify({"error": "Cauldron has not been started"}), 400
    cauldron.cause_explosion()
    return jsonify({"result": "success"})


# Play a random voice
@app.route("/effect/cauldron/play_random_voice", methods=["POST"])
def cauldron_play_random_voice():
    global cauldron
    if cauldron is None:
        return jsonify({"error": "Cauldron has not been started"}), 400
    cauldron.play_random_voice()
    return jsonify({"result": "success"})


# Play a specific sound by name or index from AUDIO_SOUNDBITES
@app.route("/effect/cauldron/play_sound", methods=["POST"])
def cauldron_play_sound():
    global cauldron
    if cauldron is None:
        return jsonify({"error": "Cauldron has not been started"}), 400
    data = request.get_json(force=True)
    sound = data.get("sound")
    soundbites = config.AUDIO_SOUNDBITES
    idx = None
    # Accept index (int or str) or filename
    if isinstance(sound, int) or (isinstance(sound, str) and sound.isdigit()):
        idx = int(sound)
        if 0 <= idx < len(soundbites):
            cauldron.play_sound(idx)  # +1 for legacy offset
            return jsonify({"result": "success"})
        else:
            return jsonify({"error": f"Invalid sound index: {sound}"}), 400
    elif isinstance(sound, str) and sound in soundbites:
        idx = soundbites.index(sound)
        cauldron.play_sound(idx)
        return jsonify({"result": "success"})
    else:
        return jsonify({"error": f"Invalid sound: {sound}"}), 400


# Start a realtime voice by name
@app.route("/effect/cauldron/start_voice", methods=["POST"])
def cauldron_start_voice():
    global cauldron
    if cauldron is None:
        return jsonify({"error": "Cauldron has not been started"}), 400
    data = request.get_json(force=True)
    voice_name = data.get("voice_name")
    if not voice_name:
        return jsonify({"error": "Missing voice_name"}), 400
    cauldron.start_voice(voice_name)
    return jsonify({"result": "success"})


# Stop the active realtime voice
@app.route("/effect/cauldron/stop_voice", methods=["POST"])
def cauldron_stop_voice():
    global cauldron
    if cauldron is None:
        return jsonify({"error": "Cauldron has not been started"}), 400
    cauldron.stop_active_voice()
    return jsonify({"result": "success"})


# List available voices
@app.route("/effect/cauldron/voices", methods=["GET"])
def cauldron_list_voices():
    return jsonify({"voices": list(config.VOICES.keys())})


# List available soundbites
@app.route("/effect/cauldron/sounds", methods=["GET"])
def cauldron_list_sounds():
    return jsonify({"sounds": list(config.AUDIO_SOUNDBITES)})


# --- WebSocket for voice streaming ---
import threading
import numpy as np


@socketio.on("voice_stream")
def handle_voice_stream(data):
    """
    Receives binary audio data from the client and puts it in a queue for playback.
    The client should send raw PCM or WAV bytes in small chunks.
    """
    try:
        if audio_queue.full():
            audio_queue.get_nowait()  # Drop oldest if full
        audio_queue.put_nowait(data)
    except Exception as e:
        emit("error", {"error": str(e)})


def audio_stream_worker():
    """
    Continuously read from the audio_queue and play through the Cauldron's realtime voice system.
    """
    import simpleaudio as sa

    while True:
        try:
            chunk = audio_queue.get()
            # Assume 16-bit PCM, 1 channel, 44100 Hz
            audio = np.frombuffer(chunk, dtype=np.int16)
            play_obj = sa.play_buffer(audio, 1, 2, 44100)
            play_obj.wait_done()
        except Exception as e:
            print(f"Audio stream error: {e}")


# Start the audio stream worker in a background thread
audio_thread = threading.Thread(target=audio_stream_worker, daemon=True)
audio_thread.start()

if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000)
