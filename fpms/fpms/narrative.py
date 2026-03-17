"""Re-export narrative functions from spine.narrative."""
from spine.narrative import (
    append_narrative,
    read_compressed,
    read_narrative,
    write_compressed,
    write_repair_event,
)

__all__ = [
    "append_narrative",
    "read_compressed",
    "read_narrative",
    "write_compressed",
    "write_repair_event",
]
