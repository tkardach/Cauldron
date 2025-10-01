from cauldron.core.new_led_effect import TravelingLightEffect
import unittest
from unittest.mock import Mock, patch
import numpy as np
import time

# Assuming cauldron.core is in the python path
from cauldron.core.new_led_effect import (
    TravelingLightEffect,
    BubbleEffect,
    BubblingEffect,
)
from cauldron.core.led_strip import MockStrip


class TestTravelingLightEffects(unittest.TestCase):
    def setUp(self):
        self.strip = MockStrip(num_pixels=100)

    def test_traveling_light_effect_initialization(self):
        """Test initialization of TravelingLightEffect."""
        colors = [[0, 0, 0], [255, 255, 255]]
        effect = TravelingLightEffect(
            self.strip, colors=colors, tail_length=5, rps=1.0
        )
        self.assertEqual(effect._tail_length, 5)
        self.assertEqual(effect._rps, 1.0)
        np.testing.assert_array_equal(effect._colors[0], [0, 0, 0])
        np.testing.assert_array_equal(effect._colors[1], [255, 255, 255])

    def test_traveling_light_effect_head_and_tail(self):
        """Test that the head and tail are set correctly and fade exponentially."""
        colors = [[10, 20, 30], [200, 210, 220]]
        effect = TravelingLightEffect(
            self.strip, colors=colors, tail_length=4, rps=0.5
        )
        # t=0, head at position 0
        effect.update(0)
        pixels = np.array(self.strip[:])
        # Head LED should be exactly the head color
        np.testing.assert_array_equal(pixels[0], [200, 210, 220])
        # Tail LEDs should be between base and head, fading exponentially
        for i in range(1, 5):
            alpha = np.exp(-i / (4 / 3.0))
            expected = (1 - alpha) * np.array([10, 20, 30]) + alpha * np.array(
                [200, 210, 220]
            )
            np.testing.assert_array_almost_equal(
                pixels[-i], expected, decimal=0
            )

    def test_traveling_light_effect_wraps_around(self):
        """Test that the effect wraps around the strip correctly."""
        short_strip = MockStrip(num_pixels=8)
        colors = [[0, 0, 0], [255, 0, 0]]
        effect = TravelingLightEffect(
            short_strip, colors=colors, tail_length=3, rps=1.0
        )
        # Set t so that head is near the end
        t = 7.5 / 8.0  # head at position 7.5
        effect.update(t)
        pixels = np.array(short_strip[:])
        head_idx = int((t * 1.0 * 8) % 8)
        self.assertTrue(np.all(pixels[head_idx] == [255, 0, 0]))
        # Tail should wrap around to the start
        tail_indices = [(head_idx - i) % 8 for i in range(1, 4)]
        for i, idx in enumerate(tail_indices, 1):
            alpha = np.exp(-i / (3 / 3.0))
            expected = (1 - alpha) * np.array([0, 0, 0]) + alpha * np.array(
                [255, 0, 0]
            )
            np.testing.assert_array_almost_equal(
                pixels[idx], expected, decimal=0
            )


class TestBubbleEffect(unittest.TestCase):
    def setUp(self):
        self.n_leds = 20
        self.strip = MockStrip(self.n_leds)
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
        # Only interior pixels should be greater than base_color
        if self.bubble_length > 2:
            interior = bubble_pixels[1:-1]
            # At least one channel in each interior pixel should be greater than base_color
            self.assertTrue(np.all(np.any(interior > self.base_color, axis=1)))
        # Endpoints should be base_color (cosine bubble)
        self.assertTrue(np.allclose(bubble_pixels[0], self.base_color, atol=1))
        self.assertTrue(
            np.allclose(bubble_pixels[-1], self.base_color, atol=1)
        )
        # Pixels outside bubble should be base color
        before = self.strip[: self.bubble_index]
        after = self.strip[self.bubble_index + self.bubble_length :]
        self.assertTrue(np.all(before == self.base_color))
        self.assertTrue(np.all(after == self.base_color))

    def test_bubble_end(self):
        self.effect.update(self.bubble_pop_speed)
        # At t=pop_speed, bubble should be base color (allow rounding)
        bubble_pixels = self.strip[
            self.bubble_index : self.bubble_index + self.bubble_length
        ]
        self.assertTrue(np.all(bubble_pixels == self.base_color))

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
        self.strip = MockStrip(self.n_leds)
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
