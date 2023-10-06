from audio.audio_player import AudioPlayer, PlaybackHandle
from led.led_effect import LedEffect
from led.led_strip import LedStrip
import threading


class AudioVisual:
    def __init__(self, effect: LedEffect, audio: AudioPlayer):
        self._effect = effect
        self._audio = audio
        self._playing = False
        self._lock = threading.Lock()

    def start(self, strip: LedStrip) -> None:
        while self._playing:
            
