class AudioInspectionError(RuntimeError):
    """Raised when an audio file cannot be inspected reliably."""


class FFprobeNotFoundError(AudioInspectionError):
    """Raised when ffprobe is not installed or not available on PATH."""
