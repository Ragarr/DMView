# DMView 🎲

**Map projection at true physical scale with editable fog-of-war, for in-person tabletop play.**

## What it does
- Project a static image map to a player display at a physically accurate scale (mm → pixels).
- Manual **Fog of War** editing (brush & rectangle), with separate DM (semi-transparent fog) and Player (opaque fog) views.
- Session management (save/load maps, fog masks, per-map metadata).
- Import maps with three scaling methods (default: 3x3 sample selector, also by image width or tiles across).
- DM preview shows a green overlay of the player viewport which you can drag to move the player view.

## Quick start

Requirements:
- Python 3.12.3 (Tkinter available)  
- Install dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Run the app (normal):

```bash
python dmview/main.py --player-monitor 0
```

Useful options:
- `--list-monitors` — show detected monitors
- `--player-monitor <index>` — set which monitor is used for player display