# Guide & Installation Instructions for AI Agents (`AGENTS.md`)

This repository contains the **`game-mod-e2e`** skill: an end-to-end engineering, build/deploy, in-engine IPC bridge, and automated verification pipeline for PC game mods across any genre or engine.

 It is portable across **Google Antigravity**, **Claude Code**, **OpenAI Codex**, **Cursor**, **Windsurf**, and any agent supporting the `SKILL.md` standard.

---

## 1. Agent-Assisted Installation Steps

If the user asks you (the AI agent) to install this skill on their machine or into their current project, identify which agent environment you are running in and execute the corresponding steps below.

### Option A: Universal One-Command Install (Skills CLI)
If `npx` is available on the system, you can install this skill for the active agent or all agents at once:
```bash
# Install globally for all supported agents (Claude Code, Codex, Gemini/Antigravity, Cursor, Windsurf)
npx skills add Co0lDoge/game-mod-e2e --global --agent '*'

# Or target a specific agent:
npx skills add Co0lDoge/game-mod-e2e --global --agent claude-code
npx skills add Co0lDoge/game-mod-e2e --global --agent codex
```

### Option B: Direct Git Clone (Zero Node.js Dependency)

#### 1. Google Antigravity / Gemini
- **Global install (recommended):**
  - **Windows (PowerShell):**
    ```powershell
    git clone https://github.com/Co0lDoge/game-mod-e2e.git "$HOME\.gemini\config\skills\game-mod-e2e"
    ```
  - **macOS / Linux:**
    ```bash
    git clone https://github.com/Co0lDoge/game-mod-e2e.git ~/.gemini/config/skills/game-mod-e2e
    ```
- **Workspace-only install:**
  ```bash
  git clone https://github.com/Co0lDoge/game-mod-e2e.git .agents/skills/game-mod-e2e
  ```

#### 2. Claude Code (Anthropic)
- **Global install:**
  - **Windows (PowerShell):**
    ```powershell
    git clone https://github.com/Co0lDoge/game-mod-e2e.git "$HOME\.claude\skills\game-mod-e2e"
    ```
  - **macOS / Linux:**
    ```bash
    git clone https://github.com/Co0lDoge/game-mod-e2e.git ~/.claude/skills/game-mod-e2e
    ```
- **Project-local install:**
  ```bash
  git clone https://github.com/Co0lDoge/game-mod-e2e.git .claude/skills/game-mod-e2e
  ```

#### 3. OpenAI Codex CLI
- **Global install:**
  - **Windows (PowerShell):**
    ```powershell
    git clone https://github.com/Co0lDoge/game-mod-e2e.git "$HOME\.codex\skills\game-mod-e2e"
    ```
  - **macOS / Linux:**
    ```bash
    git clone https://github.com/Co0lDoge/game-mod-e2e.git ~/.codex/skills/game-mod-e2e
    ```
- **Project-local install:**
  ```bash
  git clone https://github.com/Co0lDoge/game-mod-e2e.git .agents/skills/game-mod-e2e
  ```

#### 4. Verification After Installing
After cloning, verify that `<target_dir>/SKILL.md`, `<target_dir>/references/`, and `<target_dir>/examples/` exist, and inform the user that the `game-mod-e2e` skill is installed and ready.

---

## 2. How to Use This Skill on a Game Mod Project

When activated on a game modding repository:
1. Read [`SKILL.md`](./SKILL.md) first for the core workflow and architectural rules.
2. Read the modular guides in [`references/`](./references/) as needed:
   - [`references/injection-and-hooks.md`](./references/injection-and-hooks.md) — Selecting between a native Mod SDK (Tier 1), a raw Proxy DLL + Detours/MinHook (Tier 2), or an external black-box process harness (Tier 3).
   - [`references/verification-and-test-matrix.md`](./references/verification-and-test-matrix.md) — Designing the 7 universal test categories (`SYS`, `CTX`, `TOG`, `FEAT`, `REV`, `SEQ`, `PER`, `EDG`) and applying 3-layer verification (Engine State + ROI Pixel Diffs or Telemetry + Mandatory Post-Run Agent Critique).
   - [`references/build-deploy-and-ci.md`](./references/build-deploy-and-ci.md) — Preventing DLL file-lock build failures, gating the `TestBridge`, and configuring GitHub Actions CI.
3. Copy and adapt the starter templates from [`examples/`](./examples/) into the target project:
   - [`examples/cpp_named_pipe_bridge.h`](./examples/cpp_named_pipe_bridge.h) — In-engine thread-safe Named Pipe + Main-Thread Command Queue server.
   - [`examples/bridge_client.py`](./examples/bridge_client.py) — Host-side Python Named Pipe JSON-RPC client and CLI probe tool.
   - [`examples/run_matrix_template.py`](./examples/run_matrix_template.py) — Atomic batch test runner (`Launch -> Auto-Load Save -> Run Matrix -> Immediate Kill -> Report`).

---

## 3. Repository Maintenance Rules

If you are editing this skill repository:
- Keep [`SKILL.md`](./SKILL.md) concise, agent-neutral, and free of game-specific coupling.
- Keep version numbers synchronized across [`SKILL.md`](./SKILL.md) (`metadata.version`), [`.claude-plugin/plugin.json`](./.claude-plugin/plugin.json), and [`.cursor-plugin/plugin.json`](./.cursor-plugin/plugin.json).
- Keep [`README.md`](./README.md) and [`AGENTS.md`](./AGENTS.md) aligned whenever files or templates are added.
