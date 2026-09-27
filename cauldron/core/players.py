import abc
import logging
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import numpy as np
import time
import threading
from typing import Callable
from pedalboard.io import AudioStream
from pydub import AudioSegment
from typing import Any, Callable

from cauldron.core.led_strip import LedStrip
from cauldron.core.led_effect import LedEffect


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
        with self._condition:
            self._is_playing = False
            self._condition.notify_all()

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
        with self._condition:
            self._is_playing = False
            self._condition.notify_all()

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


class AudioPlayer(Player):
    """Plays an AudioSegment."""

    _SAMPLE_RATE = 44100
    _CHUNK_SIZE = 2048

    def __init__(
        self,
        seg: AudioSegment,
        output_device_name: str | None = None,
    ):
        super().__init__()
        seg = seg.set_sample_width(2).set_frame_rate(self._SAMPLE_RATE)
        samples = np.frombuffer(seg.raw_data, dtype=np.int16)
        self._sound = np.ascontiguousarray(
            samples.reshape(-1, seg.channels).T / 32768.0,
            dtype=np.float32,
        )
        self._channels = seg.channels
        self._output_device_name = (
            output_device_name or AudioStream.default_output_device_name
        )
        self._duration_seconds = seg.duration_seconds

    def _write_sound(self, stream: AudioStream) -> None:
        for start in range(0, self._sound.shape[1], self._CHUNK_SIZE):
            if not self._is_playing:
                return
            stream.write(
                self._sound[:, start : start + self._CHUNK_SIZE],
                self._SAMPLE_RATE,
            )

    def _loop(self):
        """Loops the audio segment until explicitly stopped."""
        try:
            with AudioStream(
                output_device_name=self._output_device_name,
                sample_rate=self._SAMPLE_RATE,
                num_output_channels=self._channels,
            ) as stream:
                while self._is_playing:
                    self._write_sound(stream)
        except Exception as e:
            logging.exception("Error during audio loop: %s", e)
        finally:
            with self._condition:
                self._is_playing = False
                self._condition.notify_all()

    def _play(self):
        """Plays the audio segment."""
        try:
            with AudioStream(
                output_device_name=self._output_device_name,
                sample_rate=self._SAMPLE_RATE,
                num_output_channels=self._channels,
            ) as stream:
                self._write_sound(stream)
        except Exception as e:
            logging.exception("Error during audio play: %s", e)
        finally:
            with self._condition:
                self._is_playing = False
                self._condition.notify_all()

    def duration_seconds(self) -> float:
        """Returns the duration of the audio segment in seconds."""
        return self._duration_seconds

    def stop(self, wait: bool = False) -> None:
        """Stops the player if it is currently playing."""
        super().stop(wait)


class AudioVisualPlayer(Player):
    """Plays both audio and LED visuals simultaneously using the new Player interface."""

    def __init__(self, effect_player: "Player", audio_player: "Player"):
        super().__init__()
        self._effect_player = effect_player
        self._audio_player = audio_player
        self._effect_handle = None
        self._audio_handle = None

    def _predicate(self) -> bool:
        """Returns True if both audio and visual players are done playing."""
        return not (
            (self._audio_handle and self._audio_handle.is_playing())
            or (self._effect_handle and self._effect_handle.is_playing())
        )

    def _loop(self):
        self._effect_handle = self._effect_player.loop()
        self._audio_handle = self._audio_player.loop()
        with self._condition:
            self._condition.wait_for(self._predicate)

    def _play(self):
        self._effect_handle = self._effect_player.play()
        self._audio_handle = self._audio_player.play()
        with self._condition:
            self._condition.wait_for(self._predicate)

    def stop(self, wait: bool = False) -> None:
        if self._effect_handle:
            self._effect_handle.stop_wait()
            self._effect_handle = None
        if self._audio_handle:
            self._audio_handle.stop_wait()
            self._audio_handle = None
        super().stop(wait)


class MockAudioVisualPlayer:
    """Mock version of AudioVisualPlayer for visualization/testing."""

    def __init__(self, effect_player, audio_player):
        self._effect_player = effect_player
        self._audio_player = audio_player
        self._effect_handle = None
        self._audio_handle = None

    def play(self):
        self._effect_handle = self._effect_player.play()
        self._audio_handle = self._audio_player.play()
        # For mocks, just return a tuple of handles
        return (self._effect_handle, self._audio_handle)

    def loop(self):
        self._effect_handle = self._effect_player.loop()
        self._audio_handle = self._audio_player.loop()
        return (self._effect_handle, self._audio_handle)

    def stop(self):
        if self._effect_handle:
            self._effect_handle.stop()
            self._effect_handle = None
        if self._audio_handle:
            self._audio_handle.stop()
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


class DropdownMenu:
    """A minimal dropdown menu widget for Matplotlib figures.

    Clicking the collapsed menu expands the list of options; clicking an
    option selects it, collapses the menu and invokes `on_select`.
    """

    def __init__(
        self,
        ax,
        options: list,
        on_select: Callable[[int, str], None] = None,
        initial_index: int = 0,
        label: str = None,
    ):
        assert options, "A DropdownMenu requires at least one option."
        self._ax = ax
        self._options = list(options)
        self._on_select = on_select
        self._selected_index = int(np.clip(initial_index, 0, len(options) - 1))
        self._label = label
        self._expanded = False
        self._option_axes = []

        self._ax.set_navigate(False)
        self._ax.set_xticks([])
        self._ax.set_yticks([])
        self._ax.set_facecolor("#efefef")
        if label:
            self._ax.set_title(label, fontsize=8, loc="left")
        self._text = self._ax.text(
            0.5,
            0.5,
            self._button_text(),
            ha="center",
            va="center",
            fontsize=8,
            transform=self._ax.transAxes,
        )
        self._create_option_axes()
        self._cid = self._ax.figure.canvas.mpl_connect(
            "button_press_event", self._on_click
        )

    @property
    def selected_index(self) -> int:
        """Index of the currently selected option."""
        return self._selected_index

    @property
    def selected_option(self) -> str:
        """Label of the currently selected option."""
        return self._options[self._selected_index]

    @property
    def expanded(self) -> bool:
        """True while the option list is visible."""
        return self._expanded

    @property
    def option_axes(self) -> list:
        return self._option_axes

    def _button_text(self) -> str:
        return f"{self.selected_option}  \u25bc"

    def _create_option_axes(self):
        """Creates one (hidden) axes per option underneath the menu."""
        fig = self._ax.figure
        x0, y0, width, height = self._ax.get_position().bounds
        for i, option in enumerate(self._options):
            rect = [x0, y0 - height * (i + 1), width, height]
            option_ax = fig.add_axes(rect, zorder=10)
            option_ax.set_navigate(False)
            option_ax.set_xticks([])
            option_ax.set_yticks([])
            option_ax.set_facecolor("#ffffff")
            option_ax.text(
                0.5,
                0.5,
                option,
                ha="center",
                va="center",
                fontsize=8,
                transform=option_ax.transAxes,
            )
            option_ax.set_visible(False)
            self._option_axes.append(option_ax)

    def _set_expanded(self, expanded: bool):
        self._expanded = expanded
        for option_ax in self._option_axes:
            option_ax.set_visible(expanded)
        self._redraw()

    def _redraw(self):
        canvas = self._ax.figure.canvas
        if canvas is not None:
            canvas.draw_idle()

    def toggle(self):
        """Expands/collapses the menu."""
        self._set_expanded(not self._expanded)

    def select(self, index: int):
        """Selects an option by index, notifying the `on_select` callback."""
        index = int(index)
        assert 0 <= index < len(self._options), "Invalid dropdown index."
        self._selected_index = index
        self._text.set_text(self._button_text())
        self._set_expanded(False)
        if self._on_select is not None:
            self._on_select(index, self._options[index])

    def _on_click(self, event):
        if event.inaxes is self._ax:
            self.toggle()
            return
        if not self._expanded:
            return
        for i, option_ax in enumerate(self._option_axes):
            if event.inaxes is option_ax:
                self.select(i)
                return
        # A click anywhere else collapses the menu.
        self._set_expanded(False)

    def disconnect(self):
        """Disconnects the menu from the canvas."""
        canvas = self._ax.figure.canvas
        if canvas is not None:
            canvas.mpl_disconnect(self._cid)


class MockEffectPlayer:
    """
    Visualizes an LED effect using Matplotlib.

    The player supports both a single LedStrip and a grid of equal length
    LedStrips (as used by effects such as the WaterDropletEffect). The grid
    is drawn with every strip laid out horizontally, strip 0 being the top
    row of the "LED Grid". The "Brightness" heat map uses the same 2D
    layout, while the RGB channel graphs render the strip(s) picked with the
    dropdown menu.

    IMPORTANT: This player must run on the main thread due to OS restrictions on
    GUI toolkits. To use it, call a method like `loop()` or `play_for()`,
    which returns a handle, and then call `plt.show()` from your main script.
    """

    ALL_STRIPS_LABEL = "All Strips"

    def __init__(
        self,
        strip: LedStrip | list = None,
        effect: LedEffect = None,
        fps: float = 30.0,
    ):
        """
        Args:
            strip: A single LedStrip or a list/grid of equal length LedStrips.
                When omitted, the strips are pulled from the effect.
            effect: The LedEffect to visualize.
            fps: Frames per second of the animation.
        """
        assert effect is not None, "MockEffectPlayer requires an LedEffect."
        self._strips = self._normalize_strips(strip, effect)
        # Kept for backwards compatibility (single strip visualizations).
        self._strip = self._strips[0]
        self._num_strips = len(self._strips)
        self._num_pixels = self._strip.num_pixels()
        self._effect = effect
        self._fps = fps
        self._play_time_s: float | None = None
        self._is_playing = False
        self._fig = None
        self._ani = None
        self._start_time = None
        self._dropdown = None
        # Index 0 selects every strip, index i + 1 selects strip i.
        self._selected_option = 0
        self._r_lines = []
        self._g_lines = []
        self._b_lines = []

    @staticmethod
    def _normalize_strips(strip, effect) -> list:
        """Returns the list of LedStrips that should be visualized."""
        if strip is None:
            strip = getattr(effect, "led_strips", None)
        if strip is None:
            strip = getattr(effect, "_strip", None)
        assert strip is not None, "MockEffectPlayer requires an LedStrip."
        strips = [strip] if isinstance(strip, LedStrip) else list(strip)
        assert strips, "MockEffectPlayer requires at least one LedStrip."
        num_pixels = strips[0].num_pixels()
        for led_strip in strips:
            assert (
                led_strip.num_pixels() == num_pixels
            ), "Every LedStrip of the grid must have the same LED count."
        return strips

    # ------------------------------------------------------------------
    # Data helpers
    # ------------------------------------------------------------------
    @property
    def strips(self) -> list:
        """The LedStrips that make up the visualized grid."""
        return self._strips

    @property
    def dropdown(self) -> DropdownMenu:
        """The dropdown menu used to pick the RGB channel source."""
        return self._dropdown

    def _strip_options(self) -> list:
        return [self.ALL_STRIPS_LABEL] + [f"Strip {i}" for i in range(self._num_strips)]

    def _pixel_grid(self) -> np.ndarray:
        """Returns a (num_strips, num_pixels, 3) grid of RGB values."""
        return np.array(
            [np.asarray(strip.get_pixels(), dtype=float) for strip in self._strips]
        )

    def _brightness_grid(self, pixels: np.ndarray) -> np.ndarray:
        """Returns the (num_strips, num_pixels) brightness of every LED."""
        strip_brightness = np.array(
            [strip.brightness for strip in self._strips], dtype=float
        )
        return np.clip(
            (pixels.max(axis=2) / 255.0) * strip_brightness[:, None], 0.0, 1.0
        )

    def _on_dropdown_select(self, index: int, _label: str):
        self._selected_option = index
        self._apply_line_visibility()
        if self._fig is not None and self._fig.canvas is not None:
            self._fig.canvas.draw_idle()

    def _apply_line_visibility(self):
        """Shows only the RGB lines of the currently selected strip(s)."""
        for i in range(self._num_strips):
            visible = self._selected_option == 0 or self._selected_option == i + 1
            for lines in (self._r_lines, self._g_lines, self._b_lines):
                lines[i].set_visible(visible)

    def select_strip(self, index: int):
        """Selects which strip the RGB graphs display (-1 for all strips)."""
        option = 0 if index < 0 else index + 1
        if self._dropdown is not None:
            self._dropdown.select(option)
        else:
            self._on_dropdown_select(option, "")

    # ------------------------------------------------------------------
    # Plot setup
    # ------------------------------------------------------------------
    def _setup_plot(self):
        """Initializes the Matplotlib figure and axes for the animation."""
        self._fig = plt.figure(figsize=(13, 7))
        try:
            self._fig.canvas.manager.set_window_title("LED Effect Mock Player")
        except AttributeError:
            pass
        grid_spec = self._fig.add_gridspec(
            6,
            2,
            width_ratios=[1.6, 1.0],
            left=0.06,
            right=0.96,
            top=0.86,
            bottom=0.08,
            hspace=1.4,
            wspace=0.22,
        )
        grid_ax = self._fig.add_subplot(grid_spec[0:3, 0])
        brightness_ax = self._fig.add_subplot(grid_spec[3:6, 0])
        r_ax = self._fig.add_subplot(grid_spec[0:2, 1])
        g_ax = self._fig.add_subplot(grid_spec[2:4, 1])
        b_ax = self._fig.add_subplot(grid_spec[4:6, 1])
        self._grid_ax = grid_ax
        self._brightness_ax = brightness_ax
        self._rgb_axes = (r_ax, g_ax, b_ax)

        pixels = self._pixel_grid()

        # --- "LED Grid": every strip laid out horizontally ----------------
        x = np.tile(np.arange(self._num_pixels), self._num_strips)
        y = np.repeat(np.arange(self._num_strips), self._num_pixels)
        grid_ax.set(
            xlim=(-1, self._num_pixels),
            ylim=(self._num_strips - 0.5, -0.5),
            title="LED Grid",
        )
        grid_ax.set_ylabel("Strip")
        grid_ax.set_facecolor("#101010")
        grid_ax.set_yticks(np.arange(self._num_strips))
        marker_size = max(8, min(100, 4000 / max(self._num_pixels, 1)))
        self._scat = grid_ax.scatter(
            x, y, s=marker_size, c=pixels.reshape(-1, 3) / 255.0
        )

        # --- "Brightness": 2D heat map using the same layout --------------
        brightness = self._brightness_grid(pixels)
        brightness_ax.set(title="Brightness")
        brightness_ax.set_ylabel("Strip")
        brightness_ax.set_xlabel("LED")
        self._brightness_image = brightness_ax.imshow(
            brightness,
            cmap="inferno",
            vmin=0.0,
            vmax=1.0,
            aspect="auto",
            interpolation="nearest",
            extent=(-0.5, self._num_pixels - 0.5, self._num_strips - 0.5, -0.5),
        )
        brightness_ax.set_yticks(np.arange(self._num_strips))
        self._fig.colorbar(
            self._brightness_image, ax=brightness_ax, fraction=0.04, pad=0.02
        )

        # --- RGB channels of the selected strip(s) ------------------------
        self._r_lines, self._g_lines, self._b_lines = [], [], []
        titles = ("RGB Channels - Red", "Green", "Blue")
        colors = ("r", "g", "b")
        x_data = np.arange(self._num_pixels)
        for axis, title, color, lines in zip(
            self._rgb_axes,
            titles,
            colors,
            (self._r_lines, self._g_lines, self._b_lines),
        ):
            axis.set(
                xlim=(-1, self._num_pixels),
                ylim=(-5, 260),
                title=title,
            )
            for strip_index in range(self._num_strips):
                (line,) = axis.plot(
                    x_data,
                    np.zeros(self._num_pixels),
                    color=color,
                    alpha=1.0 if self._num_strips == 1 else 0.75,
                    linewidth=1.2,
                    label=f"Strip {strip_index}",
                )
                lines.append(line)

        # --- Dropdown used to pick the plotted strip(s) -------------------
        dropdown_ax = self._fig.add_axes([0.72, 0.90, 0.2, 0.045])
        self._dropdown = DropdownMenu(
            dropdown_ax,
            self._strip_options(),
            on_select=self._on_dropdown_select,
            initial_index=self._selected_option,
            label="RGB Source",
        )
        self._apply_line_visibility()

    def _artists(self) -> tuple:
        return tuple(
            [self._scat, self._brightness_image]
            + self._r_lines
            + self._g_lines
            + self._b_lines
        )

    def _refresh_render(self):
        """Pulls the current pixel data and refreshes every plot."""
        pixels = self._pixel_grid()
        self._scat.set_color(pixels.reshape(-1, 3) / 255.0)
        self._brightness_image.set_data(self._brightness_grid(pixels))
        x_data = np.arange(self._num_pixels)
        for strip_index in range(self._num_strips):
            strip_pixels = pixels[strip_index]
            self._r_lines[strip_index].set_data(x_data, strip_pixels[:, 0])
            self._g_lines[strip_index].set_data(x_data, strip_pixels[:, 1])
            self._b_lines[strip_index].set_data(x_data, strip_pixels[:, 2])
        return self._artists()

    def _update_frame(self, frame):
        """The function called by FuncAnimation on each frame."""
        if not self._is_playing:
            return self._artists()

        t = time.time() - self._start_time
        if self._play_time_s is not None and t >= self._play_time_s:
            self.stop()
            return self._artists()

        self._effect.update(t)
        return self._refresh_render()

    def _on_window_close(self, evt):
        """A dedicated callback for when the Matplotlib window is closed."""
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

        self._fig.canvas.mpl_connect("close_event", self._on_window_close)

        # Blitting is disabled so the dropdown menu and the brightness heat
        # map are always redrawn correctly.
        self._ani = animation.FuncAnimation(
            fig=self._fig,
            func=self._update_frame,
            interval=interval_ms,
            blit=False,
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
        if not self._is_playing or self._fig is None:
            return
        self._is_playing = False
        if self._ani is not None and self._ani.event_source is not None:
            self._ani.event_source.stop()
        if self._dropdown is not None:
            self._dropdown.disconnect()
        plt.close(self._fig)
