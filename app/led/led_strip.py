import abc
from neopixel import NeoPixel

class LedStrip(abc.ABC):
    @abc.abstractmethod
    def fill(self, color: tuple) -> None:
        return None
    
    @abc.abstractmethod
    def set_pixel_color(self, index: int, color: tuple) -> None:
        return None
    
    @abc.abstractmethod
    def set_pixel_brightness(self, index: int, brightness: int) -> None:
        return None
    
    @abc.abstractmethod
    def num_pixels(self) -> int:
        return 0
    
    @abc.abstractmethod
    def show(self) -> None:
        return None


class NeoPixelStrip(LedStrip):
    def __init__(self, neopixel: NeoPixel):
        self.neopixel = neopixel
    
    def fill(self, color: tuple) -> None:
        self.neopixel.fill(color)
    
    def set_pixel_color(self, index: int, color: tuple) -> None:
        self.neopixel[index] = color
    
    def set_pixel_brightness(self, index: int, brightness: int) -> None:
        self.neopixel[index].brightness = brightness
    
    def show(self) -> None:
        if not self.neopixel.auto_write:
            self.neopixel.show()

