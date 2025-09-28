import led_strip
import players


class TestRunner:
    def __init__(
        self, mock_strip: led_strip.MockStrip, handles: list[players.Handle]
    ):
        self._strip = mock_strip
        self._handles = handles

    def run(self):
        try:
            while True:
                if not self._strip.callback_queue.empty():
                    self._strip.callback_queue.get(False)()
        except KeyboardInterrupt:
            for handle in self._handles:
                handle.stop_wait()
