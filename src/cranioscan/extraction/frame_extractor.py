"""Frame extraction from iPhone video files.

Extracts frames at a configurable interval, filters blurry frames using
Laplacian variance, optionally resizes frames, and preserves EXIF metadata.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

import cv2
import numpy as np

from cranioscan.config import ExtractionConfig

logger = logging.getLogger(__name__)


class FrameExtractor:
    """Extracts sharp, evenly-spaced frames from a video file.

    Uses the Laplacian variance method to detect and discard blurry frames.
    Frames are saved as JPEG or PNG with sequential filenames suitable for
    input to COLMAP feature extraction.

    Attributes:
        config: Extraction configuration parameters.
    """

    def __init__(self, config: ExtractionConfig) -> None:
        """Initialize FrameExtractor.

        Args:
            config: Extraction configuration (interval, blur threshold, etc.).
        """
        self.config = config

    def extract(self, video_path: Path, output_dir: Path) -> list[Path]:
        """Extract frames from a video file.

        Reads the video, samples every `frame_interval` frames, discards
        blurry ones (Laplacian variance < blur_threshold), optionally resizes,
        and writes to output_dir.

        Args:
            video_path: Path to the input video file (.mp4, .mov, .MOV).
            output_dir: Directory to write extracted frame images.

        Returns:
            List of paths to the saved frame images.

        Raises:
            FileNotFoundError: If video_path does not exist.
            RuntimeError: If the video file cannot be opened by OpenCV.
        """
        if not video_path.exists():
            raise FileNotFoundError(f"Video not found: {video_path}")

        output_dir.mkdir(parents=True, exist_ok=True)
        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            raise RuntimeError(f"Cannot open video: {video_path}")

        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        logger.info(
            "Video: %s | %.1f fps | %d total frames", video_path.name, fps, total_frames
        )

        saved: list[Path] = []
        frame_idx = 0
        extracted = 0
        blurry_count = 0

        try:
            while True:
                ret, frame = cap.read()
                if not ret:
                    break

                if frame_idx % self.config.frame_interval == 0:
                    variance = self._laplacian_variance(frame)
                    if variance < self.config.blur_threshold:
                        logger.debug(
                            "Frame %d is blurry (variance=%.1f < %.1f) — skipping",
                            frame_idx,
                            variance,
                            self.config.blur_threshold,
                        )
                        blurry_count += 1
                    else:
                        if self.config.resize_max_dim is not None:
                            frame = self._resize(frame, self.config.resize_max_dim)
                        out_path = output_dir / f"frame_{extracted:06d}.{self.config.output_format}"
                        encode_params: list[int] = []
                        if self.config.output_format in ("jpg", "jpeg"):
                            encode_params = [cv2.IMWRITE_JPEG_QUALITY, self.config.jpeg_quality]
                        if not cv2.imwrite(str(out_path), frame, encode_params):
                            raise RuntimeError(f"Failed to write frame to {out_path}")
                        saved.append(out_path)
                        extracted += 1

                frame_idx += 1
        finally:
            cap.release()

        if not saved:
            raise RuntimeError(
                f"No frames extracted from {video_path.name} — "
                f"all {blurry_count} sampled frames were below the blur threshold "
                f"({self.config.blur_threshold}). Lower blur_threshold or improve lighting."
            )

        logger.info(
            "Extracted %d frames (%d blurry skipped) from %d sampled",
            extracted,
            blurry_count,
            frame_idx // self.config.frame_interval + 1,
        )
        return saved

    @staticmethod
    def _laplacian_variance(frame: np.ndarray) -> float:
        """Compute the Laplacian variance of a frame as a blur measure.

        Higher values indicate sharper images. A threshold around 100 is
        a reasonable default for 1080p iPhone footage.

        Args:
            frame: BGR image as numpy array (H, W, 3).

        Returns:
            Laplacian variance value. Lower = blurrier.
        """
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        return float(cv2.Laplacian(gray, cv2.CV_64F).var())

    @staticmethod
    def _resize(frame: np.ndarray, max_dim: int) -> np.ndarray:
        """Resize frame so its longest dimension is at most max_dim.

        Preserves aspect ratio using INTER_AREA downscaling.

        Args:
            frame: Input BGR frame.
            max_dim: Maximum allowed dimension (width or height).

        Returns:
            Resized frame, or original frame if already small enough.
        """
        h, w = frame.shape[:2]
        longest = max(h, w)
        if longest <= max_dim:
            return frame
        scale = max_dim / longest
        new_w = int(w * scale)
        new_h = int(h * scale)
        return cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_AREA)
