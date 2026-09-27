import abc
from enum import Enum
import logging
import math
import numpy as np
from pydub import AudioSegment
import random
import threading

from cauldron.core.led_strip import LedStrip

TWO_PI = math.tau if hasattr(math, "tau") else 2 * math.pi


class LedEffect(abc.ABC):
    """
    Abstract base class for an LED effect.

    An LedEffect modifies an LedStrip based on a given time `t`.
    """

    def __init__(self, strip: LedStrip):
        self._strip = strip
        self._internal_show_enabled = True

    def show(self):
        if self._internal_show_enabled:
            self._strip.show()

    def disable_internal_show(self):
        """Disables internal show calls for this effect."""
        self._internal_show_enabled = False

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


class MockEffect(LedEffect):
    def __init__(self, strip: LedStrip):
        LedEffect.__init__(self, strip)

    def apply_effect(self):
        return None

    def reset(self):
        return None

    def update(self, t: float):
        return None


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
        self._prev_output_colors = None
        self._last_effect_color = None
        self._last_active_idx = None  # Track last active effect index

    def update(self, t: float):
        # t is time in seconds since animation start
        t_mod = t % self._total_time
        elapsed = 0.0
        active_idx = None
        for idx, duration in enumerate(self._durations):
            if t_mod < elapsed + duration.seconds:
                active_idx = idx
                # Before running, set input_colors from previous effect's output_colors (unless first)
                if idx == 0:
                    self._prev_output_colors = self._last_effect_color
                if self._prev_output_colors is not None:
                    duration.effect.input_colors = self._prev_output_colors
                if duration.effect.input_colors:
                    self._strip[:] = duration.effect.input_colors[0]
                # Run the effect with time offset
                duration.effect.update(t_mod - elapsed)
                self.show()
                if idx == len(self._durations) - 1:
                    self._last_effect_color = duration.effect.output_colors
                break
            self._prev_output_colors = duration.effect.output_colors
            elapsed += duration.seconds

            next_idx = (self._last_active_idx + 1) % len(self._durations)
            if active_idx != next_idx:
                self._durations[next_idx].effect.reset()
        self._last_active_idx = active_idx

    def _disable_children_internal_show(self):
        for d in self._durations:
            d.effect.disable_internal_show()

    def disable_internal_show(self):
        self._internal_show_enabled = False
        self._disable_children_internal_show()

    @property
    def input_colors(self) -> list[np.ndarray]:
        # Return input colors of all effects
        return [color for d in self._durations for color in d.effect.input_colors]

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
        return [color for d in self._durations for color in d.effect.output_colors]

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
        assert len(colors) == 2, "TravelingLightEffect requires exactly two colors."
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
        pos = (self._start_index + self._direction * t * self._rps * n_leds) % n_leds

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
        self.show()

    @property
    def input_colors(self) -> list[np.ndarray]:
        """Gets the current input colors of the effect."""
        return self._colors

    @input_colors.setter
    def input_colors(self, colors: list):
        """Sets the input colors for the effect."""
        for idx, color in enumerate(colors):
            if idx >= len(self._colors):
                break
            self._colors[idx] = np.array(color, dtype=int)

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
        assert len(colors) == 2, "BubbleEffect expects 2 colors: [base, bubble]"
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
            amp_fact = 0.5 * (1 + math.cos(2 * math.pi - fall_progress * math.pi))
        base_color = self._colors[0]
        bubble_color = self._colors[1]
        amplitude = amp_fact * (bubble_color - base_color)
        self._strip[:] = base_color.astype(int)
        colors = (np.cos(self._bubble_x_values + math.pi) + 1).reshape(
            -1, 1
        ) * amplitude + base_color
        colors = np.clip(colors, 0, 255)
        self._strip[self._bubble_index : self._max_index] = colors.astype(int)
        self.show()

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


class TransitionEffect(LedEffect):
    def __init__(
        self,
        strip: LedStrip,
        target_colors: list = None,
        duration: float = 2.0,
        randomize: bool = False,
        per_led_rates: list = None,
    ):
        """
        Transition each LED from its current color to a target color over a duration.
        Args:
            strip: The LedStrip to apply the effect on.
            target_colors: List of target colors (RGB tuples/arrays) for each LED, or a single color for all.
            duration: Duration of the transition in seconds.
            randomize: If True, target colors are random per LED.
            per_led_rates: Optional list of rates (0-1) for each LED, controlling speed.
        """
        super().__init__(strip)
        self._duration = duration
        self._randomize = randomize
        self._num_pixels = self._strip.num_pixels()
        self._start_colors = None
        self._target_colors = None
        self._per_led_rates = (
            per_led_rates if per_led_rates is not None else [1.0] * self._num_pixels
        )
        self._init_targets(target_colors)

    def _init_targets(self, target_colors):
        # Always capture current strip state as start colors
        self._start_colors = np.array(self._strip.get_pixels(), dtype=float)
        if self._randomize or target_colors is None:
            # Single random RGB color for all LEDs
            rand_color = np.random.randint(0, 256, 3)
            self._target_colors = np.array(rand_color, dtype=float)
        else:
            # Single color for all LEDs
            self._target_colors = np.array(target_colors, dtype=float)

    def update(self, t: float):
        # t: seconds since transition started
        if self._start_colors is None or self._target_colors is None:
            self._init_targets(self._target_colors)
        progress = np.clip(t / self._duration, 0.0, 1.0)
        # Each LED can have its own rate
        rates = np.array(self._per_led_rates)
        led_progress = np.clip(progress * rates, 0.0, 1.0)
        colors = (1 - led_progress[:, None]) * self._start_colors + led_progress[
            :, None
        ] * self._target_colors
        self._strip[:] = colors.astype(int)
        self.show()

    @property
    def input_colors(self) -> list:
        # Always ignore input_colors, return empty list
        return []

    @input_colors.setter
    def input_colors(self, _: list):
        pass

    @property
    def output_colors(self) -> list:
        return [self._target_colors] if self._target_colors is not None else []

    def reset(self):
        self._target_colors = None


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
        assert len(colors) == 2, "BubblingEffect expects 2 colors: [base, bubble]"
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
            b for b in self._active_bubbles if t - b["start_time"] < 2 * b["pop_speed"]
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
                bubble_index = self._rng.randint(0, self._num_pixels - bubble_length)
                if not occupied[bubble_index : bubble_index + bubble_length].any():
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
        self.show()

    def disable_internal_show(self):
        self._internal_show_enabled = False
        for b in self._active_bubbles:
            b["bubble"].disable_internal_show()

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


class AudioToBrightnessEffect(LedEffect):
    """
    Changes the brightness of the LedStrip based on AudioSegment volume.
    Uses update(t) for animation.
    """

    def __init__(self, strip: LedStrip, segment: AudioSegment):
        super().__init__(strip)
        self._lock = threading.Lock()
        data = np.array(segment.get_array_of_samples())
        data = np.abs(data.astype(np.int32))
        self._normalized_data = (data - np.min(data)) / (np.max(data) - np.min(data))
        self._duration_s = segment.duration_seconds
        self._total_frames = len(self._normalized_data)
        self._starting_brightness = None
        self._last_t = None

    def update(self, t: float):
        # t: seconds since animation start
        if self._starting_brightness is None:
            self._starting_brightness = self._strip.brightness
        # Map t to frame index
        frame_idx = int((t / self._duration_s) * self._total_frames)
        frame_idx = np.clip(frame_idx, 0, self._total_frames - 1)
        brightness = np.clip(
            self._normalized_data[frame_idx] + self._starting_brightness,
            0,
            1,
        )
        self._strip.brightness = brightness
        self.show()

    @property
    def input_colors(self) -> list:
        return []

    @input_colors.setter
    def input_colors(self, colors: list):
        pass

    @property
    def output_colors(self) -> list:
        return []

    def reset(self):
        with self._lock:
            self._starting_brightness = None
            self._last_t = None


class BrightnessEffect(LedEffect):
    """
    Changes the brightness of the LedStrip using update(t).
    If input_colors is set, expects a single float value [brightness].
    """

    def __init__(self, strip: LedStrip, initial_brightness: float = None):
        super().__init__(strip)
        self._lock = threading.Lock()
        self._starting_brightness = (
            initial_brightness
            if initial_brightness is not None
            else self._strip.brightness
        )
        self._brightness = self._starting_brightness

    def update(self, t: float):
        # t is ignored; brightness is set via input_colors
        with self._lock:
            self._strip.brightness = self._brightness
        self.show()

    @property
    def input_colors(self) -> list:
        # Return current brightness as a list
        return [self._brightness]

    @input_colors.setter
    def input_colors(self, colors: list):
        # Expect a single float value
        with self._lock:
            if colors and isinstance(colors[0], (float, int)):
                self._brightness = float(colors[0])

    @property
    def output_colors(self) -> list:
        return [self._brightness]

    def reset(self):
        with self._lock:
            self._brightness = self._starting_brightness


class BoundaryCondition(Enum):
    """Defines how a ripple behaves once it reaches the edge of the grid.

    Attributes:
        REFLECTIVE: The ripple bounces off the edge and travels back.
        DISAPPEAR: The ripple is absorbed by the edge and disappears.
        WRAPPED: The ripple leaves one edge and re-enters on the opposite one.
    """

    REFLECTIVE = "reflective"
    DISAPPEAR = "disappear"
    WRAPPED = "wrapped"

    # Aliases so the documented "Reflective"/"Disappear"/"Wrapped" spelling
    # can be used as well (identical values become enum aliases).
    Reflective = "reflective"
    Disappear = "disappear"
    Wrapped = "wrapped"

    @classmethod
    def parse(cls, value) -> "BoundaryCondition":
        """Converts a string/enum into a BoundaryCondition."""
        if isinstance(value, cls):
            return value
        if isinstance(value, str):
            normalized = value.strip().lower()
            for member in cls:
                if normalized in (member.value, member.name.lower()):
                    return member
        raise ValueError(
            f"Invalid boundary condition: {value!r}. Expected one of "
            f"{[member.value for member in cls]}"
        )


class TimeMode(Enum):
    """Defines how the time value handed to `update()` is interpreted.

    Attributes:
        ABSOLUTE: `update(t)` receives the total elapsed time since the
            animation started (the convention used by the players).
        DELTA: `update(dt)` receives the time elapsed since the previous
            call to `update()`.
    """

    ABSOLUTE = "absolute"
    DELTA = "delta"

    @classmethod
    def parse(cls, value) -> "TimeMode":
        if isinstance(value, cls):
            return value
        if isinstance(value, str):
            normalized = value.strip().lower()
            for member in cls:
                if normalized in (member.value, member.name.lower()):
                    return member
        raise ValueError(
            f"Invalid time mode: {value!r}. Expected one of "
            f"{[member.value for member in cls]}"
        )


class WaterDropletEffect(LedEffect):
    """Simulates water droplets rippling across one or more LedStrips.

    The effect numerically integrates the 2D damped wave equation

        d^2u/dt^2 + 2 * gamma * du/dt = c^2 * (d^2u/dx^2 + d^2u/dy^2)

    where `u` is the vertical displacement of the water surface in meters,
    `c` is `wave_speed` (m/s) and `gamma` is derived from `damping`.  A
    second order accurate (leapfrog) finite difference stencil is used in
    both space and time:

        u[n+1] = (2*u[n] - u[n-1] + gamma*dt*u[n-1] + c^2*dt^2*laplacian(u[n]))
                 / (1 + gamma*dt)

    The LED brightness of every pixel is derived directly from the water
    surface displacement `u` at that pixel, so the LEDs literally render an
    (overhead) view of the simulated water surface.

    Multiple *equal length* strips can be supplied to build a 2 dimensional
    grid (strip `0` is the top row of the grid).  When a single strip is
    supplied the simulation degenerates to a 1 dimensional slice taken
    horizontally through the center of the water droplet.

    The simulation always advances using a fixed internal time step, which
    makes the state a pure function of the elapsed time. Arbitrary (and
    irregular) time intervals may therefore be handed to `update()` while
    still producing a deterministic, reproducible state.
    """

    #: Fraction of the maximum stable (CFL) time step used by default.
    CFL_SAFETY = 0.5
    #: Default [base, crest] colors used to render the water surface.
    DEFAULT_COLORS = [[0, 0, 0], [0, 128, 255]]
    #: Water displacement (meters) that maps to a fully lit LED.
    DEFAULT_BRIGHTNESS_SCALE = 0.01

    def __init__(
        self,
        led_strip: LedStrip | list,
        led_strip_length: float = 1.0,
        led_density: float = 60.0,
        damping: float = 0.9,
        wave_speed: float = 0.35,
        boundary_conditions: BoundaryCondition | str = (BoundaryCondition.REFLECTIVE),
        drop_amplitude: float = 0.01,
        drop_radius: float = 0.03,
        drop_frequency: float = 0.5,
        colors: list = None,
        strip_spacing: float = None,
        brightness_scale: float = None,
        seed: int = 0,
        time_step: float = None,
        time_mode: TimeMode | str = TimeMode.ABSOLUTE,
    ):
        """
        Args:
            led_strip: A single LedStrip or a list of equal length LedStrips.
                A list of strips is laid out as a grid (strip 0 is the top
                row) which renders a 3 dimensional, over-head view of the
                droplets. A single strip is treated as a horizontal slice
                through the center of the droplet.
            led_strip_length: Physical length of a single LED strip (meters).
            led_density: Number of LEDs per meter.
            damping: Fraction of the wave amplitude that survives one second
                of simulation, within (0, 1]. Larger values ring out for a
                long time, smaller values fizzle out quickly (thick liquids
                such as oil).
            wave_speed: Speed of the ripple across the grid in meters/second.
            boundary_conditions: A BoundaryCondition (or its string name)
                describing what happens when a ripple reaches an edge.
            drop_amplitude: Displacement (meters) caused by a single droplet.
                Heavier drops create brighter and longer lasting ripples.
            drop_radius: Physical radius (meters) of the droplet impact area.
            drop_frequency: Rate (drops/second) at which new droplets spawn.
                A value of 0 disables automatic droplets.
            colors: [base_color, crest_color] RGB colors used for rendering.
            strip_spacing: Physical distance (meters) between two adjacent
                strips. Defaults to the LED pitch (1 / led_density) which
                results in square grid cells.
            brightness_scale: Displacement (meters) that maps to a fully lit
                LED. Defaults to DEFAULT_BRIGHTNESS_SCALE (1cm) so that
                heavier droplets really do glow brighter and longer.
            seed: Seed used to deterministically place the droplets.
            time_step: Optional fixed simulation time step (seconds). By
                default the largest stable step (scaled by CFL_SAFETY) is
                used.
            time_mode: TimeMode.ABSOLUTE (default) treats the argument of
                `update()` as the total elapsed time; TimeMode.DELTA treats
                it as the time elapsed since the previous call.
        """
        strips = self._normalize_strips(led_strip)
        LedEffect.__init__(self, strips[0])
        self._strips = strips

        assert led_strip_length > 0, "led_strip_length must be positive"
        assert led_density > 0, "led_density must be positive"
        assert 0 < damping <= 1, "damping must be within (0, 1]"
        assert wave_speed > 0, "wave_speed must be positive"
        assert drop_amplitude > 0, "drop_amplitude must be positive"
        assert drop_radius > 0, "drop_radius must be positive"
        assert drop_frequency >= 0, "drop_frequency must not be negative"

        self._led_strip_length = float(led_strip_length)
        self._led_density = float(led_density)
        self._damping = float(damping)
        self._wave_speed = float(wave_speed)
        self._boundary_conditions = BoundaryCondition.parse(boundary_conditions)
        self._drop_amplitude = float(drop_amplitude)
        self._drop_radius = float(drop_radius)
        self._drop_frequency = float(drop_frequency)
        self._time_mode = TimeMode.parse(time_mode)
        self._seed = int(seed)
        self._lock = threading.Lock()

        # --- Geometry -----------------------------------------------------
        self._rows = len(self._strips)
        self._cols = self._strips[0].num_pixels()
        # Distance between two LEDs on the same strip (meters).
        self._dx = 1.0 / self._led_density
        # Distance between two strips (meters).
        self._dy = float(strip_spacing) if strip_spacing else self._dx
        self._width_m = self._cols * self._dx
        self._height_m = self._rows * self._dy
        expected_pixels = self._led_strip_length * self._led_density
        if abs(expected_pixels - self._cols) > 1.0:
            logging.warning(
                "WaterDropletEffect: %d LEDs at %.2f LEDs/m covers %.3fm but "
                "led_strip_length is %.3fm; using the physical LED pitch.",
                self._cols,
                self._led_density,
                self._width_m,
                self._led_strip_length,
            )
        # Physical coordinates (meters) of the center of every LED.
        self._x_coords = (np.arange(self._cols) + 0.5) * self._dx
        self._y_coords = (np.arange(self._rows) + 0.5) * self._dy

        # --- Physics ------------------------------------------------------
        # u ~ exp(-gamma * t): `damping` is the amplitude retained per second.
        self._gamma = 0.0 if self._damping >= 1 else -math.log(self._damping)
        self._dt = self._resolve_time_step(time_step)
        self._drop_interval = (
            1.0 / self._drop_frequency if self._drop_frequency > 0 else math.inf
        )

        # --- Rendering ----------------------------------------------------
        self._brightness_scale = float(
            brightness_scale if brightness_scale else self.DEFAULT_BRIGHTNESS_SCALE
        )
        assert self._brightness_scale > 0, "brightness_scale must be positive"
        self._colors = [
            np.array(c, dtype=float)
            for c in (colors if colors else self.DEFAULT_COLORS)
        ]
        assert (
            len(self._colors) == 2
        ), "WaterDropletEffect expects 2 colors: [base, crest]"

        self._reset_state()

    # ------------------------------------------------------------------
    # Construction helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _normalize_strips(led_strip: LedStrip | list) -> list:
        """Returns a list of LedStrips from a strip or a collection of them."""
        if isinstance(led_strip, LedStrip):
            strips = [led_strip]
        else:
            strips = list(led_strip)
        assert strips, "WaterDropletEffect requires at least one LedStrip."
        num_pixels = strips[0].num_pixels()
        assert num_pixels > 1, "LedStrips require at least 2 pixels."
        for strip in strips:
            assert isinstance(strip, LedStrip), "Expected a list of LedStrips."
            assert (
                strip.num_pixels() == num_pixels
            ), "All LED strips in the grid must have the same LED count."
        return strips

    def _resolve_time_step(self, time_step: float) -> float:
        """Returns a numerically stable, fixed simulation time step."""
        inv_squares = 1.0 / (self._dx**2)
        if self._rows > 1:
            inv_squares += 1.0 / (self._dy**2)
        # Courant-Friedrichs-Lewy stability condition.
        max_dt = 1.0 / (self._wave_speed * math.sqrt(inv_squares))
        if time_step is None:
            return self.CFL_SAFETY * max_dt
        time_step = float(time_step)
        assert time_step > 0, "time_step must be positive"
        if time_step > max_dt:
            logging.warning(
                "WaterDropletEffect: time_step %.5fs is unstable, clamping to "
                "%.5fs.",
                time_step,
                max_dt,
            )
            return max_dt
        return time_step

    def _reset_state(self):
        """(Re)initializes the simulation to t = 0."""
        shape = (self._rows, self._cols)
        # u[n] and u[n-1] water surface displacement grids (meters).
        self._u = np.zeros(shape, dtype=float)
        self._u_prev = np.zeros(shape, dtype=float)
        self._brightness = np.zeros(shape, dtype=float)
        self._step_index = 0
        self._sim_time_s = 0.0
        self._elapsed_time_s = 0.0
        self._next_drop_index = 0
        self._drops = []
        self._spawn_due_drops()
        self._render()

    # ------------------------------------------------------------------
    # Simulation
    # ------------------------------------------------------------------
    def _laplacian(self, u: np.ndarray) -> np.ndarray:
        """Second order finite difference Laplacian honouring the boundary."""
        if self._boundary_conditions == BoundaryCondition.WRAPPED:
            padded = np.pad(u, 1, mode="wrap")
        else:
            # Neumann (zero gradient) edges reflect the wave back. For the
            # "disappear" boundary the edge values are overwritten by the
            # absorbing boundary right after the update step.
            padded = np.pad(u, 1, mode="edge")

        laplacian = (padded[1:-1, 2:] + padded[1:-1, :-2] - 2.0 * u) / self._dx**2
        if self._rows > 1:
            laplacian += (padded[2:, 1:-1] + padded[:-2, 1:-1] - 2.0 * u) / self._dy**2
        return laplacian

    def _apply_absorbing_boundary(self, u_next: np.ndarray):
        """First order Mur absorbing boundary, ripples simply disappear."""
        u = self._u
        c_dt = self._wave_speed * self._dt
        # An absorbing edge needs an interior neighbour to extrapolate from;
        # axes shorter than 3 cells stay reflective instead.
        if self._cols > 2:
            kx = (c_dt - self._dx) / (c_dt + self._dx)
            # Evaluate every edge before assigning so the order never matters.
            left = u[:, 1] + kx * (u_next[:, 1] - u[:, 0])
            right = u[:, -2] + kx * (u_next[:, -2] - u[:, -1])
            u_next[:, 0] = left
            u_next[:, -1] = right
        if self._rows > 2:
            ky = (c_dt - self._dy) / (c_dt + self._dy)
            top = u[1, :] + ky * (u_next[1, :] - u[0, :])
            bottom = u[-2, :] + ky * (u_next[-2, :] - u[-1, :])
            u_next[0, :] = top
            u_next[-1, :] = bottom

    def _step(self):
        """Advances the wave simulation by exactly one fixed time step."""
        gamma_dt = self._gamma * self._dt
        u_next = (
            2.0 * self._u
            - self._u_prev
            + gamma_dt * self._u_prev
            + (self._wave_speed * self._dt) ** 2 * self._laplacian(self._u)
        ) / (1.0 + gamma_dt)

        if self._boundary_conditions == BoundaryCondition.DISAPPEAR:
            self._apply_absorbing_boundary(u_next)

        self._u_prev = self._u
        self._u = u_next
        self._step_index += 1
        self._sim_time_s = self._step_index * self._dt
        self._spawn_due_drops()

    def _advance_to(self, elapsed_time_s: float):
        """Simulates until `elapsed_time_s` seconds have elapsed."""
        elapsed_time_s = max(0.0, float(elapsed_time_s))
        # The state only depends on the number of fixed steps taken, which
        # makes it independent of how the time was chunked by the caller.
        target_steps = int(math.floor(elapsed_time_s / self._dt + 1e-9))
        if target_steps < self._step_index:
            # Time travelled backwards; re-simulate to stay deterministic.
            self._reset_state()
        while self._step_index < target_steps:
            self._step()
        self._elapsed_time_s = elapsed_time_s

    # ------------------------------------------------------------------
    # Droplets
    # ------------------------------------------------------------------
    def _spawn_due_drops(self):
        """Spawns every scheduled droplet that is due at the current time."""
        if self._drop_interval == math.inf:
            return
        while self._next_drop_index * self._drop_interval <= self._sim_time_s + 1e-9:
            self._spawn_scheduled_drop(self._next_drop_index)
            self._next_drop_index += 1

    def _spawn_scheduled_drop(self, drop_index: int):
        """Deterministically places the `drop_index`-th droplet."""
        rng = np.random.default_rng([abs(self._seed), abs(int(drop_index))])
        x = float(rng.uniform(0.0, self._width_m))
        if self._rows > 1:
            y = float(rng.uniform(0.0, self._height_m))
        else:
            # A single strip is a slice through the center of the droplet.
            y = self._height_m / 2.0
        self.add_drop(x, y)

    def add_drop(
        self, x: float, y: float = None, amplitude: float = None, radius: float = None
    ):
        """Adds a water droplet impact to the surface.

        Args:
            x: Position of the droplet along the strips, in meters.
            y: Position of the droplet across the strips, in meters.
                Defaults to the center of the grid.
            amplitude: Displacement of the droplet in meters. Defaults to
                `drop_amplitude`.
            radius: Radius of the splash zone in meters. Defaults to
                `drop_radius`.
        """
        amplitude = self._drop_amplitude if amplitude is None else float(amplitude)
        radius = self._drop_radius if radius is None else float(radius)
        assert radius > 0, "radius must be positive"
        y = self._height_m / 2.0 if y is None else float(y)

        dx = self._x_coords - float(x)
        dy = self._y_coords - y
        if self._boundary_conditions == BoundaryCondition.WRAPPED:
            # Use the minimum image distance so drops wrap around the edges.
            dx = (dx + self._width_m / 2.0) % self._width_m - self._width_m / 2.0
            if self._rows > 1:
                dy = (dy + self._height_m / 2.0) % self._height_m - self._height_m / 2.0
        if self._rows > 1:
            distance = np.sqrt(dy[:, None] ** 2 + dx[None, :] ** 2)
        else:
            distance = np.abs(dx)[None, :] * np.ones((self._rows, 1))

        # A raised cosine "crater" (smooth, finite support, zero gradient at
        # the rim) is the classic droplet impact initial condition.
        profile = np.where(
            distance <= radius,
            0.5 * (1.0 + np.cos(np.pi * np.minimum(distance / radius, 1.0))),
            0.0,
        )
        if not profile.any():
            # The splash zone is smaller than the LED pitch; light up the
            # LED closest to the impact so tiny drops are still simulated.
            profile[np.unravel_index(np.argmin(distance), distance.shape)] = 1.0
        displacement = -amplitude * profile
        # Displace u[n] and u[n-1] identically so the droplet starts at rest.
        self._u = self._u + displacement
        self._u_prev = self._u_prev + displacement
        self._drops.append(
            {
                "x": float(x),
                "y": y,
                "amplitude": amplitude,
                "radius": radius,
                "time": self._sim_time_s,
            }
        )
        self._render()

    # ------------------------------------------------------------------
    # Rendering
    # ------------------------------------------------------------------
    def _render(self):
        """Derives the LED colors from the water surface displacement."""
        self._brightness = np.clip(np.abs(self._u) / self._brightness_scale, 0.0, 1.0)
        base, crest = self._colors[0], self._colors[1]
        colors = (
            base[None, None, :]
            + self._brightness[:, :, None] * (crest - base)[None, None, :]
        )
        pixels = np.clip(np.rint(colors), 0, 255).astype(int)
        for row, strip in enumerate(self._strips):
            strip[:] = pixels[row]

    def show(self):
        """Pushes the pixel data of every strip in the grid."""
        if self._internal_show_enabled:
            for strip in self._strips:
                strip.show()

    def update(self, t: float):
        """Renders the water surface for the given time.

        Args:
            t: Elapsed time in seconds since the animation started when the
                effect uses TimeMode.ABSOLUTE (default), otherwise the time
                delta since the previous `update()` call.
        """
        with self._lock:
            if self._time_mode == TimeMode.DELTA:
                self._advance_to(self._elapsed_time_s + max(0.0, float(t)))
            else:
                self._advance_to(t)
            self._render()
        self.show()

    # ------------------------------------------------------------------
    # Introspection helpers (useful for tests/visualization)
    # ------------------------------------------------------------------
    @property
    def led_strips(self) -> list:
        """The LedStrips that make up the grid (index 0 is the top row)."""
        return self._strips

    @property
    def grid_shape(self) -> tuple:
        """(rows, columns) shape of the LED grid."""
        return (self._rows, self._cols)

    @property
    def displacement(self) -> np.ndarray:
        """The water surface displacement `u` (meters) of every LED."""
        return self._u.copy()

    @property
    def brightness_grid(self) -> np.ndarray:
        """Normalized [0, 1] brightness derived from `u` for every LED."""
        return self._brightness.copy()

    @property
    def time_step(self) -> float:
        """The fixed simulation time step in seconds."""
        return self._dt

    @property
    def simulation_time(self) -> float:
        """The time (seconds) that has actually been simulated."""
        return self._sim_time_s

    @property
    def drop_count(self) -> int:
        """Number of droplets that have hit the surface so far."""
        return len(self._drops)

    @property
    def boundary_conditions(self) -> BoundaryCondition:
        return self._boundary_conditions

    def get_displacement(self, row: int, col: int) -> float:
        """Returns the water displacement (meters) of a single LED."""
        return float(self._u[row, col])

    def get_brightness(self, row: int, col: int) -> float:
        """Returns the normalized brightness [0, 1] of a single LED."""
        return float(self._brightness[row, col])

    def get_pixel(self, row: int, col: int) -> np.ndarray:
        """Returns the RGB value of a single LED in the grid."""
        return np.array(self._strips[row][col])

    # ------------------------------------------------------------------
    # LedEffect interface
    # ------------------------------------------------------------------
    @property
    def input_colors(self) -> list:
        """[base_color, crest_color] used to render the water surface."""
        return self._colors

    @input_colors.setter
    def input_colors(self, colors: list):
        if not colors:
            return
        assert len(colors) == 2, "WaterDropletEffect expects [base, crest]"
        self._colors = [np.array(c, dtype=float) for c in colors]

    @property
    def output_colors(self) -> list:
        return self._colors

    def reset(self):
        """Resets the simulation back to a flat water surface at t = 0."""
        with self._lock:
            self._reset_state()
