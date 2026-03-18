"""Pipeline configuration dataclass.

Loads parameters from YAML files and/or CLI overrides. All pipeline stages
draw their settings from a single Config object passed down from the orchestrator.

Example:
    cfg = Config.from_yaml("configs/default.yaml")
    cfg = Config.from_yaml("configs/fast.yaml", overrides={"mesh.poisson_depth": 7})
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import yaml

logger = logging.getLogger(__name__)


@dataclass
class ExtractionConfig:
    """Frame extraction parameters."""

    frame_interval: int = 15
    blur_threshold: float = 100.0
    resize_max_dim: Optional[int] = None
    output_format: str = "jpg"
    jpeg_quality: int = 95


@dataclass
class ReconstructionConfig:
    """COLMAP sparse reconstruction parameters."""

    camera_model: str = "SIMPLE_RADIAL"
    single_camera: bool = True
    exhaustive_matching: bool = True
    colmap_bin: str = "colmap"
    openmvs_bin_dir: str = ""


@dataclass
class DenseConfig:
    """OpenMVS dense reconstruction parameters."""

    densify_resolution_level: int = 1
    densify_min_resolution: int = 640
    densify_max_resolution: int = 3200
    reconstruct_mesh: bool = True
    refine_mesh: bool = True


@dataclass
class MeshConfig:
    """Open3D mesh post-processing parameters."""

    outlier_nb_neighbors: int = 20
    outlier_std_ratio: float = 2.0
    poisson_depth: int = 9
    smooth_iterations: int = 5
    smooth_lambda: float = 0.5


@dataclass
class ScaleConfig:
    """Reference-object scale correction parameters.

    A small physical object of known size (e.g. a standard 16mm die) is placed
    in the scene during capture. Its color is used to segment it from the dense
    point cloud; its bounding box size is compared to the known physical size to
    derive a mm/model-unit scale factor.

    color_hint selects a preset HSV threshold. Supported values: white, red,
    yellow, blue. Override with hsv_* fields for non-standard colors.
    """

    reference_size_mm: float = 16.0
    color_hint: str = "white"
    hsv_hue_center: Optional[float] = None
    hsv_hue_width: Optional[float] = None
    hsv_sat_max: float = 0.25
    hsv_val_min: float = 0.70
    dbscan_eps_fraction: float = 0.02
    dbscan_min_samples: int = 10
    min_cluster_points: int = 50
    min_isotropy: float = 0.4
    min_scale_factor: float = 50.0
    max_scale_factor: float = 2000.0
    fallback_on_detection_failure: bool = True


@dataclass
class PipelineConfig:
    """Top-level pipeline behaviour settings."""

    stop_on_error: bool = True
    log_level: str = "INFO"


@dataclass
class Config:
    """Root configuration object for the CranioScan3D pipeline.

    All pipeline stages receive an instance of this class. Build one via
    Config.from_yaml() or Config.defaults().

    Attributes:
        extraction: Frame extraction settings.
        reconstruction: COLMAP sparse SfM settings.
        dense: OpenMVS dense reconstruction settings.
        mesh: Open3D mesh processing settings.
        scale: Scale correction settings.
        pipeline: Global pipeline behaviour settings.
    """

    extraction: ExtractionConfig = field(default_factory=ExtractionConfig)
    reconstruction: ReconstructionConfig = field(default_factory=ReconstructionConfig)
    dense: DenseConfig = field(default_factory=DenseConfig)
    mesh: MeshConfig = field(default_factory=MeshConfig)
    scale: ScaleConfig = field(default_factory=ScaleConfig)
    pipeline: PipelineConfig = field(default_factory=PipelineConfig)

    @classmethod
    def defaults(cls) -> "Config":
        """Return a Config with all default values.

        Returns:
            Config: Default configuration instance.
        """
        return cls()

    @classmethod
    def from_yaml(cls, path: str | Path, overrides: Optional[dict] = None) -> "Config":
        """Load configuration from a YAML file.

        Args:
            path: Path to the YAML configuration file.
            overrides: Optional flat dict of dot-separated key overrides,
                e.g. {"mesh.poisson_depth": 7}.

        Returns:
            Config: Populated configuration instance.

        Raises:
            FileNotFoundError: If the YAML file does not exist.
            ValueError: If YAML contains unknown section keys.
        """
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Config file not found: {path}")

        logger.info("Loading config from %s", path)
        with path.open() as f:
            data: dict = yaml.safe_load(f) or {}

        cfg = cls()

        section_map = {
            "extraction": (cfg.extraction, ExtractionConfig),
            "reconstruction": (cfg.reconstruction, ReconstructionConfig),
            "dense": (cfg.dense, DenseConfig),
            "mesh": (cfg.mesh, MeshConfig),
            "scale": (cfg.scale, ScaleConfig),
            "pipeline": (cfg.pipeline, PipelineConfig),
        }

        for section_key, section_data in data.items():
            if section_key not in section_map:
                raise ValueError(f"Unknown config section: '{section_key}'")
            obj, _ = section_map[section_key]
            for k, v in section_data.items():
                if not hasattr(obj, k):
                    logger.warning("Unknown config key %s.%s — ignoring", section_key, k)
                    continue
                setattr(obj, k, v)

        if overrides:
            for dotted_key, value in overrides.items():
                parts = dotted_key.split(".", 1)
                if len(parts) != 2 or parts[0] not in section_map:
                    logger.warning("Cannot apply override '%s' — skipping", dotted_key)
                    continue
                obj, _ = section_map[parts[0]]
                setattr(obj, parts[1], value)

        # Resolve colmap_bin / openmvs_bin_dir from environment if not set
        cfg.reconstruction.colmap_bin = (
            cfg.reconstruction.colmap_bin
            or os.environ.get("COLMAP_BIN", "colmap")
        )
        cfg.reconstruction.openmvs_bin_dir = (
            cfg.reconstruction.openmvs_bin_dir
            or os.environ.get("OPENMVS_BIN_DIR", "")
        )

        logger.debug("Loaded config: %s", cfg)
        return cfg
