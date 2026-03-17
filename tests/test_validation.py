"""Tests for input validation and dependency checks."""

from __future__ import annotations

import shutil
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pytest

from cranioscan.config import Config
from cranioscan.utils.validation import (
    SUPPORTED_VIDEO_EXTENSIONS,
    _check_binary,
    validate_input_video,
)


def test_validate_input_video_missing_file(tmp_path):
    """validate_input_video should raise FileNotFoundError for non-existent file."""
    with pytest.raises(FileNotFoundError):
        validate_input_video(tmp_path / "nonexistent.mp4")


def test_validate_input_video_wrong_extension(tmp_path):
    """validate_input_video should raise ValueError for unsupported extension."""
    bad_file = tmp_path / "video.avi"
    bad_file.touch()
    with pytest.raises(ValueError, match="Unsupported video format"):
        validate_input_video(bad_file)


def test_validate_input_video_txt_extension(tmp_path):
    """validate_input_video should raise ValueError for .txt extension."""
    bad_file = tmp_path / "video.txt"
    bad_file.touch()
    with pytest.raises(ValueError, match="Unsupported video format"):
        validate_input_video(bad_file)


def test_validate_input_video_supported_extensions():
    """All listed extensions should be in the supported set."""
    for ext in [".mp4", ".mov", ".MOV", ".MP4"]:
        assert ext in SUPPORTED_VIDEO_EXTENSIONS


def test_check_binary_nonexistent():
    """_check_binary should return False for a binary that does not exist."""
    assert _check_binary("__nonexistent_binary_xyz__") is False


def test_check_binary_python():
    """_check_binary should return True for 'python3' which is available."""
    if shutil.which("python3"):
        assert _check_binary("python3") is True


def test_check_binary_absolute_path_nonexistent(tmp_path):
    """_check_binary with a full path should return False if file doesn't exist."""
    assert _check_binary(str(tmp_path / "no_such_binary")) is False


def test_check_binary_absolute_path_exists(tmp_path):
    """_check_binary with a full path should return True if file exists."""
    fake_bin = tmp_path / "mybin"
    fake_bin.write_text("#!/bin/sh\necho ok\n")
    assert _check_binary(str(fake_bin)) is True


def test_validate_input_video_valid_mp4(tmp_path):
    """validate_input_video should pass for a valid .mp4 with sufficient frames."""
    import cv2

    video_path = tmp_path / "valid.mp4"
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(str(video_path), fourcc, 30.0, (320, 240))
    rng = np.random.default_rng(0)
    for _ in range(60):
        writer.write(rng.integers(0, 256, (240, 320, 3), dtype=np.uint8))
    writer.release()
    # Should not raise
    validate_input_video(video_path)


def test_validate_input_video_too_few_frames(tmp_path):
    """validate_input_video should raise ValueError for a video with too few frames."""
    import cv2

    video_path = tmp_path / "short.mp4"
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(str(video_path), fourcc, 30.0, (320, 240))
    rng = np.random.default_rng(1)
    for _ in range(10):  # Way below MIN_FRAME_COUNT=30
        writer.write(rng.integers(0, 256, (240, 320, 3), dtype=np.uint8))
    writer.release()

    with pytest.raises(ValueError, match="frames"):
        validate_input_video(video_path)
