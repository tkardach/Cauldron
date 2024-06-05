import led_effect
import led_strip
from players import MockEffectPlayer
from pydub import AudioSegment
import time


NUM_PIXELS = 50


def test_mock_sine_wave():
    color0 = [3, 252, 11]
    color1 = [229, 245, 5]

    mock_strip = led_strip.MockStrip(NUM_PIXELS)
    sine_wave = led_effect.SineWaveEffect(
        mock_strip,
        color0,
        color1,
        oscillate=True,
        b=5,
        oscillation_speed_ms=1000,
    )
    player = MockEffectPlayer(mock_strip, sine_wave)
    handle = player.play()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        handle.stop()


def test_bubble_effect():
    color0 = [32, 139, 25]
    color1 = [43, 199, 32]

    mock_strip = led_strip.MockStrip(NUM_PIXELS)
    bubble_effect = led_effect.BubbleEffect(
        mock_strip, int(NUM_PIXELS / 2), color0, color1, bubble_length=9
    )
    player = MockEffectPlayer(mock_strip, bubble_effect)
    mock_strip.fill(color0)
    handle = player.play()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        handle.stop()


def test_bubbling_effect():
    # color0 = [32, 139, 25]
    # color1 = [43, 199, 32]
    # color0 = [142, 75, 166]
    # color1 = [196, 119, 223]
    color0 = [255, 179, 0]
    color1 = [255, 222, 0]
    bubble_lengths = [7, 9, 11]
    bubble_pop_speeds = [3000, 4000, 5000]
    weights = [0.5, 0.25, 0.25]

    NUM_PIXELS = 50
    HOST = "192.168.0.4"
    PORT = 5456
    mock_strip = led_strip.UdpStreamStrip(NUM_PIXELS, HOST, PORT)
    bubble_effect = led_effect.BubblingEffect(
        mock_strip,
        color0,
        color1,
        bubble_lengths,
        weights,
        bubble_pop_speeds,
        weights,
        10,
        0.05,
    )
    player = MockEffectPlayer(mock_strip, bubble_effect)
    mock_strip.fill(color0)
    handle = player.play()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        handle.stop()


def test_a2b_effect():
    segment = AudioSegment.from_file("app/files/audio/poof.wav")
    color0 = [32, 139, 25]

    mock_strip = led_strip.MockStrip(NUM_PIXELS)
    a2b_effect = led_effect.AudioToBrightnessEffect(mock_strip, segment)
    mock_strip.brightness = 0.5
    player = MockEffectPlayer(mock_strip, a2b_effect)
    mock_strip.fill(color0)
    handle = player.play()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        handle.stop()


# test_mock_sine_wave()
# test_bubble_effect()
test_bubbling_effect()
# test_a2b_effect()
