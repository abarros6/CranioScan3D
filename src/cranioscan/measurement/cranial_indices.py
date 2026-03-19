"""Cranial index computation from 3D landmark coordinates.

Implements the standard clinical measurements used in craniosynostosis
assessment, derived from 3D craniometric landmark positions.

All measurements assume landmarks are in millimeter units after scale correction.

References:
    - Loveday & de Chalain (2001). Active helmet therapy or surgery for
      isolated sagittal synostosis?
    - Plank et al. (2006). A 3-dimensional morphometric analysis of isolated
      metopic synostosis.
"""

from __future__ import annotations

import logging
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)


def cephalic_index(
    bitemporal_width: float,
    ap_length: float,
) -> float:
    """Compute the Cephalic Index (CI).

    CI = (maximum head width / maximum AP length) × 100

    Normal range: 75–85. <75 = dolichocephaly, >85 = brachycephaly.

    Args:
        bitemporal_width: Maximum head width (eurion-to-eurion distance) in mm.
        ap_length: Anteroposterior length (glabella-to-opisthocranion) in mm.

    Returns:
        Cephalic index as a percentage [0, 200].

    Raises:
        ValueError: If ap_length is zero or negative.

    Example:
        >>> cephalic_index(bitemporal_width=140.0, ap_length=175.0)
        80.0
    """
    if ap_length <= 0:
        raise ValueError(f"ap_length must be positive, got {ap_length}")
    ci = (bitemporal_width / ap_length) * 100.0
    logger.debug(
        "Cephalic Index: %.1f (width=%.1fmm, AP=%.1fmm)", ci, bitemporal_width, ap_length
    )
    return ci


def cranial_vault_asymmetry_index(
    diagonal_1: float,
    diagonal_2: float,
) -> float:
    """Compute the Cranial Vault Asymmetry Index (CVAI).

    CVAI = |diagonal_1 - diagonal_2| / diagonal_1 × 100

    where diagonal_1 > diagonal_2 by convention (longer diagonal in numerator).

    Normal: <3.5%. Mild: 3.5–6.25%. Moderate: 6.25–8.75%. Severe: >8.75%.

    Args:
        diagonal_1: Length of the first oblique diagonal (mm). Should be the longer one.
        diagonal_2: Length of the second oblique diagonal (mm).

    Returns:
        CVAI as a percentage.

    Raises:
        ValueError: If diagonal_1 is zero or negative.

    Example:
        >>> cranial_vault_asymmetry_index(diagonal_1=180.0, diagonal_2=172.0)
        4.44...
    """
    if diagonal_1 <= 0:
        raise ValueError(f"diagonal_1 must be positive, got {diagonal_1}")
    d1, d2 = max(diagonal_1, diagonal_2), min(diagonal_1, diagonal_2)
    cvai = (abs(d1 - d2) / d1) * 100.0
    logger.debug("CVAI: %.2f%% (d1=%.1fmm, d2=%.1fmm)", cvai, d1, d2)
    return cvai


def ap_length(glabella: np.ndarray, opisthocranion: np.ndarray) -> float:
    """Compute the anteroposterior (AP) cranial length.

    Euclidean distance between glabella and opisthocranion landmarks.

    Args:
        glabella: 3D position of glabella landmark (x, y, z) in mm.
        opisthocranion: 3D position of opisthocranion landmark in mm.

    Returns:
        AP length in millimeters.

    Example:
        >>> import numpy as np
        >>> ap_length(np.array([0, 0, 0]), np.array([175, 0, 0]))
        175.0
    """
    length = float(np.linalg.norm(opisthocranion - glabella))
    logger.debug("AP length: %.2fmm", length)
    return length


def bitemporal_width(eurion_l: np.ndarray, eurion_r: np.ndarray) -> float:
    """Compute the bitemporal (transverse) head width.

    Euclidean distance between left and right eurion landmarks.

    Args:
        eurion_l: 3D position of left eurion landmark in mm.
        eurion_r: 3D position of right eurion landmark in mm.

    Returns:
        Bitemporal width in millimeters.

    Example:
        >>> import numpy as np
        >>> bitemporal_width(np.array([-70, 0, 0]), np.array([70, 0, 0]))
        140.0
    """
    width = float(np.linalg.norm(eurion_r - eurion_l))
    logger.debug("Bitemporal width: %.2fmm", width)
    return width


def head_circumference_arc(
    mesh,
    landmark_positions: list[np.ndarray],
) -> float:
    """Estimate head circumference as arc length along the mesh surface.

    Computes the geodesic arc length passing through the provided landmark
    positions on the mesh surface. This is more accurate than the straight-line
    perimeter for curved surfaces.

    Args:
        mesh: Open3D TriangleMesh or trimesh object with the head surface.
        landmark_positions: Ordered list of 3D positions (in mm) defining the
            circumference path (e.g., [glabella, eurion_r, opisthocranion, eurion_l]).

    Returns:
        Estimated head circumference arc length in millimeters.

    Raises:
        NotImplementedError: Geodesic arc computation not yet implemented.
    """
    raise NotImplementedError(
        "TODO: implement in Month 3 — geodesic head circumference. "
        "Approach: build adjacency graph from mesh edges with Euclidean edge weights, "
        "then run Dijkstra between sequential landmark_positions "
        "(e.g. glabella → eurion_r → opisthocranion → eurion_l → glabella). "
        "Use scipy.sparse.csgraph.shortest_path (already installed). "
        "Steps: (1) find nearest vertex index for each landmark position, "
        "(2) build sparse weight matrix from mesh.triangles edge pairs, "
        "(3) run shortest_path(graph, method='D', indices=vertex_indices), "
        "(4) sum the four arc lengths."
    )


def all_measurements(
    glabella: np.ndarray,
    opisthocranion: np.ndarray,
    eurion_l: np.ndarray,
    eurion_r: np.ndarray,
    diagonal_1: Optional[float] = None,
    diagonal_2: Optional[float] = None,
) -> dict[str, float]:
    """Compute all available cranial measurements from landmark coordinates.

    Args:
        glabella: 3D position of glabella in mm.
        opisthocranion: 3D position of opisthocranion in mm.
        eurion_l: 3D position of left eurion in mm.
        eurion_r: 3D position of right eurion in mm.
        diagonal_1: First oblique diagonal length in mm (optional, for CVAI).
        diagonal_2: Second oblique diagonal length in mm (optional, for CVAI).

    Returns:
        Dict with keys: 'ap_length_mm', 'bitemporal_width_mm', 'cephalic_index',
        and optionally 'cvai' if diagonal values are provided.
    """
    apl = ap_length(glabella, opisthocranion)
    btw = bitemporal_width(eurion_l, eurion_r)
    ci = cephalic_index(btw, apl)

    result: dict[str, float] = {
        "ap_length_mm": apl,
        "bitemporal_width_mm": btw,
        "cephalic_index": ci,
    }

    if diagonal_1 is not None and diagonal_2 is not None:
        result["cvai"] = cranial_vault_asymmetry_index(diagonal_1, diagonal_2)

    logger.info("Measurements: %s", result)
    return result
