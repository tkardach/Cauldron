from led.led_effect import SineWaveEffect
import matplotlib.animation as animation
import matplotlib.pyplot as plt
import numpy as np


def test_sine_wave():
    sine_wave = SineWaveEffect(oscillate = True) 
    fig, ax = plt.subplots()

    x_max = 2*np.pi
    num_pixels = 50
    x = np.arange(0, x_max, x_max / num_pixels)

    line, = ax.plot(x, sine_wave.get_brightness_for_pixel(x))

    def animate():
        sine_wave.update_oscillation()
        line.set_ydata(sine_wave.get_brightness_for_pixel(x))
        return line,

    ani = animation.FuncAnimation(fig, animate, interval=20, blit=True, save_count=50)
    plt.show()

test_sine_wave()
