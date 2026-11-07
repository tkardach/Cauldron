import numpy as np

from cauldron.core.led_strip import LedStrip


class LiveBrightnessAnalyzer:
    """Analyze live audio chunks and drive an LED strip's brightness.

    The ``process`` signature follows Pedalboard's audio processor convention.
    It is called by ``RealtimeAudioPlayer`` for captured chunks because
    Pedalboard's native ``Plugin`` type cannot be subclassed in Python.
    """

    def __init__(self, strip: LedStrip):
        self._strip = strip

    def process(
        self,
        input_array: np.ndarray,
        sample_rate: float,
        buffer_size: int = 8192,
        reset: bool = False,
    ) -> np.ndarray:
        """Set brightness to the chunk RMS and return the input unchanged."""
        del sample_rate, buffer_size, reset
        audio = np.asarray(input_array)
        if audio.size == 0:
            brightness = 0.0
        else:
            finite_audio = np.nan_to_num(audio, nan=0.0, posinf=1.0, neginf=-1.0)
            rms = float(np.sqrt(np.mean(np.square(finite_audio, dtype=np.float64))))
            brightness = float(np.clip(rms, 0.0, 1.0))
        self._strip.brightness = brightness
        self._strip.show()
        return input_array
