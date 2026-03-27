"""Audio analysis — beat detection, spectrum analysis, and level extraction.

Produces frame-level data that drives visualizers and beat-synced effects.
Uses librosa-style analysis with numpy/scipy fallback.
"""

import logging
import struct
import wave
from pathlib import Path

import numpy as np

log = logging.getLogger(__name__)


def analyze_audio(audio_path: Path, fps: int = 24) -> dict:
    """Analyze an audio file and return per-frame data for visualization.

    Returns a dict with:
        - beats: list of beat timestamps in seconds
        - bpm: estimated BPM
        - levels: per-frame RMS level (0.0–1.0), length = total_frames
        - spectrum: per-frame frequency band energies (shape: frames x n_bands)
        - duration: total duration in seconds
        - sample_rate: audio sample rate
    """
    audio_path = Path(audio_path)
    if not audio_path.exists():
        raise FileNotFoundError(f"Audio not found: {audio_path}")

    # Load audio as mono float array
    samples, sr = _load_audio(audio_path)
    duration = len(samples) / sr

    hop = sr // fps  # samples per frame
    n_frames = int(np.ceil(len(samples) / hop))

    # Per-frame RMS levels
    levels = _compute_rms(samples, hop, n_frames)

    # Per-frame spectrum (8 frequency bands)
    spectrum = _compute_spectrum(samples, sr, hop, n_frames, n_bands=8)

    # Beat detection
    beats, bpm = _detect_beats(samples, sr, hop, levels)

    log.info(
        "Audio analysis: %.1fs, %d BPM, %d beats, %d frames @ %dfps",
        duration, bpm, len(beats), n_frames, fps,
    )

    return {
        "beats": [round(b, 3) for b in beats],
        "bpm": round(bpm, 1),
        "levels": levels.tolist(),
        "spectrum": spectrum.tolist(),
        "duration": round(duration, 3),
        "sample_rate": sr,
        "fps": fps,
        "n_frames": n_frames,
    }


def _load_audio(path: Path) -> tuple[np.ndarray, int]:
    """Load audio file as mono float32 numpy array.

    Supports WAV natively, falls back to pydub for other formats.
    """
    ext = path.suffix.lower()
    if ext == ".wav":
        return _load_wav(path)

    # Use pydub for mp3, flac, ogg, etc.
    from pydub import AudioSegment
    seg = AudioSegment.from_file(str(path))
    seg = seg.set_channels(1)
    sr = seg.frame_rate
    samples = np.array(seg.get_array_of_samples(), dtype=np.float32)
    # Normalize to -1.0 to 1.0
    peak = max(abs(samples.max()), abs(samples.min()), 1.0)
    samples = samples / peak
    return samples, sr


def _load_wav(path: Path) -> tuple[np.ndarray, int]:
    """Load WAV file as mono float32."""
    with wave.open(str(path), "rb") as wf:
        sr = wf.getframerate()
        n_channels = wf.getnchannels()
        sampwidth = wf.getsampwidth()
        n_frames = wf.getnframes()
        raw = wf.readframes(n_frames)

    if sampwidth == 2:
        fmt = f"<{n_frames * n_channels}h"
        samples = np.array(struct.unpack(fmt, raw), dtype=np.float32) / 32768.0
    elif sampwidth == 4:
        fmt = f"<{n_frames * n_channels}i"
        samples = np.array(struct.unpack(fmt, raw), dtype=np.float32) / 2147483648.0
    else:
        samples = np.frombuffer(raw, dtype=np.uint8).astype(np.float32) / 128.0 - 1.0

    # Mix to mono
    if n_channels > 1:
        samples = samples.reshape(-1, n_channels).mean(axis=1)

    return samples, sr


def _compute_rms(samples: np.ndarray, hop: int, n_frames: int) -> np.ndarray:
    """Compute per-frame RMS levels, normalized to 0.0–1.0."""
    levels = np.zeros(n_frames, dtype=np.float32)
    for i in range(n_frames):
        start = i * hop
        end = min(start + hop, len(samples))
        if start >= len(samples):
            break
        chunk = samples[start:end]
        levels[i] = np.sqrt(np.mean(chunk ** 2))

    # Normalize
    peak = levels.max()
    if peak > 0:
        levels = levels / peak
    return levels


def _compute_spectrum(
    samples: np.ndarray,
    sr: int,
    hop: int,
    n_frames: int,
    n_bands: int = 8,
) -> np.ndarray:
    """Compute per-frame frequency band energies using FFT.

    Bands are logarithmically spaced from ~60Hz to ~16kHz.
    Returns shape (n_frames, n_bands), values 0.0–1.0.
    """
    fft_size = 2048
    spectrum = np.zeros((n_frames, n_bands), dtype=np.float32)

    # Logarithmic band edges (Hz)
    min_freq, max_freq = 60.0, min(16000.0, sr / 2)
    band_edges = np.logspace(
        np.log10(min_freq), np.log10(max_freq), n_bands + 1,
    )
    # Convert to FFT bin indices
    bin_edges = (band_edges * fft_size / sr).astype(int)
    bin_edges = np.clip(bin_edges, 0, fft_size // 2)

    window = np.hanning(fft_size)

    for i in range(n_frames):
        start = i * hop
        end = start + fft_size
        if end > len(samples):
            chunk = np.zeros(fft_size, dtype=np.float32)
            valid = min(len(samples) - start, fft_size)
            if valid > 0:
                chunk[:valid] = samples[start:start + valid]
        else:
            chunk = samples[start:end]

        windowed = chunk * window
        fft_mag = np.abs(np.fft.rfft(windowed))

        for b in range(n_bands):
            lo = bin_edges[b]
            hi = max(bin_edges[b + 1], lo + 1)
            spectrum[i, b] = np.mean(fft_mag[lo:hi])

    # Normalize per band
    for b in range(n_bands):
        peak = spectrum[:, b].max()
        if peak > 0:
            spectrum[:, b] /= peak

    return spectrum


def _detect_beats(
    samples: np.ndarray, sr: int, hop: int, levels: np.ndarray,
) -> tuple[list[float], float]:
    """Simple onset-based beat detection.

    Uses spectral flux (difference in energy between frames) to find onsets,
    then estimates BPM from inter-beat intervals.
    """
    # Compute spectral flux
    fft_size = 1024
    n_frames = len(levels)
    flux = np.zeros(n_frames, dtype=np.float32)
    prev_mag = np.zeros(fft_size // 2 + 1, dtype=np.float32)

    for i in range(n_frames):
        start = i * hop
        end = start + fft_size
        if end > len(samples):
            chunk = np.zeros(fft_size, dtype=np.float32)
            valid = min(len(samples) - start, fft_size)
            if valid > 0:
                chunk[:valid] = samples[start:start + valid]
        else:
            chunk = samples[start:end]

        mag = np.abs(np.fft.rfft(chunk))
        diff = mag - prev_mag
        flux[i] = np.sum(np.maximum(diff, 0))
        prev_mag = mag

    # Smooth and threshold
    kernel_size = 5
    if len(flux) > kernel_size:
        kernel = np.ones(kernel_size) / kernel_size
        smoothed = np.convolve(flux, kernel, mode="same")
    else:
        smoothed = flux

    threshold = np.mean(smoothed) + 1.2 * np.std(smoothed)

    # Find peaks above threshold with minimum spacing
    min_spacing = int(0.25 * sr / hop)  # at least 0.25s between beats
    beats = []
    last_beat = -min_spacing
    for i in range(1, len(smoothed) - 1):
        if (
            smoothed[i] > threshold
            and smoothed[i] > smoothed[i - 1]
            and smoothed[i] > smoothed[i + 1]
            and (i - last_beat) >= min_spacing
        ):
            beats.append(i * hop / sr)
            last_beat = i

    # Estimate BPM from inter-beat intervals
    if len(beats) > 2:
        intervals = np.diff(beats)
        median_interval = np.median(intervals)
        bpm = 60.0 / median_interval if median_interval > 0 else 120.0
        # Clamp to sane range
        if bpm < 40:
            bpm *= 2
        elif bpm > 220:
            bpm /= 2
    else:
        bpm = 120.0

    return beats, bpm
