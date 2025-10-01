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


class TravelingLightEffect(LedEffect):
    def __init__(
        self,
        strip: LedStrip,
        colors: list,
        tail_length: int = 10,
        rps: float = 1.0,
        fade_type: str = "exponential",  # 'exponential' or 'linear'
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

    def update(self, t: float):
        n_leds = self._strip.num_pixels()
        base = np.array(self._colors[0], dtype=float)
        head = np.array(self._colors[1], dtype=float)

        # Calculate head position (wraps around strip)
        pos = (t * self._rps * n_leds) % n_leds
        led_colors = np.tile(base, (n_leds, 1))

        for i in range(self._tail_length + 1):
            led_idx = int((pos - i) % n_leds)
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
            led_colors[led_idx] = color

        self._strip[:] = led_colors.astype(int)

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


class BubblingEffect(LedEffect):
    def __init__(
        self,
        strip: LedStrip,
        colors: list,
        bubble_lengths: list,
        bubble_length_weights: list,
        bubble_pop_speeds: list,
        bubble_pop_speed_weights: list,
        max_bubbles: int,
        bubble_spawn_prob: float,
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
            if t - b["start_time"] < b["pop_speed"]
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
