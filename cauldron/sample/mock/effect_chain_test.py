import matplotlib.pyplot as plt
import numpy as np

import cauldron.core.new_led_effect as led_effect
from cauldron.core.led_strip import MockStrip


# Make sure to import the corrected MockPlayer class
from cauldron.core.new_players import MockEffectPlayer


# 1. Set up the strip and effect
strip = MockStrip(num_pixels=50)


def random_color():
    return np.random.randint(0, 256, size=3).tolist()


bubbling_effect = led_effect.BubblingEffect(
    strip, [random_color(), random_color()]
)
effect = led_effect.EffectChain(
    strip,
    [
        led_effect.EffectWithDuration(bubbling_effect, 120),
        led_effect.EffectWithDuration(
            led_effect.TransitionEffect(strip, randomize=True), 5
        ),
        led_effect.EffectWithDuration(
            led_effect.TravelingLightEffect(strip, [[0, 0, 0], [0, 256, 0]]),
            5,
        ),
    ],
)
# 2. Create the player instance
player = MockEffectPlayer(strip, effect, fps=60.0)

# 3. Configure the player to run the animation. This call is non-blocking.
handle = player.play_for(60)

# 4. Show the plot. This is a BLOCKING call that runs the animation.
#    The script will pause here until you close the window.
plt.show()

# The script will only reach this line after the animation window is closed.
print("Animation finished.")
