"""Tests for scale factor computation (no COLMAP/OpenMVS required)."""

from __future__ import annotations

import numpy as np
import open3d as o3d
import pytest

from cranioscan.mesh.scale import ScaleCorrector


def test_compute_scale_factor_known_values():
    """Scale factor should be known_mm / detected."""
    factor = ScaleCorrector.compute_scale_factor(detected_size=5.0, known_size_mm=10.0)
    assert factor == pytest.approx(2.0)


def test_compute_scale_factor_identity():
    """Scale factor should be 1.0 when detected and known sizes match."""
    factor = ScaleCorrector.compute_scale_factor(detected_size=10.0, known_size_mm=10.0)
    assert factor == pytest.approx(1.0)


def test_compute_scale_factor_sub_unit():
    """Scale factor < 1 for detected larger than known (over-scaled model)."""
    factor = ScaleCorrector.compute_scale_factor(detected_size=20.0, known_size_mm=10.0)
    assert factor == pytest.approx(0.5)


def test_compute_scale_factor_zero_detected_raises():
    """Scale factor should raise ValueError if detected_size is zero."""
    with pytest.raises(ValueError):
        ScaleCorrector.compute_scale_factor(detected_size=0.0, known_size_mm=10.0)


def test_compute_scale_factor_negative_raises():
    """Scale factor should raise ValueError if detected_size is negative."""
    with pytest.raises(ValueError):
        ScaleCorrector.compute_scale_factor(detected_size=-1.0, known_size_mm=10.0)


def test_compute_scale_factor_result_positive():
    """Scale factor must always be positive for positive inputs."""
    factor = ScaleCorrector.compute_scale_factor(detected_size=3.7, known_size_mm=25.0)
    assert factor > 0.0


def test_apply_scale_changes_mesh_size():
    """apply_scale should scale mesh vertices by the given factor."""
    mesh = o3d.geometry.TriangleMesh.create_sphere(radius=1.0)
    original_extent = np.asarray(mesh.get_axis_aligned_bounding_box().get_extent())

    scaled = ScaleCorrector.apply_scale(mesh, scale_factor=2.0)
    new_extent = np.asarray(scaled.get_axis_aligned_bounding_box().get_extent())

    np.testing.assert_allclose(new_extent, original_extent * 2.0, rtol=1e-5)


def test_apply_scale_identity():
    """apply_scale with factor=1.0 should leave mesh unchanged."""
    mesh = o3d.geometry.TriangleMesh.create_box(width=5.0, height=3.0, depth=2.0)
    original_verts = np.asarray(mesh.vertices).copy()
    original_center = mesh.get_center()

    ScaleCorrector.apply_scale(mesh, scale_factor=1.0)
    new_center = mesh.get_center()

    # Center should be preserved; vertices should be same relative to center
    np.testing.assert_allclose(new_center, original_center, atol=1e-6)


def test_apply_scale_half():
    """apply_scale with factor=0.5 should halve the bounding box extents."""
    mesh = o3d.geometry.TriangleMesh.create_sphere(radius=10.0)
    original_extent = np.asarray(mesh.get_axis_aligned_bounding_box().get_extent())

    ScaleCorrector.apply_scale(mesh, scale_factor=0.5)
    new_extent = np.asarray(mesh.get_axis_aligned_bounding_box().get_extent())

    np.testing.assert_allclose(new_extent, original_extent * 0.5, rtol=1e-4)


def test_correct_raises_not_implemented(tmp_path):
    """ScaleCorrector.correct should raise NotImplementedError (stub)."""
    corrector = ScaleCorrector()
    # Create a dummy PLY file
    mesh = o3d.geometry.TriangleMesh.create_sphere()
    input_path = tmp_path / "mesh.ply"
    o3d.io.write_triangle_mesh(str(input_path), mesh)

    with pytest.raises(NotImplementedError):
        corrector.correct(input_path, tmp_path / "scaled.ply")
