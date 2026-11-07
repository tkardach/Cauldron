import importlib.resources

from pydub import AudioSegment

from cauldron.assets.audio import AUDIO_FILES


class AssetManager:
    """Resolves project audio resources and applies audio format adjustments."""

    def __init__(self, package: str = "cauldron.assets.audio"):
        self._package = package

    def get_path(self, filename: str) -> str:
        """Return the installed path for a known audio resource."""
        if filename not in AUDIO_FILES:
            raise ValueError(f"Audio file '{filename}' not found in assets.")
        resource = importlib.resources.files(self._package).joinpath(filename)
        return str(resource)

    def load_audio(
        self,
        filename: str,
        *,
        sample_width: int | None = None,
        frame_rate: int | None = None,
        frame_rate_scale: float = 1.0,
        playback_rate_scale: float = 1.0,
        gain_db: float = 0.0,
    ) -> AudioSegment:
        """Load an audio asset and apply optional format, speed, and gain changes.

        ``frame_rate_scale`` resamples the audio; ``playback_rate_scale`` changes
        playback speed by adjusting the segment's frame-rate metadata.
        """
        if frame_rate_scale <= 0:
            raise ValueError("frame_rate_scale must be greater than zero")
        if playback_rate_scale <= 0:
            raise ValueError("playback_rate_scale must be greater than zero")
        if filename not in AUDIO_FILES:
            raise ValueError(f"Audio file '{filename}' not found in assets.")
        resource = importlib.resources.files(self._package).joinpath(filename)
        with importlib.resources.as_file(resource) as path:
            segment = AudioSegment.from_file(path)
        if sample_width is not None:
            segment = segment.set_sample_width(sample_width)
        if frame_rate is not None:
            segment = segment.set_frame_rate(frame_rate)
        elif frame_rate_scale != 1.0:
            segment = segment.set_frame_rate(
                max(1, int(segment.frame_rate * frame_rate_scale))
            )
        if playback_rate_scale != 1.0:
            segment.frame_rate = max(
                1, int(segment.frame_rate * playback_rate_scale)
            )
        if gain_db:
            segment += gain_db
        return segment
