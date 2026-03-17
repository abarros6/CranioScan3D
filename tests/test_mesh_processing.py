"""Tests for Open3D mesh post-processing operations."""

from __future__ import annotations

import numpy as np
import open3d as o3d
import pytest

from cranioscan.config import MeshConfig
from cranioscan.mesh.processing import MeshProcessor


def test_remove_small_components_keeps_main_body(synthetic_sphere_mesh):
    """Large connected component should survive small-component removal."""
    mesh = synthetic_sphere_mesh
    initial_triangles = len(mesh.triangles)
    cleaned = MeshProcessor._remove_small_components(mesh, min_triangle_fraction=0.01)
    # Main sphere component should be retained
    assert len(cleaned.triangles) > 0
    assert len(cleaned.triangles) <= initial_triangles


def test_remove_small_components_removes_isolated_triangles():
    """Tiny isolated components well below the fraction threshold should be removed."""
    # Sphere as main body (~2400 triangles)
    sphere = o3d.geometry.TriangleMesh.create_sphere(radius=1.0, resolution=10)

    # Tiny separate box (12 triangles) placed far away — counts as a small component
    box = o3d.geometry.TriangleMesh.create_box(width=0.01, height=0.01, depth=0.01)
    box.translate([1000.0, 0.0, 0.0])

    combined = sphere + box
    total_before = len(combined.triangles)

    cleaned = MeshProcessor._remove_small_components(combined, min_triangle_fraction=0.05)
    # Box should be gone; sphere should remain
    assert len(cleaned.triangles) < total_before
    assert len(cleaned.triangles) > 0


def test_mesh_processor_raises_on_missing_file(tmp_path):
    """MeshProcessor.process should raise FileNotFoundError for missing input."""
    config = MeshConfig()
    processor = MeshProcessor(config)
    with pytest.raises(FileNotFoundError):
        processor.process(tmp_path / "nonexistent.ply", tmp_path / "out.ply")


def test_mesh_processor_writes_output(tmp_path, synthetic_sphere_mesh):
    """MeshProcessor.process should write a valid mesh to the output path."""
    input_path = tmp_path / "input.ply"
    output_path = tmp_path / "output.ply"
    o3d.io.write_triangle_mesh(str(input_path), synthetic_sphere_mesh)

    config = MeshConfig(poisson_depth=6, smooth_iterations=2)
    processor = MeshProcessor(config)
    processor.process(input_path, output_path)

    assert output_path.exists()
    loaded = o3d.io.read_triangle_mesh(str(output_path))
    assert len(loaded.vertices) > 0


def test_mesh_processor_output_has_normals(tmp_path, synthetic_sphere_mesh):
    """Processed mesh should have vertex normals computed."""
    input_path = tmp_path / "input.ply"
    output_path = tmp_path / "output.ply"
    o3d.io.write_triangle_mesh(str(input_path), synthetic_sphere_mesh)

    config = MeshConfig(poisson_depth=6, smooth_iterations=1)
    processor = MeshProcessor(config)
    processor.process(input_path, output_path)

    loaded = o3d.io.read_triangle_mesh(str(output_path))
    assert loaded.has_vertex_normals()
