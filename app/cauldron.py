import board
from led.led_effect import SineWaveEffect
import neopixel

class BubblingEffect(SineWaveEffect):
  """Simulates a bubbling affect on an LedStrip."""

  def __init__(self, bubbling_speed: float = 0.5):
    self.bubbling_speed = 1
