# CranioScan3D — Video Capture Protocol

**Version:** 1.1 (2026-03-18)
**Applies to:** CranioScan3D pipeline v0.1.0+
**Target operator:** Clinician or researcher with no photogrammetry background

---

## Why this document matters

The 3D reconstruction quality is almost entirely determined by video quality. A perfect 5-minute reconstruction cannot recover from a poorly recorded 45-second clip. COLMAP (the Structure-from-Motion engine used in this pipeline) needs:

- Consistent, sharp frames with natural texture
- Sufficient overlap between adjacent frames (≥80%)
- Coverage of the entire surface with no gaps
- A stationary subject relative to the camera between frames
- Stable, non-varying lighting (no flickering, no moving shadows)

Every instruction in this document exists because violating it causes a specific, hard-to-diagnose failure in the pipeline. The troubleshooting table at the end maps symptoms to root causes.

---

## 1. Equipment

### Required

| Item | Notes |
|------|-------|
| iPhone 12 or later | Any model with 4K video. LiDAR not needed. |
| White swim cap | **Required for any subject with hair.** Hair has no texture for COLMAP; the swim cap gives the scalp a trackable, uniform surface. A standard latex or silicone swim cap works. |
| Calibration object | A rigid object with a **known size** placed next to the subject. A standard 16mm die (white) is the default; a 3D-printed cube of known dimension also works. Must be fully stationary relative to the subject. |
| Plain background | Light grey or white cloth, mat, or foam pad. Non-reflective. No patterns. |

### Recommended

| Item | Notes |
|------|-------|
| Two diffuse light sources | Softboxes, ring lights with diffuser, or large windows — see lighting section |
| Second operator | One to hold/distract the infant, one to record |
| Foam head support | Keeps the infant's head stable during recording |
| Pacifier | Useful for keeping infants calm and still |

---

## 2. iPhone Camera Settings

Configure these **before** entering the room. Settings changes mid-session waste time and risk forgetting a critical toggle.

### Step-by-step

1. Open **Settings → Camera → Record Video**
   - Set to **4K at 30 fps**
   - Do **not** use 4K 60fps (larger files, no benefit for reconstruction)
   - Do **not** use slow-motion modes

2. Open **Settings → Camera**
   - Turn **Smart HDR off** — HDR composites multiple exposures, creating inconsistent brightness between frames that breaks COLMAP's feature matching
   - Turn **Lens Correction off** (if visible on your model) — the pipeline applies its own undistortion using COLMAP's recovered camera model; double-correcting warps the geometry

3. Open the **Camera app → Video mode**
   - Swipe away any filter (make sure the filter dot shows "Original")
   - Turn off **Cinematic mode** — use standard video recording only

4. **Do not switch lenses.** Tap the 1× button to confirm you are on the standard wide lens. The pipeline's `SIMPLE_RADIAL` camera model is calibrated for a single fixed lens. Switching between wide, standard, and telephoto mid-video is fatal to the reconstruction.

### Settings summary

| Setting | Required value | Why |
|---------|---------------|-----|
| Resolution | 4K 30fps | Sufficient detail, manageable file size |
| Smart HDR | Off | Frame-to-frame brightness consistency |
| Lens Correction | Off | Avoid double undistortion |
| Cinematic mode | Off | Standard video only |
| Flash | Off | Creates harsh, moving shadows |
| Lens | Standard (1×) | Consistent camera model throughout |
| Enhanced Stabilisation | **Off** | Critical — see note below |

### Critical: Electronic Image Stabilisation (EIS)

This is the single most important setting. **Enhanced Stabilisation must be off.**

EIS works by cropping and warping the image to counteract hand movement. This means consecutive frames are not from a rigid camera — the field of view shifts, rotates, and scales between frames in a way that is invisible to the operator but catastrophic for Structure-from-Motion. COLMAP assumes a pinhole camera with fixed intrinsics; EIS violates this assumption and will either cause the reconstruction to fail entirely or produce a severely distorted mesh.

In testing, this setting caused every frame to be motion-blurred (Laplacian score 8–10 vs a normal score of 100+), producing fewer than 10 usable frames from a full 1,564-frame video. Turning it off brought the video back to normal sharpness.

**How to disable EIS on iPhone:**
- Settings → Camera → Record Video → **Enhanced Stabilisation → Off**
- The option labelled "Standard" uses optical stabilisation (hardware gimbal only), which is acceptable. Only "Enhanced" uses electronic/digital warping and must be off.
- This option is easy to miss — it is nested inside Record Video, not at the top level of Settings → Camera.

---

## 3. Scene Setup

Get the scene right before involving the subject. Changing lights or background mid-session causes frame-to-frame inconsistencies.

### 3a. Lighting

The goal is **soft, even, shadow-free illumination** across the entire head surface.

**Ideal setup:**
```
  [softbox / window]              [softbox / window]
          \                               /
           \          HEAD               /
            \          ●                /
             \                         /
             45°                     45°
         (slightly above head height on each side)
```

- Two light sources at roughly 45° left and right, slightly above head height
- Both sources should be similar brightness — one dominant light casts deep shadows on the opposite side that COLMAP cannot match
- A large north-facing window on one side + a white foam reflector card on the other works well if softboxes are unavailable

**What to avoid:**

| Lighting problem | Effect on reconstruction |
|-----------------|--------------------------|
| Direct sunlight | Harsh shadows that move as you orbit; blown-out highlights |
| Single point source | Deep shadows on opposite side — SIFT features missing in shadow |
| Flickering fluorescents | Per-frame brightness variation; SIFT matching fails |
| Overhead downlight only | Top overexposed, sides underexposed |
| Mirrors or shiny windows in background | Reflections create ghost geometry |

**Hair:** Dark, uniform hair has no texture for COLMAP to track and causes large holes in the final mesh that cannot be closed in post-processing. A **white swim cap is required** for any infant with visible hair. The swim cap also provides a consistent, repeatable head surface that does not change between visits. Bald and very short-haired infants can be recorded without a cap, but the cap is still recommended for consistency.

### 3b. Background

- Use a **plain, non-patterned, matte surface** — light grey or white foam mat, cloth, or clinical paper roll
- The background should have minimal texture — COLMAP will attempt to reconstruct it; a plain background keeps the sparse model focused on the head
- Keep the background at least 20–30 cm behind the subject so it is at a different depth

### 3c. Calibration object

The calibration object allows pipeline stage 6 to convert the mesh from arbitrary model units into millimetres.

- Use a **rigid** object with a **precisely known dimension**. The default configuration (`color_hint: white`, `reference_size_mm: 16.0`) is calibrated for a **standard 16mm die (white)**. This is the recommended reference object — cheap, available everywhere, and the correct size and colour for the default config.
- Alternative objects: a 3D-printed 10mm white cube, a 25mm coin, or any rigid object of known size. If using a non-white object, set `scale.color_hint` in your config to `red`, `yellow`, or `blue`, or override the HSV thresholds manually.
- Place it **adjacent to the subject**, attached to the head support so it moves with the infant if they move
- It must be **visible from at least half the orbit angles** — place it at the side or front of the head support, not behind the head
- The object must be **completely stationary** relative to the subject during recording
- Avoid placing it directly against the subject's skin — a small gap ensures the DBSCAN cluster detector can isolate it from the skin point cloud

---

## 4. Recording Procedure

### 4a. Lock focus and exposure before pressing record

1. Open Camera app in Video mode
2. **Tap and hold** on the infant's head in the viewfinder until the **AE/AF Lock** banner appears at the top of the screen
3. This locks both autofocus and autoexposure for the duration of the recording
4. If the subject moves significantly, stop recording, re-lock, and start a new clip

Why this matters: autofocus changes the effective focal length between frames, which changes the camera's intrinsic parameters. COLMAP assumes fixed intrinsics (`single_camera=1`). Autofocus drift causes feature matches to disagree about 3D positions, producing a distorted sparse model.

### 4b. The orbit path

The operator moves around the stationary subject in a continuous, slow arc. The subject must not move.

```
              [CROWN PASS]
           tilt phone 30° down
              ↓  ↓  ↓  ↓
          _______________
         /               \
        |   [TOP VIEW]    |
        |        ●        |   ← subject's head
        |                 |
         \_______________/

← ← ← ← EQUATORIAL ORBIT → → → →

   Start at left ear.
   Move: left ear → forehead → right ear → back of head → left ear
   One full 360° circle.
```

**Required passes:**

| Pass | Camera angle | Duration | What it captures |
|------|-------------|----------|-----------------|
| Equatorial | Camera held level, pointed at sides of head | 15–20 sec | Ears, forehead, temples, occiput |
| Crown | Tilt phone ~30° downward while orbiting | 10–15 sec | Top of skull, bregma, sagittal region |

**Optional pass:**

| Pass | Camera angle | Duration | What it captures |
|------|-------------|----------|-----------------|
| Low | Tilt phone ~20° upward while orbiting | 10 sec | Sub-occipital, chin/neck junction |

**Total recording time:** 30–50 seconds for both required passes.

### 4c. Distance and framing

- Maintain **30–40 cm** from the surface of the head throughout the entire orbit
- The head should fill **60–70% of the frame** — large enough to capture surface detail, small enough that the whole head stays in frame
- Keep the head **centred** horizontally and vertically in every frame
- Both ears must be fully visible during the equatorial pass; the full crown must be visible during the crown pass

```
Good framing:              Too close:              Too small:
┌───────────────┐         ┌───────────────┐       ┌───────────────┐
│               │         │  ┌──────────┐ │       │               │
│  ┌─────────┐  │         │  │▓▓▓▓▓▓▓▓▓▓│ │       │  (  HEAD  )   │
│  │  HEAD   │  │         │  │▓▓▓▓▓▓▓▓▓▓│ │       │               │
│  └─────────┘  │         │  └──────────┘ │       │               │
│               │         └───────────────┘       └───────────────┘
└───────────────┘              ✗ cropped              ✗ too small
      ✓ ideal
```

### 4d. Movement speed

Move **as slowly as you comfortably can** while continuously circling the subject.

At 4K 30fps, each frame should overlap at least 80% with the previous frame. For a head at 35 cm distance, this means:

- Equatorial orbit: **one full circle in 15–20 seconds**
- You will record approximately 450–600 frames per pass
- After frame extraction (default: every 15 frames with blur filtering), you get 30–50 usable frames per pass — enough for COLMAP

**Self-check:** After recording, scrub through the video at 1× speed. Adjacent frames should look nearly identical with only a tiny lateral shift. If you can see obvious movement from frame to frame, the orbit was too fast.

Consequences of moving too fast:
- Frame overlap drops below 80%
- COLMAP's exhaustive matcher cannot find enough correspondences between adjacent views
- The sparse model either fails entirely or registers only a fraction of images

### 4e. If the subject moves

If the infant moves their head significantly (more than ~2–3 cm) mid-orbit:

1. **Stop recording immediately**
2. Wait for the infant to settle and reposition their head
3. Re-lock AE/AF
4. **Start a new recording file from the beginning**

Do not attempt to continue the same file after a large head movement. There is no post-processing fix for a mid-orbit rigid-body violation. COLMAP will fail to stitch the frames before and after the movement into a consistent model.

---

## 5. File Transfer and Naming

### Transfer to Mac Mini

| Method | Instructions |
|--------|-------------|
| AirDrop | On iPhone: Photos → select video → Share → AirDrop → Mac Mini. Fastest. |
| USB-C cable | Connect iPhone, open Image Capture on Mac, import the .MOV file. |
| iCloud Photos | Video appears in ~/Pictures after sync — allow 2–5 min for 4K files. |

### File naming convention

Save to `data/captures/` using an anonymised session ID:

```
data/captures/
└── SCN001/
    ├── SCN001_20260317.mp4     ← primary recording
    └── SCN001_20260317_b.mp4  ← second attempt if needed
```

Format: `SCN` + zero-padded subject number + `_` + ISO date (YYYYMMDD).

Do not include subject names, dates of birth, or any identifying information in filenames. The entire `data/` directory is git-ignored and must not be committed.

### Pre-pipeline verification

Before running the pipeline, verify in QuickTime Player:
- Video plays back smoothly — no stuttering or dropped frames
- Full head is visible throughout with correct framing
- Lighting is consistent across the orbit (no sudden brightness changes)
- Calibration object is visible for most of the orbit
- No large head movements visible

---

## 6. Running the Pipeline

```bash
cd ~/projects/CranioScan3D
source venv/bin/activate

# First run on a new subject — use fast config to check quality quickly:
cranioscan \
  --input data/captures/SCN001/SCN001_20260317.mp4 \
  --output-dir data/results/SCN001 \
  --config configs/fast.yaml

# Default full-quality run:
cranioscan \
  --input data/captures/SCN001/SCN001_20260317.mp4 \
  --output-dir data/results/SCN001 \
  --config configs/default.yaml

# Highest quality clinical run (slower — 30–60 min on Mac Mini M4):
cranioscan \
  --input data/captures/SCN001/SCN001_20260317.mp4 \
  --output-dir data/results/SCN001 \
  --config configs/clinical.yaml

# Run only extraction + COLMAP to check coverage before full pipeline:
cranioscan \
  --input data/captures/SCN001/SCN001_20260317.mp4 \
  --output-dir data/results/SCN001 \
  --stop-after sparse \
  --config configs/fast.yaml
```

### Reading the COLMAP output

After the `sparse` stage, check the logs for:

```
Mapper: registered 87/92 images
```

| Registration rate | Interpretation |
|------------------|---------------|
| ≥ 90% | Good — proceed to dense |
| 70–90% | Acceptable — some coverage gaps but usually recoverable |
| < 70% | Poor — inspect the video and consider re-recording |

---

## 7. Quality Targets

| Metric | Minimum | Target |
|--------|---------|--------|
| Sharp frames extracted | 50 | 80–150 |
| COLMAP registered images | 80% | ≥ 95% |
| Sparse point cloud | 3,000 pts | ≥ 8,000 pts |
| Dense point cloud | 200,000 pts | ≥ 500,000 pts |
| Final mesh triangles | 30,000 | ≥ 80,000, watertight |
| AP length accuracy vs caliper | — | < 2 mm |
| CVAI repeatability (same video, two runs) | — | < 0.5% |

---

## 8. Troubleshooting

| Symptom | Likely cause | How to confirm | Fix |
|---------|-------------|----------------|-----|
| Very few frames extracted (<30) | Video too short, or blur threshold too high | Check `frame_extractor` log | Slow down orbit; re-record |
| All frames marked blurry | EIS active, or orbit too fast | All frames below blur threshold in log | Disable EIS; slow orbit |
| COLMAP registers <60% of images | Insufficient overlap or coverage gaps | Check unregistered image list in COLMAP log | Slow down; fill coverage gaps |
| Large holes in top of skull mesh | Crown pass missing or rushed | Sparse point cloud has no superior points | Add proper crown pass |
| Mesh stretched or sheared | EIS was active | Point cloud looks smeared in one direction | Disable EIS; re-record |
| Mesh scale wildly wrong | Calibration cube not detected | Scale correction stage logs a warning or None | Use brighter cube colour; ensure visible from most angles |
| Two disconnected model fragments | Infant moved head mid-orbit | Two clusters visible in sparse point cloud | Re-record; always start new clip after any large movement |
| One side has poor mesh detail | Lighting too one-sided | That side's frames have few SIFT features | Add second light source; use reflector card |
| Scalp blown out / overexposed | Overhead light too strong, or HDR on | White regions in mesh texture | Reduce overhead light; confirm Smart HDR off |
| Hair causes holes in mesh | Uniform dark texture, no SIFT features | Missing points over hair region | Use light-coloured cotton cap |
| Reconstruction fails entirely | Multiple possible causes | Find first ERROR in stage logs | Use `--stop-after` to isolate failing stage |

---

## 9. Testing Without an Infant

To validate the pipeline before clinical use, record any round object of similar scale (~15–18 cm diameter):

| Stand-in object | Why it works |
|-----------------|-------------|
| Football / basketball | Similar diameter; round geometry |
| Large melon or pumpkin | Natural surface texture; excellent SIFT features |
| Foam head model (photography prop) | Correct geometry; available from suppliers |
| 3D-printed head phantom | Best for quantitative validation — compare pipeline output to caliper measurements in `data/phantoms/` |

Apply the **same protocol exactly**: same lighting setup, same camera settings, same orbit path, same calibration object placement. This confirms the full pipeline works correctly before any clinical contact.

**Minimum software smoke test:**

```bash
# Record any round object and run:
cranioscan \
  --input data/captures/test/object.mp4 \
  --output-dir data/results/test \
  --config configs/fast.yaml \
  --stop-after mesh
```

---

## 10. Planned: CranioCapture iOS App

A dedicated iPhone app (**CranioCapture**) is on the project roadmap. It will replace this manual protocol with a fully guided workflow:

- Automatically enforces all required camera settings (4K 30fps, AE/AF lock, EIS off)
- On-screen orbit guide showing the operator's real-time position around the head
- Audio and haptic feedback for orbit speed (too fast / too slow) and frame sharpness
- Automatic detection of orbit completion — stops recording after equatorial + crown pass
- Wireless video transfer directly to the Mac pipeline

Until CranioCapture is available, this document is the operating protocol.
