import board
from cauldron import Cauldron
from led_strip import UdpStreamStrip
from ir_remote import IrRemote
import pulseio
import adafruit_irremote


NUM_PIXELS = 50
HOST = "192.168.0.4"
PORT = 5456
strip = UdpStreamStrip(NUM_PIXELS, HOST, PORT)
strip.brightness = 0.2

pulsein = pulseio.PulseIn(board.D22, maxlen=120, idle_state=True)
decoder = adafruit_irremote.GenericDecode()

ir_remote = IrRemote()

cauldron = Cauldron(strip)

while True:
    pulses = decoder.read_pulses(pulsein)
    try:
        code = decoder.decode_bits(pulses)
        decoded = ir_remote.decode(code)
        if decoded is None:
            pass
        elif decoded == "ok":
            print("Causing Explosion")
            cauldron.cause_explosion()
        elif decoded == "*":
            print("Starting Cauldron")
            cauldron.start()
        elif decoded == "#":
            print("Stopping Cauldron")
            cauldron.stop()

    except adafruit_irremote.IRNECRepeatException:  # unusual short code!
        print("NEC repeat!")
    except adafruit_irremote.IRDecodeException as e:  # failed to decode
        print("Failed to decode: ", e.args)
