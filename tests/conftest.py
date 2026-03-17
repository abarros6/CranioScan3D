"""Pytest fixtures for CranioScan3D test suite.

Provides synthetic mesh geometry, sample frames, and temporary directories
without requiring COLMAP, OpenMVS, or real video data.
"""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
import open3d as o3d
import pytest


@pytest.fixture
def tmp_output_dir(tmp_path: Path) -> Path:
    """Provide a temporary output directory."""
    out = tmp_path / "output"
    out.mkdir()
    return out


@pytest.fixture
def synthetic_sphere_mesh() -> o3d.geometry.TriangleMesh:
    """Create a synthetic sphere mesh for testing mesh processing operations."""
    mesh = o3d.geometry.TriangleMesh.create_sphere(radius=100.0, resolution=20)
    mesh.compute_vertex_normals()
    # Scale to roughly head-sized (150mm radius) with some noise
    vertices = np.asarray(mesh.vertices)
    noise = np.random.default_rng(42).normal(0, 0.5, vertices.shape)
    mesh.vertices = o3d.utility.Vector3dVector(vertices + noise)
    return mesh


@pytest.fixture
def sample_frames_dir(tmp_path: Path) -> Path:
    """Create a directory of synthetic JPEG frames for extraction tests."""
    frames_dir = tmp_path / "frames"
    frames_dir.mkdir()
    rng = np.random.default_rng(42)
    for i in range(5):
        # Sharp frame (high variance)
        img = rng.integers(0, 256, (480, 640, 3), dtype=np.uint8)
        cv2.imwrite(str(frames_dir / f"frame_{i:06d}.jpg"), img)
    return frames_dir


@pytest.fixture
def sharp_frame() -> np.ndarray:
    """Return a sharp synthetic BGR frame (high Laplacian variance)."""
    rng = np.random.default_rng(42)
    return rng.integers(0, 256, (480, 640, 3), dtype=np.uint8)


@pytest.fixture
def blurry_frame() -> np.ndarray:
    """Return a blurry synthetic BGR frame (low Laplacian variance)."""
    # Uniform solid color = zero variance
    return np.full((480, 640, 3), 128, dtype=np.uint8)


@pytest.fixture
def head_landmarks() -> dict[str, np.ndarray]:
    """Return a synthetic set of craniometric landmark positions in mm.

    Based on approximate values for a 3-month-old infant head.
    """
    return {
        "glabella": np.array([0.0, 0.0, 0.0]),
        "opisthocranion": np.array([130.0, 0.0, 0.0]),
        "eurion_l": np.array([65.0, -68.0, 10.0]),
        "eurion_r": np.array([65.0, 68.0, 10.0]),
    }
