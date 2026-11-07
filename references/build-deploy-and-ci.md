# Build, Deploy, Gating & CI/CD Pipeline Guide

Game mods have strict binary architecture and file-locking constraints. Follow these rules to prevent corrupted CMake caches, locked DLL build errors, and broken CI pipelines.

---

## 1. Local Build & Deploy Rules

### Rule 1: Always Terminate the Game Before Building
Windows locks loaded `.dll`, `.swf`, and `.tlk`/archive files while the game process is alive.
- Before running any build/deploy script, check for and terminate any running game process (`Stop-Process -Name "<Game>" -Force -ErrorAction SilentlyContinue`).

### Rule 2: Self-Contained Toolchain Environment (`build.ps1`)
Never run raw `cmake --build` from an uninitialized shell, as it can re-trigger CMake configure without MSVC/vcpkg environment variables (`VCPKG_ROOT`, `INCLUDE`, `LIB`) and corrupt `CMakeCache.txt`.
- Encapsulate the entire build in a single `tools/build.ps1` script that:
  1. Locates and imports `vcvarsall.bat` for the exact game architecture (`amd64_x86` for 32-bit games; `amd64` for 64-bit games).
  2. Sets `VCPKG_ROOT` and adds `ninja` to `PATH`.
  3. Runs any asset/code generators (e.g., localization tables, UI bytecode headers).
  4. Runs `cmake --preset <preset>` and `cmake --build --preset <preset>`.
  5. Runs headless unit tests (`ctest --preset <preset>`).
  6. Deploys the compiled plugin and assets to the game directory.
- If `CMakeCache.txt` ever becomes corrupted from an uninitialized shell run, delete `build/<preset>/CMakeCache.txt` and `build/<preset>/CMakeFiles` and re-run `tools/build.ps1`.

---

## 2. Gating the In-Engine Test Bridge

Keep the Named Pipe `TestBridge` active during development and automated E2E runs, but safe for end-user distribution:

1. **Compile-Time CMake Option:**
   ```cmake
   option(ENABLE_TEST_BRIDGE "Compile in-engine Named Pipe E2E test bridge" ON)
   if(ENABLE_TEST_BRIDGE)
       target_compile_definitions(MyMod PRIVATE ENABLE_TEST_BRIDGE=1)
       target_sources(MyMod PRIVATE src/TestBridge.cpp src/TestBridge.h)
   endif()
   ```
2. **Runtime Activation Guard (Optional Extra Safety):**
   Even when compiled in, you can gate pipe creation on an environment variable (`MOD_TEST_BRIDGE=1`) or config flag so normal gameplay sessions do not spawn a pipe thread unless requested.

---

## 3. GitHub Actions CI/CD Pre-Flight Checklist

GitHub Actions runners do not have the target game installed. Configure CI to build the mod DLL, package release artifacts, and run the **decoupled core unit tests** (`ctest`).

Before pushing `.github/workflows/ci.yml`, verify all 5 items below:

1. **Architecture Match:**
   - 32-bit (`x86`) games **must** configure `ilammy/msvc-dev-cmd@v1` with `arch: x86` (or `amd64_x86`) and use a 32-bit vcpkg triplet (`x86-windows-static-md` or `x86-windows-static`).
   - 64-bit (`x64`) games must use `arch: x64` and `x64-windows-static-md`.
2. **Explicit `CMAKE_TOOLCHAIN_FILE`:**
   - Never rely on implicit environment variables for vcpkg in CI when calling `cmake -B build`. Always pass:
     ```yaml
     -DCMAKE_TOOLCHAIN_FILE="$env:VCPKG_INSTALLATION_ROOT/scripts/buildsystems/vcpkg.cmake"
     ```
3. **vcpkg Binary Archive Caching:**
   - Cache compiled vcpkg packages so CI runs finish in ~1–2 minutes instead of rebuilding dependencies from source every time:
     ```yaml
     - name: Cache vcpkg binary archives
       uses: actions/cache@v4
       with:
         path: ~/AppData/Local/vcpkg/archives
         key: ${{ runner.os }}-vcpkg-${{ hashFiles('vcpkg.json', 'vcpkg-configuration.json') }}
         restore-keys: |
           ${{ runner.os }}-vcpkg-
     ```
4. **Disable Game Deployment in CI:**
   - Guard any CMake `POST_BUILD` copy-to-game-folder steps behind `if(DAO_GAME_DIR AND EXISTS "${DAO_GAME_DIR}")` so CI builds do not fail when the game installation directory is absent.
5. **Run Headless Unit Tests via `ctest`:**
   - Execute `ctest --test-dir build --output-on-failure -C Release` to validate all pure logic and serialization tests on every push and pull request.
