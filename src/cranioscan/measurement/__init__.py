"""Cranial measurement subpackage.

Provides two modules:

- cranial_indices:  Computes standard craniometric measurements from 3D
                    landmark coordinates (in mm). Fully implemented:
                    cephalic_index(), cranial_vault_asymmetry_index(),
                    ap_length(), bitemporal_width(), all_measurements().
                    head_circumference_arc() is a Month-3 stub.

- report:           Generates a PDF clinical summary report using ReportLab.
                    The ReportData dataclass and ReportGenerator interface
                    are defined; generate() is a Month-4 implementation stub.

All measurement functions assume landmarks are in millimeter units after
scale correction has been applied by cranioscan.mesh.scale.ScaleCorrector.
"""
