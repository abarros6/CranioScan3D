"""GUI subpackage for interactive landmark placement.

Provides a PyQt5-based 3D viewer that renders the reconstructed head mesh
and allows the operator to:

  1. View curvature-based landmark suggestions overlaid on the mesh surface.
  2. Click on the mesh surface to place or adjust landmark positions.
  3. Save the confirmed landmark set for downstream measurement.

The GUI is designed for single-operator use on the Mac Mini. It uses Open3D's
VisualizerWithEditing for the 3D viewport, embedded in a PyQt5 QMainWindow
that also shows the landmark checklist and measurement preview.

Implementation target: Month 3.

Typical usage (once implemented):
    from cranioscan.gui.landmark_gui import LandmarkGUI
    gui = LandmarkGUI(mesh_path=Path("data/mesh/mesh_scaled.ply"))
    landmark_set = gui.run()  # blocks until user confirms all landmarks
"""
