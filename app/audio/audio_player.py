import abc
import audioop
from pydub import AudioSegment
import simpleaudio as sa
import threading


class PlaybackHandle:
    def __init__(self, player: "AudioPlayer"):
        self._player = player

    def __del__(self):
        self._player.stop()

    def stop(self):
        self._player.stop()


class AudioPlayer(abc.ABC):
    @abc.abstractmethod
    def play(self) -> None:
        return None

    @abc.abstractmethod
    def play_async(self) -> PlaybackHandle:
        return None

    @abc.abstractmethod
    def loop(self) -> PlaybackHandle:
        return None

    @abc.abstractmethod
    def stop(self) -> None:
        return None

    @property
    @abc.abstractmethod
    def volume(self) -> int:
        return 0

    @volume.setter
    @abc.abstractmethod
    def volume(self, volume_diff: int) -> None:
        return None

    @property
    @abc.abstractmethod
    def frequency(self) -> int:
        return 0

    @frequency.setter
    @abc.abstractmethod
    def frequency(self, frequency: int) -> None:
        return None


class PydubAudioPlayer(AudioPlayer):
    def __init__(self, file: str):
        AudioPlayer.__init__(self)
        self._file = file
        self._lock = threading.Lock()
        self._sound = AudioSegment.from_wav(self._file)
        self._loop_thread = None
        self._loop_handler = None
        self._play_buffer = None

    def _create_play_buffer(self) -> sa.PlayObject:
        return sa.play_buffer(
            self._sound.raw_data,
            num_channels=self._sound.channels,
            bytes_per_sample=self._sound.sample_width,
            sample_rate=self._sound.frame_rate,
        )

    def _loop_audio(self):
        while self._play_audio:
            with self._lock:
                self._play_buffer = self._create_play_buffer()
            self._play_buffer.wait_done()

    def play(self) -> None:
        with self._lock:
            self._play_buffer = self._create_play_buffer()
        self._play_buffer.wait_done()

    def play_async(self) -> PlaybackHandle:
        return PlaybackHandle(self)

    def loop(self) -> PlaybackHandle:
        with self._lock:
            if self._loop_handler is None:
                return self._loop_handler
            self._play_audio = True
            self._loop_thread = threading.Thread(
                target=self._loop_audio
            ).start()
            self._loop_handler = PlaybackHandle(self)
            return self._loop_handler

    def stop(self):
        with self._lock:
            self._play_audio = False
            if self._play_buffer:
                self._play_buffer.stop()

    @property
    def volume(self) -> int:
        return audioop.rms(self._sound.raw_data, self._sound.sample_width)

    @volume.setter
    def volume(self, volume_diff: int) -> None:
        with self._lock:
            self._sound += volume_diff

    @property
    def frequency(self) -> int:
        return self._sound.frame_rate

    @frequency.setter
    def frequency(self, frequency: int) -> None:
        with self._lock:
            self._sound.frame_rate = frequency
