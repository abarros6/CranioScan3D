# CranioScan3D

> **Master's thesis project** — End-to-end 3D cranial reconstruction and measurement pipeline for craniosynostosis screening. Classical computer vision only (no ML). Runs entirely on CPU on a Mac Mini Apple Silicon.

---

## Pipeline Overview

```
iPhone video (.mp4 / .mov)
        │
        ▼
┌───────────────────┐
│  1. extraction    │  OpenCV — sample frames, discard blurry (Laplacian)
└────────┬──────────┘
         │  sharp JPEG frames
         ▼
┌───────────────────┐
│  2. sparse SfM    │  COLMAP — SIFT extraction + exhaustive matching +
│                   │           incremental mapper  (CPU, no GPU)
└────────┬──────────┘
         │  cameras.bin / images.bin / points3D.bin
         ▼
┌───────────────────┐
│  3. undistort     │  COLMAP image_undistorter — rectilinear images +
│                   │           COLMAP-format sparse model for OpenMVS
└────────┬──────────┘
         │  undistorted images + sparse/
         ▼
┌───────────────────┐
│  4. dense MVS     │  OpenMVS — InterfaceCOLMAP → DensifyPointCloud →
│                   │            ReconstructMesh → RefineMesh (CPU only)
└────────┬──────────┘
         │  mesh.ply / mesh_refined.ply
         ▼
┌───────────────────┐
│  5. mesh clean    │  Open3D — statistical outlier removal, Poisson
│                   │           reconstruction, Taubin smoothing,
│                   │           component filtering
└────────┬──────────┘
         │  mesh_clean.ply
         ▼
┌───────────────────┐
│  6. scale ①       │  Reference cube detection → mm/unit factor
└────────┬──────────┘
         │  mesh_scaled.ply (metric units)
         ▼
┌───────────────────┐
│  7. landmarks ①   │  Curvature analysis + semi-auto GUI placement
└────────┬──────────┘
         │  landmarks.json
         ▼
┌───────────────────┐
│  8. measurement ① │  Cephalic Index, CVAI, AP length, head circumference
└────────┬──────────┘
         │  measurements.json
         ▼
┌───────────────────┐
│  9. report ①      │  ReportLab PDF — measurements + mesh screenshot
└───────────────────┘
         │
         ▼
  clinical_report.pdf

① = Month 2–4 implementation targets (stubs with defined interfaces)
```

---

## Hardware Requirements

| Component | Specification |
|-----------|--------------|
| Machine | Mac Mini, Apple Silicon (M1/M2/M3) |
| RAM | 16 GB minimum, 32 GB recommended |
| Storage | 50 GB free (per session: ~2 GB raw video, ~5 GB reconstruction) |
| GPU | **None required** — fully CPU pipeline |
| Capture | iPhone 12 or later, 4K 30fps |

---

## Quick Start

### 1. Setup

```bash
git clone <repo-url> CranioScan3D
cd CranioScan3D
make setup          # Installs COLMAP, builds OpenMVS, creates venv
source venv/bin/activate
```

### 2. Verify installation

```bash
bash scripts/run_quick_test.sh
```

### 3. Record a video

Follow the protocol in [scripts/capture_guide.md](scripts/capture_guide.md).

### 4. Run the pipeline

```bash
cranioscan \
  --input data/captures/SCN001/SCN001_20240315.mp4 \
  --output-dir data/results/SCN001 \
  --config configs/default.yaml
```

### 5. Resume from a stage

```bash
# Re-run just the dense reconstruction and everything after:
cranioscan \
  --input data/captures/SCN001/SCN001_20240315.mp4 \
  --output-dir data/results/SCN001 \
  --skip-to dense
```

### 6. Dry run (no COLMAP/OpenMVS required)

```bash
cranioscan --input video.mp4 --dry-run
```

---

## Directory Structure

```
CranioScan3D/
├── src/cranioscan/          Python package
│   ├── pipeline.py          CLI orchestrator (--skip-to, --stop-after, --dry-run)
│   ├── config.py            Dataclass config, YAML loading
│   ├── extraction/          Frame extraction (OpenCV)
│   ├── reconstruction/      COLMAP sparse + undistort, OpenMVS dense
│   ├── mesh/                Open3D post-processing + scale correction
│   ├── landmarks/           Curvature analysis + semi-auto detection
│   ├── measurement/         Cranial indices + PDF report
│   ├── gui/                 PyQt5 interactive landmark GUI
│   └── utils/               Logging, shell runner, I/O, validation
├── configs/
│   ├── default.yaml         Full-quality pipeline settings
│   └── fast.yaml            Reduced-quality for rapid iteration
├── scripts/
│   ├── setup_mac.sh         macOS Apple Silicon setup (Homebrew + venv)
│   ├── capture_guide.md     iPhone recording protocol
│   └── run_quick_test.sh    Smoke test + pytest runner
├── tests/                   pytest suite (synthetic data, no COLMAP needed)
├── data/
│   ├── captures/            Raw iPhone video files (git-ignored)
│   ├── frames/              Extracted frames (git-ignored)
│   ├── reconstructions/     COLMAP + OpenMVS outputs (git-ignored)
│   ├── results/             Final meshes + measurements (git-ignored)
│   └── phantoms/            Physical phantom scans for validation
└── docs/                    Architecture, landmark definitions, protocol
```

---

## Configuration

Two YAML configs are provided. Pass with `--config`:

| Config | Frame interval | Resolution | Refine mesh | Use for |
|--------|---------------|------------|-------------|---------|
| `configs/default.yaml` | 15 | Full (4K) | Yes | Clinical capture |
| `configs/fast.yaml` | 30 | Half (1280px) | No | Development / testing |

Override individual keys via code:
```python
cfg = Config.from_yaml("configs/default.yaml", overrides={"mesh.poisson_depth": 8})
```

---

## Development

```bash
# Run tests
make test

# Run linter
make lint

# Run tests with coverage
python -m pytest tests/ -v --cov=src/cranioscan --cov-report=term-missing
```

---

## Pipeline Stages and Implementation Status

| Stage | Status | Module |
|-------|--------|--------|
| Frame extraction | Implemented | `extraction/frame_extractor.py` |
| Sparse SfM (COLMAP) | Implemented | `reconstruction/sparse.py` |
| Undistortion (COLMAP) | Implemented | `reconstruction/undistort.py` |
| Dense MVS (OpenMVS) | Implemented | `reconstruction/dense.py` |
| Mesh post-processing | Implemented | `mesh/processing.py` |
| Scale correction | Stub (Month 2) | `mesh/scale.py` |
| Landmark detection | Stub (Month 3) | `landmarks/detector.py` |
| Cranial index computation | Partially implemented | `measurement/cranial_indices.py` |
| Head circumference | Stub (Month 3) | `measurement/cranial_indices.py` |
| PDF report | Stub (Month 4) | `measurement/report.py` |
| Landmark GUI | Stub (Month 3) | `gui/landmark_gui.py` |

---

## Key Design Decisions

See [docs/pipeline-architecture-justification.md](docs/pipeline-architecture-justification.md) for full rationale. In brief:

- **COLMAP for sparse SfM**: Best-in-class open-source SfM with reliable Apple Silicon support via Homebrew. `--SiftExtraction.use_gpu 0` disables CUDA.
- **OpenMVS for dense MVS**: CPU-capable dense reconstruction; better mesh quality than COLMAP's built-in dense mode.
- **Open3D for mesh processing**: Native ARM64 Python wheels; excellent Poisson reconstruction and Taubin smoothing.
- **No ML**: Eliminates GPU dependency, simplifies clinical validation pathway, and is sufficient for structured-light-free cranial measurement.
- **SIMPLE_RADIAL camera model**: iPhone video shares identical intrinsics across all frames (`single_camera=1`); SIMPLE_RADIAL handles the mild barrel distortion of iPhone wide-angle lenses.

---

## Clinical Context

Craniosynostosis is the premature fusion of one or more cranial sutures, affecting ~1 in 2500 live births. Early diagnosis (ideally before 6 months) enables minimally invasive surgical intervention. Current gold standard is CT scan, which carries ionising radiation risk in infants. CranioScan3D aims to provide a radiation-free, low-cost screening tool that can be used in outpatient or community settings with only an iPhone.

**Key measurements:**
- **Cephalic Index (CI)**: Head width / AP length × 100. Normal 75–85. Elevated in brachycephaly (coronal synostosis).
- **Cranial Vault Asymmetry Index (CVAI)**: Diagonal asymmetry. <3.5% normal. Elevated in plagiocephaly (unilateral lambdoid or coronal synostosis).
- **Head circumference**: Geodesic arc around the cranium. Compared to age-adjusted normative data.

---

## Landmark Definitions

See [docs/landmark-definitions.md](docs/landmark-definitions.md) for clinical descriptions and 3D detection strategy for each of the nine craniometric landmarks used in this pipeline.

---

## License

Academic research use only. Not for clinical diagnosis without independent validation. See thesis for full methodology and limitations.
