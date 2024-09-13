from cauldron import Cauldron, CauldronSounds
from led_strip import MockStrip
import threading
import time

NUM_PIXELS = 50
strip = MockStrip(NUM_PIXELS)
strip.brightness = 0.2


def wait_for_explosion():
    cauldron = Cauldron(strip)
    try:
        while True:
            user = input("Enter Command: ")
            if user == "":
                print("Causing explosion")
                cauldron.cause_explosion()
            elif user.isdigit():
                print("Playing sound")
                cauldron.play_sound(CauldronSounds(int(user)))
            elif user == "r":
                print("Playing random voice")
                cauldron.play_random_voice()
            elif user == "h":
                print("Enter: Explosion")
                print("Integer: Sounds")
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
