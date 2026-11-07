# `game-mod-e2e` — End-to-End Game Modding & In-Engine Automation Skill

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)
[![Agent Skill](https://img.shields.io/badge/Agent_Skill-Antigravity_%7C_Claude_Code_%7C_Codex_%7C_Cursor-blue)](#installation)

**`game-mod-e2e`** is a portable AI Agent Skill that teaches coding agents (**Google Antigravity**, **Claude Code**, **OpenAI Codex**, **Cursor**, **Windsurf**) how to build, hook, deploy, and run **fully automated, hands-free in-engine E2E verification pipelines** for PC game mods—whether the game has a rich modding SDK or no modding support at all.

---

## Why Game Mods Need a Dedicated Agent Pipeline

Standard web/app testing workflows fail on PC games because:
1. **Binary File Locks:** Building a mod DLL while the game is running fails because the OS locks loaded binaries and archives.
2. **No Accessibility DOM:** Games render via DirectX/Vulkan/OpenGL swapchains and custom UI engines (Scaleform/Flash, Dear ImGui, Unity Canvas, Unreal Slate).
3. **Focus & Input Swallowing:** Minimized or backgrounded games ignore `SendInput` and `GetAsyncKeyState`, while polling hotkeys alongside engine callbacks causes rapid double-toggle bounces (`open -> close` in 6ms).
4. **Silent Visual Defects:** Programmatic "button clicked" checks miss overlapping UI panels, unreadable dark-on-dark typography, or broken 3D meshes.

`game-mod-e2e` replaces manual playtesting with a deterministic, closed-loop engineering pipeline.

---

## Pipeline Architecture

```text
┌─────────────────────────────────────────────────────────────────────────┐
│               AI Coding Agent (Antigravity / Claude / Codex)            │
└──────┬───────────────────────────▲───────────────────────────▲──────────┘
       │ 1. Build & Atomic Launch  │ 2. JSON-RPC over Pipe     │ 3. Offline Critique
       ▼                           ▼                           │    (State + Diffs)
┌─────────────────┐       ┌─────────────────────┐       ┌──────┴──────────┐
│  Atomic Runner  │       │  bridge_client.py   │       │  3-Layer Truth  │
│ (Direct / Task  │       │  (\\.\pipe\game_    │       │ • Engine State  │
│  Scheduler +    │       │     mcp_bridge)     │       │ • ROI Pixel Diff│
│  try..finally   │       └────────┬────────────┘       │   or Telemetry  │
│  taskkill)      │                │                    │ • Visual Review │
└──────┬──────────┘                │                    └──────▲──────────┘
       │                           ▼                           │
┌──────▼───────────────────────────────────────────────────────┴──────────┐
│                         Target Game Process                             │
│  • Tier 1: Native SDK (SKSE, DAOLib, BepInEx, UE4SS, RED4ext)           │
│  • Tier 2: Proxy DLL (version.dll / dinput8.dll / dxgi.dll + MinHook)   │
│  • Tier 3: External Black-Box (ReadProcessMemory + Desktop Duplication) │
│  • Thread-Safe Main-Thread Command Queue drained on OnFrame / Present() │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Core Capabilities

### 1. Works With or Without a Modding SDK (Tiered Injection)
- **Tier 1 (Mod SDK Available):** Integrates natively with SKSE/CommonLibSSE, DAOLib, BepInEx, MelonLoader, UE4SS, or RED4ext.
- **Tier 2 (No SDK — Raw Native C/C++ Games):** Bootstraps a self-contained **Proxy DLL** (`version.dll`, `dinput8.dll`, or `dxgi.dll`), hooks `Present()` via Detours/MinHook, and uses AOB byte-pattern scanning.
- **Tier 3 (External Black-Box):** Falls back to `ReadProcessMemory` + `PrintWindow` / Desktop Duplication API when injection is impossible.

### 2. Thread-Safe In-Engine Named Pipe Bridge
- Runs a background Named Pipe listener (`\\.\pipe\<game>_mcp_bridge`) that queues JSON commands onto the game's main/render thread (`OnFrame` / `Present`), preventing race conditions and crashes.
- Gated behind a compile-time CMake option (`ENABLE_TEST_BRIDGE`) or runtime flag so production release builds remain clean.

### 3. Strict Atomic Game Lifecycle
Every test run follows an atomic lifecycle:
1. Ensure `<Game>.exe` is closed before compiling/deploying.
2. Launch the game (with automatic Windows Scheduled Task `schtasks` fallback to bypass UAC/sandbox token isolation).
3. Poll the bridge until the Main Menu loads, then **programmatically auto-load a test save** into active gameplay.
4. Execute the entire test matrix at native speed in a single batch script.
5. **Immediately terminate `<Game>.exe`** in a `finally` block before the agent analyzes screenshots or edits code.

### 4. Universal Mod Test Matrix & 3-Layer Verification
Structures test suites across **7 universal mod test archetypes**:
- `SYS` (Smoke & Frame Loop) · `CTX` (Context Guards) · `TOG` (Navigation & Hotkey Debounce) · `FEAT` (Core Happy Paths) · `REV` (Reversibility & Cancel Flows) · `SEQ` (Multi-Step Combinatorics) · `PER` (Save/Load & Transition Persistence) · `EDG` (Idempotent No-Ops & Edge Cases).

Evaluates every test using **Three-Layer Verification**:
1. **Layer 1 (Engine State):** Asserts internal memory/variable states via `inspect_state`.
2. **Layer 2 (Domain Output Metrics):**
   - *Visual Mods (UI, 3D, Shaders):* Captures in-session clean baselines and computes Region-of-Interest (ROI) pixel diffs + layout collision checks.
   - *Non-Visual Mods (Gameplay, AI, Combat, Audio, Performance):* Queries structured event logs, stat diffs, and frame-time telemetry.
3. **Layer 3 (Mandatory Agent Critique):** Requires the agent to inspect every capture offline and write a *"What's Good / What's Wrong"* review before writing fixes.

---

## Installation

### Ask Your Agent to Install It
Paste this prompt into **Antigravity**, **Claude Code**, **Codex**, or **Cursor**:
> `Install the skill from https://github.com/Co0lDoge/game-mod-e2e following the instructions in AGENTS.md`

---

### Google Antigravity / Gemini
```powershell
# Windows (PowerShell) - Global install
git clone https://github.com/Co0lDoge/game-mod-e2e.git "$HOME\.gemini\config\skills\game-mod-e2e"
```
```bash
# macOS / Linux - Global install
git clone https://github.com/Co0lDoge/game-mod-e2e.git ~/.gemini/config/skills/game-mod-e2e
```

### Claude Code
Install via the Claude Code plugin marketplace:
```text
/plugin marketplace add Co0lDoge/game-mod-e2e
/plugin install game-mod-e2e@game-mod-e2e
```
Or clone directly into your Claude skills folder:
```powershell
# Windows (PowerShell)
git clone https://github.com/Co0lDoge/game-mod-e2e.git "$HOME\.claude\skills\game-mod-e2e"
```
```bash
# macOS / Linux
git clone https://github.com/Co0lDoge/game-mod-e2e.git ~/.claude/skills/game-mod-e2e
```

### OpenAI Codex CLI
```powershell
# Windows (PowerShell)
git clone https://github.com/Co0lDoge/game-mod-e2e.git "$HOME\.codex\skills\game-mod-e2e"
```
```bash
# macOS / Linux
git clone https://github.com/Co0lDoge/game-mod-e2e.git ~/.codex/skills/game-mod-e2e
```

### Universal Skills CLI (`npx skills`)
```bash
# Install globally for all detected agents (Claude Code, Codex, Gemini, Cursor, Windsurf)
npx skills add Co0lDoge/game-mod-e2e --global --agent '*'
```

---

## Repository Contents

```text
game-mod-e2e/
├── SKILL.md                                     # Core skill instructions & workflow runbook
├── AGENTS.md                                    # Agent-assisted install steps & maintenance guide
├── CLAUDE.md                                    # Entry point for Claude Code
├── references/
│   ├── injection-and-hooks.md                   # Tier 1 (SDK), Tier 2 (Proxy DLL + MinHook), Tier 3 (External)
│   ├── verification-and-test-matrix.md          # 7 universal test categories & 3-layer verification rules
│   └── build-deploy-and-ci.md                   # DLL lock safety, TestBridge gating & GitHub Actions CI checklist
└── examples/
    ├── cpp_named_pipe_bridge.h                  # Drop-in C++20 thread-safe Named Pipe + Main-Thread Queue
    ├── bridge_client.py                         # Zero-dependency Python Named Pipe client & CLI probe tool
    └── run_matrix_template.py                   # Atomic batch runner (Launch -> Auto-load -> Matrix -> Kill)
```

---

## License

Released under the [MIT License](./LICENSE).
