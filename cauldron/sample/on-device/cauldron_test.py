from cauldron import CauldronRunner
from led_strip import UdpStreamStrip
from pedalboard.io import AudioStream
import config

NUM_PIXELS = getattr(config, "NUM_PIXELS", 50)
HOST = getattr(config, "LED_HOST", "192.168.0.4")
PORT = getattr(config, "LED_PORT", 5456)
strip = UdpStreamStrip(NUM_PIXELS, HOST, PORT, 0.2)

print(AudioStream.output_device_names, AudioStream.input_device_names)

runner = CauldronRunner(strip, "Built-in Microphone", "SRS-XB10")
runner.run()
