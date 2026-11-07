# Tiered Game Injection & Hooking Strategies

When bootstrapping a mod and its in-engine test bridge, select the highest available tier for the target game.

---

## Tier 1: Existing Mod Loader / Native SDK (Preferred)

When the community already maintains a script extender or mod loader, build a standard plugin for that ecosystem:

| Engine / Game Family | Loader / SDK | Main-Thread Hook Point | UI / State Access |
| :--- | :--- | :--- | :--- |
| **BioWare Eclipse (DA:O)** | DAOLib | `dao::frame::Register` | Scaleform/GFx `_root`, `CClientExoApp` |
| **Bethesda Creation Engine** | SKSE / F4SE / SFSE (`CommonLibSSE-NG`) |Messaging interface (`kPostLoadGame`, main update hook) | Scaleform `BSUIScaleformData`, `RE::PlayerCharacter` |
| **Unity (Mono / IL2CPP)** | BepInEx / MelonLoader + Harmony | `MonoBehaviour.Update()` / `LateUpdate()` | `GameObject.Find`, C# Reflection, `ScreenCapture.CaptureScreenshotAsTexture` |
| **Unreal Engine 4 / 5** | UE4SS (C++ or Lua) | `ProcessEvent` hook / `Tick` | `UObjectGlobals::FindFirstOf`, `UGameViewportClient` |
| **REDengine 4 (Cyberpunk)** | RED4ext / CET | Game system tick callbacks | RTTI reflection system |

---

## Tier 2: Raw Proxy DLL + Function Hooking (Games Without a Mod SDK)

If the game has **no existing mod loader**, create a self-contained **Proxy DLL** that Windows loads automatically from the game executable's directory.

### 1. Choosing the Proxy DLL Name
Inspect the game executable's Import Address Table (`dumpbin /imports Game.exe` or PE-bear) and pick a standard Windows system DLL imported by the game:
- `version.dll` (most universal across Win32/x64 games)
- `dinput8.dll` (common in DirectX 9/10/11 games)
- `dxgi.dll` or `d3d11.dll` (common in modern DirectX 11/12 games)
- `winmm.dll` or `xinput1_3.dll`

Forward all original exports to `C:\Windows\System32\<dllname>.dll` (or `SysWOW64` for 32-bit games on 64-bit Windows) using `GetProcAddress`, and spawn your initialization routine inside `DllMain(DLL_PROCESS_ATTACH)` via `DisableThreadLibraryCalls`.

### 2. Hooking the Main Loop & Render Present (MinHook / Detours)
Never run heavy initialization inside `DllMain` (loader lock). Instead, spawn a bootstrap thread that hooks the graphics API's `Present` call:
- **DirectX 9:** Create a dummy `IDirect3DDevice9` to read vtable index `17` (`Present`) and `42` (`EndScene`), then detour with Microsoft Detours or MinHook.
- **DirectX 11 / 12 (DXGI):** Create a dummy `IDXGISwapChain` to read vtable index `8` (`Present`) and `13` (`ResizeBuffers`), then detour.

Inside your hooked `Present(swapChain, ...)`:
1. Drain and execute any pending commands from the `TestBridge` main-thread queue.
2. When a screenshot is requested, copy the backbuffer (`ID3D11DeviceContext::CopyResource` to a staging texture, or `IDirect3DDevice9::GetBackBuffer` / `GetRenderTargetData`) or capture the game's `HWND` client rect.

### 3. Address Independence (Signature / AOB Scanning)
When hooking internal game functions without an Address Library:
- Avoid hardcoded virtual addresses whenever possible (patches or Steam/GOG/EA builds shift offsets).
- Use byte-pattern (AOB) scanning with wildcards (`48 8B 05 ?? ?? ?? ?? 48 85 C0`) over the `.text` section, and log the resolved RVA on startup.

---

## Tier 3: External Black-Box Harness (Zero Injection Allowed)

When the game executable cannot be modified or injected (strict DRM, packed single-player executables, or external tool testing):
1. **State Inspection:** Use an external Python/C++ controller with `OpenProcess(PROCESS_VM_READ)` + `ReadProcessMemory` and pointer chains / signature scans to read game state.
2. **Input Dispatch:** Focus the game window (`SetForegroundWindow`) and send hardware scan codes via `SendInput` (DirectInput ignores virtual key codes; always populate `KEYBDINPUT.wScan` with `MapVirtualKey(vk, MAPVK_VK_TO_VSC)` and `KEYEVENTF_SCANCODE`).
3. **Frame Capture:** Use `PrintWindow(hwnd, hdc, PW_RENDERFULLCONTENT)` or the Windows Desktop Duplication API (`IDXGIOutputDuplication`) for fast GPU frame grabs.
