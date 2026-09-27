import unittest
from unittest.mock import Mock, patch
import time
import numpy as np
from pedalboard.io import AudioStream as PedalboardAudioStream
from pydub import AudioSegment

# Assuming cauldron.core is in the python path
from cauldron.core.players import (
    AudioPlayer,
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

    @patch("cauldron.core.players.AudioStream")
    def test_audio_player_writes_float_audio_and_finishes(self, mock_stream_type):
        mock_stream_type.default_output_device_name = (
            PedalboardAudioStream.default_output_device_name
        )
        stream = Mock()
        mock_stream_type.return_value.__enter__.return_value = stream
        segment = AudioSegment.silent(
            duration=100, frame_rate=44100
        ).set_channels(2)

        player = AudioPlayer(segment)
        handle = player.play()
        handle.wait_done()

        mock_stream_type.assert_called_once_with(
            output_device_name=PedalboardAudioStream.default_output_device_name,
            sample_rate=44100,
            num_output_channels=2,
        )
        written_frames = sum(
            call.args[0].shape[1] for call in stream.write.call_args_list
        )
        self.assertEqual(written_frames, 4410)
        for call in stream.write.call_args_list:
            audio, sample_rate = call.args
            self.assertEqual(audio.dtype, np.float32)
            self.assertEqual(sample_rate, 44100)
        self.assertFalse(player.is_playing())

    @patch("cauldron.core.players.AudioStream")
    def test_audio_player_loop_uses_configured_output(self, mock_stream_type):
        stream = Mock()
        mock_stream_type.return_value.__enter__.return_value = stream
        player = AudioPlayer(
            AudioSegment.silent(duration=100, frame_rate=44100),
            output_device_name="Test Output",
        )
        stream.write.side_effect = lambda *_: setattr(
            player, "_is_playing", False
        )

        handle = player.loop()
        handle.wait_done()

        mock_stream_type.assert_called_once_with(
            output_device_name="Test Output",
            sample_rate=44100,
            num_output_channels=1,
        )
        stream.write.assert_called_once()
        self.assertFalse(player.is_playing())


if __name__ == "__main__":
    unittest.main()
