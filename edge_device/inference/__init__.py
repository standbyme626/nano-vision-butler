"""Detection interfaces for edge runtime."""

from .detector import Detection, DetectorProtocol, LightweightDetector, create_detector_from_env
from .rknn_detector import RKNNDetector, RKNNDetectorConfig, create_rknn_detector_from_env

__all__ = [
    "Detection",
    "DetectorProtocol",
    "LightweightDetector",
    "create_detector_from_env",
    "RKNNDetector",
    "RKNNDetectorConfig",
    "create_rknn_detector_from_env",
]
