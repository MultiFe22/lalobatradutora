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
    translation_model: str  # "marian" or "m2m100"
    hotkey: str = "f11"  # default to F11


class SettingsWindow:
    """
    Simple tkinter window for adjusting Loba settings.

    Exposes user-friendly controls for:
    - Subtitle display time
    - Max lines on screen
    - Pause detection sensitivity
    """

    # Model display names
    MODEL_NAMES = {
        "marian": "MarianMT (European Portuguese)",
        "m2m100": "M2M100 (Brazilian Portuguese)",
        "none": "None (English only)",
    }

    def __init__(
        self,
        initial_values: SettingsValues,
        available_models: list[str] | None = None,
        on_settings_changed: Optional[Callable[[SettingsValues], None]] = None,
        on_quit: Optional[Callable[[], None]] = None,
    ):
        self.on_settings_changed = on_settings_changed
        self.on_quit = on_quit
        self._values = initial_values
        self._available_models = available_models or ["none"]

        self.root = tk.Tk()
        self.root.title("Loba Settings")
        self.root.geometry("420x580")
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

        # Translation model dropdown
        self._create_model_dropdown(settings_frame)

        # Hotkey selector dropdown
        self._create_hotkey_dropdown(settings_frame)

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

        # Slider - use tk.Scale for visible handle on macOS
        slider = tk.Scale(
            slider_frame,
            from_=from_,
            to=to,
            resolution=resolution,
            variable=var,
            orient=tk.HORIZONTAL,
            showvalue=False,
            sliderlength=20,
            command=lambda v, vl=value_label, u=unit, r=resolution: self._update_value_label(vl, v, u, r)
        )
        slider.pack(fill=tk.X, expand=True, side=tk.LEFT, padx=(0, 10))
        setattr(self, f"_{var_name}_slider", slider)

    def _create_model_dropdown(self, parent: ttk.Frame) -> None:
        """Create the translation model dropdown."""
        frame = ttk.Frame(parent)
        frame.pack(fill=tk.X, pady=(0, 15))

        # Label and description
        lbl = ttk.Label(frame, text="Translation Model", font=("Helvetica", 11, "bold"))
        lbl.pack(anchor=tk.W)

        desc = ttk.Label(frame, text="Language model for translation", foreground="gray")
        desc.pack(anchor=tk.W)

        # Dropdown
        self._model_var = tk.StringVar()

        # Build display values list
        display_values = [self.MODEL_NAMES.get(m, m) for m in self._available_models]

        dropdown = ttk.Combobox(
            frame,
            textvariable=self._model_var,
            values=display_values,
            state="readonly",
            width=35,
        )
        dropdown.pack(anchor=tk.W, pady=(5, 0))
        self._model_dropdown = dropdown

    def _create_hotkey_dropdown(self, parent: ttk.Frame) -> None:
        """Create the hotkey selector dropdown."""
        frame = ttk.Frame(parent)
        frame.pack(fill=tk.X, pady=(0, 15))

        # Label and description
        lbl = ttk.Label(frame, text="Toggle Hotkey", font=("Helvetica", 11, "bold"))
        lbl.pack(anchor=tk.W)

        desc = ttk.Label(frame, text="Key to enable/disable translation", foreground="gray")
        desc.pack(anchor=tk.W)

        # Dropdown
        self._hotkey_var = tk.StringVar()

        # Available hotkeys (F1-F12)
        hotkey_options = [f"F{i}" for i in range(1, 13)]

        dropdown = ttk.Combobox(
            frame,
            textvariable=self._hotkey_var,
            values=hotkey_options,
            state="readonly",
            width=10,
        )
        dropdown.pack(anchor=tk.W, pady=(5, 0))
        self._hotkey_dropdown = dropdown

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

        # Set model dropdown
        model_display = self.MODEL_NAMES.get(self._values.translation_model, self._values.translation_model)
        self._model_var.set(model_display)

        # Set hotkey dropdown
        self._hotkey_var.set(self._values.hotkey.upper())

    def _get_model_key_from_display(self, display_name: str) -> str:
        """Convert display name back to model key."""
        for key, name in self.MODEL_NAMES.items():
            if name == display_name:
                return key
        return display_name  # Fallback

    def _apply_settings(self) -> None:
        """Apply current settings."""
        model_key = self._get_model_key_from_display(self._model_var.get())
        hotkey = self._hotkey_var.get().lower()

        values = SettingsValues(
            subtitle_ttl_s=round(self._subtitle_ttl_var.get() * 2) / 2,  # Round to 0.5
            max_lines=int(self._max_lines_var.get()),
            silence_threshold_ms=int(round(self._silence_threshold_var.get() / 50) * 50),  # Round to 50
            translation_model=model_key,
            hotkey=hotkey,
        )

        self._values = values

        if self.on_settings_changed:
            self.on_settings_changed(values)

        print(f"[Settings] Applied: TTL={values.subtitle_ttl_s}s, Lines={values.max_lines}, Silence={values.silence_threshold_ms}ms, Model={model_key}, Hotkey={hotkey.upper()}")

    def _reset_defaults(self) -> None:
        """Reset to default values."""
        self._subtitle_ttl_var.set(4.5)
        self._max_lines_var.set(2)
        self._silence_threshold_var.set(300)

        # Update labels
        self._update_value_label(self._subtitle_ttl_label, "4.5", "s", 0.5)
        self._update_value_label(self._max_lines_label, "2", "", 1)
        self._update_value_label(self._silence_threshold_label, "300", "ms", 50)

        # Reset model to first available (prefer marian)
        default_model = "marian" if "marian" in self._available_models else self._available_models[0]
        self._model_var.set(self.MODEL_NAMES.get(default_model, default_model))

        # Reset hotkey to F11
        self._hotkey_var.set("F11")

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
