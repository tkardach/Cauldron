import matplotlib.pyplot as plt
from pydub import AudioSegment

import cauldron.assets.audio as audio_assets
import cauldron.core.new_led_effect as led_effect
import cauldron.core.led_strip as led_strip
import cauldron.core.new_players as players

NUM_PIXELS = 50


segment = AudioSegment.from_file(audio_assets.get_path("poof.wav"))
segment = segment.set_sample_width(2)
color0 = [32, 139, 25]

mock_strip = led_strip.MockStrip(NUM_PIXELS)
a2b_effect = led_effect.AudioToBrightnessEffect(mock_strip, segment)
audio_player = players.AudioPlayer(segment)
mock_strip.brightness = 0.25
effect_player = players.MockEffectPlayer(mock_strip, a2b_effect)
mock_strip.fill(color0)

# Initialize the MockAudioVisualPlayer
av_player = players.MockAudioVisualPlayer(effect_player, audio_player)

handle = av_player.play()

plt.show()
