from cauldron import Cauldron, CauldronSounds
from flask import Flask, request, jsonify
from led_strip import UdpStreamStrip
import config


app = Flask(__name__)


# Configurable for deployment
cauldron: Cauldron = None
NUM_PIXELS = getattr(config, "NUM_PIXELS", 50)
HOST = getattr(config, "LED_HOST", "192.168.0.4")
PORT = getattr(config, "LED_PORT", 5456)
strip = UdpStreamStrip(NUM_PIXELS, HOST, PORT, 0.2)


@app.route("/health")
def health():
    return jsonify({"status": "ok"})


@app.route("/effect/cauldron/play", methods=["POST"])
def cauldron_effect_start():
    global cauldron
    if cauldron is None:
        cauldron = Cauldron(strip)
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


# Play a specific sound by enum name or index
@app.route("/effect/cauldron/play_sound", methods=["POST"])
def cauldron_play_sound():
    global cauldron
    if cauldron is None:
        return jsonify({"error": "Cauldron has not been started"}), 400
    data = request.get_json(force=True)
    sound = data.get("sound")
    try:
        if isinstance(sound, int) or (
            isinstance(sound, str) and sound.isdigit()
        ):
            sound_enum = CauldronSounds(int(sound))
        else:
            sound_enum = CauldronSounds[sound]
    except Exception:
        return jsonify({"error": f"Invalid sound: {sound}"}), 400
    cauldron.play_sound(sound_enum)
    return jsonify({"result": "success"})


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


# List available voices and sounds
@app.route("/effect/cauldron/voices", methods=["GET"])
def cauldron_list_voices():
    return jsonify({"voices": list(config.VOICES.keys())})


@app.route("/effect/cauldron/sounds", methods=["GET"])
def cauldron_list_sounds():
    return jsonify({"sounds": [e.name for e in CauldronSounds]})
