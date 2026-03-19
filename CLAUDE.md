# CLAUDE.md — CranioScan3D

Context for Claude Code when working in this repository.

---

## What this project is

Master's thesis project. End-to-end pipeline that reconstructs a 3D model of an infant's head from iPhone video and extracts cranial measurements for craniosynostosis screening. Classical computer vision only — no ML anywhere.

**Hardware:** Mac Mini Apple Silicon (no CUDA, no NVIDIA GPU). Everything must run on CPU.

**Full system (thesis deliverable):**
1. **CranioCapture iOS app** — records guided orbit video, uploads to API, renders mesh with auto-detected landmarks (touch correction), shows measurements and PDF report in-app.
2. **CranioScan3D REST API** — FastAPI wrapping the existing pipeline; accepts video, returns mesh PLY + landmarks JSON + PDF report. Runs on Mac Mini.
3. **Pipeline (this codebase)** — API backend for stages 1–9.
4. **Desktop GUI (PyQt5)** — dev/debug tool only; not a production deliverable.

```
[CranioCapture iOS app]  →  [CranioScan3D REST API (FastAPI)]  →  [Pipeline stages 1–9]
```

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
  extraction/          # Frame extraction (OpenCV) — DONE
  reconstruction/      # COLMAP sparse + undistort, OpenMVS dense — DONE
  mesh/                # Open3D mesh cleanup + scale — DONE
  landmarks/           # Curvature + detection — STUBS (Month 3)
  measurement/         # CI/CVAI/AP/BW done; geodesic HC + report — STUBS (Month 3)
  gui/                 # PyQt5 landmark GUI — STUB (Month 3, dev tool only)
  utils/               # logging, shell runner, io, validation

api/                   # FastAPI REST API — Month 3–4 (not yet created)
  app.py               # FastAPI app with session endpoints
  sessions.py          # Session management, background processing

configs/
  default.yaml         # Full quality
  fast.yaml            # Half resolution, no mesh refinement — use for dev

tests/                 # 62 tests, all synthetic data, no COLMAP needed
```

**CranioCapture iOS app** lives in a separate Xcode project (Month 4). SwiftUI + SceneKit + URLSession.

---

## Current status (as of 2026-03-18)

**Working (end-to-end verified on real video 2026-03-18):**
- 62/62 tests passing
- Stages 1–6 fully exercised: extraction → sparse → undistort → dense → mesh → scale
- COLMAP 83/83 image registration on iPhone video of real object
- Full OpenMVS chain: InterfaceCOLMAP → DensifyPointCloud → ReconstructMesh
- Open3D mesh processing: repair → outlier removal → adaptive Poisson → Taubin → manifold cleanup
- Scale correction: white 16mm die detected from dense cloud, scale = 83.9167 mm/unit
- Pipeline correctly resumes from any stage with `--skip-to`

**Not yet working (Month 3):**
- Stage 7 (landmarks): curvature analysis + auto-detection — stubs in `landmarks/`
- Stage 8 (measurement): geodesic head circumference — stub in `measurement/cranial_indices.py`
- Stage 9 (report): PDF generation — stub in `measurement/report.py`
- RefineMesh (stage 4 of OpenMVS) skipped — OpenMVS does not produce `scene_dense_mesh.mvs`
  after ReconstructMesh; only the PLY is written. Minor quality impact.

**Not yet started:**
- REST API (`api/` module) — Month 3–4
- CranioCapture iOS app — Month 4

**Recording requirements (critical — verified through real testing):**
- iPhone **Enhanced Stabilisation must be off**: Settings → Camera → Record Video → Enhanced Stabilisation → Off
  This is the single most impactful setting. When on, it motion-blurs every frame and the pipeline
  produces fewer than 10 usable frames from a 1,564-frame video.
- **White swim cap required** for any subject with hair — hair has no SIFT texture and causes
  large, unrecoverable holes in the mesh
- Plain white/grey background — background geometry gets reconstructed and fused into the
  Poisson surface with no way to separate it automatically
- Textured subjects (skin, fabric, hair cap) reconstruct far better than smooth uniform-colour objects

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
- All COLMAP subprocess calls must include `--FeatureExtraction.use_gpu 0` and `--FeatureMatching.use_gpu 0` (COLMAP 4.x moved these from `SiftExtraction`/`SiftMatching` namespaces)
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
