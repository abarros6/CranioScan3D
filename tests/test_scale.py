"""Tests for scale correction: computation, application, and detection pipeline."""

from __future__ import annotations

import numpy as np
import open3d as o3d
import pytest

from cranioscan.config import ScaleConfig
from cranioscan.mesh.scale import ScaleCorrector


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_mesh(tmp_path, name="mesh.ply") -> "Path":
    """Write a small sphere mesh and return its path."""
    from pathlib import Path
    mesh = o3d.geometry.TriangleMesh.create_sphere(radius=1.0)
    p = tmp_path / name
    o3d.io.write_triangle_mesh(str(p), mesh)
    return p


def _make_colored_pcd(
    n_background: int = 5000,
    cube_size: float = 0.02,
    cube_color: tuple = (0.95, 0.95, 0.95),  # near-white
    scene_size: float = 1.0,
) -> o3d.geometry.PointCloud:
    """Build a synthetic colored point cloud with a known white cube embedded.

    Background points are medium gray; a compact cube of near-white points is
    placed at the scene origin. The cube's longest bounding box dimension will
    be cube_size.

    Args:
        n_background: Number of gray background points scattered over scene_size.
        cube_size: Side length of the synthetic calibration cube (model units).
        cube_color: RGB tuple for the cube (should be near-white for default config).
        scene_size: Half-width of the background point scatter volume.

    Returns:
        PointCloud with colors.
    """
    rng = np.random.default_rng(42)

    # Background: random gray points
    bg_pts = rng.uniform(-scene_size, scene_size, (n_background, 3))
    bg_colors = np.full((n_background, 3), 0.45)  # gray, S > 0.25 in HSV → not white

    # Calibration cube: near-white points, uniformly distributed in [0, cube_size]^3
    n_cube = 300
    cube_pts = rng.uniform(0.0, cube_size, (n_cube, 3))
    cube_colors = np.tile(cube_color, (n_cube, 1))

    pts = np.vstack([bg_pts, cube_pts])
    colors = np.vstack([bg_colors, cube_colors])

    pcd = o3d.geometry.PointCloud()
    pcd.points = o3d.utility.Vector3dVector(pts)
    pcd.colors = o3d.utility.Vector3dVector(colors)
    return pcd


# ---------------------------------------------------------------------------
# compute_scale_factor
# ---------------------------------------------------------------------------

def test_compute_scale_factor_known_values():
    factor = ScaleCorrector.compute_scale_factor(detected_size=5.0, known_size_mm=10.0)
    assert factor == pytest.approx(2.0)


def test_compute_scale_factor_identity():
    factor = ScaleCorrector.compute_scale_factor(detected_size=10.0, known_size_mm=10.0)
    assert factor == pytest.approx(1.0)


def test_compute_scale_factor_sub_unit():
    factor = ScaleCorrector.compute_scale_factor(detected_size=20.0, known_size_mm=10.0)
    assert factor == pytest.approx(0.5)


def test_compute_scale_factor_zero_detected_raises():
    with pytest.raises(ValueError):
        ScaleCorrector.compute_scale_factor(detected_size=0.0, known_size_mm=10.0)


def test_compute_scale_factor_negative_raises():
    with pytest.raises(ValueError):
        ScaleCorrector.compute_scale_factor(detected_size=-1.0, known_size_mm=10.0)


def test_compute_scale_factor_result_positive():
    factor = ScaleCorrector.compute_scale_factor(detected_size=3.7, known_size_mm=25.0)
    assert factor > 0.0


# ---------------------------------------------------------------------------
# apply_scale
# ---------------------------------------------------------------------------

def test_apply_scale_changes_mesh_size():
    mesh = o3d.geometry.TriangleMesh.create_sphere(radius=1.0)
    original_extent = np.asarray(mesh.get_axis_aligned_bounding_box().get_extent())
    scaled = ScaleCorrector.apply_scale(mesh, scale_factor=2.0)
    new_extent = np.asarray(scaled.get_axis_aligned_bounding_box().get_extent())
    np.testing.assert_allclose(new_extent, original_extent * 2.0, rtol=1e-5)


def test_apply_scale_identity():
    mesh = o3d.geometry.TriangleMesh.create_box(width=5.0, height=3.0, depth=2.0)
    original_center = mesh.get_center()
    ScaleCorrector.apply_scale(mesh, scale_factor=1.0)
    np.testing.assert_allclose(mesh.get_center(), original_center, atol=1e-6)


def test_apply_scale_half():
    mesh = o3d.geometry.TriangleMesh.create_sphere(radius=10.0)
    original_extent = np.asarray(mesh.get_axis_aligned_bounding_box().get_extent())
    ScaleCorrector.apply_scale(mesh, scale_factor=0.5)
    new_extent = np.asarray(mesh.get_axis_aligned_bounding_box().get_extent())
    np.testing.assert_allclose(new_extent, original_extent * 0.5, rtol=1e-4)


# ---------------------------------------------------------------------------
# correct() — failure / fallback paths
# ---------------------------------------------------------------------------

def test_correct_missing_input_raises(tmp_path):
    corrector = ScaleCorrector()
    with pytest.raises(FileNotFoundError):
        corrector.correct(
            input_path=tmp_path / "nonexistent.ply",
            output_path=tmp_path / "out.ply",
            dense_ply_path=tmp_path / "dense.ply",
        )


def test_correct_missing_dense_ply_saves_fallback(tmp_path):
    input_path = _make_mesh(tmp_path)
    output_path = tmp_path / "scaled.ply"
    corrector = ScaleCorrector()

    result = corrector.correct(
        input_path=input_path,
        output_path=output_path,
        dense_ply_path=tmp_path / "nonexistent_dense.ply",
    )

    assert result is None
    assert output_path.exists()


def test_correct_no_colors_saves_fallback(tmp_path):
    input_path = _make_mesh(tmp_path)
    output_path = tmp_path / "scaled.ply"

    # Write a colorless point cloud
    pcd = o3d.geometry.PointCloud()
    pcd.points = o3d.utility.Vector3dVector(np.random.rand(100, 3))
    dense_path = tmp_path / "dense.ply"
    o3d.io.write_point_cloud(str(dense_path), pcd)

    corrector = ScaleCorrector()
    result = corrector.correct(
        input_path=input_path,
        output_path=output_path,
        dense_ply_path=dense_path,
    )

    assert result is None
    assert output_path.exists()


def test_correct_too_few_segmented_points_saves_fallback(tmp_path):
    input_path = _make_mesh(tmp_path)
    output_path = tmp_path / "scaled.ply"

    # Dense cloud with all dark points — none pass the white threshold
    pts = np.random.rand(1000, 3)
    colors = np.full((1000, 3), 0.1)  # very dark, V < 0.7 → no white matches
    pcd = o3d.geometry.PointCloud()
    pcd.points = o3d.utility.Vector3dVector(pts)
    pcd.colors = o3d.utility.Vector3dVector(colors)
    dense_path = tmp_path / "dense.ply"
    o3d.io.write_point_cloud(str(dense_path), pcd)

    corrector = ScaleCorrector()
    result = corrector.correct(
        input_path=input_path,
        output_path=output_path,
        dense_ply_path=dense_path,
    )

    assert result is None
    assert output_path.exists()


# ---------------------------------------------------------------------------
# correct() — successful detection
# ---------------------------------------------------------------------------

def test_correct_successful_detection(tmp_path):
    """End-to-end: synthetic dense cloud with embedded white cube of known size.

    The cube has known long_dim = 0.02 model units and reference_size_mm = 16mm,
    so the expected scale factor is 16.0 / 0.02 = 800.0 mm/unit.
    """
    cube_size = 0.02
    expected_scale = 16.0 / cube_size  # = 800.0

    # Write input mesh
    input_path = _make_mesh(tmp_path)
    output_path = tmp_path / "scaled.ply"

    # Write synthetic dense point cloud
    pcd = _make_colored_pcd(cube_size=cube_size)
    dense_path = tmp_path / "dense.ply"
    o3d.io.write_point_cloud(str(dense_path), pcd)

    cfg = ScaleConfig(
        reference_size_mm=16.0,
        color_hint="white",
        dbscan_eps_fraction=0.05,   # slightly relaxed for the synthetic test
        min_cluster_points=50,
        min_isotropy=0.3,           # cube points are uniform → high isotropy
        min_scale_factor=100.0,
        max_scale_factor=5000.0,
    )
    corrector = ScaleCorrector(cfg)
    result = corrector.correct(
        input_path=input_path,
        output_path=output_path,
        dense_ply_path=dense_path,
    )

    assert result is not None, "Scale detection should succeed on synthetic data"
    assert output_path.exists()
    # Allow 20% tolerance — DBSCAN may not capture the exact cube boundary
    assert result == pytest.approx(expected_scale, rel=0.20)


# ---------------------------------------------------------------------------
# _segment_by_color
# ---------------------------------------------------------------------------

def test_segment_by_color_white_keeps_white_rejects_gray():
    """White segmentation should keep near-white points and reject gray."""
    pts = np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [2.0, 0.0, 0.0]])
    colors = np.array([
        [0.95, 0.95, 0.95],  # white → should be kept
        [0.45, 0.45, 0.45],  # gray → should be rejected
        [0.05, 0.05, 0.05],  # dark → should be rejected
    ])
    pcd = o3d.geometry.PointCloud()
    pcd.points = o3d.utility.Vector3dVector(pts)
    pcd.colors = o3d.utility.Vector3dVector(colors)

    cfg = ScaleConfig(color_hint="white", hsv_sat_max=0.25, hsv_val_min=0.75)
    result = ScaleCorrector._segment_by_color(pcd, cfg)
    assert len(result.points) == 1


def test_segment_by_color_returns_subset():
    """Segmentation result is a subset of the input point cloud."""
    rng = np.random.default_rng(0)
    pts = rng.uniform(0, 10, (200, 3))
    colors = rng.uniform(0, 1, (200, 3))
    pcd = o3d.geometry.PointCloud()
    pcd.points = o3d.utility.Vector3dVector(pts)
    pcd.colors = o3d.utility.Vector3dVector(colors)

    cfg = ScaleConfig(color_hint="white")
    result = ScaleCorrector._segment_by_color(pcd, cfg)
    assert len(result.points) <= len(pcd.points)


# ---------------------------------------------------------------------------
# _filter_compact_clusters
# ---------------------------------------------------------------------------

def test_filter_compact_clusters_rejects_flat():
    """A flat cluster (isotropy ≈ 0) should be rejected."""
    flat = np.column_stack([
        np.random.uniform(0, 1, 200),
        np.random.uniform(0, 1, 200),
        np.zeros(200),              # zero depth → short/long ≈ 0
    ])
    cfg = ScaleConfig(min_cluster_points=50, min_isotropy=0.4, reference_size_mm=16.0,
                      min_scale_factor=50.0, max_scale_factor=2000.0)
    result = ScaleCorrector._filter_compact_clusters([flat], cfg)
    assert len(result) == 0


def test_filter_compact_clusters_rejects_out_of_range():
    """A cluster with implied scale outside bounds should be rejected."""
    # Cube with long_dim = 1.0 → implied scale = 16/1 = 16 < min_scale_factor=50
    cube = np.random.uniform(0, 1.0, (200, 3))
    cfg = ScaleConfig(min_cluster_points=50, min_isotropy=0.0, reference_size_mm=16.0,
                      min_scale_factor=50.0, max_scale_factor=2000.0)
    result = ScaleCorrector._filter_compact_clusters([cube], cfg)
    assert len(result) == 0


def test_filter_compact_clusters_accepts_valid_cube():
    """A compact cube with valid implied scale should survive all filters."""
    # cube_size = 0.1 → implied scale = 16/0.1 = 160, in [50, 2000]
    rng = np.random.default_rng(7)
    cube = rng.uniform(0, 0.1, (300, 3))
    cfg = ScaleConfig(min_cluster_points=50, min_isotropy=0.4, reference_size_mm=16.0,
                      min_scale_factor=50.0, max_scale_factor=2000.0)
    result = ScaleCorrector._filter_compact_clusters([cube], cfg)
    assert len(result) == 1
    _, long_dim = result[0]
    assert long_dim == pytest.approx(0.1, rel=0.05)
