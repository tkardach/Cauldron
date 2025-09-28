import unittest
from unittest.mock import Mock, patch
import time
from pydub import AudioSegment

# Assuming cauldron.core is in the python path
from cauldron.core.players import (
    LedEffectPlayer,
    AudioPlayer,
    AudioVisualPlayer,
    Handle,
)
from cauldron.core.led_effect import MockEffect
from cauldron.core.led_strip import MockStrip


class TestPlayers(unittest.TestCase):

    def setUp(self):
        """Set up common mock objects for tests."""
        self.mock_strip = MockStrip(num_pixels=10)
        self.mock_effect = MockEffect(self.mock_strip)
        # Mock the apply_effect to avoid complex calculations in player tests
        self.mock_effect.apply_effect = Mock()

    def test_led_effect_player_loop(self):
        """Test that LedEffectPlayer loops correctly and can be stopped."""
        player = LedEffectPlayer(self.mock_effect)
        handle = player.loop()
        self.assertTrue(player.is_playing())
        time.sleep(0.05)  # Let the loop run a few times
        handle.stop_wait()
        self.assertFalse(player.is_playing())
        self.mock_effect.apply_effect.assert_called()

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

    @patch("simpleaudio.play_buffer")
    def test_audio_player_play(self, mock_play_buffer):
        """Test that AudioPlayer plays a segment and stops."""
        # Create a short, silent audio segment for testing
        silent_segment = AudioSegment.silent(duration=100)

        # Mock the play object returned by play_buffer
        mock_play_obj = Mock()
        mock_play_buffer.return_value = mock_play_obj

        player = AudioPlayer(silent_segment)
        handle = player.play()
        handle.wait_done()

        mock_play_buffer.assert_called_once()
        mock_play_obj.wait_done.assert_called_once()
        self.assertFalse(player.is_playing())

    def test_audiovisual_player(self):
        """Test that AudioVisualPlayer coordinates audio and effect players."""
        # Create mock players with mock methods
        mock_effect_player = Mock(spec=LedEffectPlayer)
        mock_audio_player = Mock(spec=AudioPlayer)
        mock_audio_player.duration_seconds.return_value = 0.1

        # Mock the handles returned by the players
        mock_effect_handle = Mock(spec=Handle)
        mock_effect_handle.is_playing.side_effect = [True, False]
        mock_audio_handle = Mock(spec=Handle)
        mock_audio_handle.is_playing.side_effect = [True, False]

        mock_effect_player.play_for.return_value = mock_effect_handle
        mock_audio_player.play.return_value = mock_audio_handle

        av_player = AudioVisualPlayer(mock_effect_player, mock_audio_player)
        av_handle = av_player.play()
        av_handle.wait_done()  # This should wait for both mocked handles to be "done"

        mock_audio_player.play.assert_called_once()
        mock_effect_player.play_for.assert_called_once_with(0.1)

    def test_handle_stop(self):
        """Test that the Handle correctly stops its player."""
        mock_player = Mock(spec=LedEffectPlayer)
        handle = Handle(mock_player)
        handle.stop()
        mock_player.stop.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
