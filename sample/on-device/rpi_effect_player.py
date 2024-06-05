import board
import led_effect
from neopixel_strip import NeoPixelStrip
import neopixel
import players
from pydub import AudioSegment
import time
import utils.led_effects as test_effects


PIXEL_ORDER = neopixel.RGB
PIXEL_PIN = board.D12
NUM_PIXELS = 50


def test_rpi_neopixel_sine_wave():
    color0 = [3, 252, 11]
    color1 = [229, 245, 5]

    device = neopixel.NeoPixel(
        PIXEL_PIN,
        NUM_PIXELS,
        auto_write=True,
        pixel_order=PIXEL_ORDER,
        brightness=0.5,
    )
    strip = NeoPixelStrip(device)
    sine_wave = led_effect.SineWaveEffect(
        strip, color0, color1, oscillate=True, b=5, oscillation_speed_ms=1000
    )
    sine_wave.frame_speed_ms = 50
    player = players.LedEffectPlayer(sine_wave)
    handle = player.play()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        handle.stop()


def play_a2b_effect():
    segment = AudioSegment.from_file("app/files/audio/poof.wav")
    segment = segment.set_sample_width(2)
    color0 = [32, 139, 25]

    device = neopixel.NeoPixel(
        PIXEL_PIN,
        NUM_PIXELS,
        auto_write=True,
        pixel_order=PIXEL_ORDER,
        brightness=0.1,
    )
    device.fill(color0)
    strip = NeoPixelStrip(device)
    a2b_effect = led_effect.AudioToBrightnessEffect(strip, segment)
    audio_player = players.AudioPlayer(segment)
    effect_player = players.LedEffectPlayer(a2b_effect)

    # Initialize the MockAudioVisualPlayer
    av_player = players.AudioVisualPlayer(effect_player, audio_player)

    handle = av_player.loop()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        handle.stop()


def test_bubbling_effect():
    colors = ([32, 139, 25], [215, 232, 23])
    bubble_lengths = [7, 9, 11]
    bubble_pop_speeds = [3000, 4000, 5000]
    weights = [0.5, 0.25, 0.25]

    device = neopixel.NeoPixel(
        PIXEL_PIN,
        NUM_PIXELS,
        auto_write=True,
        pixel_order=PIXEL_ORDER,
        brightness=0.1,
    )
    device.fill(colors[0])
    strip = NeoPixelStrip(device)
    bubble_effect = test_effects.create_bubbling_effect(
        strip, colors[0], colors[1], bubble_lengths, bubble_pop_speeds, weights
    )
    player = players.LedEffectPlayer(bubble_effect)
    handle = player.loop()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        handle.stop()


# test_rpi_neopixel_sine_wave()
# play_a2b_effect()
test_bubbling_effect()
