"""Visualizes the WaterDropletEffect on a grid of LED strips.

Run with:
    python -m cauldron.sample.water_droplet_test
"""

import matplotlib.pyplot as plt

from cauldron.core.led_effect import BoundaryCondition, WaterDropletEffect
from cauldron.core.led_strip import MockStrip
from cauldron.core.players import MockEffectPlayer

# 1. Build a grid of 12 strips, each holding 60 LEDs (1 meter at 60 LEDs/m).
NUM_STRIPS = 12
LEDS_PER_STRIP = 60
LED_DENSITY = 60.0  # LEDs per meter

strips = [MockStrip(num_pixels=LEDS_PER_STRIP) for _ in range(NUM_STRIPS)]

# 2. Configure the physical characteristics of the water surface.
effect = WaterDropletEffect(
    strips,
    led_strip_length=LEDS_PER_STRIP / LED_DENSITY,  # meters
    led_density=LED_DENSITY,  # LEDs per meter
    damping=0.75,  # amplitude retained per second
    wave_speed=0.25,  # meters per second
    boundary_conditions=BoundaryCondition.REFLECTIVE,
    drop_amplitude=0.01,  # meters
    drop_radius=0.03,  # meters
    drop_frequency=0.5,  # drops per second
    brightness_scale=0.0025,  # displacement mapped to a fully lit LED
    seed=7,
)

# 3. Create the player instance. This call is non-blocking.
player = MockEffectPlayer(strips, effect, fps=30.0)
handle = player.play_for(60)

# 4. Show the plot. This is a BLOCKING call that runs the animation.
plt.show()

print("Animation finished.")
