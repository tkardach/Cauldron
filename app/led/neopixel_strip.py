from led_strip import LedStrip
from neopixel import NeoPixel


class NeoPixelStrip(LedStrip):
    def __init__(self, neopixel: NeoPixel):
        self.neopixel = neopixel

    def fill(self, color: list) -> None:
        assert len(color) == _RGB_COLOR_SIZE
        self.neopixel.fill(np.floor(color).tolist())

    def fill_copy(self, pixels: np.array) -> int:
        assert len(pixels) == len(self.neopixel)
        self.neopixel[:] = pixels.astype(int).tolist()

    def set_pixel_color(self, index: int, color: list) -> None:
        assert len(color) == _RGB_COLOR_SIZE
        self.neopixel[index] = color

    def set_brightness(self, brightness: int) -> None:
        self.neopixel.brightness = brightness

    def num_pixels(self) -> int:
        return len(self.neopixel)

    def show(self) -> None:
        if not self.neopixel.auto_write:
            self.neopixel.show()
