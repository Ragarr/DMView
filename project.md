# System Requirements

**Map projection at scale with fog of war for in-person tabletop play**

---

## 1. Purpose

Allow projecting tactical maps at **true physical scale** onto a monitor or projector for in-person games with **physical miniatures**, with **manual control of fog of war** and map framing.

No virtual miniatures, rules, dice, turns, or game logic.

---

## 2. System Views

### 2.1 Player View

- Selected monitor/projector  
- Fullscreen  
- Shows only:
  - Scaled map
  - Fog of war

### 2.2 DM View

- DM monitor  
- Controls:
  - Map configuration
  - Scale control
  - Map position
  - Fog of war control

---

## 3. Map Management

- Works only with static images (PNG, JPG, etc.)  
- Each map has metadata:
  - Number of tiles (width and height)
  - Size of each tile in `mm`
  - Initial fog state
  - Current fog state
  - Initial and current position of the map relative to the player's viewport

---

## 4. Map Scaling

- Automatically scale the map so that each projected tile has the correct physical size
- Maintain the map's aspect ratio
- If the map is larger than the screen → only part is visible; DM can pan
- If the map is smaller than the screen → it can be positioned inside the screen; DM can pan

---

## 5. Framing Control

- DM can move the map on X and Y axes
- DM sees the entire map with an overlay indicating the area visible to players
- Changes are reflected in real time in the player view
- Map (and fog) can be rotated in 90° increments

---

## 6. Fog of War

- Layer above the map
- DM view: semi-transparent
- Player view: fully opaque
- DM can:
  - Reveal areas (brush and area selection)
  - Darken previously revealed areas
- Minimal tools:
  - Configurable brush
  - Area selection (rectangular or freeform)

---

## 7. Session Management

- Session = a set of prepared maps
- DM can:
  - Create a session
  - Add maps
  - Configure metadata and initial fog
- During the session:
  - Switch maps instantly
  - Automatically apply:
    - Scale
    - Fog
    - Position

---

## 8. Persistence and Format

- Each map: image + metadata file
  - Scale (`mm`)
  - Tiles
  - Fog state
  - Position
- Export session = folder with images + metadata
- Import session = reconstruct maps with their configurations without intervention

---

## 9. Exclusions

- Virtual miniatures
- Characters
- Dice
- Rules, turns
- Lighting or line-of-sight
- Network or remote play

---

## 10. Summary

> **Application for projecting maps at true physical scale, with editable fog of war and session management, designed exclusively for in-person play with physical miniatures.** ✨
