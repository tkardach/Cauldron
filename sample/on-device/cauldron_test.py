from cauldron import CauldronRunner
from led_strip import UdpStreamStrip
from pedalboard.io import AudioStream

NUM_PIXELS = 50
HOST = "192.168.0.4"
PORT = 5456
strip = UdpStreamStrip(NUM_PIXELS, HOST, PORT)
strip.brightness = 0.2

print(AudioStream.output_device_names, AudioStream.input_device_names)

runner = CauldronRunner(strip)
runner.run()
