"""Re-export compression functions from spine.compression."""
from spine.compression import (
    compress_narrative,
    should_compress,
)

__all__ = [
    "compress_narrative",
    "should_compress",
]
