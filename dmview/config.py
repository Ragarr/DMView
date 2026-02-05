"""User configuration management for DMView."""

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


def get_config_dir() -> Path:
    """Get the configuration directory path."""
    if os.name == "nt":
        base = Path(os.environ.get("APPDATA", Path.home()))
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return base / "dmview"


@dataclass
class Config:
    """User configuration settings."""

    # Last opened session path
    last_session_path: Optional[str] = None

    # Default sessions directory
    sessions_dir: str = field(default_factory=lambda: str(Path.cwd() / "sessions"))

    # Default values for new maps
    default_tile_pixels: int = 70
    default_tile_size_mm: float = 25.4

    # Brush settings
    brush_size: int = 30

    # Player monitor index (0-based, -1 for auto/last)
    player_monitor: int = -1

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "last_session_path": self.last_session_path,
            "sessions_dir": self.sessions_dir,
            "default_tile_pixels": self.default_tile_pixels,
            "default_tile_size_mm": self.default_tile_size_mm,
            "brush_size": self.brush_size,
            "player_monitor": self.player_monitor,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Config":
        """Create from dictionary loaded from JSON."""
        return cls(
            last_session_path=data.get("last_session_path"),
            sessions_dir=data.get("sessions_dir", str(Path.cwd() / "sessions")),
            default_tile_pixels=data.get("default_tile_pixels", 70),
            default_tile_size_mm=data.get("default_tile_size_mm", 25.4),
            brush_size=data.get("brush_size", 30),
            player_monitor=data.get("player_monitor", -1),
        )

    def save(self) -> None:
        """Save configuration to disk."""
        config_dir = get_config_dir()
        config_dir.mkdir(parents=True, exist_ok=True)
        config_file = config_dir / "config.json"
        with open(config_file, "w") as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def load(cls) -> "Config":
        """Load configuration from disk, or return defaults if not found."""
        config_file = get_config_dir() / "config.json"
        if config_file.exists():
            try:
                with open(config_file) as f:
                    return cls.from_dict(json.load(f))
            except (json.JSONDecodeError, KeyError):
                pass
        return cls()
