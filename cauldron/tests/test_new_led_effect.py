import unittest
import numpy as np
from cauldron.core.led_strip import RgbArrayStrip
from cauldron.core.new_led_effect import BubbleEffect, BubblingEffect


class TestBubbleEffect(unittest.TestCase):
    def setUp(self):
        self.n_leds = 20
        self.strip = RgbArrayStrip(self.n_leds)
        self.base_color = [10, 20, 30]
        self.bubble_color = [200, 180, 160]
        self.bubble_index = 5
        self.bubble_length = 6
        self.bubble_pop_speed = 2.0  # seconds
        self.effect = BubbleEffect(
            self.strip,
            self.bubble_index,
            [self.base_color, self.bubble_color],
            bubble_length=self.bubble_length,
            bubble_pop_speed=self.bubble_pop_speed,
        )

    def test_bubble_start(self):
        self.effect.update(0.0)
        # At t=0, bubble should be at max amplitude
        bubble_pixels = self.strip[
            self.bubble_index : self.bubble_index + self.bubble_length
        ]
        self.assertTrue(np.all(bubble_pixels.max(axis=0) > self.base_color))
        # Pixels outside bubble should be base color
        before = self.strip[: self.bubble_index]
        after = self.strip[self.bubble_index + self.bubble_length :]
        self.assertTrue(np.all(before == self.base_color))
        self.assertTrue(np.all(after == self.base_color))

    def test_bubble_end(self):
        self.effect.update(self.bubble_pop_speed)
        # At t=pop_speed, bubble should be base color
        bubble_pixels = self.strip[
            self.bubble_index : self.bubble_index + self.bubble_length
        ]
        self.assertTrue(np.allclose(bubble_pixels, self.base_color, atol=1))

    def test_bubble_mid(self):
        self.effect.update(self.bubble_pop_speed / 2)
        bubble_pixels = self.strip[
            self.bubble_index : self.bubble_index + self.bubble_length
        ]
        # Should be between base and bubble color
        self.assertFalse(np.allclose(bubble_pixels, self.base_color, atol=1))
        self.assertFalse(np.allclose(bubble_pixels, self.bubble_color, atol=1))


class TestBubblingEffect(unittest.TestCase):
    def setUp(self):
        self.n_leds = 30
        self.strip = RgbArrayStrip(self.n_leds)
        self.base_color = [0, 0, 0]
        self.bubble_color = [255, 255, 255]
        self.bubble_lengths = [3, 4]
        self.bubble_length_weights = [0.5, 0.5]
        self.bubble_pop_speeds = [1.0]
        self.bubble_pop_speed_weights = [1.0]
        self.max_bubbles = 2
        self.bubble_spawn_prob = 1.0  # Always spawn if possible
        self.effect = BubblingEffect(
            self.strip,
            [self.base_color, self.bubble_color],
            self.bubble_lengths,
            self.bubble_length_weights,
            self.bubble_pop_speeds,
            self.bubble_pop_speed_weights,
            self.max_bubbles,
            self.bubble_spawn_prob,
        )

    def test_bubbles_spawn_and_fade(self):
        # At t=0, should spawn up to max_bubbles
        self.effect.update(0.0)
        self.effect.update(0.1)
        self.effect.update(0.2)
        # There should be at least one non-base pixel
        self.assertTrue(np.any(self.strip.get_pixels() != self.base_color))
        # After enough time, all bubbles should fade
        self.effect.update(2.0)
        self.effect.update(3.0)
        # All pixels should be base color
        self.assertTrue(
            np.allclose(self.strip.get_pixels(), self.base_color, atol=1)
        )

    def test_no_overlap(self):
        # Run for a few steps to fill bubbles
        for t in np.linspace(0, 0.5, 5):
            self.effect.update(float(t))
        # Get all bubble regions
        bubble_mask = np.any(
            self.strip.get_pixels() != self.base_color, axis=1
        )
        # There should be at most max_bubbles contiguous regions
        from itertools import groupby

        regions = [list(g) for k, g in groupby(bubble_mask) if k]
        self.assertLessEqual(len(regions), self.max_bubbles)


if __name__ == "__main__":
    unittest.main()
