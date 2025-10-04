import abc
from pedalboard.io import AudioStream
from pydub import AudioSegment
from random import choice
import threading
import logging
import numpy as np

import cauldron.assets.audio as audio_assets
import cauldron.config.config as config
import cauldron.core.new_led_effect as led_effect
import cauldron.core.led_strip as led_strip
import cauldron.core.new_players as players


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
    def play_sound(self, sound: int | str) -> None:
        """
        Play a soundbite by index or name from config.AUDIO_SOUNDBITES.
        Args:
            sound: Index (int) or filename (str) from AUDIO_SOUNDBITES.
        """
        pass

    @abc.abstractmethod
    def start_voice(self, voice_name: str) -> None:
        """Plays the voice in realtime."""
        pass

    @abc.abstractmethod
    def stop_active_voice(self) -> None:
        """Stops the active realtime voice."""
        pass


class Cauldron(ICauldron):
    """Cauldron implementation."""

    def __init__(
        self,
        strip: led_strip.LedStrip,
        rt_input_device: str = None,
        rt_output_device: str = None,
    ):
        """Initialize the Cauldron with a given LED strip and optional realtime audio devices."""
        self._lock = threading.Lock()
        self._strip = strip

        # Store realtime audio device configuration
        self._rt_input_device = (
            rt_input_device or AudioStream.input_device_names[0]
        )
        self._rt_output_device = (
            rt_output_device or AudioStream.output_device_names[0]
        )

        self._bubbling_wav = audio_assets.get_path(config.AUDIO_BUBBLING)
        self._explosion_wav = audio_assets.get_path(config.AUDIO_EXPLOSION)
        # Pool all soundbites into a single list from config.AUDIO_SOUNDBITES
        self._soundbite_wavs = [
            audio_assets.get_path(wav) for wav in config.AUDIO_SOUNDBITES
        ]

        # Initialize bubbling effects players
        self._bubbling_player: players.LedEffectPlayer = None
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
        self._soundbite_audio: list[players.AudioVisualPlayer] = None
        self._init_voice_effects()

        # Inititalize realtime voice effects
        self._rt_voice_handle: players.Handle = None
        self._voice_players: dict[str, players.RealtimeAudioPlayer] = {}
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
        self._bubbling_handle = self._bubbling_player.loop()

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
            self._strip, audio_segment
        )
        effect_player = players.LedEffectPlayer(a2b_effect)
        av_player = players.AudioVisualPlayer(effect_player, audio)
        return av_player

    def _init_realtime_voice_effects(self):
        """Initializes realtime voice effects from config.VOICES using direct effect instances."""
        self._voice_players = {}
        for name, voice_cfg in config.VOICES.items():
            effects = voice_cfg.get("effects", [])
            self._voice_players[name] = players.RealtimeAudioPlayer(
                effects,
                input_device=self._rt_input_device,
                output_device=self._rt_output_device,
            )

    def _init_voice_effects(self):
        """Initializes soundbite effects."""
        self._soundbite_audio = self._init_audio_list(self._soundbite_wavs)

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
        """Initializes the bubbling effects with color transitions every 2 minutes, using color pairs."""

        def random_color():
            return np.random.randint(0, 256, size=3).tolist()

        start_color = random_color()
        self._strip.fill(start_color)
        self._strip.show()
        bubbling_effect = led_effect.BubblingEffect(
            self._strip, [start_color, random_color()]
        )
        effect = led_effect.EffectChain(
            self._strip,
            [
                led_effect.EffectWithDuration(
                    led_effect.TransitionEffect(self._strip, randomize=True, duration=10),
                    10,
                ),
                led_effect.EffectWithDuration(
                    led_effect.TransitionEffect(self._strip, randomize=True, duration=10),
                    10,
                ),
            ],
        )
        # Use the new RepeatedEffectChainPlayer with Duration objects
        self._bubbling_player = players.LedEffectPlayer(effect, 30)

        segment = AudioSegment.from_file(self._bubbling_wav)
        segment.frame_rate = int(segment.frame_rate / 4)
        self._bubbling_audio_player = players.AudioPlayer(segment)

    def cause_explosion(self):
        """Causing an explosion will change the color and strobe the lights."""
        if self._explosion_handle is not None:
            self._explosion_handle.stop_wait()
        self._explosion_handle = self._explosion_player.play()

    def play_random_voice(self):
        """Plays a random soundbite."""
        if self._voice_handle is not None:
            self._voice_handle.stop_wait()
        self._voice_handle = choice(self._soundbite_audio).play()

    def play_sound(self, sound: int | str = 0):
        """
        Play a soundbite by index or name from config.AUDIO_SOUNDBITES.
        Args:
            sound: Index (int) or filename (str) from AUDIO_SOUNDBITES.
        """
        if self._voice_handle is not None:
            self._voice_handle.stop_wait()
        idx = None
        if isinstance(sound, int):
            idx = sound
        elif isinstance(sound, str):
            if sound.isdigit():
                idx = int(sound)
            elif sound in config.AUDIO_SOUNDBITES:
                idx = config.AUDIO_SOUNDBITES.index(sound)
        if idx is not None and 0 <= idx < len(self._soundbite_audio):
            self._voice_handle = self._soundbite_audio[idx].play()
        else:
            logging.warning(f"Invalid sound: {sound}")

    def start_voice(self, voice_name: str):
        """Plays the selected voice in realtime."""
        self.stop_active_voice()
        player = self._voice_players.get(voice_name)
        if player:
            self._rt_voice_handle = player.loop()
        else:
            logging.warning(
                f"Voice '{voice_name}' not found in config.VOICES."
            )

    def stop_active_voice(self):
        """Stops the active realtime voice."""
        if self._rt_voice_handle is not None:
            self._rt_voice_handle.stop_wait()


_HELP_STRING: str = f"""
e:   Explosion
d:   Start/Stop Demon Voice
w:   Start/Stop Witch Voice
1-{len(config.AUDIO_SOUNDBITES)}: Play spooky sounds
q: exit

Input: 
"""


class CauldronRunner:
    def __init__(
        self,
        strip: led_strip.LedStrip,
        rt_input_device: str = None,
        rt_output_device: str = None,
    ):
        self._strip = strip
        self._rt_input_device = rt_input_device
        self._rt_output_device = rt_output_device
        self._command_map = {
            "e": self._explosion,
            "s": self._stop_voice,
            "q": self._quit,
        }
        # Add voice commands dynamically
        self._voice_key_map = {}
        for voice_name in config.VOICES.keys():
            key_length = 1
            while voice_name[0:key_length] in self._command_map:
                key_length += 1
            key = voice_name[0:key_length]
            self._command_map[key] = self._make_voice_cmd(voice_name)
            self._voice_key_map[key] = voice_name
        self._running = True

    def _make_voice_cmd(self, voice_name):
        def cmd(cauldron):
            cauldron.stop_active_voice()
            logging.info(f"Playing {voice_name} voice")
            cauldron.start_voice(voice_name)

        return cmd

    def _explosion(self, cauldron):
        logging.info("Causing explosion")
        cauldron.cause_explosion()

    def _stop_voice(self, cauldron):
        cauldron.stop_active_voice()
        logging.info("Stopped active voice")

    def _quit(self, cauldron):
        self._running = False
        del cauldron
        logging.info("Exiting CauldronRunner")

    def _run(self):
        cauldron = Cauldron(
            self._strip,
            rt_input_device=self._rt_input_device,
            rt_output_device=self._rt_output_device,
        )
        help_string = (
            _HELP_STRING
            + "\n"
            + "Voices: "
            + ", ".join(
                [f"{key}: {name}" for key, name in self._voice_key_map.items()]
            )
            + "\n"
        )
        try:
            while self._running:
                user = input(help_string).strip()
                if user.isdigit():
                    logging.info(f"Playing sound {user}")
                    cauldron.play_sound(int(user) - 1)
                elif user in self._command_map:
                    self._command_map[user](cauldron)
                else:
                    cauldron.cause_explosion()
                    logging.warning(f"Unknown command: {user}")
        except Exception as e:
            logging.exception("Error in CauldronRunner: %s", e)
            del cauldron

    def run(self):
        """Run the CauldronRunner in a separate thread."""
        t = threading.Thread(target=self._run)
        t.start()
        t.join()
