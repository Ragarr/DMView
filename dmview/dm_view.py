"""DM View - Control panel window for the dungeon master."""

import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk
from typing import TYPE_CHECKING, Optional

from PIL import Image, ImageTk

from map_canvas import FogEditor, MapRenderer, screen_to_map

if TYPE_CHECKING:
    from app import Application


class DMView:
    """Control panel window for the DM."""

    # Tool constants
    TOOL_BRUSH = "brush"
    TOOL_RECT = "rect"
    TOOL_PAN = "pan"

    def __init__(self, root: tk.Tk, app: "Application"):
        """
        Initialize the DM view.

        Args:
            root: The Tk root window (this will be the DM window)
            app: The main application instance
        """
        self.app = app
        self.root = root
        self.renderer = MapRenderer()

        # Tool state
        self.current_tool = self.TOOL_BRUSH
        self.reveal_mode = True  # True = reveal, False = hide
        self.brush_size = app.config.brush_size

        # Drag state
        self._drag_start: Optional[tuple[int, int]] = None
        self._rect_start: Optional[tuple[int, int]] = None
        self._rect_id: Optional[int] = None

        # Image references
        self._current_image: Optional[ImageTk.PhotoImage] = None
        self._preview_offset = (0, 0)

        self._setup_ui()
        self._bind_events()

    def _setup_ui(self) -> None:
        """Set up the UI components."""
        self.root.title("DMView - DM Control Panel")
        self.root.geometry("1200x800")

        # Main container
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Left sidebar - map list
        self._setup_sidebar(main_frame)

        # Right area - toolbar and preview
        right_frame = ttk.Frame(main_frame)
        right_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Toolbar
        self._setup_toolbar(right_frame)

        # Preview canvas
        self._setup_preview(right_frame)

    def _setup_sidebar(self, parent: ttk.Frame) -> None:
        """Set up the map list sidebar."""
        sidebar = ttk.Frame(parent, width=200)
        sidebar.pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=5)
        sidebar.pack_propagate(False)

        # Session label
        ttk.Label(sidebar, text="Maps", font=("TkDefaultFont", 12, "bold")).pack(
            anchor=tk.W, pady=(0, 5)
        )

        # Map listbox
        list_frame = ttk.Frame(sidebar)
        list_frame.pack(fill=tk.BOTH, expand=True)

        self.map_listbox = tk.Listbox(list_frame, selectmode=tk.SINGLE)
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL)
        scrollbar.config(command=self.map_listbox.yview)
        self.map_listbox.config(yscrollcommand=scrollbar.set)

        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.map_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.map_listbox.bind("<<ListboxSelect>>", self._on_map_select)

        # Map buttons
        btn_frame = ttk.Frame(sidebar)
        btn_frame.pack(fill=tk.X, pady=5)

        ttk.Button(btn_frame, text="Add Map", command=self._add_map).pack(
            side=tk.LEFT, padx=2
        )
        ttk.Button(btn_frame, text="Remove", command=self._remove_map).pack(
            side=tk.LEFT, padx=2
        )

    def _setup_toolbar(self, parent: ttk.Frame) -> None:
        """Set up the toolbar."""
        toolbar = ttk.Frame(parent)
        toolbar.pack(fill=tk.X, padx=5, pady=5)

        # Tool buttons
        tool_frame = ttk.LabelFrame(toolbar, text="Tools")
        tool_frame.pack(side=tk.LEFT, padx=5)

        self.brush_btn = ttk.Button(
            tool_frame, text="Brush", command=lambda: self._set_tool(self.TOOL_BRUSH)
        )
        self.brush_btn.pack(side=tk.LEFT, padx=2, pady=2)

        self.rect_btn = ttk.Button(
            tool_frame, text="Rectangle", command=lambda: self._set_tool(self.TOOL_RECT)
        )
        self.rect_btn.pack(side=tk.LEFT, padx=2, pady=2)

        self.pan_btn = ttk.Button(
            tool_frame, text="Pan", command=lambda: self._set_tool(self.TOOL_PAN)
        )
        self.pan_btn.pack(side=tk.LEFT, padx=2, pady=2)

        # Mode toggle
        mode_frame = ttk.LabelFrame(toolbar, text="Mode")
        mode_frame.pack(side=tk.LEFT, padx=5)

        self.mode_var = tk.StringVar(value="reveal")
        ttk.Radiobutton(
            mode_frame, text="Reveal", variable=self.mode_var, value="reveal",
            command=self._on_mode_change
        ).pack(side=tk.LEFT, padx=2, pady=2)
        ttk.Radiobutton(
            mode_frame, text="Hide", variable=self.mode_var, value="hide",
            command=self._on_mode_change
        ).pack(side=tk.LEFT, padx=2, pady=2)

        # Brush size
        brush_frame = ttk.LabelFrame(toolbar, text="Brush Size")
        brush_frame.pack(side=tk.LEFT, padx=5)

        self.brush_size_var = tk.IntVar(value=self.brush_size)
        brush_scale = ttk.Scale(
            brush_frame,
            from_=5,
            to=100,
            orient=tk.HORIZONTAL,
            variable=self.brush_size_var,
            command=self._on_brush_size_change,
        )
        brush_scale.pack(side=tk.LEFT, padx=2, pady=2)

        self.brush_size_label = ttk.Label(brush_frame, text=str(self.brush_size))
        self.brush_size_label.pack(side=tk.LEFT, padx=2)

        # Quick actions
        action_frame = ttk.LabelFrame(toolbar, text="Quick Actions")
        action_frame.pack(side=tk.LEFT, padx=5)

        ttk.Button(action_frame, text="Reveal All", command=self._reveal_all).pack(
            side=tk.LEFT, padx=2, pady=2
        )
        ttk.Button(action_frame, text="Hide All", command=self._hide_all).pack(
            side=tk.LEFT, padx=2, pady=2
        )

        # Session actions
        session_frame = ttk.LabelFrame(toolbar, text="Session")
        session_frame.pack(side=tk.RIGHT, padx=5)

        ttk.Button(session_frame, text="New", command=self.app.new_session).pack(
            side=tk.LEFT, padx=2, pady=2
        )
        ttk.Button(session_frame, text="Open", command=self.app.open_session).pack(
            side=tk.LEFT, padx=2, pady=2
        )
        ttk.Button(session_frame, text="Save", command=self.app.save_session).pack(
            side=tk.LEFT, padx=2, pady=2
        )

    def _setup_preview(self, parent: ttk.Frame) -> None:
        """Set up the preview canvas."""
        preview_frame = ttk.Frame(parent)
        preview_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.preview_canvas = tk.Canvas(
            preview_frame,
            bg="#1e1e1e",
            highlightthickness=1,
            highlightbackground="#444",
        )
        self.preview_canvas.pack(fill=tk.BOTH, expand=True)

    def _bind_events(self) -> None:
        """Bind event handlers."""
        self.preview_canvas.bind("<Button-1>", self._on_canvas_click)
        self.preview_canvas.bind("<B1-Motion>", self._on_canvas_drag)
        self.preview_canvas.bind("<ButtonRelease-1>", self._on_canvas_release)
        self.preview_canvas.bind("<Configure>", self._on_canvas_resize)

        # Keyboard shortcuts
        self.root.bind("<r>", lambda e: self.mode_var.set("reveal") or self._on_mode_change())
        self.root.bind("<h>", lambda e: self.mode_var.set("hide") or self._on_mode_change())
        self.root.bind("<b>", lambda e: self._set_tool(self.TOOL_BRUSH))
        self.root.bind("<t>", lambda e: self._set_tool(self.TOOL_RECT))
        self.root.bind("<p>", lambda e: self._set_tool(self.TOOL_PAN))
        self.root.bind("<bracketleft>", lambda e: self._adjust_brush_size(-5))
        self.root.bind("<bracketright>", lambda e: self._adjust_brush_size(5))
        self.root.bind("<Control-s>", lambda e: self.app.save_session())
        self.root.bind("<Control-o>", lambda e: self.app.open_session())
        self.root.bind("<Control-n>", lambda e: self.app.new_session())

    def _set_tool(self, tool: str) -> None:
        """Set the active tool."""
        self.current_tool = tool

        # Update button states visually
        for btn, t in [(self.brush_btn, self.TOOL_BRUSH),
                       (self.rect_btn, self.TOOL_RECT),
                       (self.pan_btn, self.TOOL_PAN)]:
            if t == tool:
                btn.state(["pressed"])
            else:
                btn.state(["!pressed"])

    def _on_mode_change(self) -> None:
        """Handle reveal/hide mode change."""
        self.reveal_mode = self.mode_var.get() == "reveal"

    def _on_brush_size_change(self, value: str) -> None:
        """Handle brush size slider change."""
        self.brush_size = int(float(value))
        self.brush_size_label.config(text=str(self.brush_size))
        self.app.config.brush_size = self.brush_size

    def _adjust_brush_size(self, delta: int) -> None:
        """Adjust brush size by delta."""
        new_size = max(5, min(100, self.brush_size + delta))
        self.brush_size_var.set(new_size)
        self._on_brush_size_change(str(new_size))

    def _on_map_select(self, event: tk.Event) -> None:
        """Handle map selection in listbox."""
        selection = self.map_listbox.curselection()
        if selection:
            index = selection[0]
            self.app.select_map(index)

    def _add_map(self) -> None:
        """Add a new map to the session."""
        if not self.app.session_manager:
            messagebox.showwarning("No Session", "Please create or open a session first.")
            return

        filepath = filedialog.askopenfilename(
            title="Select Map Image",
            filetypes=[
                ("Image files", "*.png *.jpg *.jpeg *.webp *.bmp"),
                ("All files", "*.*"),
            ],
        )

        if filepath:
            name = simpledialog.askstring("Map Name", "Enter a name for this map:")
            if name:
                self.app.add_map(filepath, name)

    def _remove_map(self) -> None:
        """Remove the selected map."""
        selection = self.map_listbox.curselection()
        if selection:
            index = selection[0]
            if messagebox.askyesno("Confirm", "Remove this map?"):
                self.app.remove_map(index)

    def _reveal_all(self) -> None:
        """Reveal the entire map."""
        self.app.reveal_all()

    def _hide_all(self) -> None:
        """Hide the entire map."""
        self.app.hide_all()

    def _on_canvas_click(self, event: tk.Event) -> None:
        """Handle canvas click."""
        if self.current_tool == self.TOOL_BRUSH:
            self._apply_brush(event.x, event.y)
        elif self.current_tool == self.TOOL_RECT:
            self._rect_start = (event.x, event.y)
        elif self.current_tool == self.TOOL_PAN:
            self._drag_start = (event.x, event.y)

    def _on_canvas_drag(self, event: tk.Event) -> None:
        """Handle canvas drag."""
        if self.current_tool == self.TOOL_BRUSH:
            self._apply_brush(event.x, event.y)
        elif self.current_tool == self.TOOL_RECT and self._rect_start:
            self._draw_rect_preview(event.x, event.y)
        elif self.current_tool == self.TOOL_PAN and self._drag_start:
            self._apply_pan(event.x, event.y)

    def _on_canvas_release(self, event: tk.Event) -> None:
        """Handle canvas release."""
        if self.current_tool == self.TOOL_RECT and self._rect_start:
            self._apply_rect(event.x, event.y)
            self._rect_start = None
            if self._rect_id:
                self.preview_canvas.delete(self._rect_id)
                self._rect_id = None
        elif self.current_tool == self.TOOL_PAN:
            self._drag_start = None
            self.app.save_session()

    def _on_canvas_resize(self, event: tk.Event) -> None:
        """Handle canvas resize."""
        self.refresh()

    def _screen_to_map_coords(self, screen_x: int, screen_y: int) -> tuple[int, int]:
        """Convert screen coordinates to map coordinates."""
        active_map = self.app.get_active_map()
        if not active_map:
            return 0, 0

        return screen_to_map(
            screen_x,
            screen_y,
            self.renderer.scale,
            active_map.pan_x,
            active_map.pan_y,
            self._preview_offset,
        )

    def _apply_brush(self, screen_x: int, screen_y: int) -> None:
        """Apply brush at screen position."""
        fog_mask = self.app.get_current_fog()
        if fog_mask is None:
            return

        map_x, map_y = self._screen_to_map_coords(screen_x, screen_y)

        # Scale brush size to map coordinates
        brush_radius = int(self.brush_size / self.renderer.scale)

        editor = FogEditor(fog_mask)
        editor.apply_brush(map_x, map_y, brush_radius, self.reveal_mode)

        self.app.update_fog(editor.get_mask())

    def _draw_rect_preview(self, x: int, y: int) -> None:
        """Draw rectangle selection preview."""
        if self._rect_id:
            self.preview_canvas.delete(self._rect_id)

        x1, y1 = self._rect_start
        color = "#00ff00" if self.reveal_mode else "#ff0000"
        self._rect_id = self.preview_canvas.create_rectangle(
            x1, y1, x, y, outline=color, width=2
        )

    def _apply_rect(self, screen_x: int, screen_y: int) -> None:
        """Apply rectangle selection."""
        fog_mask = self.app.get_current_fog()
        if fog_mask is None:
            return

        x1, y1 = self._rect_start
        map_x1, map_y1 = self._screen_to_map_coords(x1, y1)
        map_x2, map_y2 = self._screen_to_map_coords(screen_x, screen_y)

        editor = FogEditor(fog_mask)
        editor.apply_rectangle(map_x1, map_y1, map_x2, map_y2, self.reveal_mode)

        self.app.update_fog(editor.get_mask())

    def _apply_pan(self, x: int, y: int) -> None:
        """Apply pan based on drag."""
        if not self._drag_start:
            return

        dx = self._drag_start[0] - x
        dy = self._drag_start[1] - y

        # Convert to map coordinates
        map_dx = int(dx / self.renderer.scale)
        map_dy = int(dy / self.renderer.scale)

        self.app.pan_map(map_dx, map_dy)
        self._drag_start = (x, y)

    def set_map(self, map_image: Image.Image, fog_mask: Image.Image) -> None:
        """Set the map and fog to display."""
        self.renderer.set_map(map_image, fog_mask)
        self.refresh()

    def set_scale(self, scale: float) -> None:
        """Set the preview scale (DM view uses a fitted scale)."""
        self.renderer.set_scale(scale)
        self.refresh()

    def update_fog(self, fog_mask: Image.Image) -> None:
        """Update the fog mask."""
        if self.renderer.map_image is not None:
            self.renderer.fog_mask = fog_mask.convert("L")
            self.renderer.invalidate_cache()
            self.refresh()

    def refresh(self) -> None:
        """Refresh the preview display."""
        if self.renderer.map_image is None:
            return

        width = self.preview_canvas.winfo_width()
        height = self.preview_canvas.winfo_height()

        if width <= 1 or height <= 1:
            return

        # Calculate scale to fit map in preview
        map_w = self.renderer.map_image.width
        map_h = self.renderer.map_image.height

        scale_w = width / map_w
        scale_h = height / map_h
        fit_scale = min(scale_w, scale_h) * 0.95  # 5% margin

        self.renderer.set_scale(fit_scale)

        # Calculate offset to center the map
        scaled_w = int(map_w * fit_scale)
        scaled_h = int(map_h * fit_scale)
        self._preview_offset = ((width - scaled_w) // 2, (height - scaled_h) // 2)

        # Render with DM view (semi-transparent fog)
        active_map = self.app.get_active_map()
        pan_x = active_map.pan_x if active_map else 0
        pan_y = active_map.pan_y if active_map else 0

        self._current_image = self.renderer.render(
            viewport_size=(width, height),
            pan_x=0,  # DM view shows full map, no pan
            pan_y=0,
            is_dm_view=True,
        )

        if self._current_image:
            self.preview_canvas.delete("all")
            self.preview_canvas.create_image(
                width // 2,
                height // 2,
                image=self._current_image,
                anchor=tk.CENTER,
            )

    def update_map_list(self, maps: list, active_index: int) -> None:
        """Update the map listbox."""
        self.map_listbox.delete(0, tk.END)
        for m in maps:
            self.map_listbox.insert(tk.END, m.name)

        if maps and 0 <= active_index < len(maps):
            self.map_listbox.selection_clear(0, tk.END)
            self.map_listbox.selection_set(active_index)
            self.map_listbox.see(active_index)
