"""Shared rendering logic for map display with fog of war."""

from typing import Optional, Tuple

from PIL import Image, ImageDraw, ImageOps, ImageTk


class MapRenderer:
    """Handles map rendering with fog of war compositing."""

    def __init__(self):
        """Initialize renderer."""
        self.map_image: Optional[Image.Image] = None
        self.fog_mask: Optional[Image.Image] = None
        self.scale: float = 1.0
        self._cached_render: Optional[Image.Image] = None
        self._cache_valid: bool = False

    def set_map(self, map_image: Image.Image, fog_mask: Image.Image) -> None:
        """Set the map image and fog mask."""
        self.map_image = map_image.convert("RGBA")
        self.fog_mask = fog_mask.convert("L")
        self._cache_valid = False

    def set_scale(self, scale: float) -> None:
        """Set the rendering scale."""
        if self.scale != scale:
            self.scale = scale
            self._cache_valid = False

    def invalidate_cache(self) -> None:
        """Mark the render cache as invalid."""
        self._cache_valid = False

    def render(
        self,
        viewport_size: Tuple[int, int],
        pan_x: int,
        pan_y: int,
        is_dm_view: bool = False,
    ) -> Optional[ImageTk.PhotoImage]:
        """
        Render the map with fog overlay for the given viewport.

        Args:
            viewport_size: (width, height) of the display area
            pan_x: Horizontal pan offset in map pixels
            pan_y: Vertical pan offset in map pixels
            is_dm_view: If True, fog is semi-transparent; if False, fully opaque

        Returns:
            PhotoImage ready for Tkinter display, or None if no map loaded
        """
        if self.map_image is None or self.fog_mask is None:
            return None

        viewport_w, viewport_h = viewport_size

        # Calculate scaled dimensions
        scaled_w = int(self.map_image.width * self.scale)
        scaled_h = int(self.map_image.height * self.scale)

        # Scale map and fog
        scaled_map = self.map_image.resize((scaled_w, scaled_h), Image.LANCZOS)
        scaled_fog = self.fog_mask.resize((scaled_w, scaled_h), Image.NEAREST)

        # Create fog overlay
        fog_opacity = 120 if is_dm_view else 255

        # Invert fog mask: black (hidden) becomes opaque, white (revealed) becomes transparent
        inverted_fog = ImageOps.invert(scaled_fog)

        # Scale inverted mask by desired opacity so DM view fog is semi-transparent
        # (i.e. multiply each pixel by fog_opacity / 255)
        alpha_mask = inverted_fog.point(lambda p: int(p * fog_opacity / 255))
        fog_rgba = Image.new("RGBA", (scaled_w, scaled_h), (0, 0, 0, 0))
        fog_rgba.putalpha(alpha_mask)

        # Composite fog over map
        composited = Image.alpha_composite(scaled_map, fog_rgba)

        # Calculate crop region based on pan
        scaled_pan_x = int(pan_x * self.scale)
        scaled_pan_y = int(pan_y * self.scale)

        # Crop to viewport
        left = scaled_pan_x
        top = scaled_pan_y
        right = min(left + viewport_w, scaled_w)
        bottom = min(top + viewport_h, scaled_h)

        # Ensure valid crop region
        left = max(0, min(left, scaled_w - 1))
        top = max(0, min(top, scaled_h - 1))

        if right <= left or bottom <= top:
            return None

        cropped = composited.crop((left, top, right, bottom))

        # Create final image centered in viewport
        final = Image.new("RGBA", viewport_size, (30, 30, 30, 255))
        paste_x = max(0, (viewport_w - cropped.width) // 2) if cropped.width < viewport_w else 0
        paste_y = max(0, (viewport_h - cropped.height) // 2) if cropped.height < viewport_h else 0

        # Handle case where map is smaller than viewport
        if scaled_w < viewport_w:
            paste_x = (viewport_w - scaled_w) // 2
            left = 0
            right = scaled_w
            cropped = composited.crop((0, top, scaled_w, bottom))

        if scaled_h < viewport_h:
            paste_y = (viewport_h - scaled_h) // 2
            top = 0
            bottom = scaled_h
            cropped = composited.crop((left, 0, right, scaled_h))

        final.paste(cropped, (paste_x, paste_y))

        return ImageTk.PhotoImage(final)

    def render_thumbnail(
        self, size: Tuple[int, int], is_dm_view: bool = True
    ) -> Optional[ImageTk.PhotoImage]:
        """Render a thumbnail of the full map."""
        if self.map_image is None or self.fog_mask is None:
            return None

        # Calculate thumbnail scale to fit in size while preserving aspect ratio
        thumb_w, thumb_h = size
        scale_w = thumb_w / self.map_image.width
        scale_h = thumb_h / self.map_image.height
        thumb_scale = min(scale_w, scale_h)

        scaled_w = int(self.map_image.width * thumb_scale)
        scaled_h = int(self.map_image.height * thumb_scale)

        # Scale map and fog
        scaled_map = self.map_image.resize((scaled_w, scaled_h), Image.LANCZOS)
        scaled_fog = self.fog_mask.resize((scaled_w, scaled_h), Image.NEAREST)

        # Create fog overlay for thumbnail
        fog_opacity = 128 if is_dm_view else 255
        inverted_fog = ImageOps.invert(scaled_fog)
        alpha_mask = inverted_fog.point(lambda p: int(p * fog_opacity / 255))
        fog_rgba = Image.new("RGBA", (scaled_w, scaled_h), (0, 0, 0, 0))
        fog_rgba.putalpha(alpha_mask)

        composited = Image.alpha_composite(scaled_map, fog_rgba)

        return ImageTk.PhotoImage(composited)


class FogEditor:
    """Handles fog mask editing operations."""

    def __init__(self, fog_mask: Image.Image):
        """Initialize with a fog mask."""
        self.fog_mask = fog_mask.convert("L")
        self._draw = ImageDraw.Draw(self.fog_mask)

    def apply_brush(
        self, x: int, y: int, radius: int, reveal: bool = True
    ) -> None:
        """
        Apply a circular brush at the given position.

        Args:
            x: Center X in map coordinates
            y: Center Y in map coordinates
            radius: Brush radius in pixels
            reveal: If True, reveals (white); if False, hides (black)
        """
        color = 255 if reveal else 0
        self._draw.ellipse(
            [x - radius, y - radius, x + radius, y + radius],
            fill=color,
        )

    def apply_rectangle(
        self, x1: int, y1: int, x2: int, y2: int, reveal: bool = True
    ) -> None:
        """
        Apply a rectangular fill.

        Args:
            x1, y1: Top-left corner in map coordinates
            x2, y2: Bottom-right corner in map coordinates
            reveal: If True, reveals (white); if False, hides (black)
        """
        color = 255 if reveal else 0
        # Ensure coordinates are in correct order
        left = min(x1, x2)
        top = min(y1, y2)
        right = max(x1, x2)
        bottom = max(y1, y2)
        self._draw.rectangle([left, top, right, bottom], fill=color)

    def reveal_all(self) -> None:
        """Reveal the entire map."""
        self._draw.rectangle(
            [0, 0, self.fog_mask.width, self.fog_mask.height],
            fill=255,
        )

    def hide_all(self) -> None:
        """Hide the entire map."""
        self._draw.rectangle(
            [0, 0, self.fog_mask.width, self.fog_mask.height],
            fill=0,
        )

    def get_mask(self) -> Image.Image:
        """Get the modified fog mask."""
        return self.fog_mask


def calculate_scale(tile_pixels: int, tile_mm: float, monitor_ppmm: float) -> float:
    """
    Calculate the scale factor for physical-accurate display.

    Args:
        tile_pixels: Pixels per tile in source image
        tile_mm: Desired physical tile size in mm
        monitor_ppmm: Monitor pixels per mm

    Returns:
        Scale factor to apply to the image
    """
    target_pixels = tile_mm * monitor_ppmm
    return target_pixels / tile_pixels


def screen_to_map(
    screen_x: int,
    screen_y: int,
    scale: float,
    pan_x: int,
    pan_y: int,
    viewport_offset: Tuple[int, int] = (0, 0),
) -> Tuple[int, int]:
    """
    Convert screen coordinates to map coordinates.

    Args:
        screen_x, screen_y: Position in screen/canvas coordinates
        scale: Current display scale
        pan_x, pan_y: Current pan offset in map pixels
        viewport_offset: Offset of the viewport within the canvas

    Returns:
        (map_x, map_y) in original map pixel coordinates
    """
    offset_x, offset_y = viewport_offset
    map_x = int((screen_x - offset_x) / scale + pan_x)
    map_y = int((screen_y - offset_y) / scale + pan_y)
    return map_x, map_y


def map_to_screen(
    map_x: int,
    map_y: int,
    scale: float,
    pan_x: int,
    pan_y: int,
    viewport_offset: Tuple[int, int] = (0, 0),
) -> Tuple[int, int]:
    """
    Convert map coordinates to screen coordinates.

    Args:
        map_x, map_y: Position in map pixel coordinates
        scale: Current display scale
        pan_x, pan_y: Current pan offset in map pixels
        viewport_offset: Offset of the viewport within the canvas

    Returns:
        (screen_x, screen_y) in canvas coordinates
    """
    offset_x, offset_y = viewport_offset
    screen_x = int((map_x - pan_x) * scale + offset_x)
    screen_y = int((map_y - pan_y) * scale + offset_y)
    return screen_x, screen_y
