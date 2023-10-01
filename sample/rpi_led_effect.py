import led.led_effect as led
import led.led_strip as led_strip
from led.neopixel_strip import NeoPixelStrip
import matplotlib.pyplot as plt
import neopixel
import board
import numpy as np


NUM_PIXELS = 50
PIXEL_ORDER = neopixel.RGB
PIXEL_PIN = board.D18


class TestEffect:
    x = np.arange(0, NUM_PIXELS, 1)
    y = [3] * NUM_PIXELS

    @staticmethod
    def callback(pixels: np.array):
        plt.scatter(TestEffect.x, TestEffect.y, c=pixels / 255.0, s=50)

    @staticmethod
    def test_effect(strip: led_strip.LedStrip, effect: led.LedEffect):
        if isinstance(strip, led_strip.MockStrip):
            strip.set_show_callback(TestEffect.callback)
        plt.ion()
        for i in range(1000):
            effect.apply_effect(strip)
            plt.pause(effect.frame_speed_ms / 1000)

        plt.show()

def test_rpi_neopixel_sine_wave():
    color0 = [3, 252, 11]
    color1 = [229, 245, 5]

    sine_wave = led.SineWaveEffect(
        color0, color1, oscillate=True, b=5, oscillation_speed_ms=250
    )
    sine_wave.frame_speed_ms = 50
    device = neopixel.NeoPixel(
        PIXEL_PIN,
        NUM_PIXELS,
        auto_write=True,
        pixel_order=PIXEL_ORDER,
        brightness=0.5,
    )
    strip = led_strip.NeoPixelStrip(device)

    TestEffect.test_effect(strip, sine_wave)


test_rpi_neopixel_sine_wave()
