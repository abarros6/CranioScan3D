"""COLMAP sparse Structure-from-Motion pipeline.

Runs COLMAP feature extraction, exhaustive matching, and incremental mapper
with all GPU flags disabled for CPU-only operation on Apple Silicon.

COLMAP stages:
  1. feature_extractor — SIFT feature extraction (CPU)
  2. exhaustive_matcher — Exhaustive feature matching (CPU)
  3. mapper — Incremental SfM reconstruction
"""

from __future__ import annotations

import logging
from pathlib import Path

from cranioscan.config import ReconstructionConfig
from cranioscan.utils.shell import run_command

logger = logging.getLogger(__name__)


class SparsePipeline:
    """Runs the COLMAP sparse SfM pipeline (CPU-only).

    All GPU-related COLMAP flags are set to 0. Uses SIMPLE_RADIAL camera
    model with single_camera=1, appropriate for iPhone video where all frames
    share the same camera intrinsics.

    Attributes:
        config: Reconstruction configuration.
    """

    def __init__(self, config: ReconstructionConfig) -> None:
        """Initialize SparsePipeline.

        Args:
            config: Reconstruction configuration parameters.
        """
        self.config = config

    def run(self, image_dir: Path, sparse_dir: Path) -> None:
        """Run the full COLMAP sparse pipeline.

        Creates a COLMAP database, extracts SIFT features, matches them
        exhaustively, and runs the incremental mapper to produce a sparse
        point cloud and camera poses.

        Args:
            image_dir: Directory containing extracted frame images.
            sparse_dir: Output directory for COLMAP database and sparse model.

        Raises:
            RuntimeError: If any COLMAP subprocess fails.
            FileNotFoundError: If the image directory does not exist.
        """
        if not image_dir.exists():
            raise FileNotFoundError(f"Image directory not found: {image_dir}")

        sparse_dir.mkdir(parents=True, exist_ok=True)
        database_path = sparse_dir / "database.db"
        model_dir = sparse_dir / "model"
        model_dir.mkdir(exist_ok=True)

        colmap = self.config.colmap_bin

        logger.info("Step 1/3: COLMAP feature extraction")
        self._feature_extractor(colmap, database_path, image_dir)

        logger.info("Step 2/3: COLMAP exhaustive matching")
        self._exhaustive_matcher(colmap, database_path)

        logger.info("Step 3/3: COLMAP incremental mapper")
        self._mapper(colmap, database_path, image_dir, model_dir)

        logger.info("Sparse reconstruction complete: %s", model_dir)

    def _feature_extractor(
        self, colmap: str, database_path: Path, image_dir: Path
    ) -> None:
        """Run COLMAP feature_extractor.

        Args:
            colmap: Path or name of the COLMAP binary.
            database_path: Path to the COLMAP SQLite database.
            image_dir: Directory of input images.
        """
        cmd = [
            colmap, "feature_extractor",
            "--database_path", str(database_path),
            "--image_path", str(image_dir),
            "--ImageReader.camera_model", self.config.camera_model,
            "--ImageReader.single_camera", "1" if self.config.single_camera else "0",
            "--FeatureExtraction.use_gpu", "0",             # COLMAP 4.x namespace (verified)
            "--SiftExtraction.max_num_features", "16384",   # default 8192 — more features from 4K frames
            "--SiftExtraction.num_octaves", "4",
            "--SiftExtraction.peak_threshold", "0.004",     # default 0.02 — lower = more keypoints
        ]
        run_command(cmd, description="COLMAP feature extraction")

    def _exhaustive_matcher(self, colmap: str, database_path: Path) -> None:
        """Run COLMAP exhaustive_matcher.

        Args:
            colmap: Path or name of the COLMAP binary.
            database_path: Path to the COLMAP SQLite database.
        """
        cmd = [
            colmap, "exhaustive_matcher",
            "--database_path", str(database_path),
            "--FeatureMatching.use_gpu", "0",               # COLMAP 4.x namespace (verified)
            "--SiftMatching.max_ratio", "0.8",
            "--SiftMatching.cross_check", "1",
            "--SiftMatching.max_num_matches", "32768",
        ]
        run_command(cmd, description="COLMAP exhaustive matching")

    def _mapper(
        self,
        colmap: str,
        database_path: Path,
        image_dir: Path,
        model_dir: Path,
    ) -> None:
        """Run COLMAP incremental mapper.

        Args:
            colmap: Path or name of the COLMAP binary.
            database_path: Path to the COLMAP SQLite database.
            image_dir: Directory of input images.
            model_dir: Directory to write the sparse model.
        """
        cmd = [
            colmap, "mapper",
            "--database_path", str(database_path),
            "--image_path", str(image_dir),
            "--output_path", str(model_dir),
            "--Mapper.ba_refine_focal_length", "1",
            "--Mapper.ba_refine_extra_params", "1",         # refine distortion coefficients during BA
            "--Mapper.ba_global_max_num_iterations", "75",  # default 50 — more BA iterations
        ]
        run_command(cmd, description="COLMAP incremental mapper")
