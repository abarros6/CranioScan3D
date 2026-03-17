# iPhone Capture Protocol — CranioScan3D

## Overview

This guide describes how to record a video of an infant's head that is
suitable for 3D reconstruction with CranioScan3D. Following this protocol
will maximise reconstruction quality and measurement accuracy.

---

## Equipment Checklist

- iPhone 12 or later (LiDAR not required; standard camera only)
- Neutral-coloured background (light grey or white cloth / mat)
- Diffuse lighting (overcast daylight or two softboxes at 45°)
  — **avoid direct sunlight, harsh shadows, or flickering fluorescent light**
- 10mm calibration cube (3D-printed, vivid colour different from skin tone)
- A second person to hold the infant (or a foam head support)

---

## Camera Settings

Before recording, configure the iPhone camera:

| Setting | Value |
|---------|-------|
| Resolution | 4K 30fps (Settings → Camera → Record Video) |
| Format | High Efficiency (HEVC/H.265) or Most Compatible (H.264) |
| Stabilisation | Off (disable Cinematic mode; use standard video) |
| Flash | Off |
| HDR | Off (disable Smart HDR in Settings → Camera) |
| Focus lock | Tap-and-hold on the infant's head to lock AE/AF |

> **Why disable stabilisation?** Electronic stabilisation crops and warps
> frames, which breaks the rigid-body assumptions underlying COLMAP's SfM.

---

## Scene Setup

1. **Lighting**: Position two diffuse light sources at roughly 45° left and
   right of the infant's head. Aim for soft, even illumination with no
   specular highlights on the scalp. Natural north-facing window light also
   works well.

2. **Background**: Place the infant on a light-grey mat or in a white sling.
   Avoid busy patterns — COLMAP's SIFT works best with a textureless
   background behind the subject.

3. **Calibration cube**: Attach the 10mm cube to the back of the head support
   (visible from at least 50% of orbit angles). The cube must be rigid and
   stationary relative to the infant throughout the capture. Its vivid colour
   (e.g. bright red or yellow) aids segmentation during scale correction.

4. **Infant positioning**: The infant should be calm and as still as possible.
   Feeding or pacifier use during capture is recommended to minimise movement.

---

## Recording Procedure

### Orbit path

Hold the iPhone at **arm's length**, screen facing you, lens pointing at the
infant's head. Move in a continuous **horizontal orbit** around the head:

```
        [top of head]
              |
    left ─────●───── right
              |
        [chin / neck]
```

- Start at the infant's left ear (facing the ear)
- Move slowly to the forehead, right ear, back of head, back to left ear
- This full orbit should take **15–20 seconds** at 4K 30fps (~450–600 frames)
- After the horizontal orbit, tilt **downward 30°** and repeat the orbit
  (captures crown details)
- Optionally, tilt **upward 20°** for a chin-level pass

### Distance and framing

- Keep the **head centred** in frame at all times
- Maintain a **constant distance of 30–40 cm** from the top of the head
- Ensure the **full head is visible** (including ears and back of skull) in
  every frame — do not crop the head

### Movement speed

Move **slowly and steadily**. A rough guide: each frame should overlap at
least 80% with the previous frame. At 4K 30fps this means:

- Orbit speed ≈ 1 full circle per 15–20 seconds
- Avoid jerky movements or sudden direction changes

### What to avoid

- Blinking or sudden motion during recording
- Partially occluding the head with your hand
- Large gaps in coverage (e.g. going straight from ear to ear without
  covering the top)
- Reflective surfaces in the background (mirrors, shiny toys)
- Infant moving head significantly mid-orbit (re-start if this occurs)

---

## After Recording

1. **Transfer** the video to the Mac Mini via AirDrop or USB-C cable.
   Save it to `data/captures/<session_id>/`.

2. **Name the file** with an anonymised session ID:
   ```
   data/captures/SCN001/SCN001_20240315.mp4
   ```

3. **Verify** the file plays back smoothly in QuickTime before starting the
   pipeline.

4. **Run the pipeline**:
   ```bash
   cranioscan --input data/captures/SCN001/SCN001_20240315.mp4 \
              --output-dir data/results/SCN001 \
              --config configs/default.yaml
   ```

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---------|-------------|-----|
| Very few frames extracted (<50) | Video too short or all frames blurry | Re-record; slow down orbit |
| COLMAP registers <60% of images | Insufficient texture / coverage gaps | Ensure even orbit, no big jumps |
| Reconstruction has large holes | Top-of-head not captured | Add crown-pass orbit |
| Scale cube not detected | Cube not visible or too small in frame | Move cube closer; use brighter colour |
| Blurry reconstruction | Electronic stabilisation was on | Disable stabilisation and re-record |

---

## Quality Targets

A successful capture for CranioScan3D should yield:

| Metric | Target |
|--------|--------|
| Extracted frames | 80–150 sharp frames |
| COLMAP registered images | ≥ 90% of extracted frames |
| Sparse point cloud | ≥ 5000 points |
| Dense point cloud | ≥ 500,000 points |
| Final mesh | ≥ 50,000 triangles, watertight |
| Scale RMS error | < 0.5 mm |

These targets ensure measurement precision within ±1–2 mm for cephalic index
and CVAI, which is within clinical tolerance for craniosynostosis screening.
