"""
Configuration constants for the Cauldron project.
"""

from pedalboard import (
    Chorus,
    Reverb,
    PitchShift,
    Distortion,
    Phaser,
    Delay,
    Bitcrush,
    HighpassFilter,
    LowpassFilter,
)

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
## AUDIO_PATH is no longer used; audio files are accessed as a module via cauldron.assets.audio
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
# Set to the OS loopback/capture device to visualize system audio instead.
CAULDRON_INPUT_DEVICE = ""
CAULDRON_OUTPUT_DEVICE = "SRS-XB10"

# Voice configuration: name -> effect chain
VOICES = {
    "demon": {
        "effects": [
            PitchShift(semitones=-6),
            Distortion(drive_db=15),
            Reverb(room_size=0.8, wet_level=0.5),
        ],
    },
    "witch": {
        "effects": [
            PitchShift(semitones=5),
            Phaser(rate_hz=1.5, depth=0.6),
            Reverb(room_size=0.5),
        ],
    },
    "robot": {
        "effects": [
            Bitcrush(bit_depth=6),
            Chorus(rate_hz=20.0, depth=0.8),
        ],
    },
    "alien": {
        "effects": [
            PitchShift(semitones=3),
            Phaser(rate_hz=4.0, depth=0.8),
            Delay(delay_seconds=0.15, feedback=0.5),
        ],
    },
    "chipmunk": {
        "effects": [
            PitchShift(semitones=12),
            HighpassFilter(cutoff_frequency_hz=300),
        ],
    },
    "ghosts": {
        "effects": [
            PitchShift(semitones=-3),
            Chorus(rate_hz=0.5, depth=0.8),
            Delay(delay_seconds=0.4, feedback=0.4),
            Reverb(room_size=1.0, wet_level=0.8),
        ],
    },
    "zombie": {
        "effects": [
            PitchShift(semitones=-8),
            Distortion(drive_db=25),
            LowpassFilter(cutoff_frequency_hz=800),
        ],
    },
    "vintage_radio": {
        "effects": [
            HighpassFilter(cutoff_frequency_hz=400),
            LowpassFilter(cutoff_frequency_hz=3000),
            Distortion(drive_db=10),
        ],
    },
    "underwater_monster": {
        "effects": [
            PitchShift(semitones=-4),
            Chorus(rate_hz=3.0, depth=0.9),
            LowpassFilter(cutoff_frequency_hz=1200),
        ],
    },
    "cyborg_villain": {
        "effects": [
            PitchShift(semitones=-5),
            Bitcrush(bit_depth=4),
            Chorus(rate_hz=15.0, depth=1.0),
            Reverb(room_size=0.3),
        ]
    },
    "goblin": {
        "effects": [
            PitchShift(semitones=6),
            Distortion(drive_db=8),
            HighpassFilter(cutoff_frequency_hz=400),
        ],
    },
    "giant_troll": {
        "effects": [
            PitchShift(semitones=-10),
            LowpassFilter(cutoff_frequency_hz=600),
            Reverb(room_size=0.9, wet_level=0.6),
        ],
    },
    "fungal_spore_monster": {
        "effects": [
            PitchShift(semitones=-2),
            Chorus(rate_hz=6.0, depth=0.8),
            LowpassFilter(cutoff_frequency_hz=1000),
            Delay(delay_seconds=0.08, feedback=0.6),
        ],
    },
    "haunted_doll": {
        "effects": [
            PitchShift(semitones=4),
            HighpassFilter(cutoff_frequency_hz=800),
            Chorus(rate_hz=0.2, depth=1.0),
            Delay(delay_seconds=0.2, feedback=0.3),
        ],
    },
    "stadium_intercom": {
        "effects": [
            HighpassFilter(cutoff_frequency_hz=500),
            LowpassFilter(cutoff_frequency_hz=2500),
            Delay(delay_seconds=0.6, feedback=0.5),
            Reverb(room_size=0.8, wet_level=0.4),
        ],
    },
    "vr_glitch": {
        "effects": [
            Bitcrush(bit_depth=3),
            Phaser(rate_hz=10.0, depth=0.9),
            Delay(delay_seconds=0.05, feedback=0.8),
        ],
    },
}
