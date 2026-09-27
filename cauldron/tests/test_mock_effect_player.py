"""Tests for the grid aware MockEffectPlayer visualization."""

import time
import unittest

import matplotlib

matplotlib.use("Agg")  # Headless rendering for the tests.

import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

from cauldron.core.led_effect import (  # noqa: E402
    MockEffect,
    WaterDropletEffect,
)
from cauldron.core.led_strip import MockStrip  # noqa: E402
from cauldron.core.players import (  # noqa: E402
    DropdownMenu,
    MockEffectPlayer,
)


class FakeMouseEvent:
    """Minimal stand-in for a Matplotlib MouseEvent."""

    def __init__(self, inaxes):
        self.inaxes = inaxes


class TestDropdownMenu(unittest.TestCase):
    def setUp(self):
        self.fig = plt.figure()
        self.ax = self.fig.add_axes([0.1, 0.9, 0.2, 0.05])
        self.selections = []
        self.menu = DropdownMenu(
            self.ax,
            ["All Strips", "Strip 0", "Strip 1"],
            on_select=lambda i, label: self.selections.append((i, label)),
            label="RGB Source",
        )

    def tearDown(self):
        plt.close(self.fig)

    def test_defaults_to_the_first_option(self):
        self.assertEqual(self.menu.selected_index, 0)
        self.assertEqual(self.menu.selected_option, "All Strips")
        self.assertFalse(self.menu.expanded)
        self.assertEqual(len(self.menu.option_axes), 3)
        self.assertFalse(any(a.get_visible() for a in self.menu.option_axes))

    def test_clicking_expands_and_selects(self):
        self.menu._on_click(FakeMouseEvent(self.ax))
        self.assertTrue(self.menu.expanded)
        self.assertTrue(all(a.get_visible() for a in self.menu.option_axes))

        self.menu._on_click(FakeMouseEvent(self.menu.option_axes[2]))
        self.assertFalse(self.menu.expanded)
        self.assertEqual(self.menu.selected_option, "Strip 1")
        self.assertEqual(self.selections, [(2, "Strip 1")])

    def test_clicking_outside_collapses_the_menu(self):
        self.menu.toggle()
        self.assertTrue(self.menu.expanded)
        self.menu._on_click(FakeMouseEvent(self.fig.add_subplot(111)))
        self.assertFalse(self.menu.expanded)
        self.assertEqual(self.selections, [])


class TestMockEffectPlayerGrid(unittest.TestCase):
    NUM_STRIPS = 4
    NUM_PIXELS = 16

    def setUp(self):
        self.strips = [
            MockStrip(self.NUM_PIXELS) for _ in range(self.NUM_STRIPS)
        ]
        self.effect = WaterDropletEffect(
            self.strips,
            led_strip_length=self.NUM_PIXELS / 60.0,
            led_density=60.0,
            drop_frequency=2.0,
            seed=3,
        )
        self.player = MockEffectPlayer(self.strips, self.effect, fps=30.0)

    def tearDown(self):
        plt.close("all")

    def _render_once(self):
        self.player._setup_plot()
        self.player._is_playing = True
        self.player._start_time = time.time()
        self.player._play_time_s = None
        return self.player._update_frame(0)

    def test_grid_is_two_dimensional(self):
        self._render_once()
        self.assertEqual(self.player._grid_ax.get_title(), "LED Grid")
        offsets = self.player._scat.get_offsets()
        self.assertEqual(len(offsets), self.NUM_STRIPS * self.NUM_PIXELS)
        # Strip 0 is drawn as the top row of the grid.
        rows = np.unique(np.asarray(offsets)[:, 1])
        np.testing.assert_array_equal(rows, np.arange(self.NUM_STRIPS))
        self.assertGreater(
            self.player._grid_ax.get_ylim()[0],
            self.player._grid_ax.get_ylim()[1],
        )

    def test_brightness_graph_is_two_dimensional(self):
        self._render_once()
        self.assertEqual(self.player._brightness_ax.get_title(), "Brightness")
        brightness = np.asarray(self.player._brightness_image.get_array())
        self.assertEqual(brightness.shape, (self.NUM_STRIPS, self.NUM_PIXELS))
        expected = self.player._brightness_grid(self.player._pixel_grid())
        np.testing.assert_allclose(brightness, expected)
        self.assertGreater(brightness.max(), 0.0)
        self.assertLessEqual(brightness.max(), 1.0)

    def test_rgb_graphs_follow_the_dropdown_selection(self):
        self._render_once()
        options = self.player.dropdown._options
        self.assertEqual(options[0], MockEffectPlayer.ALL_STRIPS_LABEL)
        self.assertEqual(len(options), self.NUM_STRIPS + 1)

        # Every strip is plotted by default.
        self.assertTrue(all(l.get_visible() for l in self.player._r_lines))

        self.player.dropdown.select(3)  # "Strip 2"
        self.assertEqual(self.player.dropdown.selected_option, "Strip 2")
        for lines in (
            self.player._r_lines,
            self.player._g_lines,
            self.player._b_lines,
        ):
            self.assertEqual(
                [line.get_visible() for line in lines],
                [False, False, True, False],
            )

        self.player.select_strip(-1)  # back to every strip
        self.assertTrue(all(l.get_visible() for l in self.player._b_lines))

    def test_rgb_lines_render_each_strips_channels(self):
        self._render_once()
        self.player._effect.update(0.35)
        self.player._refresh_render()
        pixels = self.player._pixel_grid()
        for index in range(self.NUM_STRIPS):
            np.testing.assert_array_equal(
                self.player._r_lines[index].get_ydata(), pixels[index, :, 0]
            )
            np.testing.assert_array_equal(
                self.player._g_lines[index].get_ydata(), pixels[index, :, 1]
            )
            np.testing.assert_array_equal(
                self.player._b_lines[index].get_ydata(), pixels[index, :, 2]
            )

    def test_update_frame_advances_the_effect(self):
        self._render_once()
        first = self.effect.displacement.copy()
        time.sleep(0.05)
        self.player._update_frame(1)
        self.assertFalse(np.array_equal(first, self.effect.displacement))

    def test_play_for_stops_after_the_duration(self):
        handle = self.player.play_for(0.05)
        self.assertTrue(self.player._is_playing)
        time.sleep(0.1)
        self.player._update_frame(0)
        self.assertFalse(self.player._is_playing)
        handle.stop_wait()

    def test_loop_and_stop(self):
        handle = self.player.loop()
        self.assertTrue(self.player._is_playing)
        self.assertIsNone(self.player._play_time_s)
        self.player._update_frame(0)
        handle.stop()
        self.assertFalse(self.player._is_playing)
        # Stopping twice is a no-op.
        self.player.stop()

    def test_play_defaults_to_five_seconds(self):
        handle = self.player.play()
        self.assertEqual(self.player._play_time_s, 5.0)
        handle.stop_wait()

    def test_strips_can_be_pulled_from_the_effect(self):
        player = MockEffectPlayer(None, self.effect)
        self.assertEqual(len(player.strips), self.NUM_STRIPS)

    def test_mismatched_strip_lengths_are_rejected(self):
        with self.assertRaises(AssertionError):
            MockEffectPlayer([MockStrip(4), MockStrip(5)], self.effect)


class TestMockEffectPlayerSingleStrip(unittest.TestCase):
    """The player must stay backwards compatible with a single LedStrip."""

    def tearDown(self):
        plt.close("all")

    def test_single_strip_renders_a_one_row_grid(self):
        strip = MockStrip(12)
        strip[:] = [10, 20, 30]
        player = MockEffectPlayer(strip, MockEffect(strip), fps=30.0)
        player._setup_plot()
        player._is_playing = True
        player._start_time = time.time()
        player._play_time_s = None
        player._update_frame(0)

        self.assertEqual(len(player.strips), 1)
        self.assertEqual(len(player._scat.get_offsets()), 12)
        brightness = np.asarray(player._brightness_image.get_array())
        self.assertEqual(brightness.shape, (1, 12))
        np.testing.assert_allclose(brightness, 30.0 / 255.0)
        np.testing.assert_array_equal(
            player._r_lines[0].get_ydata(), np.full(12, 10)
        )
        self.assertEqual(
            player.dropdown._options,
            [MockEffectPlayer.ALL_STRIPS_LABEL, "Strip 0"],
        )


if __name__ == "__main__":
    unittest.main()
