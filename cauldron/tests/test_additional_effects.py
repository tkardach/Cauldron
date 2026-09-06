import unittest

import numpy as np
from pydub import AudioSegment
from pydub.generators import Sine

from cauldron.core.led_effect import (
    AudioToBrightnessEffect,
    BrightnessEffect,
    EffectChain,
    EffectWithDuration,
    MockEffect,
    TransitionEffect,
    TravelingLightEffect,
)
from cauldron.core.led_strip import RgbArrayStrip


class TestAdditionalEffects(unittest.TestCase):
    def test_traveling_light_linear_reverse_and_colors(self):
        strip = RgbArrayStrip(5)
        effect = TravelingLightEffect(
            strip,
            [[0, 0, 0], [255, 0, 0]],
            tail_length=2,
            fade_type="linear",
            reverse=True,
            start_index=2,
        )
        effect.update(0)
        np.testing.assert_array_equal(strip[2], [255, 0, 0])
        np.testing.assert_array_equal(strip[3], [127, 0, 0])
        effect.input_colors = [[1, 2, 3], [4, 5, 6]]
        np.testing.assert_array_equal(effect.output_colors[1], [4, 5, 6])

    def test_transition_and_brightness_effects(self):
        strip = RgbArrayStrip(3)
        strip[:] = [0, 0, 0]
        transition = TransitionEffect(strip, [100, 50, 0], duration=2)
        transition.update(1)
        np.testing.assert_array_equal(strip[0], [50, 25, 0])
        transition.reset()
        self.assertIsNone(transition._target_colors)

        brightness = BrightnessEffect(strip, initial_brightness=0.25)
        brightness.input_colors = [0.75]
        brightness.update(0)
        self.assertEqual(strip.brightness, 0.75)
        brightness.reset()
        self.assertEqual(brightness.input_colors, [0.25])

    def test_audio_to_brightness_reads_audio_and_resets(self):
        strip = RgbArrayStrip(2)
        segment = Sine(440).to_audio_segment(duration=100)
        effect = AudioToBrightnessEffect(strip, segment)
        effect.update(0)
        self.assertGreaterEqual(strip.brightness, 0)
        effect.reset()
        self.assertIsNone(effect._starting_brightness)

    def test_validation_errors(self):
        strip = RgbArrayStrip(2)
        with self.assertRaises(AssertionError):
            EffectChain(strip, [])
        with self.assertRaises(AssertionError):
            TravelingLightEffect(strip, [[1, 2, 3]], fade_type="linear")
        self.assertIsNone(MockEffect(strip).reset())


if __name__ == "__main__":
    unittest.main()
