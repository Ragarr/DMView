"""Map import dialog for DMView.

Provides a single modal window to select an image, choose a scaling method,
and enter the parameters required to compute pixels-per-tile and tile size.

Methods implemented:
 - Image width in mm (and optional tile size)
 - Tiles across + tile size
 - Draw 3x3 sample (placeholder)
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from typing import Optional, Callable
from pathlib import Path
from PIL import Image, ImageTk


class MapImportDialog(tk.Toplevel):
    def __init__(self, parent: tk.Tk, on_import: Callable[[str, str, int, float], None], default_tile_mm: float = 25.4):
        super().__init__(parent)
        self.parent = parent
        self.on_import = on_import
        self.default_tile_mm = default_tile_mm

        self.transient(parent)
        self.title("Import Map")
        self.resizable(False, False)

        # Vars
        self.filepath_var = tk.StringVar()
        self.name_var = tk.StringVar()
        self.method_var = tk.StringVar(value="sample")
        self.image_width_mm_var = tk.DoubleVar(value=self.default_tile_mm * 10)
        self.tile_size_mm_var = tk.DoubleVar(value=self.default_tile_mm)
        self.tiles_x_var = tk.IntVar(value=10)

        self.img_w = 0
        self.img_h = 0
        self._thumb_image: Optional[ImageTk.PhotoImage] = None

        # Sample method state
        self.sample_pixels_per_tile: Optional[float] = None
        self._sample_selector_img: Optional[ImageTk.PhotoImage] = None

        self._build_ui()
        self.grab_set()
        self.wait_window(self)

    def _build_ui(self) -> None:
        frm = ttk.Frame(self, padding=12)
        frm.grid(row=0, column=0, sticky="nsew")

        # File picker
        ttk.Label(frm, text="Image:").grid(row=0, column=0, sticky="w")
        file_row = ttk.Frame(frm)
        file_row.grid(row=1, column=0, columnspan=3, sticky="ew", pady=(0,8))
        self.file_entry = ttk.Entry(file_row, textvariable=self.filepath_var, width=48)
        self.file_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(file_row, text="Browse…", command=self._browse_file).pack(side=tk.LEFT, padx=(8,0))

        # Image info / preview
        self.img_info = ttk.Label(frm, text="No image selected")
        self.img_info.grid(row=2, column=0, columnspan=3, sticky="w")

        # Name
        ttk.Label(frm, text="Map name:").grid(row=3, column=0, sticky="w", pady=(8,0))
        ttk.Entry(frm, textvariable=self.name_var, width=40).grid(row=4, column=0, columnspan=3, sticky="w")

        # Method selector
        ttk.Label(frm, text="Scaling method:").grid(row=5, column=0, sticky="w", pady=(8,0))
        methods = [
            ("Image overall width (mm)", "image_width"),
            ("Number of tiles across + tile size (mm)", "tiles"),
            ("Draw 3x3 sample (coming soon)", "sample"),
        ]

        method_menu = ttk.Combobox(frm, values=[m[0] for m in methods], state="readonly", width=48)
        method_menu.current(2)
        method_menu.grid(row=6, column=0, columnspan=3, sticky="w")
        # keep a handle to the widget for programmatic updates
        self._method_menu = method_menu

        # Map combobox selection -> set method_var accordingly
        def _on_method_select(event):
            sel = method_menu.current()
            self.method_var.set(methods[sel][1])
            self._update_method_frame()

        method_menu.bind("<<ComboboxSelected>>", _on_method_select)
        # Keep combobox selection in sync with method_var
        self.method_selection = method_menu

        # Method-specific frames
        self.method_frame = ttk.Frame(frm)
        self.method_frame.grid(row=7, column=0, columnspan=3, sticky="ew", pady=(8,0))

        # Image width method
        self._mf_image_width = ttk.Frame(self.method_frame)
        ttk.Label(self._mf_image_width, text="Overall image width (mm):").grid(row=0, column=0, sticky="w")
        ttk.Entry(self._mf_image_width, textvariable=self.image_width_mm_var, width=20).grid(row=0, column=1, sticky="w", padx=(8,0))
        ttk.Label(self._mf_image_width, text="Tile size (mm, optional):").grid(row=1, column=0, sticky="w", pady=(6,0))
        ttk.Entry(self._mf_image_width, textvariable=self.tile_size_mm_var, width=20).grid(row=1, column=1, sticky="w", padx=(8,0))

        # Tiles method
        self._mf_tiles = ttk.Frame(self.method_frame)
        ttk.Label(self._mf_tiles, text="Tiles across (columns):").grid(row=0, column=0, sticky="w")
        ttk.Entry(self._mf_tiles, textvariable=self.tiles_x_var, width=10).grid(row=0, column=1, sticky="w", padx=(8,0))
        ttk.Label(self._mf_tiles, text="Tile size (mm):").grid(row=1, column=0, sticky="w", pady=(6,0))
        ttk.Entry(self._mf_tiles, textvariable=self.tile_size_mm_var, width=20).grid(row=1, column=1, sticky="w", padx=(8,0))

        # Sample method UI
        self._mf_sample = ttk.Frame(self.method_frame)
        ttk.Label(self._mf_sample, text="Select a 3x3 tiles region on the image to auto-scale:").grid(row=0, column=0, sticky="w")
        sample_row = ttk.Frame(self._mf_sample)
        sample_row.grid(row=1, column=0, sticky="w", pady=(6,0))
        ttk.Button(sample_row, text="Open Sample Selector…", command=self._open_sample_selector).pack(side=tk.LEFT)
        self.sample_info = ttk.Label(sample_row, text="No sample selected", foreground="#666")
        self.sample_info.pack(side=tk.LEFT, padx=(8,0))

        # Allow user to provide tile size mm (same control as other methods)
        ttk.Label(self._mf_sample, text="Tile size (mm):").grid(row=2, column=0, sticky="w", pady=(6,0))
        ttk.Entry(self._mf_sample, textvariable=self.tile_size_mm_var, width=20).grid(row=2, column=1, sticky="w", padx=(8,0))

        # Buttons
        btn_row = ttk.Frame(frm)
        btn_row.grid(row=8, column=0, columnspan=3, pady=(12,0), sticky="e")
        self.import_btn = ttk.Button(btn_row, text="Import", command=self._on_import)
        self.import_btn.pack(side=tk.RIGHT)
        ttk.Button(btn_row, text="Cancel", command=self._on_cancel).pack(side=tk.RIGHT, padx=(0,8))

        self._update_method_frame()

    def _browse_file(self) -> None:
        fp = filedialog.askopenfilename(
            title="Select Map Image",
            filetypes=[("Image files", "*.png *.jpg *.jpeg *.webp *.bmp"), ("All files", "*.*")],
            parent=self,
        )
        if not fp:
            return
        self.filepath_var.set(fp)
        self._load_image_info(fp)

    def _load_image_info(self, fp: str) -> None:
        try:
            with Image.open(fp) as img:
                self.img_w, self.img_h = img.size
                thumb = img.copy()
                thumb.thumbnail((200, 200))
                self._thumb_image = ImageTk.PhotoImage(thumb)
            # Default map name to filename if not provided
            if not self.name_var.get():
                self.name_var.set(Path(fp).stem)
            self.img_info.config(text=f"Image: {Path(fp).name} — {self.img_w}×{self.img_h} px")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open image: {e}", parent=self)
            self.filepath_var.set("")
            self.img_info.config(text="No image selected")

    def _update_method_frame(self) -> None:
        # Remove all
        for child in self.method_frame.winfo_children():
            child.grid_forget()
        # Place the correct one
        method = self.method_var.get()
        if method == "image_width":
            self._mf_image_width.grid(row=0, column=0, sticky="w")
            self.import_btn.state(["!disabled"])
        elif method == "tiles":
            self._mf_tiles.grid(row=0, column=0, sticky="w")
            self.import_btn.state(["!disabled"])
        else:  # sample
            self._mf_sample.grid(row=0, column=0, sticky="w")
            # Enable only if a sample has been selected
            if self.sample_pixels_per_tile is None:
                self.import_btn.state(["disabled"])
            else:
                self.import_btn.state(["!disabled"])
    def _on_cancel(self) -> None:
        self.destroy()

    def _open_sample_selector(self) -> None:
        """Open a window for the user to draw a 3x3 sample rectangle with zoom support."""
        fp = self.filepath_var.get()
        if not fp or not Path(fp).exists():
            messagebox.showerror("Error", "Please select a valid image file first.", parent=self)
            return

        # Create selector window
        sel_win = tk.Toplevel(self)
        sel_win.title("Select 3x3 sample region")

        # Load original image
        orig_img = Image.open(fp).convert("RGBA")
        img_w, img_h = orig_img.size

        # Initial fit scale
        max_w, max_h = 1000, 700
        scale = min(1.0, max_w / img_w, max_h / img_h)
        display_w = int(img_w * scale)
        display_h = int(img_h * scale)

        # Viewport frame with scrollbars so zooming doesn't resize the window
        view_w = min(display_w, max_w)
        view_h = min(display_h, max_h)
        view_frame = ttk.Frame(sel_win)
        view_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=False)

        canvas = tk.Canvas(view_frame, width=view_w, height=view_h, bg="black")
        hbar = ttk.Scrollbar(view_frame, orient=tk.HORIZONTAL, command=canvas.xview)
        vbar = ttk.Scrollbar(view_frame, orient=tk.VERTICAL, command=canvas.yview)
        canvas.config(xscrollcommand=hbar.set, yscrollcommand=vbar.set)

        canvas.grid(row=0, column=0, sticky="nsew")
        vbar.grid(row=0, column=1, sticky="ns")
        hbar.grid(row=1, column=0, sticky="ew")
        view_frame.rowconfigure(0, weight=1)
        view_frame.columnconfigure(0, weight=1)

        # Internal state
        sel_start = {}
        sel_rect_id = None
        image_item_id = None

        def update_display():
            """Redraw the image on the canvas at the current scale and clear selection."""
            nonlocal display_w, display_h, sel_rect_id, image_item_id
            display_w = int(img_w * scale)
            display_h = int(img_h * scale)
            display_img = orig_img.resize((display_w, display_h), Image.LANCZOS)
            self._sample_selector_img = ImageTk.PhotoImage(display_img)
            # Update or create image item
            if image_item_id is None:
                image_item_id = canvas.create_image(0, 0, image=self._sample_selector_img, anchor=tk.NW)
            else:
                canvas.itemconfigure(image_item_id, image=self._sample_selector_img)

            # Update scroll region but DO NOT change canvas widget size (prevents window resize)
            canvas.config(scrollregion=(0, 0, display_w, display_h))
            # Clear selection on zoom change
            if sel_rect_id:
                try:
                    canvas.delete(sel_rect_id)
                except Exception:
                    pass
                sel_rect_id = None
                sel_start.clear()

        update_display()

        # Selection handlers
        def on_mouse_down(evt):
            nonlocal sel_rect_id
            # Convert to canvas coordinates (accounts for scrolling)
            cx = int(canvas.canvasx(evt.x))
            cy = int(canvas.canvasy(evt.y))
            sel_start["x"] = cx
            sel_start["y"] = cy
            if sel_rect_id:
                canvas.delete(sel_rect_id)
                sel_rect_id = None

        def on_mouse_move(evt):
            nonlocal sel_rect_id
            if "x" not in sel_start:
                return
            x1, y1 = sel_start["x"], sel_start["y"]
            cx = int(canvas.canvasx(evt.x))
            cy = int(canvas.canvasy(evt.y))
            x2, y2 = cx, cy
            if sel_rect_id:
                canvas.coords(sel_rect_id, x1, y1, x2, y2)
            else:
                sel_rect_id = canvas.create_rectangle(x1, y1, x2, y2, outline="#ffcc00", width=2)

        def on_mouse_up(evt):
            nonlocal sel_rect_id
            if "x" not in sel_start:
                return
            cx = int(canvas.canvasx(evt.x))
            cy = int(canvas.canvasy(evt.y))
            x1, y1 = sel_start["x"], sel_start["y"]
            x2, y2 = cx, cy
            if sel_rect_id:
                canvas.coords(sel_rect_id, x1, y1, x2, y2)

        canvas.bind("<Button-1>", on_mouse_down)
        canvas.bind("<B1-Motion>", on_mouse_move)
        canvas.bind("<ButtonRelease-1>", on_mouse_up)

        # Zoom controls (buttons + slider)
        ctrl_fr = ttk.Frame(sel_win)
        ctrl_fr.pack(fill=tk.X, pady=(6, 0))

        def set_scale(new_scale: float, update_slider: bool = True):
            nonlocal scale
            scale = max(0.05, min(4.0, new_scale))
            update_display()
            # Update slider only when requested and available
            try:
                if update_slider and 'zoom_slider' in locals():
                    zoom_slider.set(int(scale * 100))
            except Exception:
                pass

        def zoom_in():
            set_scale(scale * 1.25)

        def zoom_out():
            set_scale(scale / 1.25)

        ttk.Button(ctrl_fr, text="-", width=3, command=zoom_out).pack(side=tk.LEFT, padx=(0,6))
        ttk.Button(ctrl_fr, text="+", width=3, command=zoom_in).pack(side=tk.LEFT)
        zoom_slider = ttk.Scale(ctrl_fr, from_=5, to=400, orient=tk.HORIZONTAL, command=lambda v: set_scale(float(v) / 100.0, False))
        zoom_slider.set(int(scale * 100))
        zoom_slider.pack(side=tk.LEFT, padx=8, fill=tk.X, expand=True)

        # Mouse wheel zoom
        # Mouse wheel zoom removed per user request. Zoom via buttons or slider only.


        # Middle-button (or space+drag) panning when zoomed
        pan_state = {"panning": False, "last": (0, 0)}

        def on_pan_start(evt):
            pan_state["panning"] = True
            pan_state["last"] = (evt.x, evt.y)
            canvas.config(cursor="fleur")

        def on_pan_move(evt):
            if not pan_state["panning"]:
                return
            lx, ly = pan_state["last"]
            dx = lx - evt.x
            dy = ly - evt.y
            # scroll the canvas
            canvas.xview_scroll(int(dx), "units")
            canvas.yview_scroll(int(dy), "units")
            pan_state["last"] = (evt.x, evt.y)

        def on_pan_end(evt):
            pan_state["panning"] = False
            canvas.config(cursor="")

        canvas.bind("<Button-2>", on_pan_start)
        canvas.bind("<B2-Motion>", on_pan_move)
        canvas.bind("<ButtonRelease-2>", on_pan_end)

        # Also allow space+drag to pan
        space_pan = {"active": False}

        def on_space_down(evt):
            space_pan["active"] = True
            canvas.config(cursor="fleur")

        def on_space_up(evt):
            space_pan["active"] = False
            canvas.config(cursor="")

        sel_win.bind("<KeyPress-space>", on_space_down)
        sel_win.bind("<KeyRelease-space>", on_space_up)

        def on_left_drag_with_space(evt):
            # If space-pan is active, pan; otherwise treat as selection drag
            if space_pan["active"]:
                on_pan_move(evt)
            else:
                on_mouse_move(evt)

        canvas.bind("<B1-Motion>", on_left_drag_with_space)

        info_lbl = ttk.Label(sel_win, text="Drag to select a 3x3 tiles region, then click Confirm")
        info_lbl.pack(pady=(6,0))

        btn_fr = ttk.Frame(sel_win)
        btn_fr.pack(pady=(8,8))

        def on_confirm():
            if "x" not in sel_start or sel_rect_id is None:
                messagebox.showerror("Error", "No selection made.", parent=sel_win)
                return
            # get current rect coords (already canvas coordinates, accounting for scroll)
            coords = canvas.coords(sel_rect_id)
            sx1, sy1, sx2, sy2 = [int(c) for c in coords]
            # normalize
            left, right = min(sx1, sx2), max(sx1, sx2)
            top, bottom = min(sy1, sy2), max(sy1, sy2)
            sel_w = right - left
            sel_h = bottom - top
            if sel_w <= 0 or sel_h <= 0:
                messagebox.showerror("Error", "Invalid selection size.", parent=sel_win)
                return

            # Transform selection to original image pixels
            # display_w = orig_w * scale
            display_w_current = int(img_w * scale)
            scale_back = (img_w / display_w_current) if display_w_current > 0 else 1.0
            orig_sel_w = sel_w * scale_back
            orig_sel_h = sel_h * scale_back

            # Each selection should correspond to 3 tiles horizontally and vertically
            pixels_per_tile_x = orig_sel_w / 3.0
            pixels_per_tile_y = orig_sel_h / 3.0
            pixels_per_tile = (pixels_per_tile_x + pixels_per_tile_y) / 2.0

            self.sample_pixels_per_tile = pixels_per_tile
            self.sample_info.config(text=f"Sample: {int(orig_sel_w)}×{int(orig_sel_h)} px → {pixels_per_tile:.1f} px/tile")
            # Enable import button only if sample selected
            self._update_method_frame()
            sel_win.destroy()

        def on_cancel_sel():
            sel_win.destroy()

        ttk.Button(btn_fr, text="Confirm", command=on_confirm).pack(side=tk.LEFT, padx=(0,8))
        ttk.Button(btn_fr, text="Cancel", command=on_cancel_sel).pack(side=tk.LEFT)

    def _on_import(self) -> None:
        fp = self.filepath_var.get()
        name = self.name_var.get().strip()
        method = self.method_var.get()

        if not fp or not Path(fp).exists():
            messagebox.showerror("Error", "Please select a valid image file.", parent=self)
            return
        if not name:
            messagebox.showerror("Error", "Please enter a map name.", parent=self)
            return
        if self.img_w <= 0:
            # Try to load info if not loaded
            self._load_image_info(fp)
            if self.img_w <= 0:
                messagebox.showerror("Error", "Failed to read image dimensions.", parent=self)
                return

        try:
            if method == "image_width":
                width_mm = float(self.image_width_mm_var.get())
                if width_mm <= 0:
                    raise ValueError("Width must be > 0")
                tile_size_mm = float(self.tile_size_mm_var.get())
                if tile_size_mm <= 0:
                    tile_size_mm = self.default_tile_mm
                ppmm = float(self.img_w) / float(width_mm)
                tile_pixels = max(1, int(round(ppmm * float(tile_size_mm))))

            elif method == "tiles":
                tiles_x = int(self.tiles_x_var.get())
                if tiles_x <= 0:
                    raise ValueError("Tiles must be > 0")
                tile_size_mm = float(self.tile_size_mm_var.get())
                if tile_size_mm <= 0:
                    tile_size_mm = self.default_tile_mm
                tile_pixels = max(1, int(round(float(self.img_w) / float(tiles_x))))

            elif method == "sample":
                if self.sample_pixels_per_tile is None:
                    raise ValueError("No sample selected")
                tile_size_mm = float(self.tile_size_mm_var.get())
                if tile_size_mm <= 0:
                    tile_size_mm = self.default_tile_mm
                tile_pixels = max(1, int(round(self.sample_pixels_per_tile)))

            else:
                messagebox.showerror("Error", "Selected method not implemented.", parent=self)
                return
        except Exception as e:
            messagebox.showerror("Error", f"Invalid input: {e}", parent=self)
            return

        # Confirm
        if not messagebox.askyesno(
            "Confirm Scale",
            f"Computed tile size: {tile_size_mm} mm\nComputed pixels per tile: {tile_pixels}\n\nProceed?",
            parent=self,
        ):
            return

        # Call callback
        try:
            self.on_import(fp, name, tile_pixels, float(tile_size_mm))
            self.destroy()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to import map: {e}", parent=self)
