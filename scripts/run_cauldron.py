from cauldron.application import build_application
from cauldron.core.led_strip import UdpStreamStrip
import cauldron.config.config as config

NUM_PIXELS = getattr(config, "NUM_PIXELS", 50)
HOST = getattr(config, "LED_HOST", "10.0.0.157")
PORT = getattr(config, "LED_PORT", 5456)
strip = UdpStreamStrip(NUM_PIXELS, HOST, PORT, 0.2)
INPUT = getattr(config, "CAULDRON_INPUT_DEVICE", "")
OUTPUT = getattr(config, "CAULDRON_OUTPUT_DEVICE", "")

application = build_application(strip, INPUT, OUTPUT)
application.run()
