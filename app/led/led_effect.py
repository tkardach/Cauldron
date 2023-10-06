import abc
from led.led_strip import LedStrip
from numpy.random import choice
import numpy as np
import matplotlib.animation as animation
import matplotlib.pyplot as plt
import random
import threading
import time


TWO_PI = np.pi * 2


class LedEffect(abc.ABC):
    def __init__(self):
        self.frame_speed_ms = 10

    @abc.abstractmethod
    def apply_effect(self, strip: LedStrip) -> None:
        return None


class EffectHandle:
    def __init__(self, player: "EffectPlayer"):
        self._player = player

    def stop(self) -> None:
        self._player.stop()


class EffectPlayer(abc.ABC):
    def __init__(self, strip: LedStrip, effect: LedEffect):
        self._strip = strip
        self._effect = effect

    @abc.abstractmethod
    def play(self) -> EffectHandle:
        return None

    @abc.abstractmethod
    def stop(self):
        return None


class MockEffectPlayer(EffectPlayer):
    def __init__(self, strip: LedStrip, effect: LedEffect):
        EffectPlayer.__init__(self, strip, effect)
        self._lock = threading.Lock()
        self._handle = None

    def _loop_effect(self):
        num_pixels = self._strip.num_pixels()
        x = np.arange(0, num_pixels, 1)
        y = [3] * num_pixels
        fig, ax = plt.subplots()
        ax.set(xlim=[0, num_pixels], ylim=[0, 6])

        # Create scatter plot to simulate LEDs
        scat = plt.scatter(x, y, s=50)

        # Create set_pixels callback to change the LED scatter plot dot colors
        def set_pixels(pixels: np.array):
            scat.set_color(pixels / 255.0)

        # Set the show callback to update the pixel colors. This will call
        # set_pixels when LedStrip.show is called.
        self._strip.set_show_callback(set_pixels)

        # Create the pyplot animation update method. This will update the
        # LedStrip pixels
        def update(_):
            self._effect.apply_effect(self._strip)
            return scat

        ani = animation.FuncAnimation(
            fig=fig,
            func=update,
            frames=40,
            interval=self._effect.frame_speed_ms,
        )
        plt.show()
        return EffectHandle(self)

    def play(self) -> EffectHandle:
        self._loop_effect()
        return None

    def stop(self) -> None:
        self._play_effect = False


class LedEffectPlayer(EffectPlayer):
    def __init__(self, strip: LedStrip, effect: LedEffect):
        EffectPlayer.__init__(self, strip, effect)
        self._play_effect = False
        self._handle = None
        self._lock = threading.Lock()

    def _loop_effect(self):
        while self._play_effect:
            self._effect.apply_effect(self._strip)
            time.sleep(self._effect.frame_speed_ms / 1000.0)

    def play(self) -> EffectHandle:
        with self._lock:
            if self._handle:
                return self._handle
            self._play_effect = True
            self._loop_thread = threading.Thread(
                target=self._loop_effect
            ).start()
            self._handle = EffectHandle(self)
            return self._handle

    def stop(self) -> None:
        self._play_effect = False


def play_effect(effect: LedEffect, strip: LedStrip):
    assert effect is not None
    assert strip is not None
    while True:
        effect.apply_effect(strip)
        time.sleep(effect.frame_speed_ms / 1000.0)


class SineWaveEffect(LedEffect):
    """Applies a modifyable sine wave effect onto an LedStrip."""

    def __init__(
        self,
        color0: list,
        color1: list,
        b: float = 1,
        oscillate: bool = False,
        oscillation_speed_ms: int = 250,
    ):
        assert len(color0) == len(color1)
        LedEffect.__init__(self)
        self._lock = threading.Lock()
        # Convert colors to numpy arrays
        self._color0 = np.array(color0)
        self._color1 = np.array(color1)
        self.oscillation_speed_ms = oscillation_speed_ms
        self._oscillate = oscillate
        self.wave_length = b

        # Offset the wave so that each color is above or equal to 0
        self._y_offsets = np.abs(
            (self._color0 - self._color1) / 2
        ) + np.minimum(self._color0, self._color1)
        # Keep track of the current amplitude value
        self._amplitudes = np.array([(self._color0 - self._color1) / 2])
        self._current_a = self._amplitudes.copy()
        # Compute how much the amplitude should change between each frame
        self._amplitude_inc = (2 * np.pi) / self._oscillation_inc
        self._amplitude_x = 0

    def _update_pixel_values_locked(self, x: np.array) -> np.array:
        """Returns the brightness value (y-value) of the sine wave.

        The sine wave equation is as follows:

        y = new color value
        x = x value for LED
        a = amplitude
        b = wave length
        y_offset = y offset

        y = a * sin(b * x) + y_offset

        If oscillation is on, the value of 'a' will range from "-a -> a" then
        "a -> -a" continuously.
        """
        assert self._lock.locked()
        pixels = np.zeros((len(x), len(self._current_a)))
        pixels = np.cos(self._b * x).T * self._current_a + self._y_offsets
        return pixels

    def _update_oscillation_locked(self):
        """Updates the sine wave variables if oscillation is on.

        Oscillation will cause the amplitude of the sine wave to range between
        "a -> -a" then "-a -> a" continuously.
        """
        assert self._lock.locked()
        if not self._oscillate:
            return
        self._amplitude_x += self._amplitude_inc
        self._current_a = self._amplitudes * np.cos(self._amplitude_x)

    def apply_effect(self, strip: LedStrip) -> None:
        """Applies the sine wave effect onto the LedStrip."""
        num_pixels = strip.num_pixels()
        x_values = np.array([np.arange(0, TWO_PI, TWO_PI / num_pixels)])
        with self._lock:
            pixels = self._update_pixel_values_locked(x_values)
            strip.fill_copy(pixels)
            self._update_oscillation_locked()

        strip.show()

    @property
    def wave_length(self) -> float:
        return self._b

    @wave_length.setter
    def wave_length(self, b: float) -> None:
        with self._lock:
            self._b = b

    @property
    def oscillate(self) -> bool:
        return self._oscillate

    @oscillate.setter
    def oscillate(self, enable: bool) -> None:
        with self._lock:
            self.oscillate = enable

    @property
    def oscillation_speed_ms(self) -> int:
        return self._oscillation_speed_ms

    @oscillation_speed_ms.setter
    def oscillation_speed_ms(self, speed_ms: int) -> None:
        with self._lock:
            self._oscillation_speed_ms = speed_ms
            self._oscillation_inc = speed_ms / self.frame_speed_ms


class BubbleEffect(LedEffect):
    """Applies a modifyable bubbling effect onto an LedStrip."""

    def __init__(
        self,
        base_color: list,
        bubble_color: list,
        max_bubble_count: int = 5,
        max_bubble_length: int = 7,
        spawn_chance: float = 0.2,
        spawn_interval_ms: int = 100,
        bubble_pop_speed_ms: int = 250,
    ):
        """Initialize the BubbleEffect."""
        LedEffect.__init__(self)
        self._min_bubble_length = 3
        self._lock = threading.Lock()
        # Convert colors to numpy arrays
        self._base_color = np.array([base_color])
        self._bubble_color = np.array([bubble_color])
        self._max_bubble_count = max_bubble_count
        self._max_bubble_length = max_bubble_length
        self._spawn_chance = spawn_chance
        self._spawn_interval_ms = spawn_interval_ms
        self._bubble_pop_speed_ms = bubble_pop_speed_ms
        self._current_iteration = 0
        self._spawn_iteration = 0

        # Example of weighted random values
        # sampleList = [100, 200, 300, 400, 500]
        # randomNumberList = numpy.random.choice(
        #     sampleList, 5, p=[0.05, 0.1, 0.15, 0.20, 0.5])

        self._bubble_indices = set()
        self._current_bubbles: list[list] = []
        self._bubble_y_values: list[np.array] = []
        for length in range(
            self._min_bubble_length, self._max_bubble_length + 1
        ):
            x_inc = 2 / length
            x_values = np.arange(0, 2 + 2 / x_inc, x_inc)
            # Calculate y values of the circle equation.
            self._bubble_y_values.append(np.sqrt(1 - (x_values - 1) ** 2))

    def _create_bubble_locked(self, num_pixels: int):
        """Create bubble with random size at random index."""
        assert self._lock.locked
        bubble_index = random.randrange(0, num_pixels + 1)
        while bubble_index in self._bubble_indices:
            bubble_index = random.randrange(0, num_pixels + 1)
        self._bubble_indices.add(bubble_index)
        bubble_length = random.randrange(
            self._min_bubble_length, self._max_bubble_length + 1
        )
        if bubble_length % 2 == 0:
            bubble_length += 1
        half_bubble = bubble_length / 2
        bubble_start = max(0, bubble_index - half_bubble)
        bubble_end = min(num_pixels - 1, bubble_index + half_bubble)
        self._current_bubbles.append((bubble_start, bubble_end))

    def _create_bubbles_locked(self, num_pixels: int):
        assert self._lock.locked
        num_pixels = num_pixels
        # If we have not maxed out our bubbles
        if len(self._bubble_indices) < self._max_bubble_count:
            spawn_bubbles = (
                self._current_iteration
                * self.frame_speed_ms
                / self._spawn_interval_ms
            ) < self._spawn_iteration
            if spawn_bubbles:
                return None

    def apply_effect(self, strip: LedStrip) -> None:
        """Applies the sine wave effect onto the LedStrip."""
        with self._lock:
            num_pixels = strip.num_pixels()
            if len(self._bubble_indices) < self._max_bubble_count:
                spawn_bubbles = (
                    self._current_iteration
                    * self.frame_speed_ms
                    / self._spawn_interval_ms
                ) < self._spawn_iteration
                if spawn_bubbles:
                    bubble_index = random.randrange(0, num_pixels + 1)
                    while bubble_index in self._bubble_indices:
                        bubble_index = random.randrange(0, num_pixels + 1)
                    self._bubble_indices.add(bubble_index)
                    bubble_length = random.randrange(
                        self._min_bubble_length, self._max_bubble_length + 1
                    )
                    if bubble_length % 2 == 0:
                        bubble_length += 1
                    half_bubble = bubble_length / 2
                    bubble_start = max(0, bubble_index - half_bubble)
                    bubble_end = min(
                        num_pixels - 1, bubble_index + half_bubble
                    )
                    self._current_bubbles.append((bubble_start, bubble_end))

            strip.show()
