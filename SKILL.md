---
name: game-mod-e2e
description: |
  End-to-end engineering, build/deploy, and automated in-engine verification pipeline for PC game mods across any genre or engine (with or without a modding SDK).
  Use this skill whenever developing, debugging, testing, or setting up CI/CD for a game mod, native plugin, DLL hook, UI overhaul, or gameplay mechanic modification.
license: MIT
metadata:
  version: "1.0.0"
---

# Game Mod Engineering & Automated E2E Pipeline

This skill establishes a closed-loop engineering and verification pipeline for game mods. Because games run custom rendering loops, lock loaded binaries, ignore background OS input, and lack standard accessibility trees, use this pipeline instead of manual playtesting or blind keyboard injection.

---

## 1. Architecture Overview: Dual-Track Mod Design

Structure every mod project into two cleanly separated tracks:

1. **Decoupled Core Logic (Headless & CI-Testable):**
   - Keep state machines, data parsers, math, configuration, and rule evaluation free of live game process memory or rendering calls.
   - Test this layer headlessly via unit tests (`ctest` / Catch2 / NUnit) on every build and in CI/CD.
2. **Engine Integration + Gated Test Bridge (In-Game E2E):**
   - Keep hooks, memory reads, UI bridges, and rendering calls in the integration layer.
   - Embed a lightweight **In-Engine Test Bridge** (Named Pipe JSON-RPC server) gated behind a build flag (`ENABLE_TEST_BRIDGE`) or runtime environment/config toggle so end-user release builds remain clean.

For build scripts, DLL lock protection, and CI/CD configuration, see [Build, Deploy & CI Guide](./references/build-deploy-and-ci.md).

---

## 2. Step-by-Step Pipeline Setup

### Step 1: Select the Engine Injection Tier
Determine how your code loads into the game process. Follow the tiered priority order in [Injection & Hooking Strategies](./references/injection-and-hooks.md):
- **Tier 1 (Mod SDK / Loader Exists):** Use the native loader (e.g., SKSE, DAOLib, F4SE, BepInEx, UE4SS, RED4ext).
- **Tier 2 (No SDK — Native C/C++ Game):** Build a **Proxy DLL** (`dinput8.dll`, `version.dll`, or `dxgi.dll`) + **MinHook / Detours** to hook the main update tick and `IDXGISwapChain::Present` / `IDirect3DDevice9::Present`.
- **Tier 3 (No Injection — Black-Box / Protected Exe):** Use an external process with `ReadProcessMemory` / AOB signature scanning + Windows Desktop Duplication API for frame capture.

### Step 2: Wire the In-Engine Test Bridge
Embed a background Named Pipe listener (`\\.\pipe\<game>_mcp_bridge`) using the template in [cpp_named_pipe_bridge.h](./examples/cpp_named_pipe_bridge.h).

**Critical Engineering Rules for the Bridge:**
- **Never touch engine state from the pipe thread:** The pipe thread must only push commands into a mutex-protected queue and wait on a condition variable. Drain and execute commands exclusively inside the game's main frame tick (`OnFrame` / `Present`).
- **Expose 5 Universal RPC Primitives:**
  1. `ping`: Returns current frame counter and responsiveness.
  2. `get_status`: Returns game mode (`main_menu`, `loading`, `in_world`), active screen, and player/entity readiness.
  3. `load_save` / `fast_forward`: Programmatically loads a test save or skips title screens.
  4. `inspect_state`: Queries mod state, memory fields, UI element coordinates/visibility/colors, or gameplay telemetry.
  5. `invoke_action` & `capture_frame`: Triggers mod actions/UI events directly and captures the backbuffer/window to PNG.
- **Background Focus & Input Debounce:**
  - When automated tests run, the game window may not hold OS foreground focus, causing `GetAsyncKeyState` or raw `SendInput` to fail. In `send_key` test handlers, invoke the mod's internal toggle/action function directly alongside Win32 `PostMessage` events.
  - When binding hotkeys in-game, never poll raw key state in `OnFrame` alongside an engine input callback without a **200–250ms timestamp debounce**, or a single keypress will double-fire (`open -> close`) within milliseconds.

### Step 3: Build the Host-Side Client & Atomic Batch Runner
Use a shared Python pipe client ([bridge_client.py](./examples/bridge_client.py)) with two execution modes instead of per-action MCP tool calls:
1. **CLI Probe Mode (Discovery Phase):** Run one-off CLI commands (`python bridge_client.py inspect_state ...`) when exploring unknown UI trees or memory structures.
2. **Standalone Batch Runner (Verification Phase):** Use [run_matrix_template.py](./examples/run_matrix_template.py) to execute the entire test suite in a single native-speed script.

### Step 4: Enforce the Strict Atomic Game Lifecycle
Never leave the game running while analyzing results or editing code:
```text
[Ensure Game Closed] -> [Build & Deploy Mod] -> [Launch Game (Direct or schtasks)]
  -> [Poll Bridge Ready] -> [Auto-Load Save into World] -> [Execute Full Test Matrix]
  -> [Save Screenshots, Telemetry & test_report.json] -> [IMMEDIATELY Kill Game Process]
  -> [Offline Agent Analysis & Screenshot/Log Critique]
```
- **UAC / Sandbox Launch Bypass:** If launching the game directly from the agent shell fails due to Windows elevation or session isolation, register and trigger a Windows Scheduled Task (`schtasks /run /tn "<Game>_AutoLauncher"`) running under the interactive user token.
- **Guaranteed Teardown:** Wrap the runner's main block in `try ... finally:` that forcefully terminates `<Game>.exe` (`taskkill /F /IM <Game>.exe`) before the script exits.

---

## 3. Verification & Universal Test Matrix

Design the project's test matrix around the **7 Universal Mod Test Archetypes** detailed in [Verification & Test Matrix Guide](./references/verification-and-test-matrix.md):
1. `SYS` — Smoke, Hook Health & Frame Loop
2. `CTX` — Context Guards (mod refuses to activate in invalid game modes/screens)
3. `FEAT` — Core Feature Happy Paths (state + output verification)
4. `REV` — Reversibility, Reset & Cancel Workflows (button reset, menu close, parent screen exit)
5. `SEQ` — Sequential & Combinatorial Operations (multi-step chains without state bleed)
6. `PER` — Persistence Across Transitions (save/load, zone change, preset swap)
7. `EDG` — Edge Cases, Idempotency & Debounce (no-op resets on clean state, hotkey bounce)

### Adaptive Three-Layer Verification
Verify every test case using the appropriate layers for the mod's domain:
1. **Layer 1 — Engine/Mod State Assertions (All Mods):** Query internal variables via `inspect_state` to confirm expected state transitions.
2. **Layer 2 — Output Metrics (Domain-Specific):**
   - **Visual Mods (UI, 3D Models, Shaders, VFX):** Capture an **in-session baseline screenshot** immediately prior to the action (avoiding cross-screen transition artifacts), crop the specific Region of Interest (ROI), and assert pixel diff thresholds ($\Delta > \text{threshold}$ for active changes; $\Delta < \text{noise\_floor}$ for reverts). Verify UI bounding boxes do not overlap vanilla elements.
   - **Non-Visual Mods (Gameplay, Combat, AI, Audio, Performance):** Capture structured event logs, state snapshots, timing deltas, or numeric telemetry before and after the action and assert exact invariants.
3. **Layer 3 — Mandatory Post-Run Agent Critique:**
   - After the game closes, inspect every captured screenshot or telemetry log.
   - Before writing any code fixes, explicitly document **"What's Good"** and **"What's Wrong"** for each capture (checking text readability/contrast, layout overlaps, visual indicators, or state anomalies that numeric diffs miss).
