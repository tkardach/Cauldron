import abc
import logging
import threading
from collections.abc import Iterable

from cauldron.core.players import Handle, Player
from cauldron.core.events import EventBus, Events


class ICauldron(abc.ABC):
    """Generic player lifecycle interface."""

    @abc.abstractmethod
    def start(self) -> None:
        """Start configured loop players."""

    @abc.abstractmethod
    def stop(self) -> None:
        """Stop managed players."""

    @abc.abstractmethod
    def is_playing(self) -> bool:
        """Return whether a managed player is active."""


class Cauldron(ICauldron):
    """Manages the lifecycle of an injected collection of players."""

    def __init__(
        self,
        players: Iterable[Player],
        loop_players: Iterable[Player] = (),
    ):
        self._lock = threading.RLock()
        self._players = list(dict.fromkeys(players))
        self._loop_players = list(dict.fromkeys(loop_players))
        unknown_players = set(self._loop_players) - set(self._players)
        if unknown_players:
            raise ValueError("loop_players must be included in players")
        self._handles: dict[Player, Handle] = {}

    def start(self) -> None:
        """Start all injected players designated to loop."""
        with self._lock:
            for player in self._loop_players:
                handle = self._handles.get(player)
                if handle is None or not handle.is_playing():
                    self._handles[player] = player.loop()

    def play(self, player: Player) -> Handle:
        """Play an injected player once and track its handle."""
        self._validate_player(player)
        with self._lock:
            handle = player.play()
            self._handles[player] = handle
            return handle

    def loop(self, player: Player) -> Handle:
        """Loop an injected player and track its handle."""
        self._validate_player(player)
        with self._lock:
            handle = player.loop()
            self._handles[player] = handle
            return handle

    def stop_player(self, player: Player) -> None:
        """Stop one injected player if it is active."""
        self._validate_player(player)
        with self._lock:
            handle = self._handles.pop(player, None)
            if handle is not None:
                handle.stop_wait()

    def stop(self) -> None:
        """Stop all players started through this manager."""
        with self._lock:
            handles = list(self._handles.values())
            for handle in handles:
                handle.stop_wait()
            self._handles.clear()

    def is_playing(self) -> bool:
        """Return whether any managed player is currently active."""
        with self._lock:
            return any(handle.is_playing() for handle in self._handles.values())

    def _validate_player(self, player: Player) -> None:
        if player not in self._players:
            raise ValueError("Player is not managed by this Cauldron")


class CauldronRunner:
    """Reads terminal commands and publishes them without owning a Cauldron."""

    def __init__(
        self,
        event_bus: EventBus,
        voice_names: Iterable[str] = (),
        sound_count: int = 0,
    ):
        self._event_bus = event_bus
        self._voice_key_map: dict[str, str] = {}
        self._command_map = {
            "b": (Events.TOGGLE_BUBBLES, None),
            "e": (Events.EXPLOSION, None),
            "s": (Events.STOP_VOICE, None),
            "q": (Events.QUIT, None),
        }
        for voice_name in voice_names:
            key_length = 1
            while voice_name[:key_length] in self._command_map:
                key_length += 1
            key = voice_name[:key_length]
            self._command_map[key] = (Events.START_VOICE, voice_name)
            self._voice_key_map[key] = voice_name
        self._sound_count = sound_count
        self._running = True

    def _help_text(self) -> str:
        sound_keys = (
            f"1-{self._sound_count}: Play spooky sounds" if self._sound_count else ""
        )
        voice_entries = sorted(
            self._voice_key_map.items(), key=lambda entry: entry[1].casefold()
        )
        key_width = max((len(key) for key, _ in voice_entries), default=0)
        voice_keys = (
            "\n".join(
                ["Voices:"]
                + [f"  {key:<{key_width}}: {name}" for key, name in voice_entries]
            )
            if voice_entries
            else ""
        )
        return "\n".join(
            part
            for part in (
                "b: Toggle bubbles",
                "e: Explosion",
                "s: Stop active voice",
                sound_keys,
                voice_keys,
                "q: exit",
            )
            if part
        )

    def _run(self) -> None:
        help_text = self._help_text()
        try:
            print(help_text)
            while self._running:
                command = input("Input: ").strip()
                if not command:
                    continue
                if command.isdigit():
                    self._event_bus.publish(Events.PLAY_SOUND, int(command) - 1)
                    continue
                event, payload = self._command_map.get(
                    command, (Events.EXPLOSION, None)
                )
                if command not in self._command_map:
                    logging.warning("Unknown command: %s", command)
                if event == Events.QUIT:
                    self._running = False
                if payload is None:
                    self._event_bus.publish(event)
                else:
                    self._event_bus.publish(event, payload)
        except Exception:
            logging.exception("Error in CauldronRunner")
            self._event_bus.publish(Events.QUIT)

    def run(self) -> None:
        """Run the interactive command reader on the calling thread."""
        self._run()
