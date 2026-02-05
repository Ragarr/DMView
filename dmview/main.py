"""Entry point for DMView application."""

import argparse
import sys
import tkinter as tk
# Import here to avoid circular imports
from app import Application
from config import Config


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="DMView - Tabletop RPG map projection with fog of war"
    )
    parser.add_argument(
        "--session",
        "-s",
        type=str,
        help="Path to session directory to open",
    )
    parser.add_argument(
        "--list-monitors",
        action="store_true",
        help="List available monitors and exit",
    )
    parser.add_argument(
        "--player-monitor",
        "-m",
        type=int,
        help="Index of monitor to use for player display (0-based)",
    )

    args = parser.parse_args()

    # Handle --list-monitors
    if args.list_monitors:
        try:
            from screeninfo import get_monitors

            monitors = get_monitors()
            print("Available monitors:")
            for i, m in enumerate(monitors):
                primary = " (primary)" if m.is_primary else ""
                size_mm = ""
                if m.width_mm and m.height_mm:
                    size_mm = f", {m.width_mm}x{m.height_mm}mm"
                print(f"  {i}: {m.name or 'Unknown'} - {m.width}x{m.height}{size_mm}{primary}")
        except ImportError:
            print("screeninfo not installed - cannot detect monitors")
            print("Install with: pip install screeninfo")
        return 0

    # Create Tk root
    root = tk.Tk()

    # Apply command line options to config
    if args.player_monitor is not None:
        config = Config.load()
        config.player_monitor = args.player_monitor
        config.save()

    # Create and run application
    app = Application(root)

    # Open session if specified
    if args.session:
        from pathlib import Path
        if not app._try_load_session(Path(args.session)):
            print(f"Warning: Could not load session from {args.session}")

    app.run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
