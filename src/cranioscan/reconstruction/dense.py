"""OpenMVS dense reconstruction pipeline.

Converts COLMAP output to OpenMVS format and runs dense multi-view stereo,
mesh reconstruction, and optional mesh refinement — all CPU-only.

OpenMVS pipeline stages:
  1. InterfaceCOLMAP  — Convert COLMAP output to OpenMVS scene
  2. DensifyPointCloud — Dense MVS depth estimation and point cloud fusion
  3. ReconstructMesh  — Poisson/Delaunay mesh from dense point cloud
  4. RefineMesh       — Mesh refinement for improved surface quality (optional)
"""

from __future__ import annotations

import logging
from pathlib import Path

from cranioscan.config import DenseConfig, ReconstructionConfig
from cranioscan.utils.shell import run_command

logger = logging.getLogger(__name__)


class DensePipeline:
    """Runs the OpenMVS dense reconstruction pipeline (CPU-only).

    Wraps the four OpenMVS command-line tools. All binaries are expected
    to be in PATH or in config.reconstruction.openmvs_bin_dir.

    Attributes:
        dense_config: Dense reconstruction parameters.
        recon_config: Reconstruction config (for binary paths).
    """

    def __init__(self, dense_config: DenseConfig, recon_config: ReconstructionConfig) -> None:
        """Initialize DensePipeline.

        Args:
            dense_config: Dense reconstruction configuration.
            recon_config: Reconstruction configuration (for OpenMVS bin dir).
        """
        self.dense_config = dense_config
        self.recon_config = recon_config

    def _bin(self, name: str) -> str:
        """Resolve an OpenMVS binary path.

        Args:
            name: Binary name (e.g., 'InterfaceCOLMAP').

        Returns:
            Full path string or just the name if openmvs_bin_dir is empty.
        """
        bin_dir = self.recon_config.openmvs_bin_dir
        if bin_dir:
            return str(Path(bin_dir) / name)
        return name

    def run(self, undistorted_dir: Path, dense_dir: Path) -> None:
        """Run the full OpenMVS dense pipeline.

        Args:
            undistorted_dir: COLMAP undistorted output directory (from Undistorter).
            dense_dir: Output directory for OpenMVS dense reconstruction results.

        Raises:
            RuntimeError: If any OpenMVS subprocess fails.
        """
        dense_dir.mkdir(parents=True, exist_ok=True)
        scene_mvs = dense_dir / "scene.mvs"

        logger.info("Step 1/4: InterfaceCOLMAP — converting to OpenMVS format")
        self._interface_colmap(undistorted_dir, dense_dir, scene_mvs)

        dense_mvs = dense_dir / "scene_dense.mvs"
        logger.info("Step 2/4: DensifyPointCloud — dense multi-view stereo")
        self._densify_point_cloud(scene_mvs, dense_dir)

        if not dense_mvs.exists():
            # OpenMVS may name output differently; search for it
            candidates = list(dense_dir.glob("*dense*.mvs"))
            if candidates:
                dense_mvs = candidates[0]
            else:
                dense_mvs = scene_mvs  # fallback

        mesh_mvs = dense_dir / "scene_dense_mesh.mvs"
        logger.info("Step 3/4: ReconstructMesh — surface reconstruction")
        self._reconstruct_mesh(dense_mvs, dense_dir)

        if self.dense_config.refine_mesh:
            logger.info("Step 4/4: RefineMesh — mesh refinement")
            self._refine_mesh(mesh_mvs, dense_dir)
        else:
            logger.info("Step 4/4: RefineMesh — skipped (config.dense.refine_mesh=False)")

        logger.info("Dense reconstruction complete: %s", dense_dir)

    def _interface_colmap(
        self, undistorted_dir: Path, dense_dir: Path, output_mvs: Path
    ) -> None:
        """Run InterfaceCOLMAP to convert COLMAP data to OpenMVS format.

        Args:
            undistorted_dir: COLMAP undistorted directory.
            dense_dir: Working directory for OpenMVS.
            output_mvs: Path for the output .mvs scene file.
        """
        cmd = [
            self._bin("InterfaceCOLMAP"),
            "-i", str(undistorted_dir),
            "-o", str(output_mvs),
            "--image-folder", str(undistorted_dir / "images"),
        ]
        run_command(cmd, cwd=dense_dir, description="InterfaceCOLMAP")

    def _densify_point_cloud(self, scene_mvs: Path, dense_dir: Path) -> None:
        """Run DensifyPointCloud for dense MVS.

        Args:
            scene_mvs: Input OpenMVS scene file.
            dense_dir: Working directory.
        """
        cmd = [
            self._bin("DensifyPointCloud"),
            "-i", str(scene_mvs),
            "--resolution-level", str(self.dense_config.densify_resolution_level),
            "--min-resolution", str(self.dense_config.densify_min_resolution),
            "--max-resolution", str(self.dense_config.densify_max_resolution),
        ]
        run_command(cmd, cwd=dense_dir, description="DensifyPointCloud")

    def _reconstruct_mesh(self, dense_mvs: Path, dense_dir: Path) -> None:
        """Run ReconstructMesh.

        Args:
            dense_mvs: Dense point cloud MVS file.
            dense_dir: Working directory.
        """
        cmd = [
            self._bin("ReconstructMesh"),
            "-i", str(dense_mvs),
        ]
        run_command(cmd, cwd=dense_dir, description="ReconstructMesh")

    def _refine_mesh(self, mesh_mvs: Path, dense_dir: Path) -> None:
        """Run RefineMesh for improved surface quality.

        Args:
            mesh_mvs: Reconstructed mesh MVS file.
            dense_dir: Working directory.
        """
        if not mesh_mvs.exists():
            candidates = list(dense_dir.glob("*mesh*.mvs"))
            if candidates:
                mesh_mvs = candidates[0]
            else:
                logger.warning("No mesh MVS file found for RefineMesh — skipping")
                return
        cmd = [
            self._bin("RefineMesh"),
            "-i", str(mesh_mvs),
        ]
        run_command(cmd, cwd=dense_dir, description="RefineMesh")
