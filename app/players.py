import abc
from led_strip import LedStrip
from led_effect import LedEffect
import matplotlib.animation as animation
import matplotlib.pyplot as plt
import numpy as np
from pydub import AudioSegment
import simpleaudio as sa
import threading
import time
from typing import Callable


def busy_sleep(seconds_to_sleep):
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

    def wait_done(self):
        """Waits for the handled player to finish playing."""
        self._player.wait_done()

    def stop(self):
        """Stops the handled player if it is playing."""
        with self._lock:
            self._player.stop()
            self._done_handling = True

    def stop_wait(self):
        """Stops the handled player and waits until finished."""
        with self._lock:
            self._player.stop(True)
            self._done_handling = True


class Player(abc.ABC):
    """A Player asynchronously plays/loops an action on another thread."""

    def __init__(self):
        self._handle = None
        self._is_playing = False
        self._thread_lock = threading.Lock()
        self._handle_lock = threading.Lock()
        self._condition = threading.Condition()
        self._thread = None

    def __del__(self):
        self.stop_wait()

    def is_playing(self):
        """Returns True if the player is currently playing."""
        with self._thread_lock:
            return self._is_playing

    def wait_done(self):
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

    def _predicate(self):
        """Returns True when the player is done/should stop playing."""
        return not self.is_playing()

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
    def stop(self, wait: bool = False):
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

    def stop_wait(self):
        self.stop(True)


class LedEffectPlayer(Player):
    """Plays an LedEffect on an LedStrip."""

    def __init__(self, effect: LedEffect):
        Player.__init__(self)
        self._effect = effect
        self._play_time_s = None

    def _loop(self):
        """Loop thread function to loop LedEffect."""
        while self._is_playing:
            self._effect.apply_effect()
            busy_sleep(self._effect.frame_speed_ms / 1000.0)

    def _play(self):
        """Play thread function to play LedEffect."""
        end_time = time.time() + self._play_time_s
        while self._is_playing and time.time() < end_time:
            self._effect.apply_effect()
            busy_sleep(self._effect.frame_speed_ms / 1000.0)

    def play_for(self, time_s: float = 5.0) -> Handle:
        """Plays the LedEffect for time_s seconds."""
        assert time_s > 0
        self._play_time_s = time_s
        return Player.play(self)

    def play(self):
        """Plays the LedEffect for 5 seconds."""
        self._effect.reset()
        return self.play_for()

    def loop(self) -> Handle:
        """Plays the LedEffect on a loop."""
        self._effect.reset()
        return self._create_thread(self._loop)

    def stop(self, wait: bool = False):
        """Stops the LedEffect."""
        Player.stop(self, wait)


class AudioPlayer(Player):
    """Plays an AudioSegment."""

    def __init__(self, seg: AudioSegment):
        Player.__init__(self)
        self._sound = seg
        self._play_buffer = None
        self._duration_seconds = seg.duration_seconds

    def _create_play_buffer(self, seg) -> sa.PlayObject:
        """Creates an audio buffer which can be played."""
        return sa.play_buffer(
            seg.raw_data,
            num_channels=seg.channels,
            bytes_per_sample=seg.sample_width,
            sample_rate=seg.frame_rate,
        )

    def _loop(self):
        """Loops the audio segment until explicilty stopped."""
        while self._is_playing:
            self._play_buffer = self._create_play_buffer(self._sound * 10)
            self._play_buffer.wait_done()

    def _play(self):
        """Plays the audio segment."""
        self._play_buffer = self._create_play_buffer(self._sound)
        self._play_buffer.wait_done()
        with self._condition:
            self._is_playing = False
            self._condition.notify_all()

    def duration_seconds(self) -> float:
        """Returns the duration of the audio segment in seconds."""
        return self._duration_seconds

    def stop(self, wait: bool = False):
        """Stops the player if it is currently playing."""
        if self._play_buffer:
            self._play_buffer.stop()
        Player.stop(self, wait)


class AudioVisualPlayer(Player):
    """Plays both audio and LED visuals simultaneously."""

    def __init__(
        self, effect_player: LedEffectPlayer, audio_player: AudioPlayer
    ):
        Player.__init__(self)
        self._effect_player = effect_player
        self._audio_player = audio_player
        self._playing = False
        self._effect_handle = None
        self._audio_handle = None

    def _predicate(self):
        """Returns True if both audio and visual players are done playing."""
        return not (
            self._audio_handle.is_playing() or self._effect_handle.is_playing()
        )

    def _loop(self):
        """Loops the audio and visual players."""
        with self._condition:
            self._audio_handle = self._audio_player.loop()
            self._effect_handle = self._effect_player.loop()
            self._condition.wait_for(self._predicate)

    def _play(self):
        """Plays the audio and visual players once."""
        with self._condition:
            self._audio_handle = self._audio_player.play()
            self._effect_handle = self._effect_player.play_for(
                self._audio_player.duration_seconds()
            )
            self._condition.wait_for(self._predicate)

    def stop(self, wait: bool = False):
        """Stops the player if it is currently playing."""
        if self._handle is None:
            return None
        if self._effect_handle is not None:
            self._effect_handle.stop_wait()

        if self._audio_handle is not None:
            self._audio_handle.stop_wait()

        Player.stop(self, wait)
        self._effect_handle = None
        self._audio_handle = None


class MockAudioVisualPlayer(AudioVisualPlayer):
    def __init__(
        self, effect_player: LedEffectPlayer, audio_player: AudioPlayer
    ):
        AudioVisualPlayer.__init__(self, effect_player, audio_player)

    def play(self):
        self._play()

    def loop(self):
        self._loop()


class MockEffectHandle(Handle):
    def __del__(self):
        return None


class MockEffectPlayer(Player):
    def __init__(self, strip: LedStrip, effect: LedEffect):
        self._strip = strip
        self._effect = effect

    def _loop(self):
        brightness_x_limit = 100
        fig, ax = plt.subplots(nrows=3, ncols=2, figsize=(12, 6))
        num_pixels = self._strip.num_pixels()
        x = np.arange(0, num_pixels, 1)
        y = [3] * num_pixels
        scat_ax = ax[0, 0]
        r_ax = ax[0, 1]
        g_ax = ax[1, 1]
        b_ax = ax[2, 1]
        brightness_ax = ax[1, 0]
        scat_ax.set(xlim=[0, num_pixels], ylim=[0, 6])
        r_ax.set(xlim=[0, num_pixels], ylim=[0, 255])
        r_ax.set_title("RGB channels")
        g_ax.set(xlim=[0, num_pixels], ylim=[0, 255])
        b_ax.set(xlim=[0, num_pixels], ylim=[0, 255])
        brightness_ax.set(xlim=[0, brightness_x_limit], ylim=[0, 1.1])
        # Create scatter plot to simulate LEDs
        scat = scat_ax.scatter(x, y, s=50)
        (r_plot,) = r_ax.plot(self._strip[:, 0])
        (g_plot,) = g_ax.plot(self._strip[:, 1])
        (b_plot,) = b_ax.plot(self._strip[:, 2])
        brightness_values = []
        (brightness_plot,) = brightness_ax.plot(brightness_values)
        r_plot.set_color((1, 0, 0))
        g_plot.set_color((0, 1, 0))
        b_plot.set_color((0, 0, 1))

        # Create set_pixels callback to change the LED scatter plot dot colors
        def set_pixels(pixels: np.array):
            brightness_values.append(self._strip.brightness)
            while len(brightness_values) > brightness_x_limit:
                brightness_values.pop(0)
            scat.set_color(pixels / 255.0)
            r_plot.set_ydata(pixels[:, 0])
            g_plot.set_ydata(pixels[:, 1])
            b_plot.set_ydata(pixels[:, 2])
            brightness_plot.set_data(
                np.arange(0, len(brightness_values), 1), brightness_values
            )

            fig.canvas.flush_events()

        # Set the show callback to update the pixel colors. This will call
        # set_pixels when LedStrip.show is called.
        self._strip.set_show_callback(set_pixels)

        # Create the pyplot animation update method. This will update the
        # LedStrip pixels
        def update(_):
            self._effect.apply_effect()
            return scat

        ani = animation.FuncAnimation(
            fig=fig,
            func=update,
            frames=60,
            interval=self._effect.frame_speed_ms,
        )
        plt.show()
        return MockEffectHandle(self)

    def _play(self):
        self._loop()

    def play(self):
        return self._loop()

    def loop(self):
        return self._loop()

    def stop(self):
        return None
