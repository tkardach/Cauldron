import led_effect
import led_strip
import players
from pydub import AudioSegment
import time


NUM_PIXELS = 50


def play_bubble_effect():
    # Initialize the AudioPlayer
    import cauldron.assets.audio as audio_assets

    segment = AudioSegment.from_file(audio_assets.get_path("bubbles.wav"))
    segment.frame_rate = int(segment.frame_rate / 4)
    audio_player = players.AudioPlayer(segment)

    color0 = [32, 139, 25]
    color1 = [43, 199, 32]

    # Initialize the MockEffectPlayer
    bubble_lengths = [7, 9, 11]
    bubble_pop_speeds = [3000, 4000, 5000]
    weights = [0.5, 0.25, 0.25]

    mock_strip = led_strip.MockStrip(NUM_PIXELS)
    bubble_effect = led_effect.BubblingEffect(
        mock_strip,
        color0,
        color1,
        bubble_lengths,
        weights,
        bubble_pop_speeds,
        weights,
        15,
        0.05,
    )
    effect_player = players.MockEffectPlayer(mock_strip, bubble_effect)
    mock_strip.fill(color0)

    # Initialize the MockAudioVisualPlayer
    av_player = players.MockAudioVisualPlayer(effect_player, audio_player)

    # Loop the player until a keyboard interrupt is received
    handle = av_player.loop()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        handle.stop()


def play_a2b_effect():
    segment = AudioSegment.from_file(audio_assets.get_path("poof.wav"))
    segment = segment.set_sample_width(2)
    color0 = [32, 139, 25]

    mock_strip = led_strip.MockStrip(NUM_PIXELS)
    a2b_effect = led_effect.AudioToBrightnessEffect(mock_strip, segment)
    audio_player = players.AudioPlayer(segment)
    mock_strip.brightness = 0.5
    effect_player = players.MockEffectPlayer(mock_strip, a2b_effect)
    mock_strip.fill(color0)

    # Initialize the MockAudioVisualPlayer
    av_player = players.MockAudioVisualPlayer(effect_player, audio_player)

    handle = av_player.loop()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        handle.stop()


# play_bubble_effect()
play_a2b_effect()
