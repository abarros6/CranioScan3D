"""Semi-automatic craniometric landmark detection coordinator.

Defines the set of craniometric landmarks relevant for craniosynostosis
assessment and coordinates their detection using curvature-based suggestions
and (eventually) a GUI for manual confirmation.

Landmark definitions follow the standard craniometric convention as used in
clinical cephalometry and anthropology.

TODO (Month 3): Integrate with CurvatureAnalyzer output and the landmark GUI.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)


class LandmarkId(str, Enum):
    """Standard craniometric landmark identifiers.

    Based on the landmark set used in clinical craniosynostosis assessment.
    """

    GLABELLA = "glabella"               # Most anterior point of forehead at midline
    OPISTHOCRANION = "opisthocranion"   # Most posterior point of skull at midline
    EURION_L = "eurion_l"               # Most lateral point of skull, left side
    EURION_R = "eurion_r"               # Most lateral point of skull, right side
    VERTEX = "vertex"                   # Highest point of skull
    BREGMA = "bregma"                   # Junction of coronal and sagittal sutures
    LAMBDA = "lambda"                   # Junction of sagittal and lambdoid sutures
    NASION = "nasion"                   # Root of nose / fronto-nasal suture
    METOPION = "metopion"               # Highest point of the frontal bone


@dataclass
class Landmark:
    """A single detected or placed craniometric landmark.

    Attributes:
        id: Landmark identifier.
        position: 3D position in mesh coordinate space (x, y, z) in mm.
        confidence: Detection confidence [0, 1]. 1.0 for manually placed.
        vertex_index: Nearest mesh vertex index, if available.
    """

    id: LandmarkId
    position: np.ndarray  # shape (3,)
    confidence: float = 1.0
    vertex_index: Optional[int] = None


@dataclass
class LandmarkSet:
    """Complete set of craniometric landmarks for one subject.

    Attributes:
        landmarks: Dict mapping LandmarkId to Landmark instances.
        complete: Whether all required landmarks are placed.
    """

    landmarks: dict[LandmarkId, Landmark] = field(default_factory=dict)

    @property
    def complete(self) -> bool:
        """Return True if all required landmarks are placed."""
        required = {
            LandmarkId.GLABELLA,
            LandmarkId.OPISTHOCRANION,
            LandmarkId.EURION_L,
            LandmarkId.EURION_R,
        }
        return required.issubset(self.landmarks.keys())

    def get_position(self, landmark_id: LandmarkId) -> Optional[np.ndarray]:
        """Get the 3D position of a landmark.

        Args:
            landmark_id: The landmark to retrieve.

        Returns:
            3D position array (x, y, z) or None if not placed.
        """
        lm = self.landmarks.get(landmark_id)
        return lm.position if lm else None


class LandmarkDetector:
    """Coordinates semi-automatic landmark detection.

    Combines curvature-based suggestions from CurvatureAnalyzer with
    manual placement via the GUI. Acts as the bridge between automated
    detection and user interaction.

    Attributes:
        landmark_set: Current set of placed/detected landmarks.
    """

    def __init__(self) -> None:
        """Initialize LandmarkDetector with an empty landmark set."""
        self.landmark_set = LandmarkSet()

    def suggest_from_curvature(self, curvature_result) -> dict[LandmarkId, np.ndarray]:
        """Generate landmark position suggestions from curvature analysis.

        Args:
            curvature_result: CurvatureResult from CurvatureAnalyzer.analyze().

        Returns:
            Dict mapping LandmarkId to suggested 3D position.

        Raises:
            NotImplementedError: Not yet implemented (Month 3).
        """
        raise NotImplementedError(
            "TODO: implement in Month 3 — curvature-based landmark suggestion. "
            "Strategy per landmark (vertices array is mesh.vertices, SI = curvature_result.shape_index):\n"
            "  GLABELLA:       SI > 0.7 candidates → most anterior (max Y or min Z depending on orientation)\n"
            "  OPISTHOCRANION: SI > 0.7 candidates → most posterior; maximises distance from glabella\n"
            "  EURION_L:       SI > 0.4 candidates → leftmost (min X)\n"
            "  EURION_R:       SI > 0.4 candidates → rightmost (max X)\n"
            "  VERTEX:         SI > 0.7 candidates → highest (max Z or Y)\n"
            "All suggestions get confidence = normalised SI score. "
            "Return dict[LandmarkId, np.ndarray] of suggested positions for API/GUI."
        )

    def place_landmark(
        self,
        landmark_id: LandmarkId,
        position: np.ndarray,
        confidence: float = 1.0,
    ) -> None:
        """Place or update a landmark at a given 3D position.

        Args:
            landmark_id: The landmark to place.
            position: 3D position in mesh coordinate space (x, y, z).
            confidence: Detection confidence [0, 1].
        """
        self.landmark_set.landmarks[landmark_id] = Landmark(
            id=landmark_id, position=position, confidence=confidence
        )
        logger.info(
            "Placed landmark %s at %s (confidence=%.2f)", landmark_id, position, confidence
        )
