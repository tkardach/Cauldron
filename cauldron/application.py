import logging
from dataclasses import dataclass

import numpy as np
from pedalboard.io import AudioStream

import cauldron.config.config as config
from cauldron.assets.manager import AssetManager
from cauldron.core.cauldron import Cauldron, CauldronRunner
from cauldron.core.events import EventBus, Events
from cauldron.core.led_effect import (
    AudioToBrightnessEffect,
    EffectChain,
    EffectWithDuration,
    TransitionEffect,
)
from cauldron.core.led_strip import LedStrip
from cauldron.core.players import (
    AudioPlayer,
    AudioVisualPlayer,
    LedEffectPlayer,
    Player,
    RealtimeAudioPlayer,
)


@dataclass
class CauldronApplication:
    """Project composition root for the generic player manager and command runner."""

    cauldron: Cauldron
    runner: CauldronRunner
    strip: LedStrip

    def run(self) -> None:
        try:
            self.runner.run()
        finally:
            self.stop()

    def stop(self) -> None:
        """Stop players and clear the project hardware output."""
        self.cauldron.stop()
        self.strip.fill((0, 0, 0))
        self.strip.show()


def build_application(
    strip: LedStrip,
    rt_input_device: str | None = None,
    rt_output_device: str | None = None,
) -> CauldronApplication:
    """Create the Halloween project effects and inject them into the generic core."""
    assets = AssetManager()
    output_device = rt_output_device or AudioStream.default_output_device_name
    input_device = _resolve_input_device(rt_input_device, output_device)

    start_color = np.random.randint(0, 256, size=3).tolist()
    strip.fill(start_color)
    strip.show()
    bubbling_effect = EffectChain(
        strip,
        [
            EffectWithDuration(
                TransitionEffect(strip, randomize=True, duration=10), 10
            ),
            EffectWithDuration(
                TransitionEffect(strip, randomize=True, duration=10), 10
            ),
        ],
    )
    bubbling_visual_player = LedEffectPlayer(bubbling_effect, 30.0)
    bubbling_audio_player = AudioPlayer(
        assets.load_audio(config.AUDIO_BUBBLING, playback_rate_scale=0.25),
        output_device_name=output_device,
    )

    def audio_visual_player(segment) -> AudioVisualPlayer:
        audio_player = AudioPlayer(segment, output_device_name=output_device)
        visual_player = LedEffectPlayer(AudioToBrightnessEffect(strip, segment))
        return AudioVisualPlayer(visual_player, audio_player)

    explosion_player = audio_visual_player(
        assets.load_audio(
            config.AUDIO_EXPLOSION,
            sample_width=2,
            gain_db=30,
        )
    )
    soundbite_players = [
        audio_visual_player(assets.load_audio(filename))
        for filename in config.AUDIO_SOUNDBITES
    ]
    voice_players = {
        name: RealtimeAudioPlayer(
            voice_config.get("effects", []),
            input_device=input_device,
            output_device=output_device,
        )
        for name, voice_config in config.VOICES.items()
    }
    all_players: list[Player] = [
        bubbling_visual_player,
        bubbling_audio_player,
        explosion_player,
        *soundbite_players,
        *voice_players.values(),
    ]
    cauldron = Cauldron(all_players)
    event_bus = EventBus()
    active_voice: dict[str, RealtimeAudioPlayer | None] = {"player": None}
    bubbles_enabled = False

    event_bus.subscribe(Events.EXPLOSION, lambda: cauldron.play(explosion_player))

    def toggle_bubbles() -> None:
        nonlocal bubbles_enabled
        if bubbles_enabled:
            cauldron.stop_player(bubbling_visual_player)
            cauldron.stop_player(bubbling_audio_player)
        else:
            cauldron.loop(bubbling_visual_player)
            cauldron.loop(bubbling_audio_player)
        bubbles_enabled = not bubbles_enabled

    def play_sound(index: int) -> None:
        if 0 <= index < len(soundbite_players):
            cauldron.play(soundbite_players[index])
        else:
            logging.warning("Invalid sound index: %s", index)

    def start_voice(voice_name: str) -> None:
        player = voice_players.get(voice_name)
        if player is None:
            logging.warning("Voice '%s' is not configured", voice_name)
            return
        stop_voice()
        active_voice["player"] = player
        cauldron.loop(player)

    def stop_voice() -> None:
        player = active_voice["player"]
        if player is not None:
            cauldron.stop_player(player)
            active_voice["player"] = None

    event_bus.subscribe(Events.PLAY_SOUND, play_sound)
    event_bus.subscribe(Events.TOGGLE_BUBBLES, toggle_bubbles)
    event_bus.subscribe(Events.START_VOICE, start_voice)
    event_bus.subscribe(Events.STOP_VOICE, stop_voice)

    cauldron.start()
    runner = CauldronRunner(
        event_bus,
        voice_names=config.VOICES.keys(),
        sound_count=len(config.AUDIO_SOUNDBITES),
    )
    application = CauldronApplication(cauldron, runner, strip)

    def stop_application() -> None:
        stop_voice()
        application.stop()

    event_bus.subscribe(Events.QUIT, stop_application)
    return application


def _resolve_input_device(
    requested_device: str | None, output_device: str
) -> str:
    """Prefer a microphone when the system default input is the output device."""
    if requested_device:
        return requested_device

    default_input = AudioStream.default_input_device_name
    if default_input != output_device:
        return default_input

    microphone = next(
        (
            device
            for device in AudioStream.input_device_names
            if device != output_device and "microphone" in device.casefold()
        ),
        None,
    )
    if microphone is not None:
        logging.info(
            "Default audio input matches output device; using microphone %s",
            microphone,
        )
        return microphone
    return default_input
