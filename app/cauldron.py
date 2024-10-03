import abc
from enum import Enum
from typing import Tuple
import led_effect
import led_strip
import os
import players
from pedalboard import Reverb, PitchShift
from pydub import AudioSegment
from random import choice
import threading


_AUDIO_BUBBLING = "bubbles.wav"
_AUDIO_DEMON = ["evie.wav", "porter.wav", "creepy_laugh0.wav"]
_AUDIO_EXPLOSION = "poof.wav"
_AUDIO_WITCH = ["witch0.wav", "witch1.wav", "witch_closer.wav"]
_AUDIO_PATH = "app/files/audio/"
_BUBBLE_LENGTHS = [7, 9, 11]
_BUBBLE_POP_SPEEDS = [3000, 4000, 5000]
_BUBBLE_PROB_WEIGHTS = [0.5, 0.25, 0.25]
_BUBBLE_SPAWN_PROB = 0.05
_CAULDRON_COLORS = [
    ([32, 139, 25], [215, 232, 23]),
    ([142, 75, 166], [237, 114, 178]),
    ([255, 179, 0], [255, 0, 60]),
    ([235, 57, 21], [76, 172, 194]),
]
_MAX_BUBBLES = 10


class CauldronSounds(Enum):
    NONE = 0
    RANDOM_WITCH = 1
    WITCH_LAUGH0 = 2
    WITCH_LAUGH1 = 3
    WITCH_LAUGH2 = 4
    RANDOM_DEMON = 5
    DEMON_EVIE = 6
    DEMON_PORTER = 7
    DEMON_LAUGH = 8


class ICauldron(abc.ABC):
    """Interface to control the Cauldron."""

    @abc.abstractmethod
    def start(self):
        pass

    @abc.abstractmethod
    def stop(self):
        pass

    @abc.abstractmethod
    def is_playing(self):
        pass

    @abc.abstractmethod
    def cause_explosion(self):
        """Causes the Cauldron to explode, changing the color."""
        return None

    @abc.abstractmethod
    def play_random_voice(self):
        """Plays a random voice effect."""
        return None

    @abc.abstractmethod
    def play_sound(self, type: CauldronSounds):
        """Plays a random voice effect."""
        return None

    @abc.abstractmethod
    def start_demon_voice(self):
        """Plays the demon voice in realtime."""
        return None

    @abc.abstractmethod
    def stop_demon_voice(self):
        """Stops the demon voice."""
        return None


class Cauldron(ICauldron):
    """Cauldron implementation."""

    def __init__(self, strip: led_strip.LedStrip):
        self._lock = threading.Lock()
        self._strip = strip

        # Initialize audio paths
        self._bubbling_wav = os.path.join(_AUDIO_PATH, _AUDIO_BUBBLING)
        self._explosion_wav = os.path.join(_AUDIO_PATH, _AUDIO_EXPLOSION)
        self._witch_wavs = []
        for wav in _AUDIO_WITCH:
            self._witch_wavs.append(os.path.join(_AUDIO_PATH, wav))
        self._demon_wavs = []
        for wav in _AUDIO_DEMON:
            self._demon_wavs.append(os.path.join(_AUDIO_PATH, wav))

        # Initialize color possibilities
        self._colors = _CAULDRON_COLORS
        self._current_color_index = 0
        self._current_colors = self._colors[self._current_color_index]

        # Initialize bubbling effects players
        self._current_bubbling_effect: players.LedEffectPlayer = None
        self._bubbling_handle: players.Handle = None
        self._bubbling_audio_player: players.AudioPlayer = None
        self._bubbling_audio_handle: players.Handle = None
        self._init_bubbling_effects()

        # Initialize explosion effects
        self._explosion_handle: players.Handle = None
        self._explosion_player: players.AudioVisualPlayer = None
        self._init_explosion_effects()

        # Initialize voice audio effects
        self._voice_handle: players.Handle = None
        self._witch_audio: list[players.AudioVisualPlayer] = None
        self._demon_audio: list[players.AudioVisualPlayer] = None
        self._all_voices: list[players.AudioVisualPlayer] = None
        self._init_voice_effects()

        # Inititalize realtime voice effects
        self._rt_demon_voice_handle: players.Handle = None
        self._rt_demon_voice_player: players.RealtimeAudioPlayer = None
        self._rt_effect_handle: players.Handle = None
        self._rt_effect_player: players.VoiceToBrightnessPlayer = None
        self._init_realtime_voice_effects()

        # Start the common effect
        self.start()

    def __del__(self):
        self.stop()

    def start(self):
        if (
            self._bubbling_audio_handle is not None
            or self._bubbling_handle is not None
        ):
            return
        self._bubbling_audio_handle = self._bubbling_audio_player.loop()
        self._start_common_effect()

    def stop(self):
        self._strip.fill((0, 0, 0))
        self._strip.show()
        if self._explosion_handle:
            self._explosion_handle.stop_wait()
            self._explosion_handle = None
        if self._bubbling_handle:
            self._bubbling_handle.stop_wait()
            self._bubbling_handle = None
        if self._bubbling_audio_handle:
            self._bubbling_audio_handle.stop_wait()
            self._bubbling_audio_handle = None

    def is_playing(self):
        return (
            self._bubbling_audio_handle.is_playing()
            and self._bubbling_handle.is_playing()
        )

    def _create_a2b_av_effect(
        self, audio_segment
    ) -> players.AudioVisualPlayer:
        """Creates an AudioVisualPlayer using an AudioToBrightness effect."""
        audio = players.AudioPlayer(audio_segment)

        a2b_effect = led_effect.AudioToBrightnessEffect(
            self._strip, audio_segment, frame_speed_ms=33
        )
        effect_player = players.LedEffectPlayer(a2b_effect)
        av_player = players.AudioVisualPlayer(effect_player, audio)
        return av_player

    def _init_realtime_voice_effects(self):
        """Initializes realtime voice effects."""
        self._rt_demon_voice_player = players.RealtimeAudioPlayer(
            [Reverb(), PitchShift(-4)]
        )
        brightness_effect = led_effect.BrightnessEffect(
            self._strip, frame_speed_ms=33
        )
        self._rt_effect_player = players.VoiceToBrightnessPlayer(
            brightness_effect
        )

    def _init_voice_effects(self):
        """Initializes voice effects."""
        self._witch_audio = [
            self._create_a2b_av_effect(AudioSegment.from_file(wav))
            for wav in self._witch_wavs
        ]
        self._demon_audio = [
            self._create_a2b_av_effect(AudioSegment.from_file(wav))
            for wav in self._demon_wavs
        ]
        self._all_voices = self._witch_audio + self._demon_audio

    def _init_explosion_effects(self):
        """Initializes the cauldron's explosion effects."""
        segment = AudioSegment.from_file(self._explosion_wav)
        segment = segment.set_sample_width(2)
        segment += 30
        self._explosion_player = self._create_a2b_av_effect(segment)

    def _init_bubbling_effects(self):
        """Initializes the bubbling effects."""
        self._bubbling_effects: list[players.LedEffectPlayer] = []
        for colors in self._colors:
            bubbling_effect = led_effect.BubblingEffect(
                self._strip,
                colors[0],
                colors[1],
                _BUBBLE_LENGTHS,
                _BUBBLE_PROB_WEIGHTS,
                _BUBBLE_POP_SPEEDS,
                _BUBBLE_PROB_WEIGHTS,
                _MAX_BUBBLES,
                _BUBBLE_SPAWN_PROB,
                frame_speed_ms=33,
            )
            bubbling_effect_player = players.LedEffectPlayer(bubbling_effect)
            self._bubbling_effects.append(bubbling_effect_player)
        self._current_bubbling_effect = self._bubbling_effects[
            self._current_color_index
        ]

        segment = AudioSegment.from_file(self._bubbling_wav)
        segment.frame_rate = int(segment.frame_rate / 4)
        self._bubbling_audio_player = players.AudioPlayer(segment)

    def _set_random_colors(self):
        """Selects a new set of colors and applies it to the LedStrip."""
        with self._lock:
            self._current_color_index = choice(
                [
                    i
                    for i in range(0, len(self._colors))
                    if i != self._current_color_index
                ]
            )
            self._current_colors = self._colors[self._current_color_index]
            self._current_bubbling_effect = self._bubbling_effects[
                self._current_color_index
            ]
        self._start_common_effect()

    def _start_common_effect(self):
        """Starts the looping cauldron bubbling effect."""
        if self._bubbling_handle is not None:
            self._bubbling_handle.stop_wait()
        with self._lock:
            self._strip.fill(self._current_colors[0])
            self._bubbling_handle = self._current_bubbling_effect.loop()

    def cause_explosion(self):
        """Causing an explosion will change the color and strobe the lights."""
        if self._explosion_handle is not None:
            self._explosion_handle.stop_wait()
        self._set_random_colors()
        self._explosion_handle = self._explosion_player.play()

    def play_random_voice(self):
        """Plays a random voice."""
        if self._voice_handle is not None:
            self._voice_handle.stop_wait()
        self._voice_handle = choice(self._all_voices).play()

    def play_sound(self, type: CauldronSounds = CauldronSounds.NONE):
        """Plays a sound using the given sound type."""
        if self._voice_handle is not None:
            self._voice_handle.stop_wait()
        match type:
            case CauldronSounds.RANDOM_WITCH:
                self._voice_handle = choice(self._witch_audio).play()
            case CauldronSounds.WITCH_LAUGH0:
                self._voice_handle = self._witch_audio[0].play()
            case CauldronSounds.WITCH_LAUGH1:
                self._voice_handle = self._witch_audio[1].play()
            case CauldronSounds.WITCH_LAUGH2:
                self._voice_handle = self._witch_audio[2].play()
            case CauldronSounds.RANDOM_DEMON:
                self._voice_handle = choice(self._demon_audio).play()
            case CauldronSounds.DEMON_EVIE:
                self._voice_handle = self._demon_audio[0].play()
            case CauldronSounds.DEMON_PORTER:
                self._voice_handle = self._demon_audio[1].play()
            case CauldronSounds.DEMON_LAUGH:
                self._voice_handle = self._demon_audio[2].play()
            case _:
                return

    def start_demon_voice(self):
        """Plays the demon voice in realtime."""
        self.stop_demon_voice()

        self._rt_demon_voice_handle = self._rt_demon_voice_player.loop()
        self._rt_effect_handle = self._rt_effect_player.loop()

    def stop_demon_voice(self):
        """Stops the demon voice."""
        if self._rt_demon_voice_handle is not None:
            self._rt_demon_voice_handle.stop_wait()
        if self._rt_effect_handle is not None:
            self._rt_effect_handle.stop_wait()
