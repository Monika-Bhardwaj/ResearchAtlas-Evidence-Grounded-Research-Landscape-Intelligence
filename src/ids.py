"""Entity-id format helpers. An id is '<prefix>:<slug>', and the prefix fixes the entity type."""
from __future__ import annotations

import re
from typing import Tuple

ID_PATTERN = r"^[a-z]+:[a-z0-9][a-z0-9_.\-]*$"
PAPER_ID_PATTERN = r"^paper:[a-z0-9][a-z0-9_.\-]*$"
_ID_RE = re.compile(ID_PATTERN)


def split_id(entity_id: str) -> Tuple[str, str]:
    """Return (prefix, local). Raises ValueError for a malformed id."""
    if not _ID_RE.match(entity_id):
        raise ValueError(f"malformed entity id: {entity_id!r}")
    prefix, local = entity_id.split(":", 1)
    return prefix, local
