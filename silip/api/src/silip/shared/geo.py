"""The map's bounding-box filter, shared by every feature that serves map points."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BoundingBox:
    """`min_lon,min_lat,max_lon,max_lat`, as in the `bbox` query parameter."""

    min_lon: float
    min_lat: float
    max_lon: float
    max_lat: float

    @classmethod
    def parse(cls, text: str) -> BoundingBox:
        """Raises ValueError if `text` is not four comma-separated numbers in order."""
        parts = [float(part) for part in text.split(",")]
        if len(parts) != 4 or parts[0] > parts[2] or parts[1] > parts[3]:
            raise ValueError("bbox must be min_lon,min_lat,max_lon,max_lat")
        return cls(*parts)

    def contains(self, lat: float, lon: float) -> bool:
        return self.min_lat <= lat <= self.max_lat and self.min_lon <= lon <= self.max_lon
