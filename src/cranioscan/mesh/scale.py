"""Mesh scale correction using a known reference object.

A physical reference object of known dimensions (e.g. a standard 16mm die) is
placed in the scene during capture. This module:

  1. Loads the colored dense point cloud produced by DensifyPointCloud.
  2. Segments points matching the reference object's color (HSV thresholding).
  3. Clusters the segmented points with Open3D DBSCAN.
  4. Selects the smallest compact cluster as the calibration reference.
  5. Measures its bounding box longest dimension.
  6. Derives scale_factor = reference_size_mm / detected_size.
  7. Applies a uniform scale to the cleaned mesh and saves the result.

On detection failure, the unscaled mesh is copied to the output path and
None is returned (graceful degradation — downstream stages continue in
model units).
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

import cv2
import numpy as np
import open3d as o3d

from cranioscan.config import ScaleConfig

logger = logging.getLogger(__name__)

# HSV color presets for common reference object colors.
# hue_center and hue_width are in OpenCV degrees (0–180).
# For "white", hue is irrelevant; filtering is done on S and V only.
_HSV_PRESETS: dict[str, dict[str, float]] = {
    "white":  {"hue_center":   0.0, "hue_width": 180.0, "sat_max": 0.25, "val_min": 0.75},
    "red":    {"hue_center":   0.0, "hue_width":  12.0, "sat_max":  1.0, "val_min": 0.35},
    "yellow": {"hue_center":  30.0, "hue_width":  15.0, "sat_max":  1.0, "val_min": 0.50},
    "blue":   {"hue_center": 105.0, "hue_width":  20.0, "sat_max":  1.0, "val_min": 0.20},
}


class ScaleCorrector:
    """Corrects mesh scale using a known reference object in the scene.

    The reference object must be visible in the dense reconstruction and have a
    distinctive color (white, red, yellow, or blue). Its color is used to
    segment it from the dense point cloud; its bounding box size determines the
    scale factor applied to the cleaned mesh.

    Attributes:
        config: Scale correction configuration.
        reference_size_mm: Known physical size of the reference object (mm).
    """

    def __init__(self, config: Optional[ScaleConfig] = None) -> None:
        """Initialize ScaleCorrector.

        Args:
            config: Scale correction configuration. Defaults to ScaleConfig().
        """
        self.config = config or ScaleConfig()
        self.reference_size_mm = self.config.reference_size_mm

    def correct(
        self,
        input_path: Path,
        output_path: Path,
        dense_ply_path: Path,
    ) -> Optional[float]:
        """Detect reference object and apply scale correction to mesh.

        Loads the colored dense point cloud, segments by color, clusters with
        DBSCAN, selects the smallest compact cluster as the calibration
        reference, computes the scale factor, and applies it to the mesh.

        On detection failure (missing dense PLY, no colors, no suitable cluster),
        the unscaled mesh is saved to output_path and None is returned.

        Args:
            input_path: Path to the unscaled cleaned mesh (mesh_clean.ply).
            output_path: Path to write the scale-corrected mesh (mesh_scaled.ply).
            dense_ply_path: Path to the colored dense point cloud (scene_dense.ply).

        Returns:
            Scale factor (mm per model unit) if detection succeeded, else None.

        Raises:
            FileNotFoundError: If input_path does not exist.
        """
        if not input_path.exists():
            raise FileNotFoundError(f"Input mesh not found: {input_path}")

        if not dense_ply_path.exists():
            logger.warning(
                "Dense PLY not found: %s — saving unscaled mesh", dense_ply_path
            )
            self._save_fallback(input_path, output_path)
            return None

        logger.info("Scale correction: loading dense cloud %s", dense_ply_path)
        pcd = o3d.io.read_point_cloud(str(dense_ply_path))
        logger.info("Dense cloud: %d points", len(pcd.points))

        if not pcd.has_colors():
            logger.warning("Dense PLY has no vertex colors — saving unscaled mesh")
            self._save_fallback(input_path, output_path)
            return None

        pcd_ref = self._segment_by_color(pcd, self.config)
        n_ref = len(pcd_ref.points)
        logger.info(
            "Color segmentation (%s): %d / %d points retained",
            self.config.color_hint,
            n_ref,
            len(pcd.points),
        )

        if n_ref < self.config.min_cluster_points:
            logger.warning(
                "Color segmentation yielded %d points (< %d min) — saving unscaled mesh",
                n_ref,
                self.config.min_cluster_points,
            )
            self._save_fallback(input_path, output_path)
            return None

        # Set DBSCAN eps relative to full scene bounding box diagonal
        all_pts = np.asarray(pcd.points)
        bbox_diag = float(np.linalg.norm(all_pts.max(axis=0) - all_pts.min(axis=0)))
        eps = bbox_diag * self.config.dbscan_eps_fraction
        logger.debug(
            "DBSCAN eps=%.6f (scene diag=%.4f × frac=%.3f)",
            eps, bbox_diag, self.config.dbscan_eps_fraction,
        )

        clusters = self._dbscan_clusters(
            np.asarray(pcd_ref.points), eps, self.config.dbscan_min_samples
        )
        logger.info("DBSCAN found %d cluster(s) in color-segmented cloud", len(clusters))

        if not clusters:
            logger.warning("No clusters found — saving unscaled mesh")
            self._save_fallback(input_path, output_path)
            return None

        candidates = self._filter_compact_clusters(clusters, self.config)
        logger.info(
            "%d / %d cluster(s) passed compactness and plausibility filters",
            len(candidates),
            len(clusters),
        )

        if not candidates:
            logger.warning("No compact plausible cluster found — saving unscaled mesh")
            self._save_fallback(input_path, output_path)
            return None

        best_points, detected_size = candidates[0]
        logger.info(
            "Reference cluster: %d points, long_dim=%.6f model units",
            len(best_points),
            detected_size,
        )

        scale_factor = self.compute_scale_factor(
            detected_size, self.config.reference_size_mm
        )
        logger.info("Scale factor: %.4f mm/unit", scale_factor)

        mesh = o3d.io.read_triangle_mesh(str(input_path))
        self.apply_scale(mesh, scale_factor)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        o3d.io.write_triangle_mesh(str(output_path), mesh)
        logger.info(
            "Saved scale-corrected mesh to %s (%d vertices)",
            output_path,
            len(mesh.vertices),
        )
        return scale_factor

    @staticmethod
    def _segment_by_color(
        pcd: o3d.geometry.PointCloud,
        config: ScaleConfig,
    ) -> o3d.geometry.PointCloud:
        """Return subset of pcd whose RGB colors match the configured color hint.

        Converts RGB [0,1] float colors to OpenCV HSV uint8 and applies
        per-preset or explicit HSV thresholds. For 'white', filtering is based
        on saturation and value only (hue is irrelevant for achromatic colors).
        For chromatic hints, a hue window test is also applied.

        Args:
            pcd: Colored point cloud (must have colors).
            config: ScaleConfig specifying color_hint and HSV thresholds.

        Returns:
            Filtered PointCloud containing only matching points.
        """
        preset = _HSV_PRESETS.get(config.color_hint, _HSV_PRESETS["white"])
        hue_center = config.hsv_hue_center if config.hsv_hue_center is not None \
            else preset["hue_center"]
        hue_width = config.hsv_hue_width if config.hsv_hue_width is not None \
            else preset["hue_width"]
        sat_max = preset["sat_max"] if config.color_hint == "white" else config.hsv_sat_max
        val_min = config.hsv_val_min

        # Convert Open3D float RGB [0,1] → uint8 BGR → HSV
        rgb = (np.asarray(pcd.colors) * 255).astype(np.uint8)
        bgr = rgb[:, ::-1]
        bgr_img = bgr.reshape(1, -1, 3)
        hsv_img = cv2.cvtColor(bgr_img, cv2.COLOR_BGR2HSV)
        hsv = hsv_img.reshape(-1, 3).astype(np.float32)
        # OpenCV HSV: H in [0,180], S in [0,255], V in [0,255]
        h = hsv[:, 0]
        s = hsv[:, 1] / 255.0
        v = hsv[:, 2] / 255.0

        if config.color_hint == "white":
            mask = (s <= sat_max) & (v >= val_min)
        else:
            h_diff = np.abs(h - hue_center)
            h_diff = np.minimum(h_diff, 180.0 - h_diff)
            mask = (h_diff <= hue_width) & (s >= 0.30) & (v >= val_min)

        indices = np.where(mask)[0]
        return pcd.select_by_index(indices.tolist())

    @staticmethod
    def _dbscan_clusters(
        points: np.ndarray,
        eps: float,
        min_samples: int,
    ) -> list[np.ndarray]:
        """Cluster 3D points with DBSCAN; return list of per-cluster point arrays.

        Uses Open3D's built-in cluster_dbscan — no sklearn dependency required.
        Noise points (label -1) are excluded from all returned clusters.

        Args:
            points: (N, 3) float array of 3D points.
            eps: DBSCAN neighbourhood radius.
            min_samples: Minimum neighbourhood population for a core point.

        Returns:
            List of (N_i, 3) arrays, one per non-noise cluster. Empty if none.
        """
        pcd_tmp = o3d.geometry.PointCloud()
        pcd_tmp.points = o3d.utility.Vector3dVector(points)
        labels = np.asarray(
            pcd_tmp.cluster_dbscan(eps=eps, min_points=min_samples, print_progress=False)
        )
        unique_labels = set(labels.tolist()) - {-1}
        return [points[labels == lbl] for lbl in unique_labels]

    @staticmethod
    def _filter_compact_clusters(
        clusters: list[np.ndarray],
        config: ScaleConfig,
    ) -> list[tuple[np.ndarray, float]]:
        """Filter clusters by population, isotropy, and size plausibility.

        Three filters applied in order:
          1. Population: cluster must have >= min_cluster_points points.
          2. Isotropy: AABB short/long ratio >= min_isotropy (rejects flat planes).
          3. Plausibility: implied scale factor in [min_scale_factor,
             max_scale_factor] mm/unit.

        Surviving clusters are sorted ascending by AABB volume so the most
        likely calibration cube is candidates[0].

        Args:
            clusters: List of (N_i, 3) point arrays from DBSCAN.
            config: ScaleConfig with filter thresholds.

        Returns:
            List of (cluster_points, long_dimension) tuples sorted by AABB
            volume ascending. Empty if no clusters survive all filters.
        """
        results: list[tuple[np.ndarray, float, float]] = []

        for pts in clusters:
            if len(pts) < config.min_cluster_points:
                continue

            aabb = pts.max(axis=0) - pts.min(axis=0)
            dims = sorted(aabb)
            long_dim = dims[2]

            if long_dim < 1e-9:
                continue

            isotropy = dims[0] / long_dim
            if isotropy < config.min_isotropy:
                logger.debug(
                    "Cluster rejected: isotropy=%.3f < %.3f",
                    isotropy, config.min_isotropy,
                )
                continue

            implied_scale = config.reference_size_mm / long_dim
            if not (config.min_scale_factor <= implied_scale <= config.max_scale_factor):
                logger.debug(
                    "Cluster rejected: implied scale=%.2f outside [%.1f, %.1f]",
                    implied_scale, config.min_scale_factor, config.max_scale_factor,
                )
                continue

            volume = dims[0] * dims[1] * dims[2]
            results.append((pts, long_dim, volume))

        results.sort(key=lambda x: x[2])
        return [(pts, long_dim) for pts, long_dim, _ in results]

    @staticmethod
    def _save_fallback(input_path: Path, output_path: Path) -> None:
        """Copy input mesh to output_path unchanged (graceful degradation).

        Args:
            input_path: Source mesh path.
            output_path: Destination path for the unscaled copy.
        """
        mesh = o3d.io.read_triangle_mesh(str(input_path))
        output_path.parent.mkdir(parents=True, exist_ok=True)
        o3d.io.write_triangle_mesh(str(output_path), mesh)
        logger.warning(
            "Saved UNSCALED mesh to %s — scale correction was not applied", output_path
        )

    @staticmethod
    def apply_scale(
        mesh: o3d.geometry.TriangleMesh, scale_factor: float
    ) -> o3d.geometry.TriangleMesh:
        """Apply uniform scale factor to an Open3D mesh.

        Scales around the mesh centroid so the shape stays centred.

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
