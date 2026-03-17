"""Tests for frame extraction: blur detection, interval sampling, and resize."""

from __future__ import annotations

import numpy as np
import pytest

from cranioscan.config import ExtractionConfig
from cranioscan.extraction.frame_extractor import FrameExtractor


def test_laplacian_variance_sharp_vs_blurry(sharp_frame, blurry_frame):
    """Sharp frames should have higher Laplacian variance than blurry ones."""
    sharp_var = FrameExtractor._laplacian_variance(sharp_frame)
    blurry_var = FrameExtractor._laplacian_variance(blurry_frame)
    assert sharp_var > blurry_var
    assert blurry_var < 10.0  # Solid color frame should be near zero


def test_laplacian_variance_positive(sharp_frame):
    """Laplacian variance should always be non-negative."""
    var = FrameExtractor._laplacian_variance(sharp_frame)
    assert var >= 0.0


def test_laplacian_variance_solid_color_is_zero():
    """A completely uniform frame must have exactly zero Laplacian variance."""
    frame = np.full((240, 320, 3), 200, dtype=np.uint8)
    var = FrameExtractor._laplacian_variance(frame)
    assert var == pytest.approx(0.0, abs=1e-6)


def test_resize_reduces_dimensions():
    """Resize should reduce frame to at most max_dim on longest side."""
    frame = np.zeros((1080, 1920, 3), dtype=np.uint8)
    resized = FrameExtractor._resize(frame, max_dim=640)
    h, w = resized.shape[:2]
    assert max(h, w) <= 640


def test_resize_preserves_aspect_ratio():
    """Resize should preserve the original aspect ratio."""
    frame = np.zeros((1080, 1920, 3), dtype=np.uint8)
    resized = FrameExtractor._resize(frame, max_dim=960)
    h, w = resized.shape[:2]
    original_ratio = 1920 / 1080
    resized_ratio = w / h
    assert abs(original_ratio - resized_ratio) < 0.01


def test_resize_no_op_if_already_small():
    """Resize should not enlarge frames already smaller than max_dim."""
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    resized = FrameExtractor._resize(frame, max_dim=1280)
    assert resized.shape == frame.shape


def test_resize_portrait_orientation():
    """Resize should constrain by height when height > width."""
    frame = np.zeros((1920, 1080, 3), dtype=np.uint8)
    resized = FrameExtractor._resize(frame, max_dim=640)
    h, w = resized.shape[:2]
    assert max(h, w) <= 640
    assert h > w  # Portrait preserved


def test_extract_creates_output_files(tmp_path):
    """Extract should write frames to output directory from a real video."""
    import cv2

    # Create a minimal synthetic video
    video_path = tmp_path / "test.mp4"
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(str(video_path), fourcc, 30.0, (320, 240))
    rng = np.random.default_rng(42)
    for _ in range(60):
        frame = rng.integers(0, 256, (240, 320, 3), dtype=np.uint8)
        writer.write(frame)
    writer.release()

    config = ExtractionConfig(frame_interval=10, blur_threshold=50.0)
    extractor = FrameExtractor(config)
    saved = extractor.extract(video_path, tmp_path / "frames")
    assert len(saved) > 0
    for p in saved:
        assert p.exists()


def test_extract_raises_on_missing_video(tmp_path):
    """Extract should raise FileNotFoundError for non-existent video."""
    config = ExtractionConfig()
    extractor = FrameExtractor(config)
    with pytest.raises(FileNotFoundError):
        extractor.extract(tmp_path / "nonexistent.mp4", tmp_path / "frames")


def test_extract_returns_paths_list(tmp_path):
    """Extract should return a list type (even if empty)."""
    import cv2

    video_path = tmp_path / "test.mp4"
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(str(video_path), fourcc, 30.0, (320, 240))
    rng = np.random.default_rng(7)
    for _ in range(30):
        frame = rng.integers(0, 256, (240, 320, 3), dtype=np.uint8)
        writer.write(frame)
    writer.release()

    config = ExtractionConfig(frame_interval=10, blur_threshold=50.0)
    extractor = FrameExtractor(config)
    result = extractor.extract(video_path, tmp_path / "frames2")
    assert isinstance(result, list)
