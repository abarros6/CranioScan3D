"""CranioScan3D pipeline orchestrator.

Entry point for the full pipeline. Runs stages in sequence:
  1. extraction   — Extract frames from iPhone video
  2. sparse       — COLMAP sparse SfM
  3. undistort    — COLMAP image undistortion
  4. dense        — OpenMVS dense reconstruction
  5. mesh         — Open3D mesh post-processing
  6. scale        — Scale correction (stub)
  7. landmarks    — Landmark detection (stub)
  8. measurement  — Cranial index computation (stub)
  9. report       — PDF report generation (stub)

CLI usage:
    cranioscan --input video.mp4 --output-dir data/results/session1
    cranioscan --input video.mp4 --skip-to dense --stop-after mesh
    cranioscan --input video.mp4 --dry-run
"""

from __future__ import annotations

import argparse
import logging
import sys
import time
from pathlib import Path
from typing import Callable, Optional

from cranioscan.config import Config
from cranioscan.extraction.frame_extractor import FrameExtractor
from cranioscan.mesh.processing import MeshProcessor
from cranioscan.mesh.scale import ScaleCorrector
from cranioscan.reconstruction.dense import DensePipeline
from cranioscan.reconstruction.sparse import SparsePipeline
from cranioscan.reconstruction.undistort import Undistorter
from cranioscan.utils.logging import setup_logging
from cranioscan.utils.validation import validate_dependencies, validate_input_video

logger = logging.getLogger(__name__)

STAGES = [
    "extraction",
    "sparse",
    "undistort",
    "dense",
    "mesh",
    "scale",
    "landmarks",
    "measurement",
    "report",
]


def _build_paths(output_dir: Path) -> dict[str, Path]:
    """Build the standard directory layout under output_dir.

    Args:
        output_dir: Root output directory for this pipeline run.

    Returns:
        Dict mapping stage names to their working directories.
    """
    paths = {
        "frames": output_dir / "frames",
        "sparse": output_dir / "sparse",
        "undistorted": output_dir / "undistorted",
        "dense": output_dir / "dense",
        "mesh": output_dir / "mesh",
        "results": output_dir / "results",
    }
    for p in paths.values():
        p.mkdir(parents=True, exist_ok=True)
    return paths


def run_pipeline(
    input_video: Path,
    output_dir: Path,
    config: Config,
    skip_to: Optional[str] = None,
    stop_after: Optional[str] = None,
    dry_run: bool = False,
) -> None:
    """Run the full CranioScan3D pipeline.

    Args:
        input_video: Path to the input iPhone video file.
        output_dir: Root directory where all pipeline outputs will be written.
        config: Pipeline configuration object.
        skip_to: If set, skip all stages before this stage name.
        stop_after: If set, stop pipeline after this stage name.
        dry_run: If True, print what would run without executing anything.

    Raises:
        SystemExit: On stage failure when config.pipeline.stop_on_error is True.
    """
    setup_logging(config.pipeline.log_level)
    logger.info("=== CranioScan3D pipeline starting ===")
    logger.info("Input:      %s", input_video)
    logger.info("Output dir: %s", output_dir)
    logger.info("Config:     %s", config)

    if not dry_run:
        validate_input_video(input_video)
        validate_dependencies(config)

    paths = _build_paths(output_dir)

    # Determine active stage range
    skip_idx = STAGES.index(skip_to) if skip_to else 0
    stop_idx = STAGES.index(stop_after) + 1 if stop_after else len(STAGES)
    active_stages = STAGES[skip_idx:stop_idx]

    logger.info("Stages to run: %s", active_stages)

    stage_fns: dict[str, Callable] = {
        "extraction": lambda: _run_extraction(input_video, paths, config, dry_run),
        "sparse": lambda: _run_sparse(paths, config, dry_run),
        "undistort": lambda: _run_undistort(paths, config, dry_run),
        "dense": lambda: _run_dense(paths, config, dry_run),
        "mesh": lambda: _run_mesh(paths, config, dry_run),
        "scale": lambda: _run_scale(paths, config, dry_run),
        "landmarks": lambda: _run_landmarks(paths, config, dry_run),
        "measurement": lambda: _run_measurement(paths, config, dry_run),
        "report": lambda: _run_report(paths, config, dry_run),
    }

    total_start = time.perf_counter()

    for stage in active_stages:
        logger.info("--- Stage: %s ---", stage)
        t0 = time.perf_counter()
        try:
            stage_fns[stage]()
        except NotImplementedError as exc:
            logger.warning("Stage '%s' not yet implemented: %s", stage, exc)
        except Exception as exc:
            logger.error("Stage '%s' failed: %s", stage, exc, exc_info=True)
            if config.pipeline.stop_on_error:
                logger.error(
                    "Aborting pipeline. Fix the error above and re-run with --skip-to %s", stage
                )
                sys.exit(1)
        elapsed = time.perf_counter() - t0
        logger.info("Stage '%s' completed in %.1fs", stage, elapsed)

    total = time.perf_counter() - total_start
    logger.info("=== Pipeline finished in %.1fs ===", total)


def _run_extraction(input_video: Path, paths: dict, config: Config, dry_run: bool) -> None:
    if dry_run:
        logger.info("[DRY RUN] Would extract frames from %s -> %s", input_video, paths["frames"])
        return
    extractor = FrameExtractor(config.extraction)
    extractor.extract(input_video, paths["frames"])


def _run_sparse(paths: dict, config: Config, dry_run: bool) -> None:
    if dry_run:
        logger.info("[DRY RUN] Would run COLMAP sparse SfM on %s", paths["frames"])
        return
    sparse = SparsePipeline(config.reconstruction)
    sparse.run(paths["frames"], paths["sparse"])


def _run_undistort(paths: dict, config: Config, dry_run: bool) -> None:
    if dry_run:
        logger.info("[DRY RUN] Would run COLMAP undistortion")
        return
    undistorter = Undistorter(config.reconstruction)
    undistorter.run(paths["frames"], paths["sparse"], paths["undistorted"])


def _run_dense(paths: dict, config: Config, dry_run: bool) -> None:
    if dry_run:
        logger.info("[DRY RUN] Would run OpenMVS dense pipeline")
        return
    dense = DensePipeline(config.dense, config.reconstruction)
    dense.run(paths["undistorted"], paths["dense"])


def _run_mesh(paths: dict, config: Config, dry_run: bool) -> None:
    if dry_run:
        logger.info("[DRY RUN] Would run Open3D mesh processing")
        return
    processor = MeshProcessor(config.mesh)
    input_mesh = paths["dense"] / "mesh_refined.ply"
    if not input_mesh.exists():
        input_mesh = paths["dense"] / "mesh.ply"
    output_mesh = paths["mesh"] / "mesh_clean.ply"
    processor.process(input_mesh, output_mesh)


def _run_scale(paths: dict, config: Config, dry_run: bool) -> None:
    if dry_run:
        logger.info("[DRY RUN] Would run scale correction")
        return
    corrector = ScaleCorrector()
    corrector.correct(paths["mesh"] / "mesh_clean.ply", paths["mesh"] / "mesh_scaled.ply")


def _run_landmarks(paths: dict, config: Config, dry_run: bool) -> None:
    raise NotImplementedError("TODO: implement in Month 3 — landmark detection")


def _run_measurement(paths: dict, config: Config, dry_run: bool) -> None:
    raise NotImplementedError("TODO: implement in Month 3 — cranial measurement")


def _run_report(paths: dict, config: Config, dry_run: bool) -> None:
    raise NotImplementedError("TODO: implement in Month 4 — PDF report generation")


def _parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="cranioscan",
        description="CranioScan3D — 3D cranial reconstruction and measurement pipeline",
    )
    parser.add_argument(
        "--input", required=True, type=Path, help="Path to input iPhone video file"
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/results/session"),
        help="Root output directory (default: data/results/session)",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("configs/default.yaml"),
        help="Path to YAML config file (default: configs/default.yaml)",
    )
    parser.add_argument(
        "--skip-to",
        choices=STAGES,
        default=None,
        help="Skip all stages before this one",
    )
    parser.add_argument(
        "--stop-after",
        choices=STAGES,
        default=None,
        help="Stop pipeline after this stage",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would execute without running anything",
    )
    return parser.parse_args(argv)


def _load_dotenv() -> None:
    """Load .env file from the project root into os.environ if it exists."""
    import os
    env_path = Path(__file__).parent.parent.parent / ".env"
    if not env_path.exists():
        return
    with env_path.open() as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            os.environ.setdefault(key.strip(), value.strip())


def main(argv: Optional[list[str]] = None) -> None:
    """CLI entry point for the CranioScan3D pipeline.

    Args:
        argv: Argument list (defaults to sys.argv if None).
    """
    _load_dotenv()
    args = _parse_args(argv)

    if args.config.exists():
        config = Config.from_yaml(args.config)
    else:
        logger.warning("Config file %s not found, using defaults", args.config)
        config = Config.defaults()

    run_pipeline(
        input_video=args.input,
        output_dir=args.output_dir,
        config=config,
        skip_to=args.skip_to,
        stop_after=args.stop_after,
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    main()
