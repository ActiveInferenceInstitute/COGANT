from cogant.schema.detector import detect_version as detect_version
from cogant.schema.versions import CURRENT_GNN_VERSION as CURRENT_GNN_VERSION
from cogant.schema.versions import GNN_V2_REQUIRED_SECTIONS as GNN_V2_REQUIRED_SECTIONS
from cogant.schema.versions import UNSUPPORTED_GNN_VERSION as UNSUPPORTED_GNN_VERSION

__all__ = [
    "CURRENT_GNN_VERSION",
    "UNSUPPORTED_GNN_VERSION",
    "GNN_V2_REQUIRED_SECTIONS",
    "detect_version",
]
