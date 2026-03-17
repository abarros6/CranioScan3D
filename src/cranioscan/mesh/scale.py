"""Mesh scale correction using a known reference object.

In the pipeline, a physical reference object of known dimensions (e.g., a
3D-printed cube) is placed in the scene during capture. This module detects
that reference object in the reconstructed mesh, computes the scale factor
needed to match the known dimensions, and applies a uniform scaling to the
entire mesh.

TODO (Month 2): Implement reference object detection and scale computation.
The interface is defined here; the implementation will use color segmentation
or geometric matching to locate the reference region.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

import numpy as np
import open3d as o3d

logger = logging.getLogger(__name__)


class ScaleCorrector:
    """Corrects mesh scale using a known reference object.

    The reference object (e.g., a 10×10×10mm calibration cube) must be
    visible in the reconstruction. Its detected size in the model is compared
    to its known physical dimensions to derive a scale factor applied uniformly
    to the mesh.

    Attributes:
        reference_size_mm: Known dimension of the reference object in millimeters.
    """

    def __init__(self, reference_size_mm: float = 10.0) -> None:
        """Initialize ScaleCorrector.

        Args:
            reference_size_mm: Known size of the reference object (mm).
                Defaults to 10.0mm for a 1cm calibration cube.
        """
        self.reference_size_mm = reference_size_mm

    def correct(self, input_path: Path, output_path: Path) -> Optional[float]:
        """Detect reference object and apply scale correction to mesh.

        Args:
            input_path: Path to the input (unscaled) mesh file.
            output_path: Path to write the scale-corrected mesh.

        Returns:
            The computed scale factor (mm/model_unit), or None if detection failed.

        Raises:
            NotImplementedError: Reference object detection is not yet implemented.
            FileNotFoundError: If input_path does not exist.
        """
        raise NotImplementedError(
            "TODO: implement in Month 2 — reference object detection and scale correction. "
            "Steps: (1) segment reference object region by color or geometry, "
            "(2) compute bounding box of reference region, "
            "(3) derive scale = reference_size_mm / detected_size_model_units, "
            "(4) apply uniform scale via mesh.scale(scale_factor, center=(0,0,0))."
        )

    @staticmethod
    def apply_scale(
        mesh: o3d.geometry.TriangleMesh, scale_factor: float
    ) -> o3d.geometry.TriangleMesh:
        """Apply uniform scale factor to an Open3D mesh.

        Args:
            mesh: Input triangle mesh (modified in place and returned).
            scale_factor: Uniform scale factor to apply.

        Returns:
            Scaled mesh (same object, modified in place).
        """
        center = mesh.get_center()
        mesh.scale(scale_factor, center=center)
        logger.info("Applied scale factor %.6f to mesh", scale_factor)
        return mesh

    @staticmethod
    def compute_scale_factor(detected_size: float, known_size_mm: float) -> float:
        """Compute the scale factor from detected and known sizes.

        Args:
            detected_size: Measured size of the reference object in model units.
            known_size_mm: Known physical size of the reference object in mm.

        Returns:
            Scale factor: known_size_mm / detected_size.

        Raises:
            ValueError: If detected_size is zero or negative.
        """
        if detected_size <= 0:
            raise ValueError(f"detected_size must be positive, got {detected_size}")
        factor = known_size_mm / detected_size
        logger.debug(
            "Scale factor: %.6f (known=%.2fmm / detected=%.6f)",
            factor,
            known_size_mm,
            detected_size,
        )
        return factor
