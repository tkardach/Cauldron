import unittest
from unittest.mock import Mock, patch
import numpy as np
import time

# Assuming cauldron.core is in the python path
from cauldron.core.led_effect import (
    LedEffect,
    SineWaveEffect,
    BubbleEffect,
    BubblingEffect,
    TransitionColors,
    RepeatingEffectChain,
    Duration,
    ColorEffect,
)
from cauldron.core.led_strip import MockStrip


class TestLedEffects(unittest.TestCase):
    def setUp(self):
        """Set up a mock LED strip for each test."""
        self.strip = MockStrip(num_pixels=100)

    def test_sine_wave_effect_initialization(self):
        """Test the initialization and color property of SineWaveEffect."""
        colors = [[255, 0, 0], [0, 0, 255]]
        effect = SineWaveEffect(self.strip, colors=colors)
        self.assertEqual(len(effect.input_colors), 2)
        np.testing.assert_array_equal(
            effect.input_colors[0], np.array([255, 0, 0])
        )

    def test_sine_wave_apply_effect(self):
        """Test that apply_effect modifies the strip."""
        colors = [[255, 0, 0], [0, 0, 255]]
        effect = SineWaveEffect(self.strip, colors=colors)
        initial_pixels = self.strip[:].copy()
        effect.apply_effect()
        modified_pixels = self.strip[:].copy()
        self.assertFalse(np.array_equal(initial_pixels, modified_pixels))

    def test_bubbling_effect_initialization(self):
        """Test initialization of BubblingEffect."""
        colors = [[10, 10, 10], [200, 50, 200]]
        effect = BubblingEffect(
            self.strip,
            colors=colors,
            bubble_lengths=[5, 10],
            bubble_length_weights=[0.5, 0.5],
            bubble_pop_speeds_ms=[1000, 2000],
            bubble_pop_speed_weights=[0.5, 0.5],
            max_bubbles=10,
            bubble_spawn_prob=1.0,
        )
        self.assertIsNotNone(effect)
        np.testing.assert_array_equal(
            effect.input_colors[1], np.array([200, 50, 200])
        )

    def test_bubbling_effect_spawns_bubbles(self):
        """Test that BubblingEffect spawns BubbleEffects."""
        colors = [[0, 0, 0], [255, 255, 255]]
        effect = BubblingEffect(
            self.strip,
            colors=colors,
            bubble_lengths=[5],
            bubble_length_weights=[1.0],
            bubble_pop_speeds_ms=[100],
            bubble_pop_speed_weights=[1.0],
            max_bubbles=5,
            bubble_spawn_prob=1.0,
        )
        self.assertEqual(len(effect._current_bubbles), 0)
        effect.apply_effect()
        # With a spawn probability of 1.0, a bubble should be created.
        self.assertGreater(len(effect._current_bubbles), 0)

    def test_transition_colors(self):
        """Test the color interpolation of TransitionColors."""
        transition = TransitionColors(
            random_colors=False, end_colors=[[200, 200, 200]]
        )
        start_colors = [[100, 100, 100]]
        num_frames = 10
        transition.prepare_transition(start_colors, num_frames)
        # First frame should be the start colors
        colors = transition.next_colors()
        np.testing.assert_array_almost_equal(colors[0], start_colors[0])

        # Step through half the frames
        for _ in range(5):
            colors = transition.next_colors()
        np.testing.assert_array_almost_equal(colors[0], [150, 150, 150])

        # Step to the end
        for _ in range(5):
            colors = transition.next_colors()
        np.testing.assert_array_equal(colors[0], [200, 200, 200])

    def test_repeating_effect_chain(self):
        """Test RepeatingEffectChain with predictable ColorEffect and TransitionColors."""
        strip = MockStrip(5)
        start_color = [10, 20, 30]
        end_color = [100, 110, 120]
        # Use ColorEffect for predictable color output
        color_effect = ColorEffect(strip, color=start_color, frame_speed_ms=10)
        # Transition from start_color to end_color over 5 frames
        transition = TransitionColors(
            random_colors=False, end_colors=[end_color], frame_speed_ms=10
        )
        chain = RepeatingEffectChain(
            Duration(color_effect, seconds=0.05),  # 5 frames
            Duration(transition, seconds=0.05),  # 5 frames
        )

        # Initial color should be start_color
        np.testing.assert_array_equal(chain.input_colors[0], start_color)

        # Run through the ColorEffect duration (should stay at start_color)
        for _ in range(5):
            chain.apply_effect()
            np.testing.assert_array_equal(chain.input_colors[0], start_color)

        # Run through the transition (should interpolate toward end_color)
        for i in range(5):
            chain.apply_effect()
            # Should be between start_color and end_color
            current = chain.input_colors[0]
            self.assertTrue(
                np.all(current >= start_color) and np.all(current <= end_color)
            )

        # After transition, the color should be end_color
        np.testing.assert_array_almost_equal(
            chain.input_colors[0], end_color, decimal=0
        )

        # Next frame should restart the cycle, feeding back end_color as input
        chain.apply_effect()
        np.testing.assert_array_almost_equal(
            chain.input_colors[0], end_color, decimal=0
        )


if __name__ == "__main__":
    unittest.main()
