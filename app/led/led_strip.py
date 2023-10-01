import abc
import numpy as np
from typing import Callable

_RGB_COLOR_SIZE = 3


class LedStrip(abc.ABC):
    @abc.abstractmethod
    def fill(self, color: tuple) -> None:
        return None

    @abc.abstractmethod
    def fill_copy(self, pixels: np.array) -> int:
        return 0

    @abc.abstractmethod
    def set_pixel_color(self, index: int, color: tuple) -> None:
        return None

    @abc.abstractmethod
    def set_brightness(self, brightness: int) -> None:
        return None

    @abc.abstractmethod
    def num_pixels(self) -> int:
        return 0

    @abc.abstractmethod
    def show(self) -> None:
        return None


class MockStrip(LedStrip):
    def __init__(self, num_pixels: int, show_callback: Callable[[np.array], None] = None):
        self._num_pixels = num_pixels
        self._pixels = np.array([[0, 0, 0]] * num_pixels)
        self._show_callback = show_callback

    def set_show_callback(self, show_callback: Callable[[np.array], None]):
        self._show_callback = show_callback

    def fill(self, color: list) -> None:
        assert len(color) == _RGB_COLOR_SIZE
        self._pixels = [color] * self._num_pixels

    def fill_copy(self, pixels: np.array) -> int:
        assert pixels.shape == self._pixels.shape, f"{colors.shape} != {self._pixels.shape}"
        self._pixels = pixels.copy()
    
    def set_pixel_color(self, index: int, color: list) -> None:
        assert len(color) == _RGB_COLOR_SIZE
        self._pixels[index] = color
    
    def set_brightness(self, brightness: int) -> None:
        return None

    def num_pixels(self) -> int:
        return self._num_pixels

    def show(self) -> None:
        if self._show_callback:
            self._show_callback(self._pixels)
