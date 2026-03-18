# iPhone Capture Protocol — CranioScan3D

## Overview

This guide describes how to record a video of an infant's head that is
suitable for 3D reconstruction with CranioScan3D. Following this protocol
will maximise reconstruction quality and measurement accuracy.

See `docs/capture-protocol.md` for the full detailed reference. This file
is a quick-reference summary.

---

## Equipment Checklist

- iPhone 12 or later (LiDAR not required; standard camera only)
- **White swim cap** — required for any subject with hair
- Neutral-coloured background (light grey or white cloth / mat)
- Diffuse lighting (overcast daylight or two softboxes at 45°)
  — **avoid direct sunlight, harsh shadows, or flickering fluorescent light**
- Calibration die — a standard **16mm white die** placed adjacent to the subject
- A second person to hold the infant (or a foam head support)

---

## Camera Settings

Before recording, configure the iPhone camera:

| Setting | Value | Path |
|---------|-------|------|
| Resolution | 4K 30fps | Settings → Camera → Record Video |
| Enhanced Stabilisation | **Off** | Settings → Camera → Record Video → Enhanced Stabilisation |
| Smart HDR | Off | Settings → Camera → Smart HDR |
| Lens Correction | Off | Settings → Camera → Lens Correction |
| Flash | Off | In Camera app |
| Lens | Standard (1×) | Tap 1× in Camera app to confirm |
| Focus / exposure | Locked | Tap-and-hold on subject's head until AE/AF Lock appears |

> **Why disable Enhanced Stabilisation?**
> Electronic stabilisation crops and warps frames to counteract hand movement.
> This makes consecutive frames inconsistent — the field of view shifts in a
> way that is invisible to the operator but catastrophic for COLMAP's SfM.
> In testing, this single setting caused every frame to be motion-blurred
> (Laplacian score 8–10 vs normal 100+), producing fewer than 10 usable
> frames from a 1,564-frame video. The option is nested inside
> Settings → Camera → Record Video — easy to miss.

---

## Scene Setup

1. **Swim cap**: Fit a white swim cap snugly over the infant's head. The cap
   must cover all hair. Its uniform white surface gives COLMAP trackable texture.

2. **Lighting**: Position two diffuse light sources at roughly 45° left and
   right of the infant's head. Aim for soft, even illumination with no
   specular highlights on the scalp. Natural north-facing window light also
   works well.

3. **Background**: Place the infant on a light-grey mat or in a white sling.
   Avoid busy patterns — COLMAP works best with a plain, textureless background.

4. **Calibration die**: Place a standard 16mm white die on the head support,
   adjacent to (not touching) the subject's head. It must be visible from at
   least half of the orbit angles and completely stationary throughout recording.
   The pipeline's default config (`color_hint: white`, `reference_size_mm: 16.0`)
   is calibrated for this die.

5. **Infant positioning**: The infant should be calm and as still as possible.
   Feeding or pacifier use during capture is recommended to minimise movement.

---

## Recording Procedure

### Orbit path

Hold the iPhone at arm's length, screen facing you, lens pointing at the
infant's head. Move in a continuous horizontal orbit around the head:

```
        [top of head]
              |
    left ─────●───── right
              |
        [chin / neck]
```

- Start at the infant's left ear (facing the ear)
- Move slowly: left ear → forehead → right ear → back of head → left ear
- Full equatorial orbit: **15–20 seconds** at 4K 30fps (~450–600 frames)
- After the equatorial orbit, tilt **downward 30°** and repeat (crown pass)
- Optionally, tilt **upward 20°** for a chin-level pass

### Distance and framing

- Maintain a **constant distance of 30–40 cm** from the surface of the head
- Keep the **head centred** and filling **60–70% of the frame** at all times
- Ensure the **full head is visible** in every frame — do not crop ears or crown

### Movement speed

Move **slowly and steadily**. Each frame should overlap at least 80% with the
previous one. Scrub through the video at 1× speed after recording — adjacent
frames should look nearly identical with only a tiny lateral shift.

### What to avoid

- Large infant head movements (re-start recording if this occurs)
- Partially occluding the head with your hand
- Large gaps in coverage (e.g. skipping the top of the head)
- Reflective surfaces in the background (mirrors, shiny toys)
- Changing lighting conditions mid-orbit

---

## After Recording

1. **Transfer** the video to the Mac Mini via AirDrop or USB-C cable.
   Save it to `data/captures/<session_id>/`.

2. **Name the file** with an anonymised session ID:
   ```
   data/captures/SCN001/SCN001_20260318.mov
   ```

3. **Verify** the file plays back smoothly in QuickTime before starting the
   pipeline.

4. **Run the pipeline**:
   ```bash
   source venv/bin/activate

   # Quick check (fast config — takes ~5 min):
   cranioscan --input data/captures/SCN001/SCN001_20260318.mov \
              --output-dir data/results/SCN001_fast \
              --config configs/fast.yaml

   # Full clinical quality (default config):
   cranioscan --input data/captures/SCN001/SCN001_20260318.mov \
              --output-dir data/results/SCN001 \
              --config configs/default.yaml

   # Highest quality (clinical.yaml — 30–60 min on Mac Mini M4):
   cranioscan --input data/captures/SCN001/SCN001_20260318.mov \
              --output-dir data/results/SCN001_clinical \
              --config configs/clinical.yaml
   ```

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---------|-------------|-----|
| Very few frames extracted (<30) | Video too short, or all frames blurry | Slow down orbit; check Enhanced Stabilisation is OFF |
| All frames marked blurry | Enhanced Stabilisation is on | Settings → Camera → Record Video → Enhanced Stabilisation → Off |
| COLMAP registers <60% of images | Insufficient overlap or coverage gaps | Slow down orbit; ensure full crown pass |
| Large holes over scalp | Hair visible — no swim cap | Fit a white swim cap before re-recording |
| Mesh contains background geometry | Plain background not used | Use plain white/grey mat; no objects in background |
| Scale die not detected | Die not visible or wrong colour | Ensure die is visible from ≥50% of orbit; use white 16mm die |
| Two disconnected mesh fragments | Infant moved head mid-orbit | Always start a new clip after any large head movement |
| Mesh stretched or sheared | Enhanced Stabilisation was on | Disable and re-record |

---

## Quality Targets

| Metric | Minimum | Target |
|--------|---------|--------|
| Sharp frames extracted | 50 | 80–150 |
| COLMAP registered images | 80% | ≥ 95% |
| Dense point cloud | 200,000 pts | ≥ 500,000 pts |
| Final mesh triangles | 50,000 | ≥ 150,000, watertight |
| Scale factor | plausible | validated against caliper |
