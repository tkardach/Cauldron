import unittest
from unittest.mock import Mock, call, patch

from cauldron.application import _resolve_input_device, build_application
from cauldron.core.events import Events


class TestInputDeviceSelection(unittest.TestCase):
    @patch("cauldron.application.AudioStream")
    def test_uses_available_microphone_when_default_input_is_output(self, stream):
        stream.default_input_device_name = "SRS-XB10"
        stream.input_device_names = [
            "SRS-XB10",
            "MacBook Air Microphone",
        ]

        self.assertEqual(
            _resolve_input_device(None, "SRS-XB10"),
            "MacBook Air Microphone",
        )

    @patch("cauldron.application.AudioStream")
    def test_preserves_explicit_input_device(self, stream):
        stream.default_input_device_name = "SRS-XB10"
        stream.input_device_names = ["MacBook Air Microphone"]

        self.assertEqual(
            _resolve_input_device("USB Microphone", "SRS-XB10"),
            "USB Microphone",
        )

    @patch("cauldron.application.AudioStream")
    def test_keeps_distinct_system_default_input(self, stream):
        stream.default_input_device_name = "MacBook Air Microphone"

        self.assertEqual(
            _resolve_input_device(None, "SRS-XB10"),
            "MacBook Air Microphone",
        )


class TestBubbleControl(unittest.TestCase):
    def test_bubbles_start_off_and_toggle_on_then_off(self):
        with (
            patch("cauldron.application.AudioStream") as audio_stream,
            patch("cauldron.application.AssetManager"),
            patch("cauldron.application.Cauldron") as cauldron_type,
            patch("cauldron.application.EffectChain"),
            patch("cauldron.application.TransitionEffect"),
            patch("cauldron.application.AudioToBrightnessEffect"),
            patch("cauldron.application.LedEffectPlayer"),
            patch("cauldron.application.AudioPlayer"),
            patch("cauldron.application.RealtimeAudioPlayer"),
        ):
            audio_stream.default_output_device_name = "Output"
            audio_stream.default_input_device_name = "Input"
            cauldron = cauldron_type.return_value
            application = build_application(Mock())

            bubbling_visual_player, bubbling_audio_player = (
                cauldron_type.call_args.args[0][:2]
            )
            cauldron.loop.assert_not_called()
            application.runner._event_bus.publish(Events.TOGGLE_BUBBLES)
            cauldron.loop.assert_has_calls(
                [call(bubbling_visual_player), call(bubbling_audio_player)]
            )

            application.runner._event_bus.publish(Events.TOGGLE_BUBBLES)
            cauldron.stop_player.assert_has_calls(
                [call(bubbling_visual_player), call(bubbling_audio_player)]
            )


if __name__ == "__main__":
    unittest.main()
