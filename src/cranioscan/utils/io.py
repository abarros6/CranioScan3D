"""File I/O helpers for mesh, metadata, and point cloud files.

Centralises all file reading/writing so the rest of the pipeline doesn't
need to import Open3D or json directly for basic I/O.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import open3d as o3d

logger = logging.getLogger(__name__)


def read_mesh(path: Path) -> o3d.geometry.TriangleMesh:
    """Read a triangle mesh from a PLY or OBJ file.

    Args:
        path: Path to the mesh file (.ply or .obj).

    Returns:
        Open3D TriangleMesh object.

    Raises:
        FileNotFoundError: If path does not exist.
        RuntimeError: If the mesh cannot be loaded.
    """
    if not path.exists():
        raise FileNotFoundError(f"Mesh file not found: {path}")
    logger.debug("Reading mesh: %s", path)
    mesh = o3d.io.read_triangle_mesh(str(path))
    if len(mesh.vertices) == 0:
        raise RuntimeError(f"Mesh loaded but has 0 vertices: {path}")
    logger.debug(
        "Loaded: %d vertices, %d triangles", len(mesh.vertices), len(mesh.triangles)
    )
    return mesh


def write_mesh(mesh: o3d.geometry.TriangleMesh, path: Path) -> None:
    """Write a triangle mesh to a PLY file.

    Args:
        mesh: Open3D TriangleMesh to write.
        path: Output path (should have .ply extension).

    Raises:
        RuntimeError: If writing fails.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    logger.debug("Writing mesh to: %s", path)
    success = o3d.io.write_triangle_mesh(str(path), mesh)
    if not success:
        raise RuntimeError(f"Failed to write mesh to {path}")
    logger.info(
        "Saved mesh: %s (%d v, %d t)", path, len(mesh.vertices), len(mesh.triangles)
    )


def read_json(path: Path) -> dict[str, Any]:
    """Read a JSON metadata file.

    Args:
        path: Path to the JSON file.

    Returns:
        Parsed JSON as a dict.

    Raises:
        FileNotFoundError: If path does not exist.
    """
    if not path.exists():
        raise FileNotFoundError(f"JSON file not found: {path}")
    with path.open() as f:
        return json.load(f)


def write_json(data: dict[str, Any], path: Path) -> None:
    """Write data to a JSON file with pretty-printing.

    Args:
        data: Data to serialise.
        path: Output path.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as f:
        json.dump(data, f, indent=2)
    logger.debug("Wrote JSON: %s", path)
