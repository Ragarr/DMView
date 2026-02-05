"""Data classes for DMView sessions and maps."""

from dataclasses import dataclass, field
from typing import Optional
import uuid


@dataclass
class Map:
    """Represents a single map with its fog state."""

    id: str
    name: str
    image_path: str  # Relative to session dir
    fog_path: str  # Fog mask PNG
    tile_size_mm: float = 25.4  # Physical tile size (default 1 inch)
    tile_pixels: int = 70  # Pixels per tile in source image
    pan_x: int = 0  # Current pan position
    pan_y: int = 0

    @classmethod
    def create(
        cls,
        name: str,
        image_path: str,
        tile_pixels: int = 70,
        tile_size_mm: float = 25.4,
    ) -> "Map":
        """Create a new map with auto-generated ID and fog path."""
        map_id = str(uuid.uuid4())[:8]
        fog_path = image_path.rsplit(".", 1)[0] + "_fog.png"
        return cls(
            id=map_id,
            name=name,
            image_path=image_path,
            fog_path=fog_path,
            tile_pixels=tile_pixels,
            tile_size_mm=tile_size_mm,
        )

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "name": self.name,
            "image_file": self.image_path,
            "fog_file": self.fog_path,
            "tile_size_mm": self.tile_size_mm,
            "tile_pixels": self.tile_pixels,
            "pan_x": self.pan_x,
            "pan_y": self.pan_y,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Map":
        """Create from dictionary loaded from JSON."""
        return cls(
            id=data["id"],
            name=data["name"],
            image_path=data["image_file"],
            fog_path=data["fog_file"],
            tile_size_mm=data.get("tile_size_mm", 25.4),
            tile_pixels=data.get("tile_pixels", 70),
            pan_x=data.get("pan_x", 0),
            pan_y=data.get("pan_y", 0),
        )


@dataclass
class Session:
    """Represents a DMView session containing multiple maps."""

    name: str
    maps: list[Map] = field(default_factory=list)
    active_map_index: int = 0

    @property
    def active_map(self) -> Optional[Map]:
        """Get the currently active map, or None if no maps exist."""
        if 0 <= self.active_map_index < len(self.maps):
            return self.maps[self.active_map_index]
        return None

    def add_map(self, map_obj: Map) -> None:
        """Add a map to the session."""
        self.maps.append(map_obj)

    def remove_map(self, map_id: str) -> bool:
        """Remove a map by ID. Returns True if removed."""
        for i, m in enumerate(self.maps):
            if m.id == map_id:
                self.maps.pop(i)
                if self.active_map_index >= len(self.maps):
                    self.active_map_index = max(0, len(self.maps) - 1)
                return True
        return False

    def set_active_map(self, map_id: str) -> bool:
        """Set active map by ID. Returns True if found."""
        for i, m in enumerate(self.maps):
            if m.id == map_id:
                self.active_map_index = i
                return True
        return False

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "name": self.name,
            "active_map_index": self.active_map_index,
            "maps": [m.to_dict() for m in self.maps],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Session":
        """Create from dictionary loaded from JSON."""
        return cls(
            name=data["name"],
            maps=[Map.from_dict(m) for m in data.get("maps", [])],
            active_map_index=data.get("active_map_index", 0),
        )
