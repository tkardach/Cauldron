from cauldron import Cauldron, CauldronSounds, CauldronRunner
from led_strip import MockStrip
import threading
import time

NUM_PIXELS = 50
strip = MockStrip(NUM_PIXELS)
strip.brightness = 0.2

runner = CauldronRunner(strip)
runner.run()
