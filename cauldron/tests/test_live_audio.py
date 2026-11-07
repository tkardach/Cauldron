import unittest
from unittest.mock import Mock, patch

import numpy as np

from cauldron.core.live_audio import LiveBrightnessAnalyzer
from cauldron.core.players import RealtimeAudioPlayer
from cauldron.core.led_strip import MockStrip


class TestLiveBrightnessAnalyzer(unittest.TestCase):
    def test_process_maps_rms_to_brightness_and_returns_input(self):
        strip = MockStrip(num_pixels=2)
        analyzer = LiveBrightnessAnalyzer(strip)
        audio = np.array([[0.5, -0.5], [0.5, -0.5]], dtype=np.float32)

        result = analyzer.process(audio, sample_rate=44100)

        self.assertIs(result, audio)
        self.assertAlmostEqual(strip.brightness, 0.5)

    def test_process_clamps_brightness_and_handles_empty_chunks(self):
        strip = MockStrip(num_pixels=2)
        analyzer = LiveBrightnessAnalyzer(strip)

        analyzer.process(np.array([2.0, -2.0], dtype=np.float32), 44100)
        self.assertEqual(strip.brightness, 1.0)

        analyzer.process(np.array([], dtype=np.float32), 44100)
        self.assertEqual(strip.brightness, 0.0)


class TestRealtimeAudioAnalyzerIntegration(unittest.TestCase):
    @patch("cauldron.core.players.AudioStream")
    def test_stop_closes_voice_stream_and_joins_reader(self, stream_type):
        stream = Mock()
        stream.plugins = []
        stream_type.return_value.__enter__.return_value = stream
        player = RealtimeAudioPlayer([])

        handle = player.loop()
        handle.stop_wait()

        self.assertFalse(player.is_playing())
        stream_type.return_value.__exit__.assert_called_once_with(
            None, None, None
        )

    @patch("cauldron.core.players.AudioStream")
    def test_analyzer_receives_live_chunks_after_audio_effects_are_attached(
        self, stream_type
    ):
        stream = Mock()
        stream.sample_rate = 44100
        stream.plugins = []
        chunk = np.ones((2, 1024), dtype=np.float32)
        player = RealtimeAudioPlayer([], visual_analyzer=Mock())

        def read_chunk():
            player._is_playing = False
            return chunk

        stream.read.side_effect = read_chunk
        stream_type.return_value.__enter__.return_value = stream
        player._is_playing = True

        player._loop()

        player._visual_analyzer.process.assert_called_once_with(chunk, 44100)
        self.assertFalse(player.is_playing())
        stream.read.assert_called_once_with()

    @patch("cauldron.core.players.AudioStream")
    def test_existing_effects_remain_in_stream_plugin_chain(self, stream_type):
        stream = Mock()
        stream.plugins = []
        stream.sample_rate = 44100
        effect = Mock()
        analyzer = Mock()
        player = RealtimeAudioPlayer([effect], visual_analyzer=analyzer)
        stream.read.side_effect = lambda: setattr(
            player, "_is_playing", False
        ) or np.zeros((1, 1024), dtype=np.float32)
        stream_type.return_value.__enter__.return_value = stream
        player._is_playing = True

        player._loop()

        self.assertEqual(stream.plugins, [effect])
        analyzer.process.assert_called_once()

    @patch("cauldron.core.players.AudioStream")
    def test_stop_wakes_analyzer_loop_without_cross_thread_close(self, stream_type):
        stream = Mock()
        stream.sample_rate = 44100
        stream.plugins = []
        stream.read.return_value = np.zeros((1, 0), dtype=np.float32)
        stream_type.return_value.__enter__.return_value = stream
        player = RealtimeAudioPlayer([], visual_analyzer=Mock())

        handle = player.loop()
        self.assertTrue(player.is_playing())
        handle.stop_wait()

        self.assertFalse(player.is_playing())
        stream.close.assert_not_called()


if __name__ == "__main__":
    unittest.main()
