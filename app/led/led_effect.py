import abc
from led_strip import LedStrip
import math
import threading


class LedEffect(abc.ABC):
    def __init__(self):
        self.frame_speed_ms = 10

    @abc.abstractmethod
    def apply_effect(self, strip: LedStrip) -> None:
        return None


class SineWaveEffect(LedEffect):
    """Applies a modifyable sine wave effect onto an LedStrip."""

    def __init__(self, a: float = 127, b: float = 1, y_offset: int = 127,
                 oscillate: bool = False, oscillation_speed_ms: int = 250):
        super(LedEffect, self).__init__()
        self.amplitude = a
        self.wave_length = b
        self.y_offset = y_offset
        self.oscillate = oscillate
        self.oscillation_speed_ms = oscillation_speed_ms
    
        self._current_a = -a
        self._oscillating_up = True
        self._lock = threading.Lock()

    def _get_brightness_for_pixel_locked(self, x: int) -> int:
        assert self._lock.locked()
        return self._a * math.sin(self._b * (x)) + self._y_offset

    def _update_oscillation_locked(self):
        assert self._lock.locked()
        if not self._oscillate:
            return
        
        a_inc = (self._a * 2) / self._oscillation_inc
        self._current_a += a_inc if self._oscillating_up else -a_inc
        if self._current_a < -self._a:
            self._current_a = -self._a
            self._oscillating_up = not self._oscillating_up
        elif self._current_a > self._a:
            self._current_a = self._a
            self._oscillation_up = not self._oscillation_up

    def get_brightness_for_pixel(self, x: int):
        """Returns the brightness value (y-value) of the sine wave.

        The sine wave equation is as follows:

        y = brightness
        x = LED
        a = amplitude
        b = wave length
        y_offset = y offset

        y = a * sin(b * x) + y_offset

        If oscillation is on, the value of 'a' will range from "-a -> a" then
        "a -> -a" continuously.
        """
        with self._lock:
            return self._get_brightness_for_pixel_locked(x)

    def update_oscillation(self):
        """Updates the sine wave variables if oscillation is on.
        
        Oscillation will cause the amplitude of the sine wave to range between
        "a -> -a" then "-a -> a" continuously.
        """
        self._update_oscillation_locked()
                
    def apply_effect(self, strip: LedStrip) -> None:
        """Applies the sine wave effect onto the LedStrip."""
        num_pixels = strip.num_pixels()
        increments = math.pi / num_pixels
        with self._lock:
            for pixel in range(0, num_pixels):
                brightness = self._get_brightness_for_pixel_locked(pixel * increments)

        strip.show()

    @property
    def amplitude(self) -> float:
        return self._a
    
    @amplitude.setter
    def amplitude(self, a: float) -> None:
        with self._lock:
            self._a = a

    @property
    def wave_length(self) -> float:
        return self._b
    
    @wave_length.setter
    def wave_length(self, b: float) -> None:
        with self._lock:
            self._b = b

    @property
    def y_offset(self) -> float:
        return self._y_offset
    
    @y_offset.setter
    def y_offset(self, offset: float) -> None:
        with self._lock:
            self._y_offset = offset

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
