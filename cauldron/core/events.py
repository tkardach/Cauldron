import threading
from collections import defaultdict
from collections.abc import Callable


class Events:
    """Common command names used by the Cauldron application."""

    EXPLOSION = "explosion"
    TOGGLE_BUBBLES = "toggle_bubbles"
    PLAY_SOUND = "play_sound"
    START_VOICE = "start_voice"
    STOP_VOICE = "stop_voice"
    QUIT = "quit"


class EventBus:
    """A small synchronous publish/subscribe event dispatcher."""

    def __init__(self):
        self._lock = threading.RLock()
        self._subscribers: dict[str, list[Callable]] = defaultdict(list)

    def subscribe(self, event: str, handler: Callable) -> Callable[[], None]:
        """Register a handler and return a callable that unsubscribes it."""
        with self._lock:
            self._subscribers[event].append(handler)

        def unsubscribe() -> None:
            with self._lock:
                handlers = self._subscribers.get(event, [])
                if handler in handlers:
                    handlers.remove(handler)

        return unsubscribe

    def publish(self, event: str, *args, **kwargs) -> None:
        """Call a snapshot of the handlers subscribed to an event."""
        with self._lock:
            handlers = tuple(self._subscribers.get(event, ()))
        for handler in handlers:
            handler(*args, **kwargs)
