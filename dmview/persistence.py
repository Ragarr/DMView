"""Session persistence - JSON load/save and fog mask management."""

import json
import shutil
from pathlib import Path
from typing import Optional

from PIL import Image

from models import Map, Session


class SessionManager:
    """Manages session file operations."""

    def __init__(self, session_dir: Path):
        """Initialize with session directory path."""
        self.session_dir = Path(session_dir)
        self.session_file = self.session_dir / "session.json"
        self.maps_dir = self.session_dir / "maps"

    @classmethod
    def create_new(cls, base_dir: Path, session_name: str) -> "SessionManager":
        """Create a new session directory structure."""
        session_dir = base_dir / session_name.lower().replace(" ", "_")
        session_dir.mkdir(parents=True, exist_ok=True)
        (session_dir / "maps").mkdir(exist_ok=True)

        manager = cls(session_dir)
        session = Session(name=session_name)
        manager.save_session(session)
        return manager

    @classmethod
    def open_existing(cls, session_dir: Path) -> Optional["SessionManager"]:
        """Open an existing session directory."""
        session_dir = Path(session_dir)
        if not (session_dir / "session.json").exists():
            return None
        return cls(session_dir)

    def save_session(self, session: Session) -> None:
        """Save session to JSON file."""
        with open(self.session_file, "w") as f:
            json.dump(session.to_dict(), f, indent=2)

    def load_session(self) -> Optional[Session]:
        """Load session from JSON file."""
        if not self.session_file.exists():
            return None
        try:
            with open(self.session_file) as f:
                data = json.load(f)
            return Session.from_dict(data)
        except (json.JSONDecodeError, KeyError) as e:
            print(f"Error loading session: {e}")
            return None

    def add_map_from_file(
        self,
        source_path: Path,
        name: str,
        tile_pixels: int = 70,
        tile_size_mm: float = 25.4,
    ) -> Map:
        """Import a map image and create fog mask."""
        source_path = Path(source_path)
        self.maps_dir.mkdir(exist_ok=True)

        # Copy image to maps directory
        dest_filename = source_path.name
        dest_path = self.maps_dir / dest_filename

        # Handle filename conflicts
        counter = 1
        while dest_path.exists():
            stem = source_path.stem
            suffix = source_path.suffix
            dest_filename = f"{stem}_{counter}{suffix}"
            dest_path = self.maps_dir / dest_filename
            counter += 1

        shutil.copy2(source_path, dest_path)

        # Create map object with relative path
        relative_path = f"maps/{dest_filename}"
        map_obj = Map.create(
            name=name,
            image_path=relative_path,
            tile_pixels=tile_pixels,
            tile_size_mm=tile_size_mm,
        )

        # Create fog mask (all black = all hidden)
        self.create_fog_mask(map_obj)

        return map_obj

    def create_fog_mask(self, map_obj: Map) -> None:
        """Create a blank fog mask for a map (all black = all hidden)."""
        image_path = self.session_dir / map_obj.image_path
        fog_path = self.session_dir / map_obj.fog_path

        with Image.open(image_path) as img:
            width, height = img.size

        # Create all-black mask (fully hidden)
        fog = Image.new("L", (width, height), 0)
        fog.save(fog_path)

    def get_map_image_path(self, map_obj: Map) -> Path:
        """Get absolute path to map image."""
        return self.session_dir / map_obj.image_path

    def get_fog_path(self, map_obj: Map) -> Path:
        """Get absolute path to fog mask."""
        return self.session_dir / map_obj.fog_path

    def load_map_image(self, map_obj: Map) -> Optional[Image.Image]:
        """Load map image as PIL Image."""
        path = self.get_map_image_path(map_obj)
        if path.exists():
            return Image.open(path)
        return None

    def load_fog_mask(self, map_obj: Map) -> Optional[Image.Image]:
        """Load fog mask as PIL Image (grayscale)."""
        path = self.get_fog_path(map_obj)
        if path.exists():
            return Image.open(path).convert("L")
        return None

    def save_fog_mask(self, map_obj: Map, fog: Image.Image) -> None:
        """Save fog mask to disk."""
        path = self.get_fog_path(map_obj)
        fog.save(path)

    def delete_map(self, map_obj: Map) -> None:
        """Delete map image and fog mask files."""
        image_path = self.get_map_image_path(map_obj)
        fog_path = self.get_fog_path(map_obj)

        if image_path.exists():
            image_path.unlink()
        if fog_path.exists():
            fog_path.unlink()
