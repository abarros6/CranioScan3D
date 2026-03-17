"""3D reconstruction subpackage.

Contains three stages of the reconstruction pipeline:

- sparse:     COLMAP sparse Structure-from-Motion (feature extraction,
              exhaustive matching, incremental mapper). CPU-only via
              --SiftExtraction.use_gpu 0 and --SiftMatching.use_gpu 0.

- undistort:  COLMAP image undistortion to produce rectilinear images
              and a COLMAP-format sparse model for OpenMVS input.

- dense:      OpenMVS dense multi-view stereo pipeline (InterfaceCOLMAP,
              DensifyPointCloud, ReconstructMesh, RefineMesh). CPU-only.

All three stages wrap external binaries via cranioscan.utils.shell.run_command
for consistent logging and error handling.
"""
