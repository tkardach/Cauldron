import unittest
from unittest.mock import Mock, patch
import time
from pydub import AudioSegment

# Assuming cauldron.core is in the python path
from cauldron.core.players import (
    LedEffectPlayer,
    Handle,
)
from cauldron.core.led_effect import MockEffect
from cauldron.core.led_strip import MockStrip


class TestPlayers(unittest.TestCase):

    def setUp(self):
        """Set up common mock objects for tests."""
        self.mock_strip = MockStrip(num_pixels=10)
        self.mock_effect = MockEffect(self.mock_strip)
        self.mock_effect.update = Mock()

    def test_led_effect_player_loop(self):
        """Test that LedEffectPlayer loops correctly and can be stopped."""
        player = LedEffectPlayer(self.mock_effect)
        handle = player.loop()
        self.assertTrue(player.is_playing())
        time.sleep(0.05)  # Let the loop run a few times
        handle.stop_wait()
        self.assertFalse(player.is_playing())
        self.mock_effect.update.assert_called()

    def test_led_effect_player_play_for(self):
        """Test playing an effect for a specific duration."""
        player = LedEffectPlayer(self.mock_effect)
        duration = 0.1
        handle = player.play_for(duration)
        start_time = time.time()
        handle.wait_done()
        end_time = time.time()
        self.assertFalse(player.is_playing())
        self.assertAlmostEqual(end_time - start_time, duration, delta=0.05)

    def test_handle_stop(self):
        """Test that the Handle correctly stops its player."""
        mock_player = Mock(spec=LedEffectPlayer)
        handle = Handle(mock_player)
        handle.stop()
        mock_player.stop.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
