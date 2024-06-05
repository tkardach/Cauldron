from cauldron import Cauldron
from led_strip import UdpStreamStrip
import threading
import time

NUM_PIXELS = 50
HOST = "192.168.0.4"
PORT = 5456
strip = UdpStreamStrip(NUM_PIXELS, HOST, PORT)
strip.brightness = 0.2


def wait_for_explosion():
    cauldron = Cauldron(strip)
    try:
        while True:
            user = input("Press Enter")
            if user == "":
                print("Causing explosion")
                cauldron.cause_explosion()
            elif user == "c":
                del cauldron
                return
    except KeyboardInterrupt:
        del cauldron


def test_explosions():
    t = threading.Thread(target=wait_for_explosion)
    t.start()
    t.join()


def test_default():
    cauldron = Cauldron(strip)

    time.sleep(60)


test_explosions()
# test_default()
