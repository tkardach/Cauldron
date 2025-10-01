import abc
import logging
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import numpy as np
import time
import threading
from typing import Callable

from cauldron.core.led_strip import LedStrip
from cauldron.core.new_led_effect import LedEffect


# ... (The first part of the file including Player, Handle, and LedEffectPlayer is unchanged) ...
def busy_sleep(seconds_to_sleep):
    """Busy sleep guarantees more precise timing when sleeping."""
    start = time.time()
    while time.time() < start + seconds_to_sleep:
        pass


class Handle(abc.ABC):
    """The Handle class can stop a Player's asynchronous play/loop action."""

    def __init__(self, player: "Player"):
        self._player = player
        self._lock = threading.Lock()
        self._done_handling = False

    def __del__(self):
        with self._lock:
            if self._done_handling:
                return
        self.stop_wait()

    def is_playing(self) -> bool:
        """Returns true if the handled player is playing."""
        return self._player.is_playing()

    def wait_done(self) -> None:
        """Waits for the handled player to finish playing."""
        self._player.wait_done()

    def stop(self) -> None:
        """Stops the handled player if it is playing."""
        with self._lock:
            self._player.stop()
            self._done_handling = True

    def stop_wait(self) -> None:
        """Stops the handled player and waits until finished."""
        with self._lock:
            self._player.stop(True)
            self._done_handling = True


class Player(abc.ABC):
    """A Player asynchronously plays/loops an action on another thread."""

    def __init__(self):
        self._handle: Handle | None = None
        self._is_playing: bool = False
        self._thread_lock = threading.Lock()
        self._handle_lock = threading.Lock()
        self._condition = threading.Condition()
        self._thread: threading.Thread | None = None

    def __del__(self):
        self.stop_wait()

    def is_playing(self) -> bool:
        """Returns True if the player is currently playing."""
        with self._thread_lock:
            return self._is_playing

    def wait_done(self) -> None:
        """Waits for the running thread to finish executing."""
        with self._thread_lock:
            if self._thread is not None:
                self._thread.join()
                self._thread = None

    def _create_thread(self, thread_func: Callable) -> Handle:
        """Runs _play on another thread, returning a Handle to the thread."""
        with self._handle_lock:
            # Destroy the running thread if it exists
            if self._handle is not None:
                self._handle.stop_wait()
        # Create a new thread for playing and create the handle
        with self._thread_lock:
            self._is_playing = True
            self._thread = threading.Thread(target=thread_func)
            self._thread.start()
        with self._handle_lock:
            self._handle = Handle(self)
        return self._handle

    def _predicate(self) -> bool:
        """Returns True when the player is done/should stop playing."""
        return not self._is_playing

    @abc.abstractmethod
    def _play(self):
        """Play function that runs on another thread."""
        with self._condition:
            self._condition.wait_for(self._predicate)

    @abc.abstractmethod
    def _loop(self):
        """Loop function that runs on another thread."""
        with self._condition:
            self._condition.wait_for(self._predicate)

    def play(self) -> Handle:
        """Runs _play on another thread, returning a Handle to the thread."""
        return self._create_thread(self._play)

    def loop(self) -> Handle:
        """Runs _loop on another thread, returning a Handle to the thread."""
        return self._create_thread(self._loop)

    @abc.abstractmethod
    def stop(self, wait: bool = False) -> None:
        """Stop playing/looping."""
        if not self.is_playing():
            return
        # Notify the thread to stop playing
        with self._thread_lock:
            self._is_playing = False
        # Notify the condition to check predicate
        with self._condition:
            self._condition.notify_all()
        # If wait is specified, wait for thread to destroy
        if wait:
            with self._thread_lock:
                if self._thread is not None:
                    self._thread.join()
                    self._thread = None

    def stop_wait(self) -> None:
        self.stop(True)


class LedEffectPlayer(Player):
    """Plays an LedEffect on an LedStrip."""

    def __init__(self, effect: LedEffect, fps: float = 30.0):
        """
        Args:
            effect: The LedEffect to play.
            fps: Frames per second for updating the effect.
        """
        super().__init__()
        self._effect = effect
        self._fps = fps
        self._frame_interval_s = 1.0 / fps
        self._start_time_s: float | None = None
        self._play_time_s: float | None = None

    def _loop(self):
        """Loop thread function to loop LedEffect."""
        self._start_time_s = time.time()
        while self._is_playing:
            try:
                t = time.time() - self._start_time_s
                self._effect.update(t)
            except Exception as e:
                logging.exception("Error applying LED effect: %s", e)
                break
            busy_sleep(self._frame_interval_s)

    def _play(self):
        """Play thread function to play LedEffect."""
        self._start_time_s = time.time()
        end_time = self._start_time_s + self._play_time_s
        while self._is_playing and time.time() < end_time:
            try:
                t = time.time() - self._start_time_s
                self._effect.update(t)
            except Exception as e:
                logging.exception("Error applying LED effect: %s", e)
                break
            busy_sleep(self._frame_interval_s)

    def play_for(self, time_s: float = 5.0) -> Handle:
        """Plays the LedEffect for time_s seconds."""
        assert time_s > 0
        self._play_time_s = time_s
        return super().play()

    def play(self) -> Handle:
        """Plays the LedEffect for 5 seconds."""
        self._effect.reset()
        return self.play_for()

    def loop(self) -> Handle:
        """Plays the LedEffect on a loop."""
        self._effect.reset()
        return self._create_thread(self._loop)

    def stop(self, wait: bool = False) -> None:
        """Stops the LedEffect."""
        super().stop(wait)


class MockHandle:
    """A simple handle for controlling the MockPlayer."""

    def __init__(self, player: "MockEffectPlayer"):
        self._player = player

    def stop(self):
        """Stops the animation by closing the plot window."""
        self._player.stop()

    def stop_wait(self):
        """Stops the animation. The action is immediate, so no wait is needed."""
        self.stop()


class MockEffectPlayer:
    """
    Visualizes an LED effect using Matplotlib.

    IMPORTANT: This player must run on the main thread due to OS restrictions on
    GUI toolkits. To use it, call a method like `loop()` or `play_for()`,
    which returns a handle, and then call `plt.show()` from your main script.
    """

    def __init__(self, strip: LedStrip, effect: LedEffect, fps: float = 30.0):
        self._strip = strip
        self._effect = effect
        self._fps = fps
        self._play_time_s: float | None = None
        self._is_playing = False
        self._fig = None
        self._ani = None
        self._start_time = None
        self._brightness_values = []

    def _setup_plot(self):
        """Initializes the Matplotlib figure and axes for the animation."""
        brightness_x_limit = 100
        self._fig, ax = plt.subplots(nrows=3, ncols=2, figsize=(12, 6))
        self._fig.canvas.manager.set_window_title("LED Effect Mock Player")
        num_pixels = self._strip.num_pixels()
        x = np.arange(0, num_pixels, 1)
        y = [3] * num_pixels
        scat_ax, r_ax = ax[0, 0], ax[0, 1]
        brightness_ax, g_ax = ax[1, 0], ax[1, 1]
        _, b_ax = ax[2, 0], ax[2, 1]
        ax[2, 0].set_visible(False)
        scat_ax.set(xlim=(-1, num_pixels), ylim=[0, 6], title="LED Strip")
        r_ax.set(xlim=(-1, num_pixels), ylim=[-5, 260], title="RGB Channels")
        g_ax.set(xlim=(-1, num_pixels), ylim=[-5, 260])
        b_ax.set(xlim=(-1, num_pixels), ylim=[-5, 260])
        brightness_ax.set(
            xlim=[0, brightness_x_limit], ylim=[0, 1.1], title="Brightness"
        )
        self._scat = scat_ax.scatter(x, y, s=100)
        (self._r_plot,) = r_ax.plot([], [], color="r")
        (self._g_plot,) = g_ax.plot([], [], color="g")
        (self._b_plot,) = b_ax.plot([], [], color="b")
        (self._brightness_plot,) = brightness_ax.plot([], [])

    def _update_frame(self, frame):
        """The function called by FuncAnimation on each frame."""
        # This check ensures that we don't try to update a closed plot
        if not self._is_playing:
            return

        t = time.time() - self._start_time
        if self._play_time_s is not None and t >= self._play_time_s:
            self.stop()
            return
        self._effect.update(t)
        pixels = self._strip.get_pixels()
        num_pixels = self._strip.num_pixels()
        x_data = np.arange(num_pixels)
        self._scat.set_color(pixels / 255.0)
        self._r_plot.set_data(x_data, pixels[:, 0])
        self._g_plot.set_data(x_data, pixels[:, 1])
        self._b_plot.set_data(x_data, pixels[:, 2])
        brightness_x_limit = 100
        self._brightness_values.append(self._strip.brightness)
        if len(self._brightness_values) > brightness_x_limit:
            self._brightness_values.pop(0)
        self._brightness_plot.set_data(
            np.arange(len(self._brightness_values)), self._brightness_values
        )

    def _on_window_close(self, evt):
        """A dedicated callback for when the Matplotlib window is closed."""
        # If the animation is running, stop its timer and update the state.
        if self._is_playing:
            if hasattr(self, "_ani") and self._ani and self._ani.event_source:
                self._ani.event_source.stop()
            self._is_playing = False

    def _start_animation(self):
        """Internal method to create the plot and FuncAnimation object."""
        if self._is_playing:
            return
        self._setup_plot()
        self._start_time = time.time()
        interval_ms = 1000.0 / self._fps

        # Connect the new, safe close handler
        self._fig.canvas.mpl_connect("close_event", self._on_window_close)

        self._ani = animation.FuncAnimation(
            fig=self._fig,
            func=self._update_frame,
            cache_frame_data=False,
        )
        self._is_playing = True

    def play(self) -> MockHandle:
        """Configures the animation to run for 5 seconds."""
        return self.play_for()

    def play_for(self, time_s: float = 5.0) -> MockHandle:
        """Configures the animation to run for a specific duration."""
        self._effect.reset()
        self._play_time_s = time_s
        self._start_animation()
        return MockHandle(self)

    def loop(self) -> MockHandle:
        """Configures the animation to run indefinitely."""
        self._effect.reset()
        self._play_time_s = None
        self._start_animation()
        return MockHandle(self)

    def stop(self):
        """Programmatically stops the animation by closing the plot window."""
        # This method is now only for external calls (e.g., from a handle).
        # It triggers the 'close_event', which is handled by _on_window_close.
        if not self._is_playing or self._fig is None:
            return
        plt.close(self._fig)
