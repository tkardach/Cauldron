# neopixel_strip.py needs to be separated from the led_strip.py for development
# environments which do not have access to RPI libraries.

from led_strip import LedStrip
from neopixel import NeoPixel
import numpy as np
from threading import Lock


_RGB_COLOR_SIZE = 3


class NeoPixelStrip(LedStrip):
    def __init__(self, neopixel: NeoPixel):
        self.neopixel = neopixel
        self._lock = Lock()

    def __setitem__(self, indices, value):
        if isinstance(value, np.ndarray):
            value = value.astype(np.int16).tolist()
        with self._lock:
            self.neopixel[indices] = value

    def __getitem__(self, indices):
        with self._lock:
            return self.neopixel[indices]

    def fill(self, color: list):
        assert len(color) == _RGB_COLOR_SIZE
        with self._lock:
            self.neopixel.fill(color)

    def fill_copy(self, pixels: np.array) -> int:
        assert len(pixels) == len(self.neopixel)
        with self._lock:
            self.neopixel[:] = pixels.astype(int).tolist()

    def set_pixel_color(self, index: int, color: list):
        assert len(color) == _RGB_COLOR_SIZE
        with self._lock:
            self.neopixel[index] = color

    @property
    def brightness(self) -> float:
        with self._lock:
            return self.neopixel.brightness

    @brightness.setter
    def brightness(self, brightness: float):
        with self._lock:
            self.neopixel.brightness = brightness

    def num_pixels(self) -> int:
        return len(self.neopixel)

    def show(self):
        if not self.neopixel.auto_write:
            with self._lock:
                self.neopixel.show()
