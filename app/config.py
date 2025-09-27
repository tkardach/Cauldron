"""
Configuration constants for the Cauldron project.
"""

from pedalboard import Reverb, PitchShift, Distortion, Compressor

AUDIO_BUBBLING = "bubbles.wav"
AUDIO_EXPLOSION = "poof.wav"
AUDIO_SOUNDBITES = [
    "witch0.wav",
    "witch1.wav",
    "witch_closer.wav",
    "evie.wav",
    "porter.wav",
    "creepy_laugh0.wav",
    "harry.wav",
]
AUDIO_PATH = "app/files/audio/"
BUBBLE_LENGTHS = [7, 9, 11]
BUBBLE_POP_SPEEDS = [3000, 4000, 5000]
BUBBLE_PROB_WEIGHTS = [0.5, 0.25, 0.25]
BUBBLE_SPAWN_PROB = 0.05
CAULDRON_COLORS = [
    ([32, 139, 25], [215, 232, 23]),
    ([142, 75, 166], [237, 114, 178]),
    ([255, 179, 0], [255, 0, 60]),
    ([235, 57, 21], [76, 172, 194]),
]
MAX_BUBBLES = 10
FRAME_SPEED_MS = 33
CAULDRON_INPUT_DEVICE = "Built-in Microphone"
CAULDRON_OUTPUT_DEVICE = "SRS-XB10"

# Voice configuration: name -> effect chain
VOICES = {
    "demon": {
        "effects": [
            Reverb(),
            PitchShift(-4),
        ],
    },
    "witch": {
        "effects": [
            Reverb(),
            PitchShift(3),
        ],
    },
    "robot": {
        "effects": [
            Reverb(),
            PitchShift(3),
        ],
    },
    "alien": {
        "effects": [
            Reverb(),
            PitchShift(-12),
        ],
    },
    "chipmunk": {
        "effects": [
            PitchShift(8),
        ],
    },
    "donald duck": {
        "effects": [PitchShift(semitones=7), Distortion(drive_db=5)],
    },
    "mickey mouse": {
        "effects": [PitchShift(semitones=9), Compressor()],
    },
}
