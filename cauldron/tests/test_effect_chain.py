import unittest
import numpy as np
from cauldron.core.led_strip import MockStrip
from cauldron.core.led_effect import MockEffect
from cauldron.core.effect_chain import (
    TimedEffect,
    TransitionEffect,
    RepeatingEffectChain,
)
import time


class DummyEffect(MockEffect):
    def __init__(self, strip, duration=0.1):
        super().__init__(strip)
        self.calls = 0
        self._duration = duration
        self._start = None

    def apply_effect(self):
        if self._start is None:
            self._start = time.time()
        self.calls += 1

    def is_done(self):
        if self._start is None:
            return False
        return (time.time() - self._start) >= self._duration

    def reset(self):
        self._start = None
        self.calls = 0


class TestEffectChain(unittest.TestCase):
    def test_timed_effect(self):
        strip = MockStrip(10)
        effect = TimedEffect(DummyEffect, strip, time_s=0.2)
        effect.reset()
        for _ in range(10):
            effect.apply_effect()
            if effect.is_done():
                break
        self.assertTrue(effect.is_done())

    def test_transition_effect(self):
        strip = MockStrip(10)
        effect = TransitionEffect(
            strip, transition_time_ms=100, random_color=False
        )
        effect.reset()
        for _ in range(10):
            effect.apply_effect()
            if effect.is_done():
                break
        self.assertTrue(effect.is_done())

    def test_repeating_chain(self):
        strip = MockStrip(10)
        e1 = TimedEffect(DummyEffect, strip, time_s=0.1)
        e2 = TimedEffect(DummyEffect, strip, time_s=0.1)
        chain = RepeatingEffectChain(e1, e2)
        chain.reset()
        # Should cycle through both effects
        for _ in range(30):
            chain.apply_effect()
        self.assertTrue(e1.calls > 0 and e2.calls > 0)


if __name__ == "__main__":
    unittest.main()
