"""Mesh curvature analysis for anatomical landmark suggestion.

Computes principal curvatures and shape index on the mesh surface to identify
candidate regions for craniometric landmarks. High-curvature extrema often
correspond to clinically relevant anatomical features.

TODO (Month 3): Implement principal curvature computation using Open3D or
trimesh. The shape index maps the two principal curvatures to a scalar field
useful for classifying surface geometry (dome, ridge, saddle, etc.).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

import numpy as np
import open3d as o3d

logger = logging.getLogger(__name__)


@dataclass
class CurvatureResult:
    """Results of mesh curvature analysis.

    Attributes:
        k1: Principal curvature 1 (max) per vertex. Shape: (N,).
        k2: Principal curvature 2 (min) per vertex. Shape: (N,).
        shape_index: Shape index per vertex in [-1, 1]. Shape: (N,).
        candidate_indices: Vertex indices of candidate landmark locations.
    """

    k1: np.ndarray
    k2: np.ndarray
    shape_index: np.ndarray
    candidate_indices: np.ndarray


class CurvatureAnalyzer:
    """Computes principal curvatures and identifies landmark candidates.

    Shape index SI = (2/pi) * arctan((k1 + k2) / (k1 - k2)) maps the
    two principal curvatures to [-1, 1]:
      -1 = spherical cup (concave)
       0 = saddle
      +1 = spherical cap (convex dome)

    Anatomical landmarks on the cranium tend to occur at:
      - Convex extrema (glabella, opisthocranion): SI close to +1, local max of mean curvature
      - Bilateral maxima (eurion L/R): SI > 0.5, lateral position

    Attributes:
        dome_threshold: Minimum shape index to consider a vertex as dome-like.
        candidate_count: Maximum number of candidate vertices to return.
    """

    def __init__(self, dome_threshold: float = 0.6, candidate_count: int = 50) -> None:
        """Initialize CurvatureAnalyzer.

        Args:
            dome_threshold: Shape index threshold for dome detection (convex extrema).
            candidate_count: Max candidate vertices per landmark class.
        """
        self.dome_threshold = dome_threshold
        self.candidate_count = candidate_count

    def analyze(self, mesh: o3d.geometry.TriangleMesh) -> CurvatureResult:
        """Compute curvature analysis on a triangle mesh.

        Args:
            mesh: Input triangle mesh. Vertex normals should be computed.

        Returns:
            CurvatureResult with per-vertex curvature fields and candidates.

        Raises:
            NotImplementedError: Not yet implemented (Month 3).
        """
        raise NotImplementedError(
            "TODO: implement in Month 3 — principal curvature computation. "
            "Approach: for each vertex, gather 1-ring neighbours from mesh.triangles; "
            "centre their positions, build 3×3 covariance matrix, eigen-decompose; "
            "k1=largest eigenvalue, k2=second eigenvalue (both in mm⁻¹). "
            "Then call self.shape_index(k1, k2) and threshold at self.dome_threshold "
            "to find candidate_indices (top self.candidate_count by shape_index score). "
            "No new dependencies — Open3D mesh gives vertices + triangles directly."
        )

    @staticmethod
    def shape_index(k1: np.ndarray, k2: np.ndarray) -> np.ndarray:
        """Compute Koenderink's shape index from principal curvatures.

        SI = (2/pi) * arctan((k1 + k2) / (k1 - k2))

        Regions where k1 == k2 (umbilic points) are assigned SI = 0.

        Args:
            k1: Max principal curvature per vertex. Shape: (N,).
            k2: Min principal curvature per vertex. Shape: (N,).

        Returns:
            Shape index per vertex in [-1, 1]. Shape: (N,).
        """
        denom = k1 - k2
        # Avoid division by zero at umbilic points
        si = np.where(
            np.abs(denom) > 1e-10,
            (2.0 / np.pi) * np.arctan((k1 + k2) / denom),
            0.0,
        )
        return si
