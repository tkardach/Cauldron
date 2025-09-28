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
        if not isinstance(effect, (LedEffect, TransitionColors)):
            raise TypeError(
                "Duration can only wrap LedEffect or TransitionColors instances."
            )
        self.effect = effect
        self.seconds = seconds
        # For non-drawing effects like TransitionColors, frame_speed might be default.
        frame_speed = effect.frame_speed_ms or 100
        self.num_frames = int((seconds * 1000) / frame_speed)


class TransitionColors(LedEffect):
    """
    An 'effect' that generates a smooth transition between colors over time.
    It does not draw to the strip itself but provides interpolated colors for other effects.
    """

    def __init__(
        self,
        random_colors: bool = False,
        end_colors: list = None,
        start_colors: list = None,
        frame_speed_ms: int = 100,
    ):
        super().__init__(strip=None, frame_speed_ms=frame_speed_ms)
        self._random = random_colors
        self._end_colors_config = (
            [np.array(c) for c in end_colors] if end_colors else None
        )
        self._start_colors_config = (
            [np.array(c) for c in start_colors] if start_colors else None
        )

        self._start_colors = []
        self._end_colors = []
        self._current_colors = []
        self._color_steps = []
        self._current_frame = 0
        self._num_frames = 0
        self.num_inputs_to_match = 0
        self.num_outputs_to_match = 0

    def prepare_transition(self, start_colors: list, num_frames: int):
        self.reset()
        self._num_frames = num_frames
        # Determine start colors: prefer argument, then config, then random if needed
        if start_colors and len(start_colors) > 0:
            self._start_colors = [np.array(c) for c in start_colors]
        elif self._start_colors_config is not None:
            self._start_colors = list(self._start_colors_config)
        elif self._random:
            count = self.num_inputs_to_match or self.num_outputs_to_match or 1
            self._start_colors = [
                _generate_random_color() for _ in range(count)
            ]
        else:
            self._start_colors = [np.array([0, 0, 0])]

        if (
            self.num_inputs_to_match > 0
            and len(self._start_colors) != self.num_inputs_to_match
        ):
            if len(self._start_colors) > self.num_inputs_to_match:
                self._start_colors = self._start_colors[
                    : self.num_inputs_to_match
                ]
            else:
                last_color = (
                    self._start_colors[-1]
                    if self._start_colors
                    else _generate_random_color()
                )
                while len(self._start_colors) < self.num_inputs_to_match:
                    self._start_colors.append(last_color)

        num_final_colors = self.num_outputs_to_match or len(self._start_colors)

        if self._random:
            self._end_colors = [
                _generate_random_color() for _ in range(num_final_colors)
            ]
        else:
            self._end_colors = list(self._end_colors_config)

        if len(self._end_colors) != len(self._start_colors):
            if len(self._end_colors) > len(self._start_colors):
                self._end_colors = self._end_colors[: len(self._start_colors)]
            else:
                last_color = (
                    self._end_colors[-1]
                    if self._end_colors
                    else _generate_random_color()
                )
                while len(self._end_colors) < len(self._start_colors):
                    self._end_colors.append(last_color)

        if self._num_frames > 0:
            self._color_steps = [
                (end - start) / self._num_frames
                for start, end in zip(self._start_colors, self._end_colors)
            ]
        self._current_colors = self._start_colors

    def next_colors(self) -> list[np.ndarray]:
        if self._current_frame >= self._num_frames:
            return self._end_colors

        self._current_colors = [
            start + step * self._current_frame
            for start, step in zip(self._start_colors, self._color_steps)
        ]
        self._current_frame += 1
        return self._current_colors

    @property
    def output_colors(self) -> list[np.ndarray]:
        return self._end_colors

    def apply_effect(self):
        # This effect does not directly manipulate the LED strip.
        pass

    def reset(self):
        self._current_frame = 0


class RepeatingEffectChain(LedEffect):
    def __init__(self, *effects_with_duration: Duration):
        if not effects_with_duration:
            raise ValueError(
                "RepeatingEffectChain requires at least one effect."
            )

        self._specs = effects_with_duration
        # Find the first non-TransitionColors effect to use as the primary effect
        self._primary_effect = None
        for spec in self._specs:
            if not isinstance(spec.effect, TransitionColors):
                self._primary_effect = spec.effect
                break
        if self._primary_effect is None:
            raise ValueError("RepeatingEffectChain requires at least one non-TransitionColors effect to draw to the strip.")

        super().__init__(
            self._primary_effect._strip, self._primary_effect.frame_speed_ms
        )

        self._total_frames = sum(spec.num_frames for spec in self._specs)
        self._current_frame = 0

        self._prepare_chain()

    def _prepare_chain(self):
        # Prepare each effect in the chain, allowing TransitionColors in any position
        self._primary_spec = self._specs[0]
        self._transition_specs = self._specs[1:]
        last_output_colors = None
        num_effects = len(self._specs)
        for i, spec in enumerate(self._specs):
            effect = spec.effect
            # Determine the required output color count for this effect
            next_input_count = None
            if i + 1 < num_effects:
                next_effect = self._specs[i + 1].effect
                # If the next effect has input_colors, use its required count
                if (
                    hasattr(next_effect, "input_colors")
                    and next_effect.input_colors
                ):
                    next_input_count = len(next_effect.input_colors)
                elif (
                    hasattr(next_effect, "num_inputs_to_match")
                    and getattr(next_effect, "num_inputs_to_match", 0) > 0
                ):
                    next_input_count = next_effect.num_inputs_to_match
                elif hasattr(next_effect, "expected_num_colors"):
                    next_input_count = next_effect.expected_num_colors
                elif hasattr(next_effect, "required_colors"):
                    next_input_count = next_effect.required_colors
                else:
                    # Fallback: try to use 1
                    next_input_count = 1
            if isinstance(effect, TransitionColors):
                # If this is the first effect, use its own config or random
                if last_output_colors is None:
                    if effect._end_colors_config:
                        start_colors = effect._end_colors_config
                    else:
                        start_colors = [
                            _generate_random_color()
                            for _ in range(next_input_count or 1)
                        ]
                else:
                    start_colors = last_output_colors
                effect.num_inputs_to_match = len(start_colors)
                effect.num_outputs_to_match = next_input_count or len(
                    start_colors
                )
                effect.prepare_transition(start_colors, spec.num_frames)
                last_output_colors = effect.output_colors
            else:
                # For non-TransitionColors, set input_colors if available
                if last_output_colors is not None:
                    effect.input_colors = last_output_colors
                last_output_colors = effect.output_colors
        self._final_loop_colors = last_output_colors

    def apply_effect(self):
        if self._total_frames == 0:
            self._primary_effect.apply_effect()
            return

        frame_in_cycle = self._current_frame % self._total_frames

        if frame_in_cycle == 0 and self._current_frame > 0:
            self._primary_effect.input_colors = self._final_loop_colors
            self._prepare_chain()

        # Walk through the chain to determine the current input colors for the primary effect
        frame_cursor = 0
        current_colors = None
        for spec in self._specs:
            duration_frames = spec.num_frames
            if frame_cursor <= frame_in_cycle < frame_cursor + duration_frames:
                effect = spec.effect
                if isinstance(effect, TransitionColors):
                    if current_colors is None:
                        # Use start colors if this is the first effect
                        current_colors = effect._start_colors
                    current_colors = effect.next_colors()
                else:
                    # This is the primary effect; set its input_colors
                    if current_colors is not None:
                        effect.input_colors = current_colors
                    break
            else:
                # For previous effects, update current_colors for the next effect
                effect = spec.effect
                if isinstance(effect, TransitionColors):
                    if current_colors is None:
                        current_colors = effect._start_colors
                    current_colors = effect.next_colors()
                else:
                    if current_colors is not None:
                        effect.input_colors = current_colors
                    current_colors = effect.output_colors
            frame_cursor += duration_frames

        self._primary_effect.apply_effect()
        self._current_frame += 1

    def reset(self):
        self._current_frame = 0
        self._primary_effect.reset()
        self._prepare_chain()

    @property
    def input_colors(self) -> list[np.ndarray]:
        return self._primary_effect.input_colors

    @input_colors.setter
    def input_colors(self, colors: list):
        self._primary_effect.input_colors = colors
        self.reset()


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
        amp_fact = self._y_increments[
            self._current_increment % self._pop_increments
        ]
        amplitude = amp_fact * self._bubble_amplitude
        colors = (
            np.cos(self._x_values + np.pi) + 1
        ).T * amplitude + self._base_color
        colors = np.clip(colors, 0, 255)
        self._strip[self._bubble_x_range[0] : self._bubble_x_range[1]] = colors
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
