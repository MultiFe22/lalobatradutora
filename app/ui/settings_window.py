"""Simple settings window for Loba configuration."""

import tkinter as tk
from tkinter import ttk
from typing import Callable, Optional
from dataclasses import dataclass


@dataclass
class SettingsValues:
    """Current settings values."""
    subtitle_ttl_s: float
    max_lines: int
    silence_threshold_ms: int


class SettingsWindow:
    """
    Simple tkinter window for adjusting Loba settings.

    Exposes user-friendly controls for:
    - Subtitle display time
    - Max lines on screen
    - Pause detection sensitivity
    """

    def __init__(
        self,
        initial_values: SettingsValues,
        on_settings_changed: Optional[Callable[[SettingsValues], None]] = None,
        on_quit: Optional[Callable[[], None]] = None,
    ):
        self.on_settings_changed = on_settings_changed
        self.on_quit = on_quit
        self._values = initial_values

        self.root = tk.Tk()
        self.root.title("Loba Settings")
        self.root.geometry("400x320")
        self.root.resizable(False, False)

        # Handle window close
        self.root.protocol("WM_DELETE_WINDOW", self._handle_quit)

        self._build_ui()
        self._apply_initial_values()

    def _build_ui(self) -> None:
        """Build the settings UI."""
        # Main frame with padding
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Title
        title = ttk.Label(
            main_frame,
            text="Loba Settings",
            font=("Helvetica", 16, "bold")
        )
        title.pack(pady=(0, 20))

        # Settings frame
        settings_frame = ttk.Frame(main_frame)
        settings_frame.pack(fill=tk.X, expand=True)

        # Subtitle display time
        self._create_slider(
            settings_frame,
            label="Subtitle Display Time",
            description="How long subtitles stay on screen",
            from_=2.0,
            to=10.0,
            resolution=0.5,
            unit="s",
            row=0,
            var_name="subtitle_ttl"
        )

        # Max lines
        self._create_slider(
            settings_frame,
            label="Max Lines",
            description="Number of subtitle lines shown",
            from_=1,
            to=4,
            resolution=1,
            unit="",
            row=1,
            var_name="max_lines"
        )

        # Silence threshold (pause detection)
        self._create_slider(
            settings_frame,
            label="Pause Detection",
            description="Silence duration before finalizing",
            from_=150,
            to=600,
            resolution=50,
            unit="ms",
            row=2,
            var_name="silence_threshold"
        )

        # Buttons frame
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(20, 0))

        # Quit button
        quit_btn = ttk.Button(
            button_frame,
            text="Quit Loba",
            command=self._handle_quit,
            style="Accent.TButton"
        )
        quit_btn.pack(side=tk.LEFT)

        # Apply button
        apply_btn = ttk.Button(
            button_frame,
            text="Apply",
            command=self._apply_settings
        )
        apply_btn.pack(side=tk.RIGHT)

        # Reset button
        reset_btn = ttk.Button(
            button_frame,
            text="Reset Defaults",
            command=self._reset_defaults
        )
        reset_btn.pack(side=tk.RIGHT, padx=(0, 10))

    def _create_slider(
        self,
        parent: ttk.Frame,
        label: str,
        description: str,
        from_: float,
        to: float,
        resolution: float,
        unit: str,
        row: int,
        var_name: str,
    ) -> None:
        """Create a labeled slider control."""
        frame = ttk.Frame(parent)
        frame.pack(fill=tk.X, pady=(0, 15))

        # Label and description
        lbl = ttk.Label(frame, text=label, font=("Helvetica", 11, "bold"))
        lbl.pack(anchor=tk.W)

        desc = ttk.Label(frame, text=description, foreground="gray")
        desc.pack(anchor=tk.W)

        # Slider row
        slider_frame = ttk.Frame(frame)
        slider_frame.pack(fill=tk.X, pady=(5, 0))

        # Variable for slider
        var = tk.DoubleVar()
        setattr(self, f"_{var_name}_var", var)

        # Value label
        value_label = ttk.Label(slider_frame, text="", width=8)
        value_label.pack(side=tk.RIGHT)
        setattr(self, f"_{var_name}_label", value_label)

        # Slider
        slider = ttk.Scale(
            slider_frame,
            from_=from_,
            to=to,
            variable=var,
            orient=tk.HORIZONTAL,
            command=lambda v, vl=value_label, u=unit, r=resolution: self._update_value_label(vl, v, u, r)
        )
        slider.pack(fill=tk.X, expand=True, side=tk.LEFT, padx=(0, 10))
        setattr(self, f"_{var_name}_slider", slider)

    def _update_value_label(self, label: ttk.Label, value: str, unit: str, resolution: float) -> None:
        """Update the value display label."""
        val = float(value)
        if resolution >= 1:
            label.config(text=f"{int(val)}{unit}")
        else:
            label.config(text=f"{val:.1f}{unit}")

    def _apply_initial_values(self) -> None:
        """Set initial slider values."""
        self._subtitle_ttl_var.set(self._values.subtitle_ttl_s)
        self._max_lines_var.set(self._values.max_lines)
        self._silence_threshold_var.set(self._values.silence_threshold_ms)

        # Update labels
        self._update_value_label(self._subtitle_ttl_label, str(self._values.subtitle_ttl_s), "s", 0.5)
        self._update_value_label(self._max_lines_label, str(self._values.max_lines), "", 1)
        self._update_value_label(self._silence_threshold_label, str(self._values.silence_threshold_ms), "ms", 50)

    def _apply_settings(self) -> None:
        """Apply current settings."""
        values = SettingsValues(
            subtitle_ttl_s=round(self._subtitle_ttl_var.get() * 2) / 2,  # Round to 0.5
            max_lines=int(self._max_lines_var.get()),
            silence_threshold_ms=int(round(self._silence_threshold_var.get() / 50) * 50),  # Round to 50
        )

        self._values = values

        if self.on_settings_changed:
            self.on_settings_changed(values)

        print(f"[Settings] Applied: TTL={values.subtitle_ttl_s}s, Lines={values.max_lines}, Silence={values.silence_threshold_ms}ms")

    def _reset_defaults(self) -> None:
        """Reset to default values."""
        self._subtitle_ttl_var.set(4.5)
        self._max_lines_var.set(2)
        self._silence_threshold_var.set(300)

        # Update labels
        self._update_value_label(self._subtitle_ttl_label, "4.5", "s", 0.5)
        self._update_value_label(self._max_lines_label, "2", "", 1)
        self._update_value_label(self._silence_threshold_label, "300", "ms", 50)

    def _handle_quit(self) -> None:
        """Handle quit button or window close."""
        if self.on_quit:
            self.on_quit()
        self.root.quit()
        self.root.destroy()

    def run(self) -> None:
        """Run the settings window (blocking)."""
        self.root.mainloop()

    def update(self) -> None:
        """Process pending UI events (non-blocking)."""
        try:
            self.root.update()
        except tk.TclError:
            pass  # Window was closed

    def is_alive(self) -> bool:
        """Check if window is still open."""
        try:
            return self.root.winfo_exists()
        except tk.TclError:
            return False
