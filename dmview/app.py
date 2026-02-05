"""Application coordinator - manages views, session, and state."""

import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog
from typing import Optional

from PIL import Image

from config import Config
from dm_view import DMView
from map_canvas import FogEditor, calculate_scale
from models import Map, Session
from persistence import SessionManager
from player_view import PlayerView


class Application:
    """Main application coordinator."""

    def __init__(self, root: tk.Tk):
        """
        Initialize the application.

        Args:
            root: The Tk root window
        """
        self.root = root
        self.config = Config.load()

        # Session state
        self.session: Optional[Session] = None
        self.session_manager: Optional[SessionManager] = None

        # Image caches
        self._map_images: dict[str, Image.Image] = {}
        self._fog_masks: dict[str, Image.Image] = {}

        # Monitor info
        self.monitors = self._detect_monitors()
        self.player_monitor = None
        self.dm_monitor = None
        self._select_monitors()

        # Create views
        self.dm_view = DMView(root, self)
        self.player_view = PlayerView(root, self)

        # Hide player view by default
        self.player_view.hide()

        # Position and show player view only when using a separate monitor
        if self.player_monitor:
            self.player_view.set_fullscreen(
                self.player_monitor["x"],
                self.player_monitor["y"],
                self.player_monitor["width"],
                self.player_monitor["height"],
            )
            self.player_view.show()

        # Load last session if available
        if self.config.last_session_path:
            self._try_load_session(Path(self.config.last_session_path))

        # Set up window close handler
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _detect_monitors(self) -> list[dict]:
        """Detect available monitors with their properties."""
        monitors = []
        try:
            from screeninfo import get_monitors

            for i, m in enumerate(get_monitors()):
                monitors.append({
                    "index": i,
                    "name": m.name or f"Monitor {i + 1}",
                    "x": m.x,
                    "y": m.y,
                    "width": m.width,
                    "height": m.height,
                    "width_mm": m.width_mm or 0,
                    "height_mm": m.height_mm or 0,
                    "is_primary": m.is_primary,
                })
        except ImportError:
            # Fallback if screeninfo not available
            monitors.append({
                "index": 0,
                "name": "Primary",
                "x": 0,
                "y": 0,
                "width": self.root.winfo_screenwidth(),
                "height": self.root.winfo_screenheight(),
                "width_mm": 0,
                "height_mm": 0,
                "is_primary": True,
            })
        return monitors

    def _select_monitors(self) -> None:
        """Select which monitors to use for DM and player views."""
        if len(self.monitors) == 1:
            # Single monitor - use it for DM only; don't show player window by default
            self.dm_monitor = self.monitors[0]
            self.player_monitor = None
            return

        # Multiple monitors - find primary for DM, secondary for player
        primary = None
        secondary = None

        for m in self.monitors:
            if m["is_primary"]:
                primary = m
            else:
                if secondary is None:
                    secondary = m

        if primary is None:
            primary = self.monitors[0]
        if secondary is None:
            secondary = self.monitors[1] if len(self.monitors) > 1 else primary

        # Use configured player monitor if valid
        if 0 <= self.config.player_monitor < len(self.monitors):
            candidate = self.monitors[self.config.player_monitor]
            # If user selected the same monitor as the DM, disable the player view
            if candidate["index"] == primary["index"]:
                secondary = None
            else:
                secondary = candidate

        # If secondary ended up being the same as primary, disable it
        if secondary and secondary["index"] == primary["index"]:
            secondary = None

        self.dm_monitor = primary
        self.player_monitor = secondary

    def _get_player_ppmm(self) -> float:
        """Get pixels per mm for the player monitor."""
        if self.player_monitor and self.player_monitor["width_mm"] > 0:
            return self.player_monitor["width"] / self.player_monitor["width_mm"]
        # Default fallback (typical 24" 1080p monitor)
        return 3.78  # ~96 DPI

    def get_active_map(self) -> Optional[Map]:
        """Get the currently active map."""
        if self.session:
            return self.session.active_map
        return None

    def get_current_fog(self) -> Optional[Image.Image]:
        """Get the current fog mask image."""
        active_map = self.get_active_map()
        if active_map and active_map.id in self._fog_masks:
            return self._fog_masks[active_map.id].copy()
        return None

    def _try_load_session(self, session_dir: Path) -> bool:
        """Try to load a session from directory."""
        manager = SessionManager.open_existing(session_dir)
        if manager:
            session = manager.load_session()
            if session:
                self.session = session
                self.session_manager = manager
                self._load_map_images()
                self._update_views()
                return True
        return False

    def _load_map_images(self) -> None:
        """Load all map images and fog masks for current session."""
        if not self.session or not self.session_manager:
            return

        self._map_images.clear()
        self._fog_masks.clear()

        for map_obj in self.session.maps:
            img = self.session_manager.load_map_image(map_obj)
            if img:
                self._map_images[map_obj.id] = img.convert("RGBA")

            fog = self.session_manager.load_fog_mask(map_obj)
            if fog:
                self._fog_masks[map_obj.id] = fog

    def _update_views(self) -> None:
        """Update both views with current state."""
        if not self.session:
            return

        active_map = self.session.active_map
        if active_map and active_map.id in self._map_images:
            map_img = self._map_images[active_map.id]
            fog_img = self._fog_masks.get(active_map.id)

            if fog_img:
                # Calculate scale for player view
                ppmm = self._get_player_ppmm()
                scale = calculate_scale(
                    active_map.tile_pixels,
                    active_map.tile_size_mm,
                    ppmm,
                )

                self.dm_view.set_map(map_img, fog_img)
                self.player_view.set_map(map_img, fog_img)
                self.player_view.set_scale(scale)

        # Update map list
        self.dm_view.update_map_list(
            self.session.maps,
            self.session.active_map_index,
        )

    def new_session(self) -> None:
        """Create a new session."""
        name = simpledialog.askstring("New Session", "Enter session name:", parent=self.root)
        if not name:
            return

        base_dir = Path(self.config.sessions_dir)
        base_dir.mkdir(parents=True, exist_ok=True)

        try:
            self.session_manager = SessionManager.create_new(base_dir, name)
            self.session = Session(name=name)
            self.session_manager.save_session(self.session)

            self._map_images.clear()
            self._fog_masks.clear()
            self._update_views()

            self.config.last_session_path = str(self.session_manager.session_dir)
            self.config.save()

        except Exception as e:
            messagebox.showerror("Error", f"Failed to create session: {e}", parent=self.root)

    def open_session(self) -> None:
        """Open an existing session."""
        initial_dir = self.config.sessions_dir
        session_dir = filedialog.askdirectory(
            parent=self.root,
            title="Select Session Directory",
            initialdir=initial_dir,
        )

        if session_dir:
            if self._try_load_session(Path(session_dir)):
                self.config.last_session_path = session_dir
                self.config.save()
            else:
                messagebox.showerror("Error", "Invalid session directory", parent=self.root)

    def save_session(self) -> None:
        """Save the current session."""
        if not self.session or not self.session_manager:
            return

        # Save session JSON
        self.session_manager.save_session(self.session)

        # Save all fog masks
        for map_obj in self.session.maps:
            if map_obj.id in self._fog_masks:
                self.session_manager.save_fog_mask(
                    map_obj,
                    self._fog_masks[map_obj.id],
                )

    def add_map(self, filepath: str, name: str, tile_pixels: int | None = None, tile_size_mm: float | None = None) -> None:
        """Add a new map to the session.

        If tile_pixels and tile_size_mm are provided, they are used directly. If
        not, fall back to the interactive prompts (legacy flow).
        """
        if not self.session or not self.session_manager:
            return

        try:
            if tile_pixels is not None and tile_size_mm is not None:
                # Import directly with provided settings
                map_obj = self.session_manager.add_map_from_file(
                    Path(filepath),
                    name,
                    tile_pixels=tile_pixels,
                    tile_size_mm=float(tile_size_mm),
                )
            else:
                # Legacy interactive prompts (kept for compatibility)
                # Open source image to inspect dimensions (do not copy yet)
                with Image.open(Path(filepath)) as src_img:
                    img_w, img_h = src_img.size

                # Ask user which method to use
                method = simpledialog.askstring(
                    "Map Scale",
                    "Choose scale input method:\n\n"
                    "1 - Enter overall image width in mm (and optional tile size)\n"
                    "2 - Enter number of tiles across and tile size in mm\n\n"
                    "Enter 1 or 2:",
                    parent=self.root,
                )

                if not method:
                    return  # user cancelled

                method = method.strip()
                if method not in ("1", "2"):
                    messagebox.showerror("Invalid option", "Please enter 1 or 2.", parent=self.root)
                    return

                t_size_mm = None
                t_pixels = None

                if method == "1":
                    # Overall image width in mm
                    width_mm = simpledialog.askfloat(
                        "Image width (mm)",
                        "Enter overall image width in millimeters:",
                        parent=self.root,
                        minvalue=1.0,
                    )
                    if width_mm is None:
                        return

                    # Optional: let user specify tile size, otherwise use default
                    t_size_mm = simpledialog.askfloat(
                        "Tile size (mm)",
                        f"Enter tile size in millimeters (default {self.config.default_tile_size_mm} mm):",
                        parent=self.root,
                        minvalue=0.1,
                    )
                    if t_size_mm is None:
                        t_size_mm = self.config.default_tile_size_mm

                    ppmm = img_w / float(width_mm)
                    t_pixels = max(1, int(round(ppmm * float(t_size_mm))))

                else:  # method == "2"
                    tiles_x = simpledialog.askinteger(
                        "Tiles across",
                        "Enter number of tiles across (columns):",
                        parent=self.root,
                        minvalue=1,
                    )
                    if tiles_x is None:
                        return

                    t_size_mm = simpledialog.askfloat(
                        "Tile size (mm)",
                        f"Enter tile size in millimeters (default {self.config.default_tile_size_mm} mm):",
                        parent=self.root,
                        minvalue=0.1,
                    )
                    if t_size_mm is None:
                        t_size_mm = self.config.default_tile_size_mm

                    # Compute pixels per tile from image width and number of tiles
                    t_pixels = max(1, int(round(img_w / float(tiles_x))))

                # Confirm computed values with the user
                if not messagebox.askyesno(
                    "Confirm Scale",
                    f"Computed tile size: {t_size_mm} mm\nComputed pixels per tile: {t_pixels}\n\nProceed?",
                    parent=self.root,
                ):
                    return

                map_obj = self.session_manager.add_map_from_file(
                    Path(filepath),
                    name,
                    tile_pixels=t_pixels,
                    tile_size_mm=float(t_size_mm),
                )

            self.session.add_map(map_obj)
            self.session_manager.save_session(self.session)

            # Load the new map
            img = self.session_manager.load_map_image(map_obj)
            if img:
                self._map_images[map_obj.id] = img.convert("RGBA")

            fog = self.session_manager.load_fog_mask(map_obj)
            if fog:
                self._fog_masks[map_obj.id] = fog

            # Select the new map
            self.session.set_active_map(map_obj.id)
            self._update_views()

        except Exception as e:
            messagebox.showerror("Error", f"Failed to add map: {e}", parent=self.root)

    def remove_map(self, index: int) -> None:
        """Remove a map by index."""
        if not self.session or not self.session_manager:
            return

        if 0 <= index < len(self.session.maps):
            map_obj = self.session.maps[index]

            # Remove from caches
            self._map_images.pop(map_obj.id, None)
            self._fog_masks.pop(map_obj.id, None)

            # Delete files
            self.session_manager.delete_map(map_obj)

            # Remove from session
            self.session.remove_map(map_obj.id)
            self.session_manager.save_session(self.session)

            self._update_views()

    def select_map(self, index: int) -> None:
        """Select a map by index."""
        if not self.session:
            return

        if 0 <= index < len(self.session.maps):
            self.session.active_map_index = index
            self._update_views()

    def update_fog(self, fog_mask: Image.Image) -> None:
        """Update the fog mask for the active map."""
        active_map = self.get_active_map()
        if not active_map:
            return

        self._fog_masks[active_map.id] = fog_mask

        # Update both views
        self.dm_view.update_fog(fog_mask)
        self.player_view.update_fog(fog_mask)

        # Auto-save fog
        if self.session_manager:
            self.session_manager.save_fog_mask(active_map, fog_mask)

    def reveal_all(self) -> None:
        """Reveal the entire active map."""
        fog = self.get_current_fog()
        if fog:
            editor = FogEditor(fog)
            editor.reveal_all()
            self.update_fog(editor.get_mask())

    def hide_all(self) -> None:
        """Hide the entire active map."""
        fog = self.get_current_fog()
        if fog:
            editor = FogEditor(fog)
            editor.hide_all()
            self.update_fog(editor.get_mask())

    def pan_map(self, dx: int, dy: int) -> None:
        """Pan the map by the given delta.

        Clamp pan so the player's viewport always stays within the map bounds
        (based on the player view's current scale and size). Refresh both
        player and DM views so overlays update in real time.
        """
        active_map = self.get_active_map()
        if not active_map:
            return

        active_map.pan_x += dx
        active_map.pan_y += dy

        # Clamp to valid range based on player viewport size (in map pixels)
        if active_map.id in self._map_images:
            img = self._map_images[active_map.id]

            # Default to full image (no panning possible)
            viewport_map_w = img.width
            viewport_map_h = img.height

            try:
                pv = self.player_view
                pv_w = pv.canvas.winfo_width()
                pv_h = pv.canvas.winfo_height()
                if pv_w > 1 and pv_h > 1 and pv.renderer.scale > 0:
                    viewport_map_w = int(pv_w / pv.renderer.scale)
                    viewport_map_h = int(pv_h / pv.renderer.scale)
            except Exception:
                # If we can't query player view, fall back to full image
                viewport_map_w = img.width
                viewport_map_h = img.height

            max_pan_x = max(0, img.width - viewport_map_w)
            max_pan_y = max(0, img.height - viewport_map_h)

            active_map.pan_x = max(0, min(active_map.pan_x, max_pan_x))
            active_map.pan_y = max(0, min(active_map.pan_y, max_pan_y))

        # Refresh both views so overlay and player display update
        try:
            self.player_view.refresh()
        except Exception:
            pass
        try:
            self.dm_view.refresh()
        except Exception:
            pass

    def _on_close(self) -> None:
        """Handle application close."""
        self.save_session()
        self.config.save()
        self.player_view.destroy()
        self.root.destroy()

    def run(self) -> None:
        """Run the application main loop."""
        self.root.mainloop()
