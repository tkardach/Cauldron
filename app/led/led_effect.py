import abc
from led.led_strip import LedStrip
import math
import numpy as np
import threading


class LedEffect(abc.ABC):
    def __init__(self):
        self.frame_speed_ms = 10

    @abc.abstractmethod
    def apply_effect(self, strip: LedStrip) -> None:
        return None


class SineWaveEffect(LedEffect):
    """Applies a modifyable sine wave effect onto an LedStrip."""

    def __init__(self, color0: list, color1: list, b: float = 1, oscillate: bool = False,
                 oscillation_speed_ms: int = 250):
        assert len(color0) == len(color1)
        LedEffect.__init__(self)
        self._lock = threading.Lock()
        # Convert colors to numpy arrays
        self._color0 = np.array(color0)
        self._color1 = np.array(color1)
        self.oscillation_speed_ms = oscillation_speed_ms
        self._oscillate = oscillate
        self.wave_length = b

        # Offset the wave so that each color is above or equal to 0
        self._y_offsets = np.abs((self._color0 - self._color1) / 2) + np.minimum(self._color0, self._color1)
        # Keep track of the current amplitude value
        self._amplitudes = np.array([(self._color0 - self._color1) / 2])
        self._current_a = self._amplitudes.copy()
        #
        self._amplitude_inc = (2 * np.pi) / self._oscillation_inc
        self._amplitude_x = 0

    def _update_pixel_values_locked(self, x: np.array) -> np.array:
        """Returns the brightness value (y-value) of the sine wave.

        The sine wave equation is as follows:

        y = new color value
        x = x value for LED
        a = amplitude
        b = wave length

        y = a * sin(b * x)

        If oscillation is on, the value of 'a' will range from "-a -> a" then
        "a -> -a" continuously.
        """
        assert self._lock.locked()
        pixels = np.zeros((len(x), len(self._current_a)))
        pixels = np.cos(self._b * x).T * self._current_a + self._y_offsets
        return pixels

    def _update_oscillation_locked(self):
        """Updates the sine wave variables if oscillation is on.
        
        Oscillation will cause the amplitude of the sine wave to range between
        "a -> -a" then "-a -> a" continuously.
        """
        assert self._lock.locked()
        if not self._oscillate:
            return
        self._amplitude_x += self._amplitude_inc
        self._current_a = self._amplitudes * np.cos(self._amplitude_x)

    def apply_effect(self, strip: LedStrip) -> None:
        """Applies the sine wave effect onto the LedStrip."""
        num_pixels = strip.num_pixels()
        two_pi = np.pi * 2
        x_values = np.array([np.arange(0, two_pi, two_pi / num_pixels)])
        with self._lock:
            pixels = self._update_pixel_values_locked(x_values)
            strip.fill(pixels)
            self._update_oscillation_locked()

        strip.show()

    @property
    def wave_length(self) -> float:
        return self._b
    
    @wave_length.setter
    def wave_length(self, b: float) -> None:
        with self._lock:
            self._b = b

    @property
    def oscillate(self) -> bool:
        return self._oscillate

    @oscillate.setter
    def oscillate(self, enable: bool) -> None:
        with self._lock:
            self.oscillate = enable

    @property
    def oscillation_speed_ms(self) -> int:
        return self._oscillation_speed_ms

    @oscillation_speed_ms.setter
    def oscillation_speed_ms(self, speed_ms: int) -> None:
        with self._lock:
            self._oscillation_speed_ms = speed_ms
            self._oscillation_inc = speed_ms / self.frame_speed_ms
