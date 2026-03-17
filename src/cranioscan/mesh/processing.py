"""Open3D mesh post-processing pipeline.

Cleans up the dense reconstruction mesh: removes outliers, reconstructs
a watertight surface using Poisson reconstruction, applies Taubin smoothing,
and fills small holes.
"""

from __future__ import annotations

import logging
from pathlib import Path

import numpy as np
import open3d as o3d

from cranioscan.config import MeshConfig

logger = logging.getLogger(__name__)


class MeshProcessor:
    """Cleans and post-processes a raw reconstruction mesh using Open3D.

    Pipeline:
      1. Statistical outlier removal on the point cloud / vertex set
      2. Poisson surface reconstruction (watertight)
      3. Taubin smoothing (low-pass filter, volume-preserving)
      4. Remove small disconnected components

    Attributes:
        config: Mesh processing configuration.
    """

    def __init__(self, config: MeshConfig) -> None:
        """Initialize MeshProcessor.

        Args:
            config: Mesh processing configuration.
        """
        self.config = config

    def process(self, input_path: Path, output_path: Path) -> None:
        """Run the full mesh processing pipeline.

        Args:
            input_path: Path to the input mesh file (.ply or .obj).
            output_path: Path to write the cleaned output mesh (.ply).

        Raises:
            FileNotFoundError: If input_path does not exist.
            RuntimeError: If mesh loading or processing fails.
        """
        if not input_path.exists():
            raise FileNotFoundError(f"Mesh not found: {input_path}")

        logger.info("Loading mesh: %s", input_path)
        mesh = o3d.io.read_triangle_mesh(str(input_path))
        logger.info(
            "Loaded mesh: %d vertices, %d triangles",
            len(mesh.vertices),
            len(mesh.triangles),
        )

        # Step 1: Statistical outlier removal on point cloud
        logger.info("Step 1: Statistical outlier removal")
        pcd = mesh.sample_points_uniformly(number_of_points=len(mesh.vertices))
        pcd_clean, _ = pcd.remove_statistical_outlier(
            nb_neighbors=self.config.outlier_nb_neighbors,
            std_ratio=self.config.outlier_std_ratio,
        )
        logger.info(
            "Points after outlier removal: %d / %d",
            len(pcd_clean.points),
            len(pcd.points),
        )

        # Step 2: Poisson surface reconstruction
        logger.info(
            "Step 2: Poisson surface reconstruction (depth=%d)", self.config.poisson_depth
        )
        pcd_clean.estimate_normals(
            search_param=o3d.geometry.KDTreeSearchParamHybrid(radius=0.01, max_nn=30)
        )
        pcd_clean.orient_normals_consistent_tangent_plane(k=15)
        mesh_poisson, densities = o3d.geometry.TriangleMesh.create_from_point_cloud_poisson(
            pcd_clean, depth=self.config.poisson_depth
        )

        # Remove low-density vertices (surface reconstruction artifacts)
        densities_np = np.asarray(densities)
        density_threshold = np.quantile(densities_np, 0.05)
        vertices_to_remove = densities_np < density_threshold
        mesh_poisson.remove_vertices_by_mask(vertices_to_remove)
        logger.info(
            "After Poisson: %d vertices, %d triangles",
            len(mesh_poisson.vertices),
            len(mesh_poisson.triangles),
        )

        # Step 3: Taubin smoothing (volume-preserving low-pass)
        logger.info(
            "Step 3: Taubin smoothing (%d iterations, lambda=%.2f)",
            self.config.smooth_iterations,
            self.config.smooth_lambda,
        )
        mesh_smooth = mesh_poisson.filter_smooth_taubin(
            number_of_iterations=self.config.smooth_iterations,
            lambda_filter=self.config.smooth_lambda,
        )
        mesh_smooth.compute_vertex_normals()

        # Step 4: Remove small disconnected components
        logger.info("Step 4: Removing small disconnected components")
        mesh_clean = self._remove_small_components(mesh_smooth)

        output_path.parent.mkdir(parents=True, exist_ok=True)
        o3d.io.write_triangle_mesh(str(output_path), mesh_clean)
        logger.info(
            "Saved cleaned mesh to %s (%d vertices, %d triangles)",
            output_path,
            len(mesh_clean.vertices),
            len(mesh_clean.triangles),
        )

    @staticmethod
    def _remove_small_components(
        mesh: o3d.geometry.TriangleMesh, min_triangle_fraction: float = 0.01
    ) -> o3d.geometry.TriangleMesh:
        """Remove small disconnected mesh components.

        Keeps only components with at least min_triangle_fraction of total triangles.

        Args:
            mesh: Input triangle mesh.
            min_triangle_fraction: Minimum fraction of total triangles to keep a component.

        Returns:
            Mesh with small components removed.
        """
        triangle_clusters, cluster_n_triangles, _ = mesh.cluster_connected_triangles()
        triangle_clusters = np.asarray(triangle_clusters)
        cluster_n_triangles = np.asarray(cluster_n_triangles)

        total = len(mesh.triangles)
        min_count = int(total * min_triangle_fraction)
        triangles_to_remove = cluster_n_triangles[triangle_clusters] < min_count
        mesh.remove_triangles_by_mask(triangles_to_remove)
        mesh.remove_unreferenced_vertices()
        return mesh
