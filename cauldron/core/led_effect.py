import abc
from itertools import groupby
from cauldron.core.led_strip import LedStrip
import numpy as np
from numpy.random import choice
from pydub import AudioSegment
import random
import threading
import time


TWO_PI = np.pi * 2


def _generate_random_color():
    """Generates a single random RGB color."""
    return np.random.randint(0, 256, 3)


class LedEffect(abc.ABC):
    def __init__(self, strip: LedStrip, frame_speed_ms: int = 100):
        self._frame_speed_ms = frame_speed_ms
        self._strip = strip
        self._input_colors = []
        self._color_lock = threading.Lock()

    @property
    def frame_speed_ms(self) -> int:
        return self._frame_speed_ms

    @abc.abstractmethod
    def apply_effect(self):
        return None

    @abc.abstractmethod
    def reset(self):
        return None

    @property
    def input_colors(self) -> list[np.ndarray]:
        """Gets the current input colors of the effect."""
        return self._input_colors

    @input_colors.setter
    def input_colors(self, colors: list):
        """Sets the input colors for the effect."""
        with self._color_lock:
            self._input_colors = [np.array(c) for c in colors]
            self._on_colors_changed()

    @property
    def output_colors(self) -> list[np.ndarray]:
        """The colors to be passed to the next effect. Defaults to input_colors."""
        return self.input_colors

    def _on_colors_changed(self):
        """
        Called when input_colors is set.
        Subclasses should override this to react to color changes.
        """
        pass


# Simple static color effect for testing
class ColorEffect(LedEffect):
    """A simple effect that sets the strip to a static color (for testing)."""

    def __init__(
        self, strip: LedStrip, color: list, frame_speed_ms: int = 100
    ):
        super().__init__(strip, frame_speed_ms)
        self.input_colors = [color]
        self._applied_color = None

    def apply_effect(self):
        self._applied_color = self.input_colors[0]
        if self._strip is not None:
            self._strip[:] = self._applied_color
            self._strip.show()

    def reset(self):
        self._applied_color = None

    @property
    def output_colors(self) -> list:
        return self.input_colors


class Duration:
    """A container to associate an effect with a duration."""

    def __init__(self, effect: LedEffect, seconds: float):
        if not isinstance(effect, (LedEffect, RandomColorTransition)):
            raise TypeError(
                "Duration can only wrap LedEffect or RandomColorTransition instances."
            )
        self.effect = effect
        self.seconds = seconds


class RandomColorTransition(LedEffect):
    """
    An 'effect' that generates a smooth transition between colors over time.
    It does not draw to the strip itself but provides interpolated colors for other effects.
    """

    def __init__(
        self,
        start_colors: int,
        end_colors: int,
        duration_ms: int = 5000,
        frame_speed_ms: int = 100,
    ):
        super().__init__(strip=None, frame_speed_ms=frame_speed_ms)
        self._total_increments = max(1, int(duration_ms / frame_speed_ms))
        self._current_increment = 0
        self._start_colors = [
            _generate_random_color() for _ in range(start_colors)
        ]
        self._end_colors = [
            _generate_random_color() for _ in range(end_colors)
        ]
        self._primary_color = self._start_colors[0]
        self._primary_diff = self._end_colors[0] - self._start_colors[0]
        self._color_increments = self._primary_diff / self._total_increments

    @property
    def input_colors(self) -> list[np.ndarray]:
        """Gets the current input colors of the effect."""
        return self._start_colors

    @input_colors.setter
    def input_colors(self, colors: list):
        """Sets the input colors for the effect."""
        self._start_colors = [np.array(c) for c in colors]
        self._on_colors_changed()

    @property
    def output_colors(self) -> list[np.ndarray]:
        return self._end_colors

    @property
    def output_colors(self) -> list[np.ndarray]:
        return self._end_colors

    def apply_effect(self):
        if (
            self._total_increments <= 0
            or self._current_increment >= self._total_increments
        ):
            # If there are no frames, the transition is instantaneous, return end_colors
            self._strip[:] = np.clip(
                self._end_colors[0].astype(np.uint8), 0, 255
            ).astype(np.uint8)
            self._strip.show()
            return

        self._primary_color += self._color_increments
        self._strip[:] = np.clip(self._primary_color, 0, 255).astype(np.uint8)
        self._current_increment += 1
        self._strip.show()

    def reset(self):
        self._current_increment = 0


class MockEffect(LedEffect):
    def __init__(self, strip: LedStrip):
        LedEffect.__init__(self, strip)

    def apply_effect(self):
        return None

    def reset(self):
        return None


class SineWaveEffect(LedEffect):
    """Applies a modifyable sine wave effect onto an LedStrip."""

    def __init__(
        self,
        strip: LedStrip,
        colors: list,
        b: float = 1,
        oscillate: bool = False,
        oscillation_speed_ms: int = 250,
        frame_speed_ms: int = 100,
    ):
        LedEffect.__init__(self, strip, frame_speed_ms)
        self._lock = threading.Lock()

        self.input_colors = colors
        self.oscillation_speed_ms = oscillation_speed_ms
        self._oscillate = oscillate
        self.wave_length = b

        self._amplitude_inc = (2 * np.pi) / self._oscillation_inc
        self._amplitude_x = 0

        num_pixels = self._strip.num_pixels()
        self._x_values = np.array([np.arange(0, TWO_PI, TWO_PI / num_pixels)])

    def _on_colors_changed(self):
        with self._lock:
            if len(self.input_colors) != 2:
                raise ValueError("SineWaveEffect requires 2 colors.")
            self._color0 = self.input_colors[0]
            self._color1 = self.input_colors[1]

            self._y_offsets = np.abs(
                (self._color0 - self._color1) / 2
            ) + np.minimum(self._color0, self._color1)
            self._amplitudes = np.array([(self._color0 - self._color1) / 2])
            self._current_a = self._amplitudes.copy()

    def _update_pixel_values_locked(self, x: np.array) -> np.array:
        assert self._lock.locked()
        pixels = np.zeros((len(x), len(self._current_a)))
        pixels = np.cos(self._b * x).T * self._current_a + self._y_offsets
        return pixels

    def _update_oscillation_locked(self):
        assert self._lock.locked()
        if not self._oscillate:
            return
        self._amplitude_x += self._amplitude_inc
        self._current_a = self._amplitudes * np.cos(self._amplitude_x)

    def apply_effect(self):
        with self._lock:
            pixels = self._update_pixel_values_locked(self._x_values)
            self._strip[:] = pixels
            self._update_oscillation_locked()
        self._strip.show()

    def reset(self):
        with self._lock:
            self._current_a = np.array([(self._color0 - self._color1) / 2])
            self._amplitude_x = 0

    # ... (properties like wave_length, oscillate, etc. remain the same)
    @property
    def wave_length(self) -> float:
        return self._b

    @wave_length.setter
    def wave_length(self, b: float):
        with self._lock:
            self._b = b

    @property
    def oscillate(self) -> bool:
        return self._oscillate

    @oscillate.setter
    def oscillate(self, enable: bool):
        with self._lock:
            self._oscillate = enable

    @property
    def oscillation_speed_ms(self) -> int:
        return self._oscillation_speed_ms

    @oscillation_speed_ms.setter
    def oscillation_speed_ms(self, speed_ms: int):
        with self._lock:
            self._oscillation_speed_ms = speed_ms
            self._oscillation_inc = speed_ms / self._frame_speed_ms


class BubbleEffect(LedEffect):
    def __init__(
        self,
        strip: LedStrip,
        bubble_index: int,
        colors: list,
        bubble_length: int = 5,
        bubble_pop_speed_ms: int = 3000,
        frame_speed_ms: int = 100,
    ):
        assert bubble_index >= 0
        self._lock = threading.Lock()
        LedEffect.__init__(self, strip, frame_speed_ms)
        num_pixels = self._strip.num_pixels()
        assert bubble_index < num_pixels
        self._bubble_index = bubble_index
        self._bubble_pop_speed_ms = bubble_pop_speed_ms

        self.input_colors = colors

        self._pop_increments = int(
            self._bubble_pop_speed_ms / self._frame_speed_ms
        )
        self._current_increment = 0

        x_values = self._get_x_values(self._pop_increments)
        self._y_increments = np.array((np.cos(x_values + np.pi) + 1) / 2)

        self._max_index = min(
            num_pixels - 1, self._bubble_index + bubble_length - 1
        )
        self._bubble_x_values = np.array(
            np.arange(self._bubble_index, self._max_index, 1)
        )
        self._bubble_x_range = (self._bubble_index, self._max_index)
        self._x_values = np.array(
            [self._get_x_values(len(self._bubble_x_values))]
        )

    def _on_colors_changed(self):
        with self._lock:
            if len(self.input_colors) != 2:
                raise ValueError(
                    "BubbleEffect expects 2 colors: [base_color, bubble_color]"
                )
            self._base_color = self.input_colors[0]
            self._bubble_color = self.input_colors[1]
            self._bubble_amplitude = self._bubble_color - self._base_color

    def set_colors(self, base_color, bubble_color):
        """Allows live updating of bubble colors."""
        self.input_colors = [base_color, bubble_color]

    def _get_x_values(self, length: int) -> np.array:
        if length <= 1:
            return np.array([0])
        x_inc = TWO_PI / (length - 1)
        return np.arange(0, TWO_PI + x_inc, x_inc)

    def bubble_index_range(self):
        return (self._bubble_index, self._max_index)

    def apply_effect(self):
        with self._lock:
            amp_fact = self._y_increments[
                self._current_increment % self._pop_increments
            ]
            amplitude = amp_fact * self._bubble_amplitude
            colors = (
                np.cos(self._x_values + np.pi) + 1
            ).T * amplitude + self._base_color
            colors = np.clip(colors, 0, 255)
            self._strip[self._bubble_x_range[0] : self._bubble_x_range[1]] = (
                colors
            )
            self._current_increment += 1

    def reset(self):
        with self._lock:
            self._current_increment = 0


class BubblingEffect(LedEffect):
    def __init__(
        self,
        strip: LedStrip,
        colors: list,
        bubble_lengths: list,
        bubble_length_weights: list,
        bubble_pop_speeds_ms: list,
        bubble_pop_speed_weights: list,
        max_bubbles: int,
        bubble_spawn_prob: float,
        frame_speed_ms: int = 100,
    ):
        LedEffect.__init__(self, strip, frame_speed_ms)
        self._lock = threading.Lock()
        assert len(bubble_lengths) == len(bubble_length_weights)
        assert len(bubble_pop_speeds_ms) == len(bubble_pop_speed_weights)
        assert 0 < bubble_spawn_prob <= 1

        # Initialize attributes before setting colors, as the setter uses them
        self._current_bubbles: dict[int, BubbleEffect] = {}

        self.input_colors = colors

        self._max_bubbles = max_bubbles
        self._bubble_spawn_prob = bubble_spawn_prob
        self._bubble_lengths = bubble_lengths
        self._bubble_length_weights = bubble_length_weights
        self._bubble_pop_speeds = bubble_pop_speeds_ms
        self._bubble_pop_speed_weights = bubble_pop_speed_weights
        self._num_pixels = self._strip.num_pixels()
        self._bubble_indices = np.ones(self._num_pixels)
        self._max_bubbles_reached = False

    def _on_colors_changed(self):
        if len(self.input_colors) != 2:
            raise ValueError(
                "BubblingEffect expects 2 colors: [base_color, bubble_color]"
            )

        base_color = self.input_colors[0]
        bubble_color = self.input_colors[1]

        self._base_color = base_color
        self._bubble_color = bubble_color

        with self._lock:
            for bubble in self._current_bubbles.values():
                bubble.set_colors(base_color, bubble_color)

    def _spawn_bubble(self):
        return (
            random.random() <= self._bubble_spawn_prob
            and not self._max_bubbles_reached
        )

    def _bubble_exists(self, min_index: int, max_index: int) -> bool:
        return not np.all(self._bubble_indices[min_index:max_index])

    def _get_bubble_location(self):
        bubble_length = choice(
            self._bubble_lengths, 1, p=self._bubble_length_weights
        )[0]
        bubble_index = random.randint(0, self._num_pixels - 1)
        bubble_max_index = bubble_index + bubble_length - 1
        try_count = 0
        while (
            self._bubble_exists(bubble_index, bubble_max_index)
            or bubble_max_index >= self._num_pixels
        ) and try_count < 30:
            try_count += 1
            bubble_index = random.randint(0, self._num_pixels - 1)
            bubble_length = choice(
                self._bubble_lengths, 1, p=self._bubble_length_weights
            )[0]
            bubble_max_index = bubble_index + bubble_length - 1
        if try_count >= 30:
            self._max_bubbles_reached = True
            return None
        return (bubble_index, bubble_length)

    def apply_effect(self):
        if not self._max_bubbles_reached:
            try:
                # Filter for groups of 1s (available spaces)
                groups = (
                    sum(1 for _ in g)
                    for k, g in groupby(self._bubble_indices)
                    if k == 1
                )
                longest_possible_bubble = max(groups, default=0)
            except ValueError:
                longest_possible_bubble = 0

            if (
                longest_possible_bubble < np.min(self._bubble_lengths)
                and len(self._current_bubbles) >= self._max_bubbles
            ):
                self._max_bubbles_reached = True

        if self._spawn_bubble() and not self._max_bubbles_reached:
            result = self._get_bubble_location()
            if result is not None:
                bubble_index, bubble_length = result
                bubble_pop_speed_ms = choice(
                    self._bubble_pop_speeds,
                    1,
                    p=self._bubble_pop_speed_weights,
                )[0]
                bubble_effect = BubbleEffect(
                    self._strip,
                    bubble_index,
                    [self._base_color, self._bubble_color],
                    bubble_length,
                    bubble_pop_speed_ms,
                    self._frame_speed_ms,
                )
                bubble_range = bubble_effect.bubble_index_range()
                self._bubble_indices[bubble_range[0] : bubble_range[1]] = 0
                with self._lock:
                    self._current_bubbles[bubble_index] = bubble_effect

        for bubbles in list(self._current_bubbles.values()):
            bubbles.apply_effect()
        self._strip.show()

    def reset(self):
        with self._lock:
            self._current_bubbles.clear()
        self._bubble_indices.fill(1)
        self._max_bubbles_reached = False


class AudioToBrightnessEffect(LedEffect):
    """Changes the brightness of the LedStrip based on AudioSegment volume."""

    def __init__(
        self, strip: LedStrip, segment: AudioSegment, frame_speed_ms: int = 100
    ):
        LedEffect.__init__(self, strip, frame_speed_ms)
        self._lock = threading.Lock()
        data = np.array(segment.get_array_of_samples())
        data = np.abs(data.astype(np.int32))
        self._normalized_data = (data - np.min(data)) / (
            np.max(data) - np.min(data)
        )
        self._duration_s = segment.duration_seconds
        self._current_iteration = 0
        self._total_increments = (
            segment.duration_seconds * 1000 / self._frame_speed_ms
        )
        self._iteration_increment = (
            len(self._normalized_data) / self._total_increments
        )
        self._starting_brightness = None

    def apply_effect(self):
        if self._starting_brightness is None:
            self._starting_brightness = self._strip.brightness
        brightness = np.clip(
            self._normalized_data[int(self._current_iteration)]
            + self._starting_brightness,
            0,
            1,
        )
        self._strip.brightness = brightness
        with self._lock:
            self._current_iteration += self._iteration_increment
            if self._current_iteration >= len(self._normalized_data):
                self._strip.brightness = self._starting_brightness
                self._current_iteration = 0
        self._strip.show()

    def reset(self):
        with self._lock:
            self._current_iteration = 0


class BrightnessEffect(LedEffect):
    """Changes the brightness of the LedStrip."""

    def __init__(self, strip: LedStrip, frame_speed_ms: int = 100):
        LedEffect.__init__(self, strip, frame_speed_ms)
        self._lock = threading.Lock()
        self._starting_brightness = self._strip.brightness
        self._brightness_range = 1.0 - self._starting_brightness

    def apply_effect(self):
        self._strip.show()

    def set_brightness(self, brightness: float):
        with self._lock:
            self._strip.brightness = self._starting_brightness + (
                self._brightness_range * brightness
            )

    def reset(self):
        with self._lock:
            self._strip.brightness = self._starting_brightness
