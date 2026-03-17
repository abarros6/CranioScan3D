"""CranioScan3D — 3D cranial reconstruction and measurement pipeline.

An end-to-end pipeline that reconstructs a 3D model of an infant's head
from iPhone video and extracts cranial measurements for craniosynostosis screening.

Classical computer vision only: COLMAP (sparse SfM) + OpenMVS (dense MVS) + Open3D.
Designed for Mac Mini Apple Silicon (CPU-only, no CUDA).
"""

__version__ = "0.1.0"
__author__ = "CranioScan3D Authors"
