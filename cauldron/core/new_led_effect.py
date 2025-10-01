import abc
import math
import numpy as np
import random

from cauldron.core.led_strip import LedStrip


TWO_PI = math.tau if hasattr(math, "tau") else 2 * math.pi


class LedEffect(abc.ABC):
    """
    Abstract base class for an LED effect.

    An LedEffect modifies an LedStrip based on a given time `t`.
    """

    def __init__(self, strip: LedStrip):
        self._strip = strip

    @abc.abstractmethod
    def update(self, t: float):
        """
        Updates the LED strip to render the effect for the current animation frame.

        This method should be deterministic; for a given `t`, it should
        always produce the same output on the strip.

        Args:
            strip: The LedStrip object to be modified.
            t: The current time in seconds since the animation started.
        """

    @property
    def input_colors(self) -> list[np.ndarray]:
        """Gets the current input colors of the effect."""
        pass

    @input_colors.setter
    def input_colors(self, colors: list):
        """Sets the input colors for the effect."""
        pass

    @property
    def output_colors(self) -> list[np.ndarray]:
        """The colors to be passed to the next effect. Defaults to input_colors."""
        pass

    @abc.abstractmethod
    def reset(self):
        pass


class EffectWithDuration:
    """A container to associate an effect with a duration."""

    def __init__(self, effect: LedEffect, seconds: float):
        self.effect = effect
        self.seconds = seconds


class EffectChain(LedEffect):
    """
    Runs a sequence of effects for specified durations, looping the sequence.
    Each element is a Duration(effect, seconds).
    """

    def __init__(self, strip: LedStrip, durations: list[EffectWithDuration]):
        super().__init__(strip)
        assert durations, "EffectChain requires at least one Duration."
        self._durations = durations
        self._total_time = sum(d.seconds for d in durations)

    def update(self, t: float):
        # t is time in seconds since animation start
        t_mod = t % self._total_time
        elapsed = 0.0
        for duration in self._durations:
            if t_mod < elapsed + duration.seconds:
                # Run the effect with time offset
                self._strip[:] = duration.effect.input_colors[0]
                duration.effect.update(t_mod - elapsed)
                break
            elapsed += duration.seconds

    @property
    def input_colors(self) -> list[np.ndarray]:
        # Return input colors of all effects
        return [
            color for d in self._durations for color in d.effect.input_colors
        ]

    @input_colors.setter
    def input_colors(self, colors: list):
        # Distribute colors to effects
        idx = 0
        for d in self._durations:
            n = len(d.effect.input_colors)
            d.effect.input_colors = colors[idx : idx + n]
            idx += n

    @property
    def output_colors(self) -> list[np.ndarray]:
        return [
            color for d in self._durations for color in d.effect.output_colors
        ]

    def reset(self):
        for d in self._durations:
            d.effect.reset()


class TravelingLightEffect(LedEffect):
    def __init__(
        self,
        strip: LedStrip,
        colors: list,
        tail_length: int = 10,
        rps: float = 1.0,
        fade_type: str = "exponential",  # 'exponential' or 'linear'
        reverse: bool = False,
        start_index: int = 0,
    ):
        """
        A traveling light with a fading tail using an exponential curve.
        Args:
            strip: The LedStrip to apply the effect on.
            colors: [background, head] colors as RGB tuples or arrays.
            tail_length: Number of LEDs in the fading tail.
            rps: Revolutions per second (speed of the traveling light).
            fade_type: Type of fade for the tail ('exponential' or 'linear').
        """
        super().__init__(strip)
        assert (
            len(colors) == 2
        ), "TravelingLightEffect requires exactly two colors."
        self._colors = colors
        self._tail_length = tail_length
        self._rps = rps
        assert fade_type in (
            "exponential",
            "linear",
        ), "fade_type must be 'exponential' or 'linear'"
        self._fade_type = fade_type
        self._direction = -1 if reverse else 1
        self._start_index = start_index

    def update(self, t: float):
        n_leds = self._strip.num_pixels()
        base = np.array(self._colors[0], dtype=float)
        head = np.array(self._colors[1], dtype=float)

        # Calculate head position (wraps around strip)
        pos = (
            self._start_index + self._direction * t * self._rps * n_leds
        ) % n_leds

        for i in range(self._tail_length + 1):
            led_idx = int((pos - self._direction * i) % n_leds)
            if i == 0:
                alpha = 1.0
            else:
                if self._fade_type == "exponential":
                    alpha = np.exp(-i / (self._tail_length / 3.0))
                elif self._fade_type == "linear":
                    alpha = max(0.0, 1.0 - i / self._tail_length)
                else:
                    alpha = 0.0  # fallback
            color = (1 - alpha) * base + alpha * head
            self._strip[led_idx] = color.astype(int)

    @property
    def input_colors(self) -> list[np.ndarray]:
        """Gets the current input colors of the effect."""
        return self._colors

    @input_colors.setter
    def input_colors(self, colors: list):
        """Sets the input colors for the effect."""
        self._colors = colors

    @property
    def output_colors(self) -> list[np.ndarray]:
        """The colors to be passed to the next effect. Defaults to input_colors."""
        return self._colors

    def reset(self):
        pass


class BubbleEffect(LedEffect):
    def __init__(
        self,
        strip: LedStrip,
        bubble_index: int,
        colors: list,
        bubble_length: int = 5,
        bubble_pop_speed: float = 3.0,  # seconds
    ):
        super().__init__(strip)
        assert bubble_index >= 0
        num_pixels = self._strip.num_pixels()
        assert bubble_index < num_pixels
        assert (
            len(colors) == 2
        ), "BubbleEffect expects 2 colors: [base, bubble]"
        self._bubble_index = bubble_index
        self._bubble_length = bubble_length
        self._bubble_pop_speed = bubble_pop_speed
        self._colors = [np.array(c, dtype=float) for c in colors]

        self._max_index = min(num_pixels, bubble_index + bubble_length)
        self._bubble_x_values = np.linspace(
            0, TWO_PI, self._max_index - self._bubble_index, endpoint=False
        )

    def update(self, t: float):
        # t is in seconds since animation start
        # Bubble pop progress: 0 (start) to 2 (end), then repeat
        duration = self._bubble_pop_speed
        if duration > 0:
            progress = (t / duration) % 2.0
        else:
            progress = 0.0
        # amplitude factor: grows (0-1), then falls (1-2)
        if progress <= 1.0:
            amp_fact = 0.5 * (1 + math.cos(math.pi + progress * math.pi))
        else:
            # reverse progress for fall
            fall_progress = progress - 1.0
            amp_fact = 0.5 * (
                1 + math.cos(2 * math.pi - fall_progress * math.pi)
            )
        base_color = self._colors[0]
        bubble_color = self._colors[1]
        amplitude = amp_fact * (bubble_color - base_color)
        colors = (np.cos(self._bubble_x_values + math.pi) + 1).reshape(
            -1, 1
        ) * amplitude + base_color
        colors = np.clip(colors, 0, 255)
        self._strip[self._bubble_index : self._max_index] = colors.astype(int)

    @property
    def input_colors(self) -> list[np.ndarray]:
        """Gets the current input colors of the effect."""
        return self._colors

    @input_colors.setter
    def input_colors(self, colors: list):
        """Sets the input colors for the effect."""
        assert len(colors) == 2
        self._colors = [
            np.array(colors[0], dtype=int),
            np.array(colors[1], dtype=int),
        ]

    @property
    def output_colors(self) -> list[np.ndarray]:
        """The colors to be passed to the next effect. Defaults to input_colors."""
        return self.input_colors

    def reset(self):
        pass


class MultiLedEffect(LedEffect):
    def __init__(self, strip: LedStrip, effects: list[LedEffect]):
        super().__init__(strip)
        self._effects = effects

    def update(self, t: float):
        self._strip[:] = self.input_colors[0]
        for effect in self._effects:
            effect.update(t)

    @property
    def input_colors(self) -> list[np.ndarray]:
        return [
            color for effect in self._effects for color in effect.input_colors
        ]

    @input_colors.setter
    def input_colors(self, colors: list):
        # Distribute colors to effects if possible
        idx = 0
        for effect in self._effects:
            n = len(effect.input_colors)
            effect.input_colors = colors[idx : idx + n]
            idx += n

    @property
    def output_colors(self) -> list[np.ndarray]:
        return [
            color for effect in self._effects for color in effect.output_colors
        ]

    def reset(self):
        for effect in self._effects:
            effect.reset()


class BubblingEffect(LedEffect):
    def __init__(
        self,
        strip: LedStrip,
        colors: list,
        bubble_lengths: list = [5, 7, 9],
        bubble_length_weights: list = [0.5, 0.25, 0.25],
        bubble_pop_speeds: list = [3, 4, 5],
        bubble_pop_speed_weights: list = [0.5, 0.25, 0.25],
        max_bubbles: int = 10,
        bubble_spawn_prob: float = 0.05,
    ):
        super().__init__(strip)
        assert (
            len(colors) == 2
        ), "BubblingEffect expects 2 colors: [base, bubble]"
        assert len(bubble_lengths) == len(bubble_length_weights)
        assert len(bubble_pop_speeds) == len(bubble_pop_speed_weights)
        assert 0 < bubble_spawn_prob <= 1
        self._colors = [np.array(c, dtype=float) for c in colors]
        self._bubble_lengths = bubble_lengths
        self._bubble_length_weights = bubble_length_weights
        self._bubble_pop_speeds = bubble_pop_speeds
        self._bubble_pop_speed_weights = bubble_pop_speed_weights
        self._max_bubbles = max_bubbles
        self._bubble_spawn_prob = bubble_spawn_prob
        self._num_pixels = self._strip.num_pixels()
        self._active_bubbles = (
            []
        )  # List of dicts: {"bubble": BubbleEffect, "start_time": float, "pop_speed": float}
        self._rng = random.Random()

    def update(self, t: float):
        # t is the current time in seconds
        # Remove finished bubbles
        self._active_bubbles = [
            b
            for b in self._active_bubbles
            if t - b["start_time"] < 2 * b["pop_speed"]
        ]

        # Possibly spawn a new bubble
        if (
            len(self._active_bubbles) < self._max_bubbles
            and self._rng.random() < self._bubble_spawn_prob
        ):
            # Find a free region
            occupied = np.zeros(self._num_pixels, dtype=bool)
            for b in self._active_bubbles:
                idx = b["bubble"]._bubble_index
                length = b["bubble"]._bubble_length
                occupied[idx : idx + length] = True
            # Try to find a free spot
            for _ in range(30):
                bubble_length = self._rng.choices(
                    self._bubble_lengths, weights=self._bubble_length_weights
                )[0]
                bubble_pop_speed = self._rng.choices(
                    self._bubble_pop_speeds,
                    weights=self._bubble_pop_speed_weights,
                )[0]
                bubble_index = self._rng.randint(
                    0, self._num_pixels - bubble_length
                )
                if not occupied[
                    bubble_index : bubble_index + bubble_length
                ].any():
                    bubble = BubbleEffect(
                        self._strip,
                        bubble_index,
                        self._colors,
                        bubble_length=bubble_length,
                        bubble_pop_speed=bubble_pop_speed,
                    )
                    self._active_bubbles.append(
                        {
                            "bubble": bubble,
                            "start_time": t,
                            "pop_speed": bubble_pop_speed,
                        }
                    )
                    break

        # Fill base color
        self._strip[:] = np.array(self._colors[0], dtype=int)
        # Draw all bubbles
        for b in self._active_bubbles:
            bubble_t = t - b["start_time"]
            b["bubble"].update(bubble_t)

    def input_colors(self) -> list[np.ndarray]:
        """Gets the current input colors of the effect."""
        return self._colors

    def input_colors(self, colors: list):
        """Sets the input colors for the effect."""
        assert len(colors) == 2
        self._colors = [
            np.array(colors[0], dtype=int),
            np.array(colors[1], dtype=int),
        ]

    def output_colors(self) -> list[np.ndarray]:
        """The colors to be passed to the next effect. Defaults to input_colors."""
        return self.input_colors

    def reset(self):
        pass
