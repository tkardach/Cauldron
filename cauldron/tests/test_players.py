import led_effect
import led_strip
import players
import unittest


NUM_PIXELS = 50


class TestPlayers(unittest.TestCase):
    def test_led_effect_start_stop(self):
        strip = led_strip.MockStrip(NUM_PIXELS)
        effect = led_effect.MockEffect(strip)
        player = players.LedEffectPlayer(effect)
        self.assertFalse(player.is_playing())
        handle = player.play()
        self.assertTrue(handle.is_playing())
        self.assertTrue(player.is_playing())
        handle.stop()
        self.assertFalse(handle.is_playing())
        self.assertFalse(player.is_playing())
        handle.wait_done()
        # Create multiple handles
        handle = player.play()
        handle = player.play()
        handle = player.play()
        handle = player.play()
        handle.stop()
        self.assertFalse(handle.is_playing())
        self.assertFalse(player.is_playing())
        handle.wait_done()

    def test_led_effect_start_stop_loop(self):
        strip = led_strip.MockStrip(NUM_PIXELS)
        effect = led_effect.MockEffect(strip)
        player = players.LedEffectPlayer(effect)
        self.assertFalse(player.is_playing())
        handle = player.loop()
        self.assertTrue(handle.is_playing())
        self.assertTrue(player.is_playing())
        handle.stop()
        self.assertFalse(handle.is_playing())
        self.assertFalse(player.is_playing())
        handle.wait_done()
        # Create multiple handles
        handle = player.loop()
        handle = player.loop()
        handle = player.loop()
        handle = player.loop()
        handle.stop()
        self.assertFalse(handle.is_playing())
        self.assertFalse(player.is_playing())
        handle.wait_done()


if __name__ == "__main__":
    unittest.main()
