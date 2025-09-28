import unittest
import numpy as np
from cauldron.core.led_strip import RgbArrayStrip, MockStrip, PixelOrder


class TestLedStrip(unittest.TestCase):
    def test_rgb_array_strip_initialization(self):
        """Test that the RgbArrayStrip initializes correctly."""
        strip = RgbArrayStrip(num_pixels=50)
        self.assertEqual(strip.num_pixels(), 50)
        self.assertEqual(strip.brightness, 1.0)
        self.assertEqual(strip[:].shape, (50, 3))
        self.assertTrue(np.all(strip[:] == 0))

    def test_set_and_get_pixel(self):
        """Test setting and getting a single pixel color."""
        strip = RgbArrayStrip(num_pixels=10)
        color = (10, 20, 30)
        strip[5] = color
        np.testing.assert_array_equal(strip[5], np.array(color))

    def test_set_and_get_slice(self):
        """Test setting and getting a slice of pixels."""
        strip = RgbArrayStrip(num_pixels=10)
        color = (255, 0, 128)
        strip[2:5] = color
        for i in range(2, 5):
            np.testing.assert_array_equal(strip[i], np.array(color))

    def test_fill(self):
        """Test filling the entire strip with a single color."""
        strip = RgbArrayStrip(num_pixels=20)
        color = [100, 150, 200]
        strip.fill(color)
        for i in range(20):
            np.testing.assert_array_equal(strip[i], np.array(color))

    def test_brightness(self):
        """Test the brightness property."""
        strip = RgbArrayStrip(num_pixels=5)
        self.assertEqual(strip.brightness, 1.0)
        strip.brightness = 0.5
        self.assertEqual(strip.brightness, 0.5)

    def test_get_pixels_order(self):
        """Test getting pixels in different color orders (RGB vs BGR)."""
        strip = RgbArrayStrip(num_pixels=2)
        strip[0] = [1, 2, 3]
        rgb_pixels = strip.get_pixels(PixelOrder.RGB)
        bgr_pixels = strip.get_pixels(PixelOrder.BGR)
        np.testing.assert_array_equal(rgb_pixels[0], [1, 2, 3])
        np.testing.assert_array_equal(bgr_pixels[0], [3, 2, 1])

    def test_mock_strip_show_callback(self):
        """Test that the MockStrip's show method calls the callback."""
        callback_called = False

        def my_callback(pixels):
            nonlocal callback_called
            callback_called = True
            np.testing.assert_array_equal(pixels[0], np.array([255, 0, 0]))

        strip = MockStrip(num_pixels=10, show_callback=my_callback)
        strip[0] = [255, 0, 0]
        strip.show()

        # The callback is put into a queue, so we process it.
        callback_func = strip.callback_queue.get()
        callback_func()

        self.assertTrue(callback_called)


if __name__ == "__main__":
    unittest.main()
