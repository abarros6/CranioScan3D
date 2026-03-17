"""COLMAP image undistortion for OpenMVS compatibility.

Undistorts images using COLMAP's recovered camera model, producing
rectilinear images and an MVS-compatible sparse model for OpenMVS input.
"""

from __future__ import annotations

import logging
from pathlib import Path

from cranioscan.config import ReconstructionConfig
from cranioscan.utils.shell import run_command

logger = logging.getLogger(__name__)


class Undistorter:
    """Runs COLMAP image_undistorter to prepare data for OpenMVS.

    The undistorted output directory contains:
      - images/      Undistorted, rectilinear images
      - sparse/      Sparse model in COLMAP TXT format (cameras, images, points3D)
      - stereo/      Depth map placeholder directories

    Attributes:
        config: Reconstruction configuration.
    """

    def __init__(self, config: ReconstructionConfig) -> None:
        """Initialize Undistorter.

        Args:
            config: Reconstruction configuration parameters.
        """
        self.config = config

    def run(self, image_dir: Path, sparse_dir: Path, undistorted_dir: Path) -> None:
        """Run COLMAP image undistortion.

        Selects the best (largest) sparse sub-model from the mapper output
        (COLMAP writes numbered subdirectories 0, 1, 2, ...) and undistorts
        all images using that model's camera parameters.

        Args:
            image_dir: Original image directory (as passed to COLMAP mapper).
            sparse_dir: COLMAP sparse output directory (contains model/0, model/1, ...).
            undistorted_dir: Output directory for undistorted images and model.

        Raises:
            FileNotFoundError: If no sparse model sub-directory is found.
            RuntimeError: If the COLMAP subprocess fails.
        """
        model_dir = sparse_dir / "model"
        sub_model = self._find_best_submodel(model_dir)
        undistorted_dir.mkdir(parents=True, exist_ok=True)

        colmap = self.config.colmap_bin
        cmd = [
            colmap, "image_undistorter",
            "--image_path", str(image_dir),
            "--input_path", str(sub_model),
            "--output_path", str(undistorted_dir),
            "--output_type", "COLMAP",
        ]
        run_command(cmd, description="COLMAP image undistortion")
        logger.info("Undistorted images written to %s", undistorted_dir)

    @staticmethod
    def _find_best_submodel(model_dir: Path) -> Path:
        """Find the sub-model directory with the most reconstructed images.

        COLMAP's mapper may produce multiple disconnected components (0, 1, 2, ...).
        We pick the one with the most images.txt lines as a proxy for quality.

        Args:
            model_dir: Directory containing numbered sub-model directories.

        Returns:
            Path to the best sub-model directory.

        Raises:
            FileNotFoundError: If no valid sub-model is found.
        """
        sub_dirs = sorted(model_dir.iterdir()) if model_dir.exists() else []
        candidates = [d for d in sub_dirs if d.is_dir() and (d / "images.txt").exists()]
        if not candidates:
            raise FileNotFoundError(
                f"No valid COLMAP sparse model found in {model_dir}. "
                "Check that COLMAP mapper ran successfully."
            )

        def image_count(d: Path) -> int:
            lines = (d / "images.txt").read_text().splitlines()
            # images.txt has 2 lines per image (header lines start with #)
            data_lines = [ln for ln in lines if ln and not ln.startswith("#")]
            return len(data_lines) // 2

        best = max(candidates, key=image_count)
        n = image_count(best)
        logger.info("Using sparse sub-model %s (%d images)", best.name, n)
        return best
