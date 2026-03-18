# CranioScan3D — Decision & Session Log

Append-only log of architectural decisions, bugs found, things tried, and session summaries.
Most recent entry at the top.

---

## 2026-03-18 — Scale correction implemented; mesh quality improved

### What was done
Implemented Stage 6 (scale correction) and improved mesh post-processing quality. All 62 tests pass.

### Scale correction (mesh/scale.py)
Replaced the `NotImplementedError` stub with a full implementation:
- Loads the OpenMVS dense point cloud (`scene_dense.ply`)
- HSV colour segmentation isolates the reference object (presets: white, red, yellow, blue)
- DBSCAN clustering on the segmented cloud — eps = `bbox_diag * dbscan_eps_fraction` (self-normalising)
- Cluster filter: ≥50 points, isotropy ≥0.4 (cubic check), implied scale in [50, 2000] mm/unit
- Selects smallest surviving cluster by AABB volume; computes `scale_factor = reference_size_mm / long_dim`
- Applies scale to mesh by multiplying all vertex positions
- On detection failure: saves unscaled mesh with a warning rather than crashing

Verified on IMG_9840.MOV recording: white 16mm die detected from dense cloud, scale factor = 83.9167 mm/unit.

### Mesh post-processing improvements (mesh/processing.py)
Rewrote MeshProcessor with 6 explicit pipeline steps:
1. Mesh repair (remove duplicates, degenerate triangles, unreferenced vertices)
2. Statistical outlier removal (unchanged)
3. Poisson reconstruction with **adaptive normal radius**: `radius = bbox_diag × normal_radius_fraction` (1% of diagonal). Previously used a hardcoded absolute radius which produced incorrect normals if model units changed.
4. Density cutoff raised from 0.05 → **0.15** quantile (removes more Poisson hallucination artifacts)
5. Taubin smoothing (unchanged)
6. **Non-manifold edge removal** via `remove_non_manifold_edges()` — replaces planned `fill_holes()` which does not exist in Open3D 0.19

### New config: configs/clinical.yaml
Created for highest-quality clinical runs:
- `densify_resolution_level: 0` (full 4K depth maps)
- `poisson_depth: 10`
- `outlier_std_ratio: 1.5` (tighter)
- `refine_mesh: true`

### Open3D 0.19 limitation discovered
`fill_holes()` does not exist in Open3D 0.19. The `fill_holes` and `fill_hole_size` keys were in all three YAML configs causing "Unknown config key" warnings on every run. Removed from all configs and from `MeshConfig`.

### Commits this session
- `f36968a` — Improve mesh quality: adaptive normals, manifold repair, clinical config
- `8e58bff` — Remove stale fill_holes keys from all config files

### Test results (IMG_9840 re-run with new mesh processing)
- Input: 105,193 vertices / 210,253 triangles (from OpenMVS)
- Outlier removal: 3,120 points removed (3.0%)
- After Poisson (depth=9): 146,708 vertices / 279,777 triangles
- Non-manifold tris removed: 13
- Final: **146,649 vertices / 279,736 triangles**, watertight=False
- Scale factor confirmed: 83.9167 mm/unit (die detected, 434-point cluster)
- `watertight=False` expected for this recording — speaker has uncovered regions; a proper head scan with swim cap and full orbit should be closer to watertight

---

## 2026-03-18 — First full end-to-end pipeline run

### What was tested
Three iPhone videos (IMG_9837–9839.MOV) of a Bluetooth speaker with dice as scale
reference. Progressive failures led to finding and fixing 4 bugs, culminating in a
successful full pipeline run on IMG_9839.MOV.

### Bugs found and fixed (all committed in 1353f52)

| Stage | Bug | Fix |
|-------|-----|-----|
| sparse | `--SiftExtraction.use_gpu` unrecognised | COLMAP 4.x renamed to `--FeatureExtraction.use_gpu` / `--FeatureMatching.use_gpu` |
| undistort | `images.txt` not found | COLMAP 4.x writes binary format; updated check to accept `images.bin`, parse count from first 8 bytes (uint64) |
| dense | `cameras.bin` not found by InterfaceCOLMAP | `cwd=dense_dir` caused relative paths to resolve against wrong directory; fixed by resolving all paths to absolute |
| mesh | `mesh.ply` not found | Hardcoded fallback names didn't match OpenMVS outputs; fixed to search for `scene_dense_mesh_refine.ply` → `scene_dense_mesh.ply` |

### Results
- **COLMAP**: 83/83 images registered (100%), 5,842 points, reprojection error 0.70px
- **DensifyPointCloud**: 83 depth maps generated
- **ReconstructMesh**: 149,643 vertices / 299,090 triangles
- **Poisson + Taubin**: final mesh 317,847 vertices / 633,271 triangles
- Output: `data/results/test_IMG_9839/mesh/mesh_clean.ply` — viewable in MeshLab

### Known issues with this run
- First two videos (IMG_9837, IMG_9838) had severe motion blur (median Laplacian score
  8–10) caused by iPhone Enhanced Stabilisation being on. Fixed by disabling it.
- IMG_9839 had max blur score of 49.7 (vs 155 when EIS is truly off). Pipeline still
  worked but quality would be better with sharper frames.
- Background geometry (floor, laundry basket) was reconstructed alongside the object.
  Root cause: no plain background. Poisson creates a single unified watertight surface
  so software-only cleanup is not feasible — fix is at the recording stage.
- RefineMesh was skipped (OpenMVS did not produce `scene_dense_mesh.mvs`; only the PLY).
  Minor quality impact.

### Lessons for recording setup
- EIS must be **off** (Settings → Camera → Record Video → Enhanced Stabilisation → Off)
- Use a **plain white/grey background** (sheet, foam mat) to avoid background reconstruction
- Use a **textured subject** — the black speaker with uniform mesh texture is near-worst-case
  for SIFT. Hair, skin, shoes, fruit all have better texture.
- Tap-hold for AE/AF lock before pressing record

### Pipeline config used
`/tmp/debug.yaml`: `frame_interval=5`, `blur_threshold=20.0`, `resize_max_dim=1280`.
Default config (`default.yaml`) has `blur_threshold=100.0` which is correct for
well-recorded video; the permissive threshold was only needed due to EIS blur.

---

## 2026-03-17 — Session close: verification gap documented

### What was clarified
OpenMVS was confirmed to load and print version info (`DensifyPointCloud --help` returns
v2.4.0, CPU: Apple M4, RAM 16GB). However this is only a binary-presence check.

**The following have never been exercised end-to-end:**
- `reconstruction/dense.py` — wraps the InterfaceCOLMAP → DensifyPointCloud →
  ReconstructMesh → RefineMesh chain. Zero test coverage.
- `reconstruction/sparse.py` — wraps COLMAP feature extraction, exhaustive matching,
  and incremental mapper. Zero test coverage.
- `reconstruction/undistort.py` — wraps COLMAP image undistortion. Zero test coverage.

The 53 passing tests cover: frame extraction (mocked), mesh processing (synthetic Open3D
geometry), cranial indices (pure math), and input validation. No subprocess call is ever
made in the test suite.

### What needs to happen next
Record a test video (any ~15 cm round object — melon, ball, foam head) following
`docs/capture-protocol.md` and run the pipeline through `--stop-after sparse` first
to confirm COLMAP registers ≥ 80% of images, then through `--stop-after mesh` for a
full stages 1–5 run.

### Commits this session
- `1eb8c9f` — OpenMVS build complete: fix linker path, dotenv loading, DYLD_LIBRARY_PATH

### .gitignore
Added `.build/` and `.openmvs/` exclusions — these were accidentally staged before the
first commit attempt and had to be cleaned up.

---

## 2026-03-17 — OpenMVS build completed

### What was done
Completed the OpenMVS build from source on Apple Silicon. All 4 required binaries now present in `.openmvs/bin/OpenMVS/`.

### Issues encountered and fixed

**`ld: library 'jxl' not found`**
- Root cause: OpenCV 4.13 has a transitive dependency on `libjxl` (JPEG XL). The library is installed at `/opt/homebrew/lib/libjxl.dylib` but the linker couldn't find it because `-L/opt/homebrew/lib` was missing from the link command.
- Passing `-DCMAKE_EXE_LINKER_FLAGS="-L/opt/homebrew/lib"` to CMake did not work — the flag didn't propagate into the cached target link commands for imported OpenCV targets.
- **Fix:** Set `LIBRARY_PATH=/opt/homebrew/lib` as an environment variable when calling `cmake --build`. `LIBRARY_PATH` is respected by the macOS linker as an additional search path. Added to `setup_mac.sh`.

**Binaries installed to `bin/OpenMVS/` not `bin/`**
- OpenMVS installs to `$INSTALL_PREFIX/bin/OpenMVS/`, not `$INSTALL_PREFIX/bin/`.
- Fixed the `OPENMVS_BIN_DIR` path in `setup_mac.sh` and updated `.env`.

**Runtime: `libjxl` not found at runtime**
- Even after linking, OpenMVS binaries need `DYLD_LIBRARY_PATH=/opt/homebrew/lib` at runtime so macOS can find `libjxl.dylib`.
- **Fix:** Added `DYLD_LIBRARY_PATH=/opt/homebrew/lib` to `.env`. Added propagation of this variable in `utils/shell.py:run_command()` so all subprocess calls from the pipeline automatically have it set.

**`.env` not loaded by `cranioscan` CLI**
- The pipeline wasn't loading `.env`, so `OPENMVS_BIN_DIR` from `.env` wasn't reaching the config.
- **Fix:** Added `_load_dotenv()` call at the top of `main()` in `pipeline.py`. Simple implementation using stdlib only (no python-dotenv dependency).

### Current state
- OpenMVS binaries: `InterfaceCOLMAP`, `DensifyPointCloud`, `ReconstructMesh`, `RefineMesh`, `TextureMesh` — all built and installed
- `cranioscan --dry-run` confirms `openmvs_bin_dir` is correctly set to `.openmvs/bin/OpenMVS`
- `DYLD_LIBRARY_PATH` is automatically injected by `shell.py` for all subprocess calls
- 53/53 tests still passing

### Next steps
- Record a test video of a physical object and run the full pipeline stages 1–5
- Verify dense point cloud and mesh output quality

---

## 2026-03-17 — Initial scaffold + environment setup

### Decisions
- **COLMAP for sparse SfM** — CPU-only via `--SiftExtraction.use_gpu 0`. Installed via Homebrew (`colmap 4.0.1`).
- **OpenMVS for dense MVS** — COLMAP's dense module requires CUDA, unavailable on Apple Silicon. OpenMVS supports CPU-only dense reconstruction. Must be built from source.
- **Open3D for mesh processing** — Native ARM64 wheels; Poisson reconstruction + Taubin smoothing.
- **Python 3.12 for the venv** — `open3d 0.19.0` does not support Python 3.14 (system default on this machine). Venv created explicitly with `python3.12`.
- **`setuptools.build_meta` as build backend** — The scaffolded `pyproject.toml` incorrectly used `setuptools.backends.legacy:build`, which caused `BackendUnavailable` on Python 3.14's bundled pip. Fixed to `setuptools.build_meta`.
- **`set -euo pipefail` in setup_mac.sh made OpenMVS failures abort Python setup** — Fixed by wrapping the OpenMVS build block in an `if` guard so Python venv creation always runs even if OpenMVS build fails.

### OpenMVS CMake issues encountered and fixed
1. **`boost_system` not found** — Since Boost 1.74, `boost_system` is header-only. Homebrew 1.90.0 ships no `boost_systemConfig.cmake`. OpenMVS's CMakeLists.txt sets `CMP0167 NEW` which removes the old FindBoost fallback, making `-DBoost_NO_BOOST_CMAKE=ON` ineffective. **Fix:** Patched OpenMVS `CMakeLists.txt` line 238 to remove `system` from the `FIND_PACKAGE(Boost ...)` components list.
2. **CMake can't find Homebrew packages** — Apple Silicon Homebrew installs to `/opt/homebrew`, not `/usr/local`. **Fix:** Added `-DCMAKE_PREFIX_PATH=/opt/homebrew`.
3. **VCGLib not found** — OpenMVS depends on VCGLib but it is not a git submodule. **Fix:** Clone `https://github.com/cnr-isti-vclab/vcglib.git` separately to `.build/vcglib`; pass via `-DVCG_ROOT`.
4. **`nanoflann` not found** — Not installed by default. **Fix:** `brew install nanoflann`. Added to `setup_mac.sh`.

### Current state at end of session
- 53/53 pytest tests passing
- All 17 module imports OK
- Pipeline dry-run verified through all 9 stages
- COLMAP 4.0.1 working
- Python stack fully installed (open3d 0.19.0, opencv 4.13.0, numpy 2.4.3, scipy, PyQt5, reportlab)
- **OpenMVS: NOT yet built** — CMake configure was fixed but full build not yet completed

### Next session priorities
1. Complete OpenMVS build (run cmake build + install, verify binaries in `.openmvs/bin/`)
2. Run end-to-end test on a real video through stages 1–5
