import abc
from enum import Enum
import numpy as np
import queue
import socket
from typing import Callable


_RGB_COLOR_SIZE = 3


class PixelOrder(Enum):
    RGB = (0,)
    BGR = 1


class LedStrip(abc.ABC):
    def __del__(self):
        self.fill((0, 0, 0))

    @abc.abstractmethod
    def __setitem__(self, indices, value):
        return None

    @abc.abstractmethod
    def __getitem__(self, indices):
        return None

    @abc.abstractmethod
    def fill(self, color: tuple):
        return None

    @abc.abstractmethod
    def set_pixel_color(self, index: int, color: tuple):
        return None

    @property
    @abc.abstractmethod
    def brightness(self) -> float:
        return None

    @brightness.setter
    @abc.abstractmethod
    def brightness(self, brightness: float):
        return None

    @abc.abstractmethod
    def num_pixels(self) -> int:
        return 0

    @abc.abstractmethod
    def get_pixels(self) -> np.ndarray:
        """Returns the current pixel data as a numpy array."""
        pass

    def show(self):
        return None


class RgbArrayStrip(LedStrip):
    def __init__(self, num_pixels: int):
        self._num_pixels = num_pixels
        self._pixels = np.zeros((num_pixels, 3)).astype(np.uint8)
        self._brightness = 1.0

    def __setitem__(self, indices, value):
        self._pixels[indices] = value

    def __getitem__(self, indices):
        return self._pixels[indices]

    def fill(self, color: list):
        assert len(color) == _RGB_COLOR_SIZE
        self._pixels[:] = color

    def set_pixel_color(self, index: int, color: list):
        assert len(color) == _RGB_COLOR_SIZE
        self._pixels[index] = color

    @property
    def brightness(self) -> float:
        return self._brightness

    @brightness.setter
    def brightness(self, brightness: float):
        self._brightness = brightness

    def get_pixels(self, pixel_order: PixelOrder = PixelOrder.RGB):
        if pixel_order == PixelOrder.RGB:
            return self._pixels
        elif pixel_order == PixelOrder.BGR:
            return self._pixels[:, [2, 1, 0]]
        raise ValueError("Invalid PixelOrder")

    def num_pixels(self) -> int:
        return self._num_pixels


class UdpStreamStrip(RgbArrayStrip):
    def __init__(
        self, num_pixels: int, address: str, port: int, brightness: float = 1
    ):
        RgbArrayStrip.__init__(self, num_pixels)
        self._address = address
        self._port = port
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._show_callback = None
        self._brightness = brightness

    def set_show_callback(self, show_callback: Callable[[np.array], None]):
        self._show_callback = show_callback

    def __setitem__(self, indices, value):
        RgbArrayStrip.__setitem__(self, indices, value)

    def fill(self, color: list):
        RgbArrayStrip.fill(self, color)

    def show(self):
        pixels = self.get_pixels(PixelOrder.RGB)
        brightness = int(self._brightness * 255)
        pixels = ((np.uint64(pixels) * brightness) >> 8).astype(np.uint8)
        data = pixels.tobytes()
        self._socket.sendto(data, (self._address, self._port))
        if self._show_callback:
            self._show_callback(self._pixels)


class MockStrip(RgbArrayStrip):
    callback_queue = queue.Queue()

    def __init__(
        self, num_pixels: int, show_callback: Callable[[np.array], None] = None
    ):
        RgbArrayStrip.__init__(self, num_pixels)
        self._show_callback = show_callback

    def set_show_callback(self, show_callback: Callable[[np.array], None]):
        self._show_callback = show_callback

    def get_pixels(self, pixel_order: PixelOrder = PixelOrder.RGB):
        return super().get_pixels(pixel_order)

    def show(self):
        def callback():
            self._show_callback(self._pixels)

        if self._show_callback:
            self.callback_queue.put(callback)
