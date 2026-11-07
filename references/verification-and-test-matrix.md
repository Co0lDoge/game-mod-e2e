# Universal Mod Verification & Test Matrix Design

A reliable game mod test suite never relies solely on "button was clicked without crashing." Every test case must verify both **internal engine/mod state** and **observable output** (visual or telemetry).

---

## 1. The 7 Universal Mod Test Archetypes

Structure every project's test matrix (`test_matrix.md` and `test_matrix_runner.py`) around these 7 mod-agnostic categories:

| Prefix | Category | Purpose & What to Test |
| :--- | :--- | :--- |
| **`SYS-`** | **System & Smoke** | Bridge connectivity (`ping`), frame counter advancing, game save auto-loaded into active world gameplay. |
| **`CTX-`** | **Context & State Guards** | Mod only activates when prerequisites are met (e.g., sub-menus refuse to open if parent screen is closed; combat hooks do not fire on main menu or loading screens). |
| **`TOG-`** | **Navigation & Input Entry** | Opening/closing/triggering mod features via all supported entry points (UI buttons, hotkeys, console/script commands). Tests rapid double-press debounce. |
| **`FEAT-`** | **Core Feature Happy Paths** | Primary mod capabilities. Verifies both internal data mutation and immediate visual/gameplay output. |
| **`REV-`** | **Reversibility, Reset & Cancel** | Undoing or discarding changes via every possible exit path: explicit `[Reset]` / `[Cancel]` buttons, hotkey menu close, and parent screen exit (`ESC`). |
| **`SEQ-`** | **Sequential & Combinatorial** | Performing multiple modifications in sequence (`Feature A -> Feature B`), partial resets (`Reset B while keeping A`), and overriding already-committed states. |
| **`PER-`** | **Persistence & Transitions** | Verifying mod state survives closing/re-opening menus, switching presets/profiles, area/level transitions, and Save/Load cycles. |
| **`EDG-`** | **Edge Cases & Idempotency** | Clicking `[Reset]` or `[Discard]` when zero changes exist (safe no-op without flicker or crash), empty slots/lists, and switching presets without leaking uncommitted staging. |

---

## 2. Adaptive Three-Layer Verification

### Layer 1: Programmatic Engine/Mod State (Required for All Mods)
Query the in-engine bridge (`inspect_state`) after every action to assert internal truth:
- Active flags, state enum values, dirty/staged booleans (`hasStagedChanges == false`).
- UI element properties (coordinates `_x`, `_y`, `_width`, `_height`, `_visible`, text content, hex text color).
- Vanilla elements hidden/restored properly when custom overlays open/close.

### Layer 2: Domain-Appropriate Output Metrics

#### A. For Visual Mods (UI, 3D Meshes, Textures, Shaders, Lighting, HUD)
1. **Region-of-Interest (ROI) Pixel Diffing:**
   - Crop the specific screen region affected by the mod (e.g., 3D character viewport, custom UI panel, minimap) and compute the Mean Absolute Error (MAE) between RGB channels.
   - **Positive Change Assertion:** `diff(baseline_crop, active_crop) > min_change_threshold` (confirms the 3D mesh, shader, or UI visually changed on screen).
   - **Revert / Cancel Assertion:** `diff(baseline_crop, reverted_crop) < max_noise_threshold` (confirms the visual state returned to the original look).
2. **The In-Session Baseline Rule (Critical):**
   - Never compare a reverted crop against a screenshot taken in a *different* screen session if opening/closing the screen alters background stats, lighting, or camera angle.
   - Always capture a fresh **in-session clean baseline** immediately before staging the change within the same open menu/scene, then compare both the active preview and the reverted state against that immediate baseline.
3. **UI Layout & Contrast Checks:**
   - Verify custom UI bounds do not collide with vanilla headers, borders, or bottom status bars.
   - Verify text colors maintain high contrast against dark or parchment backgrounds.

#### B. For Non-Visual Mods (Gameplay Mechanics, AI, Combat, Audio, Performance, Bugfixes)
When a mod has no visual footprint, replace pixel diffing with structured telemetry queries over the bridge:
- **Combat / Mechanics / AI:** Query entity stats, effect/buff arrays, cooldown timers, AI state machine transitions, or combat log ring-buffers before and after triggering the mechanic.
- **Audio Mods:** Query active sound bank IDs, FMOD/Wwise event states, or channel playback flags.
- **Performance / Memory Mods:** Query frame-time percentiles (p50/p99), allocator heap counters, or load-time durations.
- **Save / Co-Save Mods:** Serialize state, trigger a save/load cycle, and diff the restored struct fields against the pre-save snapshot.

### Layer 3: Mandatory Post-Run Agent Critique
Automated numbers do not catch aesthetic defects (such as unreadable dark-on-dark fonts, overlapping icons, clipped text, or missing selection indicators like `>>`).
- Immediately after the batch runner terminates the game, inspect the generated screenshots (or telemetry traces) in full.
- Provide a structured **"What's Good / What's Wrong"** commentary for each key capture **before** moving to code changes.
