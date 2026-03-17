# Capture Protocol — CranioScan3D Clinical Use

## Purpose

This document defines the standard operating procedure (SOP) for recording
iPhone video suitable for CranioScan3D 3D reconstruction. It is intended for
trained clinical staff and should be read in conjunction with
`scripts/capture_guide.md` (operator quick reference).

---

## 1. Patient Preparation

### 1.1 Eligibility

CranioScan3D is designed for infants aged 0–18 months presenting for
craniosynostosis screening or follow-up. The pipeline is not validated for
older children or adults (different scalp texture, hair coverage).

### 1.2 Hair and scalp preparation

- Remove any hat, headband, or hair clip before capture.
- If hair is present: part it to expose as much scalp as possible. Dense
  hair significantly reduces MVS point cloud quality because it creates
  occluded, textureless regions.
- If the infant has minimal hair (common under 3 months): no preparation needed.

### 1.3 Infant positioning

**Supine on padded support (preferred):**
- Place the infant on a white or light-grey padded foam support that allows
  the operator to walk a full 360° orbit.
- Ensure the head is gently supported but free to be viewed from all angles.

**Held by caregiver:**
- Caregiver holds infant in front-facing position.
- Operator walks orbit around caregiver and infant.
- Slightly more difficult to achieve full posterior coverage.

---

## 2. Environment Setup

### 2.1 Lighting

| Setup | Acceptable? | Notes |
|-------|-------------|-------|
| Two diffuse softboxes, 45° bilateral | Optimal | Best for even illumination |
| North-facing window (overcast) | Good | Soft diffuse daylight |
| Overhead fluorescent (clinic standard) | Marginal | May cause specular on bare scalp |
| Direct sunlight | Unacceptable | Harsh shadows break MVS |
| Single point light source | Unacceptable | Half the head will be too dark |

Target lighting level: subject illumination 300–800 lux at the head surface.
Check iPhone preview: the scalp should show visible skin texture, not be
washed out (overexposed) or under-lit.

### 2.2 Background

Place a light-grey or white cloth behind and below the infant's head. This
gives COLMAP features to distinguish the head from the background (needed for
correct camera pose estimation) while avoiding distracting patterns.

Avoid: toys, patterned blankets, or other heads/faces in the frame.

### 2.3 Calibration cube placement

Attach the 10×10×10mm calibration cube to the foam support, positioned so
it is visible at approximately 40–50% of orbit positions. Recommended
placement: lateral to the infant's ear, at head height. Use a small piece of
non-permanent adhesive to secure it.

The cube colour must differ strongly from the skin tone and from the
background. **Recommended: vivid red or vivid yellow.**

---

## 3. iPhone Setup

### 3.1 Pre-capture checklist

- [ ] Battery > 50%
- [ ] Storage > 2 GB free
- [ ] Camera mode: **Video** (not Cinematic, not Slow-Mo)
- [ ] Resolution: **4K at 30fps** (Settings → Camera → Record Video)
- [ ] Format: Most Compatible (H.264) or High Efficiency — both supported
- [ ] Electronic Image Stabilisation: OFF (Settings → Camera → toggle off
      if available on your model; most models disable it automatically in
      Video mode when set to 4K 60fps or lower)
- [ ] Flash: OFF
- [ ] HDR: OFF (Settings → Camera → Smart HDR: off)
- [ ] Lock focus/exposure: tap-and-hold on the infant's forehead until
      AE/AF Lock banner appears

### 3.2 Focus lock procedure

Before starting recording:
1. Frame the infant's forehead in the centre of the viewfinder.
2. Tap and hold until "AE/AF Lock" appears at the top of the screen.
3. Begin recording immediately.

This prevents the autofocus from hunting during the orbit, which would
cause frames to be defocused and discarded by the blur filter.

---

## 4. Recording Procedure

### 4.1 Orbit sequence

Execute three orbital passes at increasing inclination angles:

**Pass 1 — Equatorial orbit (primary)**
- Hold iPhone at 0° elevation (lens level with the infant's ear)
- Orbit fully around the head in 15–20 seconds
- Starting position: operator facing infant's right ear

**Pass 2 — Superior orbit (crown coverage)**
- Hold iPhone at approximately 30–40° above horizontal (angled down toward
  the top of the head)
- Orbit fully around the head in 15–20 seconds

**Pass 3 — Inferior orbit (base coverage, optional)**
- Hold iPhone at approximately 20° below horizontal (angled up toward the chin)
- Partial orbit 180° (front to back) — do not tilt below neck level

Total video duration: 45–60 seconds (all three passes in one continuous take,
or as separate files).

### 4.2 Movement guidelines

- Move at a **constant, slow speed** — approximately 1 full orbit per 15–20s
- Do not pause or reverse direction mid-orbit
- Keep the **head centred** in the frame at all times
- Maintain a **consistent distance of 30–40 cm** from the top of the head
- Ensure both **ears, the forehead, the vertex, and the back of the head**
  are all visible in at least 10 frames each

### 4.3 When to stop and re-record

Stop and re-record if:
- The infant moves their head significantly (>15°) during an orbit pass
- The iPhone autofocus hunts (image goes blurry for more than 0.5 seconds)
- You accidentally occlude the head with your hand or arm
- A caregiver's head enters the frame

---

## 5. File Transfer and Naming

### 5.1 Transfer

Transfer video from iPhone to Mac Mini via:
- **AirDrop** (fastest, wireless): share from Photos app
- **USB-C cable** + Image Capture app

### 5.2 File naming convention

```
data/captures/<SESSION_ID>/<SESSION_ID>_<DATE>.mp4

Examples:
  data/captures/SCN001/SCN001_20240315.mp4
  data/captures/SCN002/SCN002_20240315.mp4
```

**Session ID format**: `SCN` + three-digit sequential number.
Do **not** include the infant's name, date of birth, or NHS/hospital number
in the filename. Record the session ID to patient identifier mapping in the
secure clinical database only.

### 5.3 Video quality verification

Before starting the pipeline, verify the video in QuickTime Player:
- Plays without stuttering
- Head is in focus throughout
- Calibration cube is visible
- No obvious motion blur on the scalp texture

---

## 6. Pipeline Execution

```bash
# Activate the environment
source ~/CranioScan3D/venv/bin/activate

# Run the pipeline
cranioscan \
  --input data/captures/SCN001/SCN001_20240315.mp4 \
  --output-dir data/results/SCN001 \
  --config configs/default.yaml

# Expected runtime on Mac Mini M2 (8-core):
#   Extraction:    ~1 min
#   COLMAP sparse: ~5–15 min (depends on frame count)
#   Undistortion:  ~2 min
#   OpenMVS dense: ~20–40 min (CPU-only)
#   Mesh cleanup:  ~3 min
#   Total:         ~30–60 min per session
```

For faster iteration during development, use `configs/fast.yaml` (~10–20 min).

---

## 7. Landmark Placement (Month 3 — pending implementation)

After mesh processing completes, run the landmark GUI:

```bash
# (Available from Month 3)
python -m cranioscan.gui.landmark_gui \
  --mesh data/results/SCN001/mesh/mesh_scaled.ply \
  --output data/results/SCN001/results/landmarks.json
```

The GUI will suggest landmark positions based on mesh curvature. The operator
confirms or adjusts each suggestion using the 3D viewer.

**Estimated time per session**: 5–10 minutes with curvature assistance.

---

## 8. Output Review and Report

After pipeline completion, outputs are in `data/results/<SESSION_ID>/`:

```
SCN001/
├── frames/          Extracted JPEG frames
├── sparse/          COLMAP database and sparse model
├── undistorted/     Undistorted images for OpenMVS
├── dense/           OpenMVS dense output (mesh.ply)
├── mesh/            Cleaned mesh (mesh_clean.ply, mesh_scaled.ply)
└── results/         measurements.json, landmarks.json, report.pdf
```

Review the cleaned mesh in MeshLab or Open3D Viewer before confirming
measurements. Check for:
- Topological completeness (no large holes)
- Correct scale (head should be approximately 100–130mm AP length for
  an infant aged 0–6 months)
- No obvious outlier spikes or artefacts

---

## 9. Data Governance

- All session data must be stored on the encrypted Mac Mini local drive.
- Session ID → patient mapping is maintained only in the clinical database.
- The `data/` directory must never be committed to git (enforced by `.gitignore`).
- Video files, frames, and reconstructions are deleted after report generation
  and clinical filing, per the data retention policy.
- This tool is a **research prototype** and **not a CE-marked medical device**.
  Measurements are for research purposes only and must not be used alone to
  inform clinical decisions.
