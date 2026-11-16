"""Custom UI components for the Spotify desktop overlay."""

import tkinter as tk
from typing import Callable, Optional
from PIL import Image, ImageDraw, ImageTk


class ModernButton(tk.Canvas):
    """Custom canvas-based button with rounded corners and smooth hover states."""

    def __init__(
        self,
        parent,
        text: str,
        command: Callable[[], None],
        width: int = 30,
        height: int = 30,
        radius: int = 6,
        bg_color: str = "#222222",
        hover_color: str = "#333333",
        active_color: str = "#1DB954",
        text_color: str = "#FFFFFF",
        font: tuple = ("Segoe UI", 10, "bold"),
        tooltip: str = "",
        **kwargs,
    ):
        super().__init__(
            parent,
            width=width,
            height=height,
            bg=kwargs.pop("container_bg", "#141414"),
            highlightthickness=0,
            cursor="hand2",
            **kwargs,
        )
        self.btn_width = width
        self.btn_height = height
        self.radius = radius
        self.command = command
        self.default_bg = bg_color
        self.hover_bg = hover_color
        self.active_bg = active_color
        self.current_bg = bg_color
        self.text_color = text_color
        self.font = font
        self.tooltip = tooltip
        self._text = text
        self._is_toggled = False

        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<Button-1>", self._on_click)
        self.render()

    def set_text(self, text: str) -> None:
        """Update button symbol/text."""
        self._text = text
        self.render()

    def set_toggled(self, toggled: bool, active_bg: Optional[str] = None) -> None:
        """Set active toggle state."""
        self._is_toggled = toggled
        if active_bg:
            self.active_bg = active_bg
        self.current_bg = self.active_bg if self._is_toggled else self.default_bg
        self.render()

    def render(self) -> None:
        """Draw button with rounded pill background and centered text."""
        self.delete("all")
        w, h, r = self.btn_width, self.btn_height, self.radius

        # Draw rounded rectangle
        self.create_arc(0, 0, 2 * r, 2 * r, start=90, extent=90, fill=self.current_bg, outline="")
        self.create_arc(w - 2 * r, 0, w, 2 * r, start=0, extent=90, fill=self.current_bg, outline="")
        self.create_arc(0, h - 2 * r, 2 * r, h, start=180, extent=90, fill=self.current_bg, outline="")
        self.create_arc(w - 2 * r, h - 2 * r, w, h, start=270, extent=90, fill=self.current_bg, outline="")
        self.create_rectangle(r, 0, w - r, h, fill=self.current_bg, outline="")
        self.create_rectangle(0, r, w, h - r, fill=self.current_bg, outline="")

        # Draw centered icon
        self.create_text(
            w // 2,
            h // 2,
            text=self._text,
            fill=self.text_color,
            font=self.font,
        )

    def _on_enter(self, _):
        if not self._is_toggled:
            self.current_bg = self.hover_bg
            self.render()

    def _on_leave(self, _):
        self.current_bg = self.active_bg if self._is_toggled else self.default_bg
        self.render()

    def _on_click(self, _):
        if self.command:
            self.command()


class RoundedArtworkCanvas(tk.Canvas):
    """Canvas displaying album artwork with rounded corners."""

    def __init__(self, parent, size: int = 56, radius: int = 8, bg_color: str = "#141414"):
        super().__init__(parent, width=size, height=size, bg=bg_color, highlightthickness=0)
        self.artwork_size = size
        self.radius = radius
        self._current_photo: Optional[ImageTk.PhotoImage] = None
        self._last_img_id: Optional[str] = None
        self.render_placeholder()

    def render_placeholder(self) -> None:
        """Draw a placeholder icon when no album cover is loaded."""
        size = self.artwork_size
        img = Image.new("RGBA", (size, size), (24, 24, 24, 255))
        draw = ImageDraw.Draw(img)

        # Rounded background
        draw.rounded_rectangle([0, 0, size - 1, size - 1], radius=self.radius, fill=(30, 30, 30, 255))

        # Stylized Spotify / music disc icon
        center = size // 2
        r = size // 3
        draw.ellipse([center - r, center - r, center + r, center + r], fill=(45, 45, 45, 255))
        draw.ellipse([center - 4, center - 4, center + 4, center + 4], fill=(30, 215, 96, 255))

        self._set_image(img)

    def update_artwork(self, pil_image: Optional[Image.Image], identifier: str = "") -> None:
        """Update cover image with rounded mask."""
        if not pil_image:
            self.render_placeholder()
            return

        if identifier and identifier == self._last_img_id:
            return

        self._last_img_id = identifier
        size = self.artwork_size
        resized = pil_image.resize((size, size), Image.Resampling.LANCZOS).convert("RGBA")

        # Create round mask
        mask = Image.new("L", (size, size), 0)
        mask_draw = ImageDraw.Draw(mask)
        mask_draw.rounded_rectangle([0, 0, size - 1, size - 1], radius=self.radius, fill=255)

        # Composite onto mask
        output = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        output.paste(resized, (0, 0), mask=mask)

        self._set_image(output)

    def _set_image(self, pil_image: Image.Image) -> None:
        self._current_photo = ImageTk.PhotoImage(pil_image)
        self.delete("all")
        self.create_image(0, 0, anchor="nw", image=self._current_photo)


class ProgressBar(tk.Canvas):
    """Horizontal progress bar for track playback."""

    def __init__(
        self,
        parent,
        width: int = 340,
        height: int = 3,
        bg_color: str = "#2B2B2B",
        fill_color: str = "#1DB954",
        container_bg: str = "#141414",
    ):
        super().__init__(
            parent,
            width=width,
            height=height,
            bg=container_bg,
            highlightthickness=0,
        )
        self.bar_width = width
        self.bar_height = height
        self.bg_color = bg_color
        self.fill_color = fill_color
        self.progress: float = 0.0
        self.render()

    def set_progress(self, current_ms: int, total_ms: int) -> None:
        """Set track progress ratio."""
        if total_ms <= 0:
            self.progress = 0.0
        else:
            self.progress = max(0.0, min(1.0, current_ms / total_ms))
        self.render()

    def resize(self, new_width: int) -> None:
        """Dynamically adapt width."""
        self.bar_width = new_width
        self.configure(width=new_width)
        self.render()

    def render(self) -> None:
        """Draw track bar."""
        self.delete("all")
        w, h = self.bar_width, self.bar_height
        # Background track
        self.create_rectangle(0, 0, w, h, fill=self.bg_color, outline="")
        # Active progress fill
        fill_w = int(w * self.progress)
        if fill_w > 0:
            self.create_rectangle(0, 0, fill_w, h, fill=self.fill_color, outline="")

