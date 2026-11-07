import unittest
from unittest.mock import Mock, patch

from cauldron.core.cauldron import Cauldron, CauldronRunner
from cauldron.core.events import EventBus, Events


class TestCauldron(unittest.TestCase):
    def test_start_and_stop_manage_injected_loop_players(self):
        player = Mock()
        handle = Mock()
        handle.is_playing.return_value = True
        player.loop.return_value = handle
        cauldron = Cauldron([player], loop_players=[player])

        cauldron.start()

        player.loop.assert_called_once_with()
        self.assertTrue(cauldron.is_playing())
        cauldron.stop()
        handle.stop_wait.assert_called_once_with()
        self.assertFalse(cauldron.is_playing())

    def test_only_injected_players_can_be_started(self):
        cauldron = Cauldron([])

        with self.assertRaises(ValueError):
            cauldron.play(Mock())


class TestEventBus(unittest.TestCase):
    def test_publish_calls_subscribers_and_unsubscribe_removes_handler(self):
        bus = EventBus()
        handler = Mock()
        unsubscribe = bus.subscribe("command", handler)

        bus.publish("command", "payload")
        unsubscribe()
        bus.publish("command", "ignored")

        handler.assert_called_once_with("payload")

    def test_runner_broadcasts_commands_without_cauldron_reference(self):
        bus = EventBus()
        handler = Mock()
        bus.subscribe(Events.EXPLOSION, handler)
        runner = CauldronRunner(bus)

        with patch("builtins.input", side_effect=["e", "q"]):
            runner.run()

        handler.assert_called_once_with()

    def test_runner_toggles_bubbles(self):
        bus = EventBus()
        handler = Mock()
        bus.subscribe(Events.TOGGLE_BUBBLES, handler)
        runner = CauldronRunner(bus)

        with patch("builtins.input", side_effect=["b", "q"]):
            runner.run()

        handler.assert_called_once_with()
        self.assertIn("b: Toggle bubbles", runner._help_text())

    def test_runner_accepts_stop_and_quit_after_starting_a_voice(self):
        bus = EventBus()
        start_voice = Mock()
        stop_voice = Mock()
        quit_application = Mock()
        bus.subscribe(Events.START_VOICE, start_voice)
        bus.subscribe(Events.STOP_VOICE, stop_voice)
        bus.subscribe(Events.QUIT, quit_application)
        runner = CauldronRunner(bus, voice_names=["demon"])

        with patch("builtins.input", side_effect=["d", "s", "q"]):
            runner.run()

        start_voice.assert_called_once_with("demon")
        stop_voice.assert_called_once_with()
        quit_application.assert_called_once_with()

    def test_runner_formats_voice_help_as_alphabetical_aligned_list(self):
        runner = CauldronRunner(EventBus(), voice_names=["demon", "dragon", "witch"])

        self.assertIn(
            "Voices:\n  d : demon\n  dr: dragon\n  w : witch",
            runner._help_text(),
        )


if __name__ == "__main__":
    unittest.main()
