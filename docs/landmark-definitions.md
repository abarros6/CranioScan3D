# Craniometric Landmark Definitions

## Overview

CranioScan3D uses nine craniometric landmarks for cranial measurement. These
landmarks follow the standard conventions of physical anthropology and clinical
cephalometry as codified in the Howells (1973) and Bass (2005) references.

All landmark positions are stored as 3D coordinates in millimetres in the mesh
coordinate system after scale correction.

---

## Required Landmarks (for CI and CVAI)

These four landmarks must be placed for any measurement output.

### 1. Glabella (G)

**Definition**: The most anteriorly projecting point on the frontal bone in the
midsagittal plane, located between the supraorbital ridges (brow ridges).

**3D detection strategy**:
- Axis: most negative Y coordinate (assuming Y = anterior-posterior)
- Shape index: high positive (convex dome, SI > 0.7)
- Constraint: on or near the midsagittal plane (|X| < 5mm)
- Typically the anterior extreme of the mean curvature maximum along the
  superior frontal surface

**Clinical relevance**: One of the two poles of the AP measurement axis.
In metopic synostosis, glabella is displaced anteriorly relative to the
forehead, creating a characteristic triangular forehead shape.

---

### 2. Opisthocranion (Op)

**Definition**: The most posteriorly projecting point on the occipital bone
in the midsagittal plane, measured as the point maximising AP length from
glabella.

**3D detection strategy**:
- Axis: most positive Y coordinate (posterior extreme)
- Shape index: high positive (SI > 0.6)
- Constraint: on or near the midsagittal plane (|X| < 10mm), superior to
  the external occipital protuberance
- **Important**: This is the point that maximises the G–Op distance, not simply
  the most posterior vertex. The two may differ if the occiput is asymmetric.

**Clinical relevance**: With glabella, defines the AP length used in the
Cephalic Index. Posterior flattening (brachycephaly, coronal synostosis) or
posterior elongation (dolichocephaly, sagittal synostosis) are captured by
the CI deviation from the normal range.

---

### 3. Eurion Left (EuL)

**Definition**: The most lateral point on the left side of the cranium at
the level of maximum width (typically in the temporal region).

**3D detection strategy**:
- Axis: most negative X coordinate (left lateral extreme)
- Shape index: moderate positive (SI > 0.4)
- Height constraint: roughly at the level of the external acoustic meatus
  (mid-height of the skull)
- Search in the left temporal parietal region (X < −40mm for typical infant)

**Clinical relevance**: One pole of the bitemporal width measurement. Together
with EuR, defines the transverse diameter of the head. Asymmetric eurion
positions contribute to CVAI.

---

### 4. Eurion Right (EuR)

**Definition**: The most lateral point on the right side of the cranium at
the level of maximum width.

**3D detection strategy**: Mirror of EuL — most positive X coordinate at
equivalent height.

**Clinical relevance**: See EuL. The |EuL − EuR| distance is the bitemporal
width used in the Cephalic Index. Asymmetry between the Y coordinates of EuL
and EuR contributes to CVAI oblique diagonal computation.

---

## Optional Landmarks (for extended measurements)

These landmarks improve measurement completeness but are not required for
the initial CI/CVAI screening output.

### 5. Vertex (V)

**Definition**: The most superior point of the skull in standard anatomical
position (Frankfurt horizontal plane levelled).

**3D detection strategy**:
- Most positive Z coordinate (superior extreme)
- Shape index: high positive (SI > 0.7)
- Constraint: near midsagittal plane (|X| < 10mm)

**Clinical relevance**: Used in skull height measurements and for verifying
correct orientation of the reconstructed mesh.

---

### 6. Bregma (B)

**Definition**: The point of intersection of the coronal suture and the
sagittal suture on the superior surface of the calvaria.

**3D detection strategy**:
- In adults, bregma is visible as a sulcus at the coronal/sagittal suture
  intersection. In infants, the anterior fontanelle (bregmatic fontanelle)
  may still be open, creating a flat or depressed region.
- Shape index: low (near 0, saddle-like) or slightly negative in infants
  with open fontanelle.
- Position: approximately 40% of the way from nasion to lambda along the
  sagittal arc, but anatomical variation is high in infants.

**Clinical relevance**: In craniosynostosis involving the coronal or sagittal
suture, bregma position and fontanelle shape are diagnostic. Bregma is used
as the reference point for placing EEG electrodes (10–20 system) in infant
neuroimaging — relevant for co-registration with future EEG studies.

---

### 7. Lambda (Λ)

**Definition**: The point of intersection of the sagittal suture and the
lambdoid suture on the posterior surface of the calvaria.

**3D detection strategy**:
- Shape index: saddle-like (SI near 0 or slightly negative)
- Position: on the midsagittal plane, posterior to vertex, superior to
  opisthocranion
- Approximately 60% of the distance from bregma to opisthocranion along
  the posterior sagittal arc.

**Clinical relevance**: In lambdoid synostosis (rarest form), the lambdoid
suture fuses prematurely, creating true posterior plagiocephaly (asymmetric
flattening). Lambda displacement is a key diagnostic marker.

---

### 8. Nasion (N)

**Definition**: The intersection of the internasal suture and the
frontonasal suture, at the root of the nose.

**3D detection strategy**:
- The nasion is typically at the lowest point of the frontal bone at the
  midline, just above the bridge of the nose.
- Shape index: saddle-like (SI near 0, boundary between frontal and nasal
  surfaces)
- Position: near the inferior frontal midline, anterior to glabella

**Clinical relevance**: Nasion-to-vertex height and nasion-to-opisthocranion
distance are used in facial profile analysis relevant to frontoorbital
advancement planning.

---

### 9. Metopion (M)

**Definition**: The most anterior point of the frontal eminence (highest
point of the frontal bone) — sometimes called the frontal boss.

**3D detection strategy**:
- Shape index: high positive (SI > 0.7, convex dome)
- Position: on the midsagittal plane, superior to glabella, inferior to vertex
- Typically the highest mean curvature point on the frontal bone between
  glabella and vertex.

**Clinical relevance**: Frontal bossing (prominent metopion) is a hallmark of
metopic synostosis (trigonocephaly). The metopion-to-nasion angle characterises
the severity of the triangular forehead deformity.

---

## Measurement Formulas

### Cephalic Index (CI)
```
CI = (EuL–EuR distance / G–Op distance) × 100
```
- Normal: 75–85
- Dolichocephaly (sagittal synostosis): CI < 75
- Brachycephaly (bilateral coronal synostosis): CI > 85

### Cranial Vault Asymmetry Index (CVAI)
```
d1 = distance from right frontal to left occipital (oblique diagonal 1)
d2 = distance from left frontal to right occipital (oblique diagonal 2)
CVAI = |d1 − d2| / max(d1, d2) × 100
```
Diagonal endpoints are defined as the 45° oblique points between G/Op and EuL/EuR.
- Normal: < 3.5%
- Mild plagiocephaly: 3.5–6.25%
- Moderate: 6.25–8.75%
- Severe: > 8.75%

### AP Length
```
AP = |G − Op|  (Euclidean distance in 3D)
```

### Bitemporal Width
```
BW = |EuL − EuR|  (Euclidean distance in 3D)
```

### Head Circumference (geodesic, Month 3)
```
HC_arc = geodesic_length(G → EuR → Op → EuL → G)
         along mesh surface
```
Note: straight-line sum G→EuR→Op→EuL→G underestimates true circumference;
geodesic arc is the clinically appropriate measure.

---

## References

- Bass, W.M. (2005). *Human Osteology: A Laboratory and Field Manual*. 5th ed.
- Howells, W.W. (1973). *Cranial Variation in Man*. Papers of the Peabody Museum.
- Loveday, B.P.T. & de Chalain, T.B. (2001). Active helmet therapy or surgery
  for isolated sagittal synostosis. *J Craniofac Surg*, 12(1), 41–46.
- Plank, L.H. et al. (2006). A 3-dimensional morphometric analysis of isolated
  metopic synostosis. *J Craniofac Surg*, 17(4), 651–656.
- Aldridge, K. et al. (2005). Anthropometric facial features and the measurement
  of nasal surface shape. *Am J Phys Anthropol*, 128(3), 600–612.
