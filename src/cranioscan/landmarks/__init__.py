"""Landmark detection subpackage.

Provides semi-automatic detection of craniometric landmarks on the
reconstructed 3D head mesh. The workflow is:

  1. CurvatureAnalyzer (curvature.py) — Compute per-vertex principal
     curvatures and Koenderink's shape index to identify candidate
     regions corresponding to anatomical extrema (glabella, opisthocranion,
     eurion L/R, vertex, bregma, lambda, nasion, metopion).

  2. LandmarkDetector (detector.py) — Combine curvature-based suggestions
     with anatomical priors to propose likely positions for each landmark.
     Passes suggestions to the GUI for user confirmation or correction.

Both modules are Month-3 implementation targets. The data structures
(LandmarkId, Landmark, LandmarkSet) and public interfaces are fully defined
so that measurement and GUI code can be written against the interface now.
"""
