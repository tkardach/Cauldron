import led_effect
import led_strip
from pedalboard import Reverb, PitchShift
import players
import time
from test_runner import TestRunner

fx = [
    Reverb(wet_level=1),
    PitchShift(semitones=-4),
]
NUM_PIXELS = 50

mock_strip = led_strip.MockStrip(NUM_PIXELS)
mock_strip.fill([100, 200, 55])
mock_strip.brightness = 0.25

brightness_effect = led_effect.BrightnessEffect(mock_strip)
v2b_player = players.VoiceToBrightnessPlayer(brightness_effect)
effect_player = players.MockStripPlayer(mock_strip)
v2b_handle = v2b_player.loop()
effect_handle = effect_player.loop()
runner = TestRunner(mock_strip, [v2b_handle, effect_handle])
runner.run()
