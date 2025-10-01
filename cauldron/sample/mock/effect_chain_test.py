import matplotlib.pyplot as plt
from cauldron.core.led_strip import MockStrip
from cauldron.core.new_led_effect import (
    TravelingLightEffect,
    EffectChain,
    EffectWithDuration,
)

# Make sure to import the corrected MockPlayer class
from cauldron.core.new_players import MockEffectPlayer


# 1. Set up the strip and effect
strip = MockStrip(num_pixels=50)
base_color = [0, 0, 0]
light_color = [200, 50, 50]
effect_a = TravelingLightEffect(
    strip, [base_color, light_color], 10, 1, fade_type="linear"
)
effect_b = TravelingLightEffect(
    strip,
    [base_color, light_color],
    10,
    1,
    fade_type="linear",
    reverse=True,
    start_index=49,
)
effect = EffectChain(
    strip, [EffectWithDuration(effect_a, 5), EffectWithDuration(effect_b, 5)]
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
