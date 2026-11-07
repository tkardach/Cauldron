import unittest
from unittest.mock import Mock, patch

from cauldron.assets.manager import AssetManager


class TestAssetManager(unittest.TestCase):
    @patch("cauldron.assets.manager.AudioSegment.from_file")
    def test_load_audio_applies_requested_formatting(self, from_file):
        segment = Mock()
        segment.frame_rate = 44100
        segment.set_sample_width.return_value = segment
        segment.set_frame_rate.return_value = segment
        segment.__iadd__ = Mock(return_value=segment)
        from_file.return_value = segment

        result = AssetManager().load_audio(
            "bubbles.wav",
            sample_width=2,
            playback_rate_scale=0.25,
            gain_db=3,
        )

        self.assertIs(result, segment)
        segment.set_sample_width.assert_called_once_with(2)
        self.assertEqual(segment.frame_rate, 11025)
        segment.set_frame_rate.assert_not_called()
        segment.__iadd__.assert_called_once_with(3)

    def test_load_audio_rejects_unknown_assets_and_invalid_scale(self):
        manager = AssetManager()

        with self.assertRaises(ValueError):
            manager.load_audio("missing.wav")
        with self.assertRaises(ValueError):
            manager.load_audio("bubbles.wav", frame_rate_scale=0)
        with self.assertRaises(ValueError):
            manager.load_audio("bubbles.wav", playback_rate_scale=0)


if __name__ == "__main__":
    unittest.main()
