"""Interactive landmark placement GUI.

Provides a PyQt5 window that wraps an Open3D 3D mesh viewer. The operator
can place and adjust craniometric landmarks by clicking on the mesh surface.
Curvature-based auto-suggestions are shown as coloured sphere markers that
the operator can accept or drag to the correct position.

TODO (Month 3): Full implementation. The class interface is defined here so
that the pipeline can call gui.run() and receive a LandmarkSet.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from cranioscan.landmarks.detector import LandmarkDetector, LandmarkId, LandmarkSet

logger = logging.getLogger(__name__)

# Reference ranges for the live measurement panel (displayed while placing landmarks)
_REFERENCE_RANGES: dict[str, tuple[float, float]] = {
    "cephalic_index": (75.0, 85.0),   # Normal CI range
    "cvai": (0.0, 3.5),               # Normal CVAI (<3.5% is symmetric)
}


class LandmarkGUI:
    """PyQt5 + Open3D interactive landmark placement window.

    Opens the cleaned, scaled mesh in a 3D viewport. Uses Open3D's
    VisualizerWithEditing to support point picking. The right-hand panel
    shows the landmark checklist, current measurement values, and accept/
    reject buttons.

    Workflow:
      1. Load mesh and any curvature suggestions.
      2. Display suggestion spheres on mesh.
      3. Operator clicks each landmark in sequence (or accepts suggestion).
      4. Live measurement panel updates after each placement.
      5. When all required landmarks are confirmed, "Export" becomes active.
      6. Returns a LandmarkSet on close.

    Attributes:
        mesh_path: Path to the scaled mesh file to display.
        detector: LandmarkDetector coordinating placement state.
        _suggestions: Curvature-based landmark position suggestions.
    """

    def __init__(
        self,
        mesh_path: Path,
        detector: Optional[LandmarkDetector] = None,
        suggestions: Optional[dict[LandmarkId, object]] = None,
    ) -> None:
        """Initialize LandmarkGUI.

        Args:
            mesh_path: Path to the mesh file (.ply) to display.
            detector: Optional pre-configured LandmarkDetector instance.
                Creates a new one if not provided.
            suggestions: Optional curvature-based position suggestions
                (dict of LandmarkId -> np.ndarray position).
        """
        self.mesh_path = mesh_path
        self.detector = detector or LandmarkDetector()
        self._suggestions: dict[LandmarkId, object] = suggestions or {}
        logger.info("LandmarkGUI initialised for mesh: %s", mesh_path)

    def run(self) -> LandmarkSet:
        """Launch the GUI and block until the operator exits.

        Returns:
            LandmarkSet containing all placed landmarks.

        Raises:
            NotImplementedError: GUI is not yet implemented (Month 3).
        """
        raise NotImplementedError(
            "TODO: implement in Month 3 — interactive landmark placement GUI. "
            "Implementation plan: "
            "(1) Import PyQt5.QtWidgets and open3d.visualization, "
            "(2) Create QMainWindow with QSplitter: left=Open3D QWidget viewport, "
            "    right=QVBoxLayout with landmark checklist (QListWidget), "
            "    measurements panel (QTableWidget), confirm/skip buttons, "
            "(3) Load mesh with o3d.io.read_triangle_mesh, display with "
            "    VisualizerWithEditing.get_picked_points() for click picking, "
            "(4) On pick event, call self.detector.place_landmark(), update "
            "    the checklist and live measurement preview, "
            "(5) Render suggestion spheres as o3d.geometry.TriangleMesh.create_sphere "
            "    positioned at suggestion coordinates, coloured by confidence, "
            "(6) Export button serialises landmark_set to JSON in output_dir."
        )

    def _load_suggestions(self, curvature_result) -> None:
        """Populate suggestion dict from a CurvatureResult.

        Args:
            curvature_result: Output of CurvatureAnalyzer.analyze().

        Raises:
            NotImplementedError: Not yet implemented (Month 3).
        """
        raise NotImplementedError(
            "TODO: implement in Month 3 — populate _suggestions from CurvatureResult."
        )
