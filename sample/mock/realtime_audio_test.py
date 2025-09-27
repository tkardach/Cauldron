import led_effect
import led_strip
from pedalboard import Reverb, PitchShift, LowpassFilter
from pedalboard.io import AudioStream
import players
import time
from test_runner import TestRunner

fx = [
    PitchShift(semitones=8),
]
NUM_PIXELS = 50

mock_strip = led_strip.MockStrip(NUM_PIXELS)
mock_strip.fill([100, 200, 55])
mock_strip.brightness = 0.25

print(AudioStream.input_device_names)
print(AudioStream.output_device_names)

rt_demon_voice_player = players.RealtimeAudioPlayer(
    fx,
    input_device="Built-in Microphone",
    output_device="SRS-XB10",
)
v2b_handle = rt_demon_voice_player.loop()
runner = TestRunner(mock_strip, [v2b_handle])
runner.run()
