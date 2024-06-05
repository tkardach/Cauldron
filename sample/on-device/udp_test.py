import led_effect
from led_strip import UdpStreamStrip
from players import LedEffectPlayer, MockEffectPlayer
import sys
import socket
import time


def test_bubbling_effect():
    colors = ([142, 75, 166], [0, 255, 0])
    bubble_lengths = [7, 9, 11]
    bubble_pop_speeds = [3000, 4000, 5000]
    weights = [0.5, 0.25, 0.25]

    bubble_effect = led_effect.BubblingEffect(
        strip,
        colors[0],
        colors[1],
        bubble_lengths,
        weights,
        bubble_pop_speeds,
        weights,
        10,
        0.05,
    )
    # bubble_effect = led_effect.SineWaveEffect(
    #     strip,
    #     colors[0],
    #     colors[1],
    #     oscillate=True,
    #     b=5,
    #     oscillation_speed_ms=1000,
    # )
    return bubble_effect


import numpy as np

HOST = "192.168.0.4"
PORT = 5456
strip = UdpStreamStrip(50, HOST, PORT)
strip.fill([0, 0, 0])
strip.show()

# bubble_effect = test_bubbling_effect()

# player = MockEffectPlayer(strip, bubble_effect)
# handle = player.play()
# try:
#     while True:
#         time.sleep(1)
# except KeyboardInterrupt:
#     handle.stop()
