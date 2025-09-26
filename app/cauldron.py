import abc
from enum import Enum
import led_effect
import led_strip
import os
import players
from pedalboard import Reverb, PitchShift
from pedalboard.io import AudioStream
from pydub import AudioSegment
from random import choice
import threading
import logging
import config


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
    def start(self) -> None:
        """Start the cauldron effects."""
        pass

    @abc.abstractmethod
    def stop(self) -> None:
        """Stop all cauldron effects."""
        pass

    @abc.abstractmethod
    def is_playing(self) -> bool:
        """Check if the cauldron is currently playing any effects."""
        pass

    @abc.abstractmethod
    def cause_explosion(self) -> None:
        """Causes the Cauldron to explode, changing the color."""
        pass

    @abc.abstractmethod
    def play_random_voice(self) -> None:
        """Plays a random voice effect."""
        pass

    @abc.abstractmethod
    def play_sound(self, sound: CauldronSounds) -> None:
        """Plays a sound using the given sound type."""
        pass

    @abc.abstractmethod
    def start_demon_voice(self) -> None:
        """Plays the demon voice in realtime."""
        pass

    @abc.abstractmethod
    def start_witch_voice(self) -> None:
        """Plays the witch voice in realtime."""
        pass

    @abc.abstractmethod
    def stop_active_voice(self) -> None:
        """Stops the active realtime voice."""
        pass


class Cauldron(ICauldron):
    """Cauldron implementation."""

    def __init__(self, strip: led_strip.LedStrip):
        """Initialize the Cauldron with a given LED strip."""
        self._lock = threading.Lock()
        self._strip = strip

        # Initialize audio paths
        self._bubbling_wav = os.path.join(
            config.AUDIO_PATH, config.AUDIO_BUBBLING
        )
        self._explosion_wav = os.path.join(
            config.AUDIO_PATH, config.AUDIO_EXPLOSION
        )
        self._witch_wavs = [
            os.path.join(config.AUDIO_PATH, wav) for wav in config.AUDIO_WITCH
        ]
        self._demon_wavs = [
            os.path.join(config.AUDIO_PATH, wav) for wav in config.AUDIO_DEMON
        ]

        # Initialize color possibilities
        self._colors = config.CAULDRON_COLORS
        self._current_color_index = 1
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
        self._rt_voice_handle: players.Handle = None
        self._rt_demon_voice_player: players.RealtimeAudioPlayer = None
        self._rt_witch_voice_player: players.RealtimeAudioPlayer = None
        self._init_realtime_voice_effects()

        # Start the common effect
        self.start()

    def __del__(self):
        self.stop()

    def start(self):
        """Start the cauldron effects."""
        if (
            self._bubbling_audio_handle is not None
            or self._bubbling_handle is not None
        ):
            return
        self._bubbling_audio_handle = self._bubbling_audio_player.loop()
        self._start_common_effect()

    def stop(self):
        """Stop all cauldron effects."""
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
        if self._voice_handle:
            self._voice_handle.stop_wait()
            self._voice_handle = None
        if self._rt_voice_handle:
            self._rt_voice_handle.stop_wait()
            self._rt_voice_handle = None

    def is_playing(self):
        """Check if the cauldron is currently playing any effects."""
        return (
            self._bubbling_audio_handle.is_playing()
            and self._bubbling_handle.is_playing()
        )

    def _create_a2b_av_effect(
        self, audio_segment: AudioSegment
    ) -> players.AudioVisualPlayer:
        """Creates an AudioVisualPlayer using an AudioToBrightness effect."""
        audio = players.AudioPlayer(audio_segment)

        a2b_effect = led_effect.AudioToBrightnessEffect(
            self._strip, audio_segment, frame_speed_ms=config.FRAME_SPEED_MS
        )
        effect_player = players.LedEffectPlayer(a2b_effect)
        av_player = players.AudioVisualPlayer(effect_player, audio)
        return av_player

    def _init_realtime_voice_effects(self):
        """Initializes realtime voice effects."""
        self._rt_demon_voice_player = players.RealtimeAudioPlayer(
            [Reverb(), PitchShift(-4)],
            input_device=AudioStream.input_device_names[0],
        )
        self._rt_witch_voice_player = players.RealtimeAudioPlayer(
            [Reverb(), PitchShift(3)],
            input_device=AudioStream.input_device_names[0],
        )

    def _init_voice_effects(self):
        """Initializes voice effects."""
        self._witch_audio = self._init_audio_list(self._witch_wavs)
        self._demon_audio = self._init_audio_list(self._demon_wavs)
        self._all_voices = self._witch_audio + self._demon_audio

    def _init_audio_list(
        self, wav_list: list[str]
    ) -> list[players.AudioVisualPlayer]:
        """Helper to create AudioVisualPlayers from a list of wav files."""
        return [
            self._create_a2b_av_effect(AudioSegment.from_file(wav))
            for wav in wav_list
        ]

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
                config.BUBBLE_LENGTHS,
                config.BUBBLE_PROB_WEIGHTS,
                config.BUBBLE_POP_SPEEDS,
                config.BUBBLE_PROB_WEIGHTS,
                config.MAX_BUBBLES,
                config.BUBBLE_SPAWN_PROB,
                frame_speed_ms=config.FRAME_SPEED_MS,
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
        self._explosion_handle = self._explosion_player.play()
        self._set_random_colors()

    def play_random_voice(self):
        """Plays a random voice."""
        if self._voice_handle is not None:
            self._voice_handle.stop_wait()
        self._voice_handle = choice(self._all_voices).play()

    def play_sound(self, sound: CauldronSounds = CauldronSounds.NONE):
        """Plays a sound using the given sound type."""
        if self._voice_handle is not None:
            self._voice_handle.stop_wait()
        match sound:
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
        self.stop_active_voice()

        self._rt_voice_handle = self._rt_demon_voice_player.loop()

    def start_witch_voice(self):
        """Plays the witch voice in realtime."""
        self.stop_active_voice()

        self._rt_voice_handle = self._rt_witch_voice_player.loop()

    def stop_active_voice(self):
        """Stops the active realtime voice."""
        if self._rt_voice_handle is not None:
            self._rt_voice_handle.stop_wait()


_HELP_STRING: str = """
e:   Explosion
d:   Start/Stop Demon Voice
w:   Start/Stop Witch Voice
1-8: Play spooky voices
q: exit

Input: 
"""


class CauldronRunner:
    def __init__(self, strip: led_strip.LedStrip):
        self._strip = strip
        self._command_map = {
            "e": self._explosion,
            "w": self._witch_voice,
            "d": self._demon_voice,
            "s": self._stop_voice,
            "q": self._quit,
        }
        self._running = True

    def _explosion(self, cauldron):
        logging.info("Causing explosion")
        cauldron.cause_explosion()

    def _witch_voice(self, cauldron):
        cauldron.stop_active_voice()
        logging.info("Playing witch voice")
        cauldron.start_witch_voice()

    def _demon_voice(self, cauldron):
        cauldron.stop_active_voice()
        logging.info("Playing demon voice")
        cauldron.start_demon_voice()

    def _stop_voice(self, cauldron):
        cauldron.stop_active_voice()
        logging.info("Stopped active voice")

    def _quit(self, cauldron):
        self._running = False
        del cauldron
        logging.info("Exiting CauldronRunner")

    def _run(self):
        cauldron = Cauldron(self._strip)
        try:
            while self._running:
                user = input(_HELP_STRING).strip()
                if user.isdigit():
                    logging.info(f"Playing sound {user}")
                    cauldron.play_sound(CauldronSounds(int(user)))
                elif user in self._command_map:
                    self._command_map[user](cauldron)
                else:
                    logging.warning(f"Unknown command: {user}")
        except Exception as e:
            logging.exception("Error in CauldronRunner: %s", e)
            del cauldron

    def run(self):
        """Run the CauldronRunner in a separate thread."""
        t = threading.Thread(target=self._run)
        t.start()
        t.join()
