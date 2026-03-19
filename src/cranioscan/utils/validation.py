"""Input validation and dependency availability checks.

Called at pipeline startup to fail fast with helpful error messages if
prerequisites are missing or inputs are invalid.
"""

from __future__ import annotations

import logging
import shutil
from pathlib import Path

from cranioscan.config import Config

logger = logging.getLogger(__name__)

SUPPORTED_VIDEO_EXTENSIONS = {".mp4", ".mov", ".MOV", ".MP4", ".m4v"}
MIN_FRAME_COUNT = 30  # Absolute minimum for a viable reconstruction


def validate_input_video(path: Path) -> None:
    """Validate that the input video exists and has a supported format.

    Args:
        path: Path to the input video file.

    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError: If the file extension is not supported or the video
            has too few frames for reconstruction.
    """
    if not path.exists():
        raise FileNotFoundError(f"Input video not found: {path}")

    if path.suffix not in SUPPORTED_VIDEO_EXTENSIONS:
        raise ValueError(
            f"Unsupported video format '{path.suffix}'. "
            f"Supported: {sorted(SUPPORTED_VIDEO_EXTENSIONS)}"
        )

    # Quick frame count check via OpenCV
    import cv2

    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        raise ValueError(f"Cannot open video (may be corrupt): {path}")
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    cap.release()
    if frame_count < MIN_FRAME_COUNT:
        raise ValueError(
            f"Video has only {frame_count} frames (minimum {MIN_FRAME_COUNT}). "
            "Record a longer video orbiting the subject."
        )
    logger.info("Input video OK: %s (%d frames)", path.name, frame_count)


def validate_dependencies(config: Config) -> None:
    """Check that all required external binaries are available.

    Checks COLMAP and OpenMVS binaries. Logs warnings for optional tools.

    Args:
        config: Pipeline configuration (for binary paths).

    Raises:
        RuntimeError: If a required binary is not found.
    """
    errors: list[str] = []

    # Check COLMAP
    colmap_bin = config.reconstruction.colmap_bin
    if not _check_binary(colmap_bin):
        errors.append(
            f"COLMAP binary not found: '{colmap_bin}'. "
            "Install with: brew install colmap"
        )

    # Check OpenMVS binaries
    openmvs_bins = ["InterfaceCOLMAP", "DensifyPointCloud", "ReconstructMesh", "RefineMesh"]
    bin_dir = config.reconstruction.openmvs_bin_dir
    for binary in openmvs_bins:
        full_name = f"{bin_dir}/{binary}" if bin_dir else binary
        if not _check_binary(full_name):
            errors.append(
                f"OpenMVS binary not found: '{full_name}'. "
                "Build from source — see scripts/setup_mac.sh"
            )

    if errors:
        msg = "Missing required dependencies:\n" + "\n".join(f"  - {e}" for e in errors)
        raise RuntimeError(msg)

    logger.info("All required dependencies found")


def _check_binary(name: str) -> bool:
    """Check if a binary is executable.

    Args:
        name: Binary name or full path.

    Returns:
        True if the binary is found and executable.
    """
    if "/" in name or "\\" in name:
        return Path(name).is_file()
    found = shutil.which(name) is not None
    if found:
        logger.debug("Found binary: %s", name)
    else:
        logger.debug("Binary not found: %s", name)
    return found
