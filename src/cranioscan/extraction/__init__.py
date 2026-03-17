"""Frame extraction subpackage.

Provides the FrameExtractor class for sampling sharp, evenly-spaced frames
from iPhone video files (.mp4, .mov). Extracted frames are written to disk
as JPEG/PNG images suitable for input to COLMAP feature extraction.

Typical usage:
    from cranioscan.extraction.frame_extractor import FrameExtractor
    from cranioscan.config import ExtractionConfig

    config = ExtractionConfig(frame_interval=15, blur_threshold=100.0)
    extractor = FrameExtractor(config)
    saved_paths = extractor.extract(Path("video.mp4"), Path("data/frames/"))
"""
