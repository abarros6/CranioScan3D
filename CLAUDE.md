# CLAUDE.md — CranioScan3D

Context for Claude Code when working in this repository.

---

## What this project is

Master's thesis project. End-to-end pipeline that reconstructs a 3D model of an infant's head from iPhone video and extracts cranial measurements for craniosynostosis screening. Classical computer vision only — no ML anywhere.

**Hardware:** Mac Mini Apple Silicon (no CUDA, no NVIDIA GPU). Everything must run on CPU.

---

## Environment

```bash
source venv/bin/activate          # always activate before running anything
python --version                  # should be 3.12.x
cranioscan --input x.mp4 --dry-run
make test
make lint
```

**Python:** 3.12 (open3d does not support 3.14, which is the system default on this machine)

**Key installed versions:**
- COLMAP 4.0.1 (via Homebrew, CPU-only)
- open3d 0.19.0
- opencv-python 4.13.0
- numpy 2.4.3
- PyQt5 5.15.11
- reportlab 4.4.10

**OpenMVS:** Built and installed to `.openmvs/bin/OpenMVS/`. All 4 required binaries present. Runtime requires `DYLD_LIBRARY_PATH=/opt/homebrew/lib` (set in `.env`, auto-injected by `utils/shell.py`). `.env` is loaded by `main()` on startup via `_load_dotenv()`.

---

## Project structure

```
src/cranioscan/
  pipeline.py          # CLI orchestrator — start here to understand flow
  config.py            # Config dataclass; all stages read from this
  extraction/          # Frame extraction (OpenCV) — IMPLEMENTED
  reconstruction/      # COLMAP sparse + undistort, OpenMVS dense — IMPLEMENTED
  mesh/                # Open3D mesh cleanup + scale (scale is stub) — IMPLEMENTED
  landmarks/           # Curvature + detection — STUBS (Month 3)
  measurement/         # Cranial indices (CI/CVAI done), report stub — PARTIAL
  gui/                 # PyQt5 landmark GUI — STUB (Month 3)
  utils/               # logging, shell runner, io, validation

configs/
  default.yaml         # Full quality
  fast.yaml            # Half resolution, no mesh refinement — use for dev

tests/                 # 53 tests, all synthetic data, no COLMAP needed
```

---

## Current status (as of 2026-03-17)

**Working:**
- 53/53 tests passing
- All 17 module imports OK
- Full pipeline dry-run verified
- COLMAP installed and on PATH
- Python venv set up with all dependencies

**Not yet working:**
- Stages 6–9 (scale, landmarks, measurement, report) are stubs raising `NotImplementedError`
- Pipeline not yet tested on real video — needs a physical object or head phantom recording

---

## How to run

```bash
source venv/bin/activate

# Dry run (no external tools needed):
cranioscan --input video.mp4 --dry-run

# Full pipeline:
cranioscan --input data/captures/session1.mp4 --output-dir data/results/session1

# Resume from a stage:
cranioscan --input video.mp4 --output-dir data/results/session1 --skip-to mesh

# Tests:
make test

# Verify everything:
bash scripts/run_quick_test.sh
```

---

## Coding conventions

- **No print statements** — use `logging.getLogger(__name__)` everywhere
- **Type hints** on all function signatures
- **Google-style docstrings** on all public functions and classes
- **Unimplemented stubs** raise `NotImplementedError("TODO: implement in Month N — description")`
- **No GPU code** anywhere — this machine has no CUDA
- All COLMAP subprocess calls must include `--SiftExtraction.use_gpu 0` and `--SiftMatching.use_gpu 0`
- External tool calls go through `utils/shell.py:run_command()` — never call `subprocess` directly
- Linter: `ruff` — run `make lint` before committing

---

## Setup quirks to be aware of

- **Python version:** Must use `python3.12`, not system `python3` (which is 3.14 on this machine). The venv was created with `python3.12 -m venv venv`.
- **pyproject.toml build backend:** Must be `setuptools.build_meta`, not `setuptools.backends.legacy:build` (the latter causes `BackendUnavailable` on Python 3.14's bundled pip).
- **OpenMVS CMake:** Requires `-DCMAKE_PREFIX_PATH=/opt/homebrew`, removal of `system` from Boost components (header-only since 1.74), and VCGLib cloned separately to `.build/vcglib`.
- **`make setup` can fail partway:** If OpenMVS build fails, the script now continues to set up the Python venv. If you see a working venv but no `.openmvs/bin/`, that's why.

---

## Data layout (all git-ignored)

```
data/
  captures/       Raw .mp4/.mov iPhone video files
  frames/         Extracted JPEG frames per session
  reconstructions/ COLMAP sparse models + OpenMVS dense outputs
  phantoms/       3D-printed phantom STL files + caliper ground truth
  results/        Final cleaned meshes + measurement JSON + PDF reports
```

Don't commit anything under `data/`. Don't commit `*.ply`, `*.obj`, `*.mvs`, `*.log`.
