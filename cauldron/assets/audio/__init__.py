# This module exposes audio files as importable resources for the Cauldron project.
# Usage: import cauldron.assets.audio as audio; audio.get_path('bubbles.wav')

# List of available audio files (update as needed)
AUDIO_FILES = [
    "bubbles.wav",
    "creepy_laugh0.wav",
    "evie.wav",
    "harry.wav",
    "poof.wav",
    "porter.wav",
    "witch0.wav",
    "witch1.wav",
    "witch_closer.wav",
]


def get_path(filename: str) -> str:
    """Return the absolute path to an audio file in this module."""
    from cauldron.assets.manager import AssetManager

    return AssetManager(__package__).get_path(filename)
