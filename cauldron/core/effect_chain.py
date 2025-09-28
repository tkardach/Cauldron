import threading
import time
import random
from cauldron.core.led_effect import LedEffect
from cauldron.core.led_strip import LedStrip
import numpy as np


class TimedEffect(LedEffect):
    """
    Wraps another LedEffect and runs it for a specified amount of time (in seconds).
    """

    def __init__(self, effect_cls, *args, time_s=1.0, **kwargs):
        self._effect = effect_cls(*args, **kwargs)
        self._duration = time_s
        super().__init__(
            self._effect._strip, frame_speed_ms=self._effect.frame_speed_ms
        )
        self._start_time = None
        self._elapsed = 0

    def apply_effect(self):
        if self._start_time is None:
            self._start_time = time.time()
        self._effect.apply_effect()
        self._elapsed = time.time() - self._start_time

    def is_done(self):
        return self._elapsed >= self._duration

    def reset(self):
        self._effect.reset()
        self._start_time = None
        self._elapsed = 0


class ColorPairTransitionEffect(LedEffect):
    """
    Transitions the LED strip from one color pair (primary, secondary) to another over a given time.
    This is suitable for effects like BubbleEffect that use two colors.
    """

    def __init__(
        self,
        strip: LedStrip,
        start_colors,
        end_colors,
        transition_time_ms=1000,
        frame_speed_ms=100,
        fill_mode="gradient",
    ):
        super().__init__(strip, frame_speed_ms)
        self._transition_time = transition_time_ms / 1000.0
        self._start_time = None
        self._start_colors = np.array(start_colors)
        self._end_colors = np.array(end_colors)
        self._num_pixels = strip.num_pixels()
        self._fill_mode = fill_mode  # 'gradient' or 'split'

    def apply_effect(self):
        now = time.time()
        if self._start_time is None:
            self._start_time = now
        t = (now - self._start_time) / self._transition_time
        t = np.clip(t, 0, 1)
        color0 = (1 - t) * self._start_colors[0] + t * self._end_colors[0]
        color1 = (1 - t) * self._start_colors[1] + t * self._end_colors[1]
        if self._fill_mode == "split":
            # First half: color0, second half: color1
            split = self._num_pixels // 2
            self._strip[:split] = color0.astype(np.uint8)
            self._strip[split:] = color1.astype(np.uint8)
        else:
            # Linear gradient from color0 to color1
            for i in range(self._num_pixels):
                frac = i / max(1, self._num_pixels - 1)
                c = (1 - frac) * color0 + frac * color1
                self._strip[i] = c.astype(np.uint8)
        self._strip.show()

    def is_done(self):
        if self._start_time is None:
            return False
        return (time.time() - self._start_time) >= self._transition_time

    def reset(self):
        self._start_time = None


class RepeatingEffectChain(LedEffect):
    """
    Chains multiple LedEffects, running each in sequence, then repeats the chain.
    Each effect must implement is_done().
    """

    def __init__(self, *effects):
        assert len(effects) > 0
        self._effects = effects
        self._current = 0
        super().__init__(
            effects[0]._strip, frame_speed_ms=effects[0].frame_speed_ms
        )

    def apply_effect(self):
        effect = self._effects[self._current]
        effect.apply_effect()
        if hasattr(effect, "is_done") and effect.is_done():
            effect.reset()
            self._current = (self._current + 1) % len(self._effects)

    def reset(self):
        for e in self._effects:
            e.reset()
        self._current = 0
