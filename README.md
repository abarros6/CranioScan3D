# CranioScan3D

> **Master's thesis project** — End-to-end 3D cranial reconstruction and measurement pipeline for craniosynostosis screening. Classical computer vision only (no ML). Runs entirely on CPU on a Mac Mini Apple Silicon.

---

## Clinical Context

Craniosynostosis is the premature fusion of one or more cranial sutures, affecting ~1 in 2,500 live births. Early diagnosis (before 6 months) is critical for minimally invasive surgical intervention. The current diagnostic gold standard is CT scanning, which carries ionising radiation risk in infants. CranioScan3D aims to provide a radiation-free, low-cost screening tool using only an iPhone and a Mac.

**Key measurements:**

| Measurement | Formula | Normal range | Clinical significance |
|-------------|---------|--------------|----------------------|
| Cephalic Index (CI) | width / AP length × 100 | 75–85 | <75 dolichocephaly, >85 brachycephaly |
| Cranial Vault Asymmetry Index (CVAI) | \|d1 − d2\| / d1 × 100 | <3.5% | Elevated in plagiocephaly |
| AP length | glabella → opisthocranion | — | Sagittal diameter |
| Bitemporal width | eurion L → eurion R | — | Transverse diameter |
| Head circumference | Geodesic arc on mesh | Age-adjusted | Overall cranial growth |

---

## Pipeline Architecture

```
iPhone video (.mp4 / .mov)
        │
        ▼
┌───────────────────┐
│  1. extraction    │  OpenCV — sample frames every N frames,
│                   │           discard blurry (Laplacian variance)
└────────┬──────────┘
         │  sharp JPEG frames
         ▼
┌───────────────────┐
│  2. sparse SfM    │  COLMAP — SIFT feature extraction + exhaustive
│                   │           matching + incremental mapper (CPU only)
└────────┬──────────┘
         │  cameras.bin / images.bin / points3D.bin
         ▼
┌───────────────────┐
│  3. undistort     │  COLMAP image_undistorter — rectilinear images
│                   │           + COLMAP-format sparse model for OpenMVS
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
│                   │           surface reconstruction, Taubin smoothing,
│                   │           small-component filtering
└────────┬──────────┘
         │  mesh_clean.ply
         ▼
┌───────────────────┐
│  6. scale ①       │  Reference object detection → mm/unit scale factor
└────────┬──────────┘
         │  mesh_scaled.ply (metric units)
         ▼
┌───────────────────┐
│  7. landmarks ①   │  Curvature analysis (shape index) +
│                   │           semi-automatic GUI placement
└────────┬──────────┘
         │  landmarks.json
         ▼
┌───────────────────┐
│  8. measurement ① │  Cephalic Index, CVAI, AP length,
│                   │           head circumference (geodesic arc)
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
| Machine | Mac Mini, Apple Silicon (M1/M2/M3/M4) |
| RAM | 16 GB minimum, 32 GB recommended |
| Storage | ~50 GB free (per session: ~2 GB raw video, ~5 GB reconstruction) |
| GPU | **None required** — fully CPU pipeline |
| Capture device | iPhone 12 or later (4K 30fps recommended) |

---

## Setup

### Prerequisites

- macOS 13+
- [Homebrew](https://brew.sh/)
- Xcode Command Line Tools (`xcode-select --install`)

### Install

```bash
git clone <repo-url> CranioScan3D
cd CranioScan3D
bash scripts/setup_mac.sh
source venv/bin/activate
```

`setup_mac.sh` will:
1. Install COLMAP via Homebrew
2. Install OpenMVS build dependencies (`cmake`, `eigen`, `opencv`, `boost`, `cgal`, `glog`, `nanoflann`)
3. Clone [OpenMVS](https://github.com/cdcseacave/openMVS) and [VCGLib](https://github.com/cnr-isti-vclab/vcglib) from source
4. Build OpenMVS with CPU-only flags
5. Create a Python **3.12** virtual environment (`open3d` requires Python ≤ 3.12)
6. Install all Python dependencies via pip

> **Note on OpenMVS:** Building on Apple Silicon requires several CMake workarounds (see [OpenMVS Build Notes](#openmvs-build-notes)). If the build fails, the script continues and finishes the Python setup — stages 1–3 and 5 work without OpenMVS.

### Verify

```bash
bash scripts/run_quick_test.sh
```

Expected: `All 4 checks PASSED` — imports, config loading, 62 pytest tests, and a pipeline dry-run.

---

## Usage

Activate the venv first:

```bash
source venv/bin/activate
```

### Full pipeline

```bash
cranioscan \
  --input data/captures/session1.mp4 \
  --output-dir data/results/session1 \
  --config configs/default.yaml
```

### Fast config (for development)

```bash
cranioscan \
  --input data/captures/session1.mp4 \
  --output-dir data/results/session1 \
  --config configs/fast.yaml
```

`fast.yaml` uses half resolution, fewer frames, and skips mesh refinement — significantly faster for iteration.

### Dry run (no COLMAP/OpenMVS needed)

```bash
cranioscan --input video.mp4 --dry-run
```

### Resume or isolate a single stage

```bash
# Re-run from dense reconstruction onward:
cranioscan --input session1.mp4 --output-dir data/results/session1 --skip-to dense

# Run only mesh processing:
cranioscan --input session1.mp4 --output-dir data/results/session1 \
  --skip-to mesh --stop-after mesh
```

Available stages: `extraction` → `sparse` → `undistort` → `dense` → `mesh` → `scale` → `landmarks` → `measurement` → `report`

### Configuration

| Config | Frame interval | Camera model | Dense resolution | Poisson depth | Refine mesh | Use for |
|--------|---------------|--------------|-----------------|---------------|-------------|---------|
| `configs/clinical.yaml` | every 5 frames | OPENCV | full 4K | 11 | yes | Final clinical measurements |
| `configs/default.yaml` | every 6 frames | OPENCV (k1,k2,p1,p2) | full 4K | 11 | yes | Standard quality runs |
| `configs/fast.yaml` | every 30 frames | RADIAL | 1280px max | 8 | no | Development / quick iteration |

Override individual keys in code:
```python
cfg = Config.from_yaml("configs/default.yaml", overrides={"mesh.poisson_depth": 8})
```

---

## Development

```bash
make test          # run pytest
make lint          # run ruff
make clean         # remove generated data and build artifacts

# With coverage:
venv/bin/python -m pytest tests/ -v --cov=src/cranioscan --cov-report=term-missing
```

Tests use fully synthetic data — no COLMAP or OpenMVS installation required.

---

## Implementation Status

| Stage | Module | Status |
|-------|--------|--------|
| Frame extraction | `extraction/frame_extractor.py` | Implemented |
| Sparse SfM (COLMAP 4.0.1) | `reconstruction/sparse.py` | Implemented |
| Undistortion (COLMAP) | `reconstruction/undistort.py` | Implemented |
| Dense MVS (OpenMVS) | `reconstruction/dense.py` | Implemented — requires OpenMVS binary |
| Mesh post-processing (Open3D 0.19) | `mesh/processing.py` | Implemented |
| Scale correction | `mesh/scale.py` | Implemented — DBSCAN-based colour detection |
| Curvature analysis | `landmarks/curvature.py` | **Stub — Month 3** |
| Landmark detection + GUI | `landmarks/detector.py`, `gui/landmark_gui.py` | **Stub — Month 3** |
| Cranial indices (CI, CVAI, AP, width) | `measurement/cranial_indices.py` | Implemented |
| Head circumference (geodesic) | `measurement/cranial_indices.py` | **Stub — Month 3** |
| PDF report | `measurement/report.py` | **Stub — Month 4** |

**Current verified state (2026-03-19):**
- 62/62 pytest tests passing
- All 17 module imports OK
- Pipeline dry-run verified through all 9 stages
- Stages 1–6 verified end-to-end on real iPhone video (IMG_9840.MOV)
  - COLMAP: 83/83 images registered, 5,842 points
  - Dense: 244,201 point cloud
  - Mesh: 146,649 vertices / 279,736 triangles
  - Scale: white 16mm die detected, scale factor = 83.9167 mm/unit
- COLMAP 4.0.1 installed (CPU-only, no CUDA)
- Python stack: open3d 0.19.0, opencv 4.13.0, numpy 2.4.3, scipy, PyQt5, reportlab
- OpenMVS: built and installed to `.openmvs/bin/OpenMVS/`

---

## OpenMVS Build Notes

OpenMVS must be built from source on Apple Silicon. `setup_mac.sh` handles this automatically, but several workarounds are required:

| Issue | Fix |
|-------|-----|
| CMake can't find Homebrew packages | `-DCMAKE_PREFIX_PATH=/opt/homebrew` |
| `boost_system` has no CMake config file (header-only since Boost 1.74, Homebrew 1.90) | Patch OpenMVS `CMakeLists.txt` to remove `system` from `FIND_PACKAGE(Boost ...)` |
| VCGLib is not a git submodule | Clone [vcglib](https://github.com/cnr-isti-vclab/vcglib) separately; pass via `-DVCG_ROOT` |
| `nanoflann` not installed by default | `brew install nanoflann` |
| CUDA unavailable | `-DOpenMVS_USE_CUDA=OFF` (also set automatically by OpenMVS on macOS) |

To retry the OpenMVS build after a failure:

```bash
rm -rf .build/openMVS_build
bash scripts/setup_mac.sh
```

---

## Project Structure

```
CranioScan3D/
├── src/cranioscan/          Python package (pip install -e ".[dev]")
│   ├── pipeline.py          CLI entry point: cranioscan --input ...
│   ├── config.py            Dataclass config + YAML loading
│   ├── extraction/          Frame extraction (OpenCV)
│   ├── reconstruction/      COLMAP sparse + undistort; OpenMVS dense
│   ├── mesh/                Open3D post-processing + scale correction
│   ├── landmarks/           Curvature analysis + detection coordinator
│   ├── measurement/         Cranial indices + PDF report generator
│   ├── gui/                 PyQt5 interactive landmark placement GUI
│   └── utils/               Logging, subprocess runner, I/O, validation
├── configs/
│   ├── clinical.yaml        Highest quality (full-res, Poisson depth 10)
│   ├── default.yaml         Full-quality pipeline parameters
│   └── fast.yaml            Reduced-quality for rapid iteration
├── scripts/
│   ├── setup_mac.sh         Full macOS Apple Silicon setup script
│   ├── capture_guide.md     iPhone recording protocol
│   └── run_quick_test.sh    Smoke test + pytest runner
├── tests/                   62 pytest tests, synthetic data only
├── docs/
│   ├── pipeline-architecture-justification.md
│   ├── landmark-definitions.md
│   └── capture-protocol.md
└── data/                    Git-ignored
    ├── captures/            Raw iPhone video
    ├── frames/              Extracted frames
    ├── reconstructions/     COLMAP + OpenMVS intermediate outputs
    ├── phantoms/            Physical phantom STL files + caliper measurements
    └── results/             Final meshes + measurement reports
```

---

## Key Design Decisions

See [`docs/pipeline-architecture-justification.md`](docs/pipeline-architecture-justification.md) for full rationale.

- **COLMAP for sparse SfM** — Best-in-class open-source SfM with Apple Silicon support via Homebrew. CPU-only via `--FeatureExtraction.use_gpu 0` and `--FeatureMatching.use_gpu 0` (COLMAP 4.x renamed these flags from `SiftExtraction`/`SiftMatching`) ([Schönberger & Frahm, 2016](#references); [Schönberger et al., 2016](#references)).
- **OpenMVS for dense MVS** — CPU-capable dense reconstruction producing watertight meshes. COLMAP's own dense module requires CUDA and is therefore unavailable on this hardware ([Cernea, 2020](#references)).
- **Open3D for mesh processing** — Native ARM64 Python wheels; Screened Poisson surface reconstruction ([Kazhdan & Hoppe, 2013](#references)) and volume-preserving Taubin smoothing ([Taubin, 1995](#references)).
- **SIMPLE_RADIAL camera model** — iPhone video frames share identical intrinsics (`single_camera=1`); SIMPLE_RADIAL handles mild iPhone wide-angle barrel distortion without overparameterisation.
- **No ML** — Eliminates GPU dependency, simplifies the clinical validation pathway, and is sufficient for controlled iPhone photogrammetry ([Khambay et al., 2008](#references)).
- **Koenderink shape index for landmark suggestion** — SI = (2/π) arctan((k₁+k₂)/(k₁−k₂)) classifies surface geometry from concave cup (−1) to convex dome (+1); cranial landmarks occur at convex extrema ([Koenderink & van Doorn, 1992](#references)).

---

## Landmark Set

See [`docs/landmark-definitions.md`](docs/landmark-definitions.md) for clinical definitions and 3D detection strategy. Nine craniometric landmarks are defined:

`glabella` · `opisthocranion` · `eurion_l` · `eurion_r` · `vertex` · `bregma` · `lambda` · `nasion` · `metopion`

---

## iPhone Capture Protocol

See [`docs/capture-protocol.md`](docs/capture-protocol.md) for the full protocol. Quick summary:
- **White swim cap required** for any subject with hair — hair has no trackable texture
- 30–40 cm distance from subject's head
- Slow, full 360° equatorial orbit + crown pass (~80–150 sharp frames)
- **Enhanced Stabilisation must be off** (Settings → Camera → Record Video → Enhanced Stabilisation)
- Place a **standard 16mm white die** adjacent to the subject for scale correction
- Even diffuse lighting — no harsh shadows or specular highlights

---

## References

- Schönberger, J.L., Frahm, J.M. (2016). *Structure-from-Motion Revisited.* CVPR. https://demuc.de/papers/schoenberger2016sfm.pdf
- Schönberger, J.L., et al. (2016). *Pixelwise View Selection for Unstructured Multi-View Stereo.* ECCV. https://demuc.de/papers/schoenberger2016mvs.pdf
- Cernea, D. (2020). *OpenMVS: Multi-View Stereo Reconstruction Library.* https://github.com/cdcseacave/openMVS
- Zhou, Q.Y., Park, J., Koltun, V. (2018). *Open3D: A Modern Library for 3D Data Processing.* arXiv:1801.09847. https://arxiv.org/abs/1801.09847
- Kazhdan, M., Hoppe, H. (2013). *Screened Poisson Surface Reconstruction.* ACM TOG 32(3). https://hhoppe.com/poissonrecon.pdf
- Taubin, G. (1995). *A Signal Processing Approach to Fair Surface Design.* SIGGRAPH. https://dl.acm.org/doi/10.1145/218380.218473
- Koenderink, J.J., van Doorn, A.J. (1992). *Surface shape and curvature scales.* Image and Vision Computing 10(8). https://doi.org/10.1016/0262-8856(92)90076-F
- Loveday, E.N., de Chalain, T.B. (2001). *Active helmet therapy or surgery for isolated sagittal synostosis?* Journal of Craniofacial Surgery 12(4).
- Plank, L.H., et al. (2006). *A 3-dimensional morphometric analysis of isolated metopic synostosis.* Journal of Neurosurgery: Pediatrics 105(2).
- Khambay, B., et al. (2008). *Validation and reproducibility of a high-resolution three-dimensional facial imaging system.* British Journal of Oral and Maxillofacial Surgery. https://pubmed.ncbi.nlm.nih.gov/18450436/

---

## License

Academic research use only. Not for clinical diagnosis without independent validation.
