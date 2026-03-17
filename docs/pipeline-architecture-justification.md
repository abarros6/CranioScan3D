# Pipeline Architecture Justification

## Overview

CranioScan3D uses a classical computer-vision pipeline deliberately constructed
to avoid any machine-learning model. This document justifies each architectural
decision in terms of the project's hardware constraints (Mac Mini Apple Silicon,
CPU-only), clinical requirements (measurement accuracy ≤2mm, no ionising
radiation), and practical constraints (open-source tooling, reproducibility).

---

## 1. Why Classical CV, Not Deep Learning?

### 1.1 Hardware constraint: no NVIDIA GPU

The development and deployment machine is a Mac Mini with Apple Silicon (M1/M2/M3).
No CUDA-compatible GPU is available. The majority of high-quality neural 3D
reconstruction methods (NeRF variants, Instant NGP, 3D Gaussian Splatting,
MonoSDF, etc.) require CUDA for any reasonable inference speed. Metal Performance
Shaders (MPS) support in PyTorch is improving but remains incomplete for the
custom CUDA kernels used by these frameworks as of 2024.

### 1.2 Clinical validation pathway

Any method used in a medical device must be independently validated against a
ground truth. Classical photogrammetry pipelines (COLMAP + MVS) have decades of
published benchmarks and error characterisation. The full processing chain is
deterministic given the same inputs. Deep learning models introduce distributional
shift concerns (model trained on adult heads, deployed on infant heads) and
opaque failure modes that complicate medical device approval.

### 1.3 Sufficient accuracy for the task

For craniosynostosis screening, the clinically relevant measurements (cephalic
index, CVAI) require spatial accuracy of approximately ±1–2 mm. Literature on
photogrammetric cranial measurement (e.g., Aldridge et al. 2005, Metzler et al.
2021) demonstrates that structured-light-free MVS achieves this accuracy on
infant head phantoms under controlled lighting. Deep learning does not offer a
meaningful accuracy advantage here.

---

## 2. Frame Extraction: OpenCV Laplacian Blur Detection

### Choice
Sample every Nth frame (configurable), reject frames below a Laplacian variance
threshold.

### Rationale
- iPhone 4K video at 30fps yields ~1800 frames for a 60-second orbit.
  Using all frames would slow COLMAP's O(n²) exhaustive matching prohibitively.
- Laplacian variance is fast (< 1ms/frame on CPU), well-characterised, and
  robust to the motion blur caused by capture-speed variations.
- A threshold of ~100 (default) empirically retains frames with sub-pixel
  projected feature motion, appropriate for SIFT reliability.

### Alternative considered
Optical flow-based frame selection. Rejected: more complex, slower, no
meaningful quality improvement for this use case.

---

## 3. Sparse SfM: COLMAP

### Choice
COLMAP with `--SiftExtraction.use_gpu 0` and `--SiftMatching.use_gpu 0`.

### Rationale
- **Apple Silicon support**: COLMAP is available via Homebrew and runs natively
  on arm64. GPU acceleration uses CUDA, which is unavailable; CPU fallback is
  fully supported.
- **SIMPLE_RADIAL model**: iPhone video uses a fixed focal length per session.
  Setting `single_camera=1` constrains all frames to share intrinsics, which
  improves robustness when self-calibration is needed.
- **Exhaustive matching**: For ≤200 images (typical for a 60-second orbit at
  every-15th-frame), exhaustive matching is tractable (~20,000 pairs) and gives
  better recall than sequential or vocabulary-tree matching for orbital captures
  where loop closure is critical.
- **Incremental mapper**: More robust than global SfM for unordered iPhone
  captures with potential coverage gaps.

### Alternative considered
OpenSfM (Python, more configurable). Rejected: slower on CPU, less mature
incremental reconstruction, more complex Apple Silicon installation.

---

## 4. Image Undistortion: COLMAP image_undistorter

### Choice
COLMAP's built-in `image_undistorter` with `--output_type COLMAP`.

### Rationale
- Produces rectilinear images and a COLMAP-format text model that is the
  standard input format for OpenMVS's `InterfaceCOLMAP`.
- Uses the same distortion model parameters that COLMAP estimated during SfM,
  ensuring consistency between the sparse model and the undistorted images.
- Zero additional dependencies.

---

## 5. Dense Reconstruction: OpenMVS

### Choice
OpenMVS pipeline: InterfaceCOLMAP → DensifyPointCloud → ReconstructMesh →
RefineMesh (optional).

### Rationale
- **CPU-capable**: OpenMVS's DensifyPointCloud uses patch-match MVS with CPU
  multi-threading via OpenMP. No CUDA required.
- **Quality**: OpenMVS consistently outperforms COLMAP's dense module (patch
  match stereo) on the ETH3D and DTU benchmarks for smooth organic surfaces
  (like a head) due to its global point cloud fusion step.
- **Mesh quality**: ReconstructMesh uses a Delaunay tetrahedralisation that
  produces cleaner manifold meshes than COLMAP's dense output (which is a point
  cloud requiring separate meshing).
- **Apple Silicon build**: OpenMVS builds cleanly from source with CMake and
  `-DOpenMVS_USE_CUDA=OFF`. VCG library is bundled; dependencies (Eigen, CGAL,
  Boost, OpenCV) are all available via Homebrew.

### Alternative considered
COLMAP dense (patch match stereo). Rejected: lower quality on smooth surfaces,
no built-in meshing step, also CPU-capable but not better.

AliceVision / Meshroom. Rejected: harder to build on Apple Silicon, less
modular command-line interface.

---

## 6. Mesh Post-Processing: Open3D

### Choice
Statistical outlier removal → Poisson surface reconstruction → Taubin smoothing
→ small component removal.

### Rationale
- **Open3D on Apple Silicon**: Official arm64 Python wheels are available via
  pip since Open3D 0.17. No compilation needed.
- **Poisson reconstruction**: Watertight mesh output is essential for reliable
  geodesic distance computation (head circumference) and for the landmark GUI to
  display a closed surface.
- **Taubin smoothing**: Volume-preserving (unlike Laplacian smoothing) — critical
  for measurement accuracy. Does not shrink the mesh.
- **Statistical outlier removal**: Reconstructed point clouds from MVS contain
  floating outliers from background textures. Removing them before Poisson
  reconstruction prevents bridge-like artefacts across the face/background
  boundary.

### Poisson depth parameter
Default depth=9 gives ~512³ grid resolution, appropriate for a ~20cm head
requiring sub-millimetre surface detail. `fast.yaml` uses depth=8 (half
spatial resolution) for quicker iteration.

---

## 7. Scale Correction: Reference Object (Month 2)

### Choice
Physical calibration cube (10mm) placed in the capture scene.

### Rationale
- SfM reconstruction is inherently scale-ambiguous: COLMAP recovers structure
  up to an unknown scale factor. A known-size physical object in the scene
  allows unambiguous metric scale recovery.
- A brightly coloured 3D-printed cube is easy to segment in the point cloud or
  mesh using colour thresholding.
- Alternative (marker-based scale): ArUco marker with known side length. Also
  viable, but requires the marker to be flat and visible — harder to attach to
  an infant's head without disturbing the capture.
- Alternative (LIDAR iPhone): iPhone Pro models have a LiDAR sensor providing
  absolute depth. However, we target iPhone 12+ (non-Pro) for broader
  accessibility.

---

## 8. Landmark Detection: Curvature + Semi-Auto GUI (Month 3)

### Choice
Curvature-based suggestion (shape index) + operator confirmation via PyQt5 GUI.

### Rationale
- **Fully automatic**: On a perfectly clean head mesh, convex extrema of the
  shape index reliably correspond to glabella, opisthocranion, and vertex.
  However, hair, infant hats, or reconstruction artefacts can displace these
  extrema. A fully automatic method would silently produce incorrect landmarks.
- **Semi-automatic**: Curvature suggestions reduce operator burden from placing
  9 landmarks from scratch to confirming or slightly adjusting suggested positions.
  This is the standard workflow in clinical photogrammetry systems.
- **PyQt5 + Open3D**: Open3D provides `VisualizerWithEditing.get_picked_points()`
  for 3D click picking. PyQt5 wraps this in a proper application window with
  checklist and measurement preview panels.

### Why not a web-based GUI?
Web-based 3D viewers (Three.js, Babylon.js) would require a local server and add
JavaScript complexity. For a single-operator clinical tool, a native desktop GUI
is simpler and more reliable.

---

## 9. Measurement: Classical Geometry

All measurements (cephalic index, CVAI, AP length, bitemporal width, head
circumference) are computed as Euclidean distances or ratios between 3D
landmark coordinates. These are deterministic, algebraically verifiable, and
directly comparable to the clinical literature that defines their normal ranges.

Head circumference via geodesic path (Month 3) requires Dijkstra's algorithm
on the mesh graph, implemented via trimesh or NetworkX — no ML involved.

---

## 10. Report: ReportLab PDF (Month 4)

ReportLab is a pure-Python PDF generation library with no system dependencies.
It produces clinical-grade tabular output with custom layouts, which is more
appropriate for a medical workflow than a Jupyter notebook or HTML report.

---

## Summary

| Stage | Tool | CPU-only? | Apple Silicon wheel/binary? |
|-------|------|-----------|----------------------------|
| Frame extraction | OpenCV | Yes | Yes (pip) |
| Sparse SfM | COLMAP | Yes (via flag) | Yes (Homebrew) |
| Undistortion | COLMAP | Yes | Yes (Homebrew) |
| Dense MVS | OpenMVS | Yes (no CUDA) | Yes (build from source) |
| Mesh processing | Open3D | Yes | Yes (pip, arm64 wheel) |
| Scale correction | Custom (OpenCV) | Yes | Yes |
| Landmarks | Open3D + PyQt5 | Yes | Yes |
| Measurement | NumPy | Yes | Yes |
| Report | ReportLab | Yes | Yes (pip) |
