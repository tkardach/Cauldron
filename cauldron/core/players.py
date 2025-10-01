import abc
import logging
from cauldron.core.led_strip import LedStrip
from cauldron.core.led_effect import LedEffect, BrightnessEffect, Duration
import matplotlib.animation as animation
import matplotlib.pyplot as plt
import numpy as np
from pedalboard.io import AudioStream
from pydub import AudioSegment
import simpleaudio as sa
import sounddevice as sd
import threading
import time
from typing import Any, Callable


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

    def __init__(self, effect: LedEffect):
        super().__init__()
        self._effect = effect
        self._play_time_s: float | None = None

    def _loop(self):
        """Loop thread function to loop LedEffect."""
        while self._is_playing:
            try:
                self._effect.apply_effect()
            except Exception as e:
                logging.exception("Error applying LED effect: %s", e)
                break
            busy_sleep(self._effect.frame_speed_ms / 1000.0)

    def _play(self):
        """Play thread function to play LedEffect."""
        end_time = time.time() + self._play_time_s
        while self._is_playing and time.time() < end_time:
            try:
                self._effect.apply_effect()
            except Exception as e:
                logging.exception("Error applying LED effect: %s", e)
                break
            busy_sleep(self._effect.frame_speed_ms / 1000.0)

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


class RepeatedEffectChainPlayer(Player):
    """
    Plays a sequence of LedEffects in order, passing output colors from one effect to the next.
    When the end of the chain is reached, loops back to the start, using the last effect's output as the input for the first.
    """

    def __init__(self, *effects_with_duration: Duration):
        """
        effects_with_duration: list of led_effect.Duration objects
        """
        super().__init__()
        assert len(effects_with_duration) > 0
        self._effects = effects_with_duration
        self._current_index = 0
        self._current_effect = effects_with_duration[
            self._current_index
        ].effect
        self._next_end_time = (
            time.time() + self._effects[self._current_index].seconds
        )

    def _run_iteration(self):
        now = time.time()
        if now >= self._next_end_time:
            prev_index = self._current_index
            # Move to the next effect in the chain
            self._current_index = (self._current_index + 1) % len(
                self._effects
            )
            self._current_effect = self._effects[self._current_index].effect
            # Set the input colors of the new effect to the output colors of the previous effect
            self._current_effect.input_colors = self._effects[
                prev_index
            ].effect.output_colors
            self._current_effect.reset()
            # Set the end time for the new effect
            self._next_end_time = (
                now + self._effects[self._current_index].end_time()
            )
        try:
            self._current_effect.apply_effect()
        except Exception as e:
            logging.exception("Error applying LED effect: %s", e)
        busy_sleep(self._effect.frame_speed_ms / 1000.0)

    def _loop(self):
        """Loop through the chain of effects indefinitely."""
        while self._is_playing:
            self._run_iteration()

    def _play(self):
        """Play thread function to play LedEffect."""
        end_time = time.time() + self._play_time_s
        while self._is_playing and time.time() < end_time:
            self._run_iteration()

    def stop(self, wait: bool = False) -> None:
        super().stop(wait)


class AudioPlayer(Player):
    """Plays an AudioSegment."""

    def __init__(self, seg: AudioSegment):
        super().__init__()
        self._sound = seg
        self._play_buffer = None
        self._duration_seconds = seg.duration_seconds

    def _create_play_buffer(self, seg: AudioSegment) -> sa.PlayObject:
        """Creates an audio buffer which can be played."""
        return sa.play_buffer(
            seg.raw_data,
            num_channels=seg.channels,
            bytes_per_sample=seg.sample_width,
            sample_rate=seg.frame_rate,
        )

    def _loop(self):
        """Loops the audio segment until explicitly stopped."""
        while self._is_playing:
            try:
                self._play_buffer = self._create_play_buffer(self._sound * 10)
                self._play_buffer.wait_done()
            except Exception as e:
                logging.exception("Error during audio loop: %s", e)
                break

    def _play(self):
        """Plays the audio segment."""
        try:
            self._play_buffer = self._create_play_buffer(self._sound)
            self._play_buffer.wait_done()
        except Exception as e:
            logging.exception("Error during audio play: %s", e)
        with self._condition:
            self._is_playing = False
            self._condition.notify_all()

    def duration_seconds(self) -> float:
        """Returns the duration of the audio segment in seconds."""
        return self._duration_seconds

    def stop(self, wait: bool = False) -> None:
        """Stops the player if it is currently playing."""
        if self._play_buffer:
            try:
                self._play_buffer.stop()
            except Exception as e:
                logging.warning("Error stopping audio buffer: %s", e)
        super().stop(wait)


class AudioVisualPlayer(Player):
    """Plays both audio and LED visuals simultaneously."""

    def __init__(
        self, effect_player: LedEffectPlayer, audio_player: AudioPlayer
    ):
        super().__init__()
        self._effect_player = effect_player
        self._audio_player = audio_player
        self._playing = False
        self._effect_handle = None
        self._audio_handle = None

    def _predicate(self) -> bool:
        """Returns True if both audio and visual players are done playing."""
        return not (
            self._audio_handle.is_playing() or self._effect_handle.is_playing()
        )

    def _loop(self):
        """Loops the audio and visual players."""
        with self._condition:
            try:
                self._audio_handle = self._audio_player.loop()
                self._effect_handle = self._effect_player.loop()
                self._condition.wait_for(self._predicate)
            except Exception as e:
                logging.exception("Error in AudioVisualPlayer loop: %s", e)

    def _play(self):
        """Plays the audio and visual players once."""
        with self._condition:
            try:
                self._audio_handle = self._audio_player.play()
                self._effect_handle = self._effect_player.play_for(
                    self._audio_player.duration_seconds()
                )
                self._condition.wait_for(self._predicate)
            except Exception as e:
                logging.exception("Error in AudioVisualPlayer play: %s", e)

    def stop(self, wait: bool = False) -> None:
        """Stops the player if it is currently playing."""
        if self._handle is None:
            return None
        if self._effect_handle is not None:
            try:
                self._effect_handle.stop_wait()
            except Exception as e:
                logging.warning("Error stopping effect handle: %s", e)

        if self._audio_handle is not None:
            try:
                self._audio_handle.stop_wait()
            except Exception as e:
                logging.warning("Error stopping audio handle: %s", e)

        super().stop(wait)
        self._effect_handle = None
        self._audio_handle = None


class RealtimeAudioPlayer(Player):
    """Plays an AudioSegment in real time with effects."""

    def __init__(
        self,
        effects: list[Any],
        input_device: str = AudioStream.default_input_device_name,
        output_device: str = AudioStream.default_output_device_name,
    ):
        super().__init__()
        self._effects = effects
        self._stream = None
        self._input_device = input_device
        self._output_device = output_device

    def _loop(self):
        """Loops the audio segment until explicitly stopped."""
        with self._condition:
            try:
                with AudioStream(
                    input_device_name=self._input_device,
                    output_device_name=self._output_device,
                    buffer_size=1024,
                    sample_rate=44100,
                ) as self._stream:
                    for effect in self._effects:
                        self._stream.plugins.append(effect)
                    self._condition.wait_for(self._predicate)
            except Exception as e:
                logging.exception("Error in RealtimeAudioPlayer loop: %s", e)

    def _play(self):
        """Plays the audio segment."""
        self._loop()

    def stop(self, wait: bool = False) -> None:
        """Stops the player if it is currently playing."""
        super().stop(wait)
        self._stream = None


# MOCK CLASSES
# Consider moving these to a separate mock_players.py for better modularity.


class MockAudioVisualPlayer(AudioVisualPlayer):
    def __init__(
        self, effect_player: LedEffectPlayer, audio_player: AudioPlayer
    ):
        super().__init__(effect_player, audio_player)

    def play(self):
        self._play()

    def loop(self):
        self._loop()


class MockEffectHandle(Handle):
    def __del__(self):
        return None


def _plot_led_strip(strip, effect, frame_speed_ms: int):
    """Helper for plotting LED strip and effect animation (used by mocks)."""
    brightness_x_limit = 100
    fig, ax = plt.subplots(nrows=3, ncols=2, figsize=(12, 6))
    num_pixels = strip.num_pixels()
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
    scat = scat_ax.scatter(x, y, s=50)
    (r_plot,) = r_ax.plot(strip[:, 0])
    (g_plot,) = g_ax.plot(strip[:, 1])
    (b_plot,) = b_ax.plot(strip[:, 2])
    brightness_values = []
    (brightness_plot,) = brightness_ax.plot(brightness_values)
    r_plot.set_color((1, 0, 0))
    g_plot.set_color((0, 1, 0))
    b_plot.set_color((0, 0, 1))

    def set_pixels(pixels: np.array):
        brightness_values.append(strip.brightness)
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

    strip.set_show_callback(set_pixels)

    def update(_):
        effect.apply_effect()
        return scat

    ani = animation.FuncAnimation(
        fig=fig,
        func=update,
        frames=60,
        interval=frame_speed_ms,
    )
    plt.show()
    return MockEffectHandle(effect)


class MockEffectPlayer(Player):
    def __init__(self, strip: LedStrip, effect: LedEffect):
        super().__init__()
        self._strip = strip
        self._effect = effect

    def _loop(self):
        return _plot_led_strip(
            self._strip, self._effect, self._effect.frame_speed_ms
        )

    def _play(self):
        return self._loop()

    def play(self):
        return self._loop()

    def loop(self):
        return self._loop()

    def stop(self):
        return None


class MockStripPlayer(Player):
    def __init__(self, strip: LedStrip, frame_speed_ms: int = 100):
        super().__init__()
        self._strip = strip
        self._frame_speed_ms = frame_speed_ms

    def _loop(self):
        return _plot_led_strip(
            self._strip, BrightnessEffect(self._strip), self._frame_speed_ms
        )

    def _play(self):
        return self._loop()

    def play(self):
        return self._loop()

    def loop(self):
        return self._loop()

    def stop(self):
        return None
