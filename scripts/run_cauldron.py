from cauldron.core.cauldron import Cauldron, CauldronRunner
from cauldron.core.led_strip import UdpStreamStrip
import cauldron.config.config as config

cauldron: Cauldron = None
NUM_PIXELS = getattr(config, "NUM_PIXELS", 50)
HOST = getattr(config, "LED_HOST", "10.0.0.157")
PORT = getattr(config, "LED_PORT", 5456)
strip = UdpStreamStrip(NUM_PIXELS, HOST, PORT, 0.2)
INPUT = getattr(config, "CAULDRON_INPUT_DEVICE", "")
OUTPUT = getattr(config, "CAULDRON_OUTPUT_DEVICE", "")

runner = CauldronRunner(strip, INPUT, OUTPUT)

runner.run()
