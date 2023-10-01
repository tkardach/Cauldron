import abc
from led.led_strip import LedStrip
import numpy as np
import threading


TWO_PI = np.pi * 2

class LedEffect(abc.ABC):
    def __init__(self):
        self.frame_speed_ms = 10

    @abc.abstractmethod
    def apply_effect(self, strip: LedStrip) -> None:
        return None


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
        bubble_index: int,
        num_pixels: int,
        wave_length: float = 1,
        bubble_pop_speed_ms: int = 250,
    ):
        """Initialize the BubbleEffect.

        This effect assumes a coordinate system with LEDs ranging from 0 to 2pi.

        Args:
            bubble_index: LED index to apply the bubble effect at.
            bubble_color: The color the wave will be converging to at its peak
            num_pixels: Number of pixels along the x-axis.
            wave_length: The width of the bubble in radians.
            bubble_pop_speed_ms: Speed which the bubble will dissipate.
            back to the base_color in milliseconds.
        """
        LedEffect.__init__(self)
        self._lock = threading.Lock()
        # Convert colors to numpy arrays
        self._base_color = np.array([base_color])
        self._bubble_color = np.array([bubble_color])
        self._bubble_index = bubble_index
        self._bubble_pop_speed_ms = bubble_pop_speed_ms
        self._wave_length = wave_length
        self._num_pixels = num_pixels

        # Compute how much the amplitude should change between each frame
        self._amplitude_inc = int(self._bubble_pop_speed_ms / self.frame_speed_ms)
        # Insure the amplitude increments are odd to optimize wave creation
        self._amplitude = np.array(self._bubble_color - self._base_color)

        theta_increment = self._bubble_pop_speed_ms / self.frame_speed_ms
        self._amplitude_step = np.arange(0, TWO_PI, TWO_PI / theta_increment)
        self._current_step = 0


    def apply_effect(self, strip: LedStrip) -> None:
        """Applies the sine wave effect onto the LedStrip."""
        with self._lock:
            # self._current_step += 1
            # self._current_step %= len(self._amplitude_step)
            # # Create the x-axis values for the wave. The cosine wave is as follows:
            # #  amplitude * sin((x + bubble_pixel) * (1 / wave_length)) + base_color
            # x_values = np.array([np.arange(0, self._wave_length, self._wave_length / wave_px)])
            # sin_wave = np.sin(x_values + x_values[:, self._bubble_index])
            # sin_wave = current_amp.T * sin_wave
            # # Create a filter of 0s, with 1s where we expect the bubble to be
            # last_index = min(self._bubble_index + wave_px, num_pixels - 1)
            # wave_indices = np.arange(self._bubble_index, last_index, 1)
            # wave_filter = np.zeros(x_values.shape).T
            # wave_filter[wave_indices.tolist()] = 1
            # wave_filter = sin_wave.T * wave_filter
            # x_full_range = np.array([np.arange(0, TWO_PI, TWO_PI / num_pixels)])
            # y_base_values = self._base_color * x_full_range
            # print(wave_filter)
            # y_values[:, wave_indices.tolist()] = self._base_color + wave_filter
            # print(sin_wave)
            # strip.fill_copy(np.floor(y_values))

            num_pixels = strip.num_pixels()
            wave_px = int(num_pixels * self._wave_length / TWO_PI)
            b = TWO_PI / self._wave_length
            current_amp = self._amplitude * np.sin(self._amplitude_step[self._current_step])
            # Create a full range of x values (0 -> 2PI)
            x_full_range = np.array([np.arange(0, TWO_PI, TWO_PI / num_pixels)]) # (1, num_pixels)
            # x_values = np.array([np.arange(0, self._wave_length, self._wave_length / wave_px)]) 
            # Create the full pixel array (num_pixels, 3), each row with base_color
            y_values = np.full((num_pixels, 3), self._base_color)

            # Create filter list of sine wave values (wave_length, 3)
            last_index = min(self._bubble_index + wave_px, num_pixels - 1)
            wave_indices = np.arange(self._bubble_index, last_index, 1)
            wave_x_values = np.array([np.arange(0, np.pi, np.pi / wave_px)])
            sin_wave = np.sin(wave_x_values + wave_x_values[:, self._bubble_index] * self._wave_length) + current_amp
            sin_wave = current_amp.T * sin_wave


            # Add the filtered list based on indices [bubble_index -> bubble_index + wave_length_px]

        strip.show()
