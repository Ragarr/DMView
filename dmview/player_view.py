"""Player view - fullscreen display window for the projector/player monitor."""

import tkinter as tk
from typing import TYPE_CHECKING, Optional

from PIL import Image, ImageTk

from map_canvas import MapRenderer

if TYPE_CHECKING:
    from app import Application


class PlayerView:
    """Fullscreen window displaying the map on the player monitor."""

    def __init__(self, root: tk.Tk, app: "Application"):
        """
        Initialize the player view.

        Args:
            root: The Tk root window
            app: The main application instance
        """
        self.app = app
        self.renderer = MapRenderer()

        # Create toplevel window
        self.window = tk.Toplevel(root)
        self.window.title("DMView - Player Display")
        self.window.configure(bg="black")

        # Remove window decorations for fullscreen
        self.window.overrideredirect(True)

        # Create canvas for display
        self.canvas = tk.Canvas(
            self.window,
            bg="black",
            highlightthickness=0,
        )
        self.canvas.pack(fill=tk.BOTH, expand=True)

        # Store current image reference to prevent garbage collection
        self._current_image: Optional[ImageTk.PhotoImage] = None
        self._canvas_image_id: Optional[int] = None

        # Bind resize event
        self.canvas.bind("<Configure>", self._on_resize)

    def position_on_monitor(self, x: int, y: int, width: int, height: int) -> None:
        """Position the window on the specified monitor area."""
        self.window.geometry(f"{width}x{height}+{x}+{y}")

    def set_fullscreen(self, monitor_x: int, monitor_y: int, width: int, height: int) -> None:
        """Set the window to fullscreen on the specified monitor."""
        self.position_on_monitor(monitor_x, monitor_y, width, height)
        self.window.attributes("-topmost", True)
        self.window.lift()

    def set_map(self, map_image: Image.Image, fog_mask: Image.Image) -> None:
        """Set the map and fog mask to display."""
        self.renderer.set_map(map_image, fog_mask)
        self.refresh()

    def set_scale(self, scale: float) -> None:
        """Set the display scale."""
        self.renderer.set_scale(scale)
        self.refresh()

    def update_fog(self, fog_mask: Image.Image) -> None:
        """Update the fog mask and refresh display."""
        if self.renderer.map_image is not None:
            self.renderer.fog_mask = fog_mask.convert("L")
            self.renderer.invalidate_cache()
            self.refresh()

    def refresh(self) -> None:
        """Refresh the display with current map state."""
        if self.renderer.map_image is None:
            return

        # Get viewport size
        width = self.canvas.winfo_width()
        height = self.canvas.winfo_height()

        if width <= 1 or height <= 1:
            return

        # Get pan position from active map
        pan_x, pan_y = 0, 0
        active_map = self.app.get_active_map()
        if active_map:
            pan_x = active_map.pan_x
            pan_y = active_map.pan_y

        # Render the map
        self._current_image = self.renderer.render(
            viewport_size=(width, height),
            pan_x=pan_x,
            pan_y=pan_y,
            is_dm_view=False,
        )

        if self._current_image:
            # Clear and redraw
            self.canvas.delete("all")
            self._canvas_image_id = self.canvas.create_image(
                width // 2,
                height // 2,
                image=self._current_image,
                anchor=tk.CENTER,
            )

    def _on_resize(self, event: tk.Event) -> None:
        """Handle canvas resize."""
        self.refresh()

    def show(self) -> None:
        """Show the player window."""
        self.window.deiconify()

    def hide(self) -> None:
        """Hide the player window."""
        self.window.withdraw()

    def destroy(self) -> None:
        """Destroy the player window."""
        self.window.destroy()
