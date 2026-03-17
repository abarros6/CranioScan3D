"""PDF report generation for cranial measurement results.

Generates a clinical summary PDF containing measurement values, reference
ranges, mesh visualization screenshots, and capture metadata.

TODO (Month 4): Implement using ReportLab. The interface is defined here.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class ReportData:
    """Data bundle for report generation.

    Attributes:
        subject_id: Anonymized subject identifier.
        capture_date: Date of iPhone video capture (ISO 8601 string).
        measurements: Dict of measurement name -> value (mm or %).
        mesh_screenshot_path: Path to a rendered mesh image for the report.
        notes: Optional clinical notes string.
    """

    subject_id: str
    capture_date: str
    measurements: dict[str, float]
    mesh_screenshot_path: Optional[Path] = None
    notes: Optional[str] = None


class ReportGenerator:
    """Generates a PDF clinical report from cranial measurements.

    The report includes:
      - Patient/subject identifier and capture date
      - Measurement table with values and normative ranges
      - Mesh visualization screenshot
      - Interpretation summary (normal / borderline / abnormal per measure)

    Attributes:
        output_dir: Directory where PDF reports are written.
    """

    def __init__(self, output_dir: Path) -> None:
        """Initialize ReportGenerator.

        Args:
            output_dir: Directory to write generated PDF reports.
        """
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate(self, data: ReportData) -> Path:
        """Generate a PDF report for one subject.

        Args:
            data: ReportData bundle with measurements and metadata.

        Returns:
            Path to the generated PDF file.

        Raises:
            NotImplementedError: Not yet implemented (Month 4).
        """
        raise NotImplementedError(
            "TODO: implement in Month 4 — PDF report generation with ReportLab. "
            "Steps: (1) create ReportLab SimpleDocTemplate, "
            "(2) build measurement table with clinical reference ranges, "
            "(3) embed mesh screenshot if provided, "
            "(4) add interpretation summary per measurement, "
            "(5) save to output_dir / f'{data.subject_id}_report.pdf'."
        )
