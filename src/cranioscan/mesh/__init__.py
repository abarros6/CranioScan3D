"""Mesh post-processing subpackage.

Contains two modules:

- processing:  Open3D-based mesh cleaning pipeline. Takes the raw output
               mesh from OpenMVS and applies: statistical outlier removal,
               Poisson surface reconstruction, Taubin smoothing, and
               small-component removal to produce a clean, watertight mesh.

- scale:       Scale correction using a known physical reference object.
               Detects a calibration cube placed in the scene, computes the
               mm-per-model-unit scale factor, and applies it uniformly to
               the mesh so all downstream measurements are in millimeters.
               Detection is a Month-2 stub; apply_scale and
               compute_scale_factor are fully implemented utilities.
"""
