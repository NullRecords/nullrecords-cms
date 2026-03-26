"""Audio processing utilities — slicing, loading, format info.

Uses pydub for audio manipulation. All operations are local-only.
"""

import logging
from pathlib import Path

from pydub import AudioSegment

log = logging.getLogger(__name__)


def load_audio(path: str | Path) -> AudioSegment:
    """Load an audio file into a pydub AudioSegment."""
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Audio file not found: {p}")
    log.info("Loading audio: %s", p.name)
    return AudioSegment.from_file(str(p))


def extract_clip(
    audio_path: str | Path,
    start_ms: int,
    duration_ms: int,
    output_path: str | Path,
) -> Path:
    """Extract a segment from an audio file and export as WAV.

    Args:
        audio_path: Source audio file.
        start_ms: Start offset in milliseconds.
        duration_ms: Duration of the clip in milliseconds.
        output_path: Where to write the extracted clip.

    Returns:
        Path to the exported audio clip.
    """
    audio = load_audio(audio_path)
    end_ms = start_ms + duration_ms

    # Clamp to audio bounds
    if start_ms >= len(audio):
        raise ValueError(
            f"start_ms ({start_ms}) exceeds audio length ({len(audio)} ms)"
        )
    end_ms = min(end_ms, len(audio))

    clip = audio[start_ms:end_ms]
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    # Export as WAV for MoviePy compatibility — re-encode to AAC in final render
    clip.export(str(out), format="wav")
    log.info(
        "Extracted audio clip: %s  (%d ms → %d ms, %d ms)",
        out.name,
        start_ms,
        end_ms,
        len(clip),
    )
    return out


def get_duration_ms(path: str | Path) -> int:
    """Return the duration of an audio file in milliseconds."""
    return len(load_audio(path))
