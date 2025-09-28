# This module exposes audio files as importable resources for the Cauldron project.
# Usage: import cauldron.assets.audio as audio; audio.get_path('bubbles.wav')
import importlib.resources
import pathlib

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
    if filename not in AUDIO_FILES:
        raise ValueError(f"Audio file '{filename}' not found in assets.")
    # Use importlib.resources to get the file path
    with importlib.resources.path(__package__, filename) as p:
        return str(p)
