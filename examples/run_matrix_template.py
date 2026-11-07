"""
Atomic End-to-End Game Mod Test Matrix Runner Template.

Lifecycle enforced by this runner:
  1. Launch game (via direct process or Scheduled Task `schtasks` to bypass UAC/sandbox isolation).
  2. Poll Named Pipe bridge until engine reaches Main Menu, then auto-load target save into world.
  3. Execute all test categories (SYS, CTX, TOG, FEAT, REV, SEQ, PER, EDG) in a single batch.
  4. Save screenshots / telemetry and `test_report.json`.
  5. IMMEDIATELY terminate the game process (`taskkill /F /IM <Game>.exe`) in `finally:` before exiting.
"""

import json
import os
import subprocess
import sys
import time
from typing import Any, Dict, List, Optional, Tuple

from PIL import Image, ImageChops, ImageStat
from bridge_client import GameBridgeClient

# --- Project Configuration ---
GAME_EXE_NAME = "Game.exe"
SCHEDULED_TASK_NAME = "Game_AutoLauncher"  # Optional scheduled task name for UAC/elevated launch
PIPE_NAME = r"\\.\pipe\game_mcp_bridge"
OUTPUT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "build", "test_screenshots"))


def compute_roi_diff(img_path_a: str, img_path_b: str, crop_box: Tuple[int, int, int, int]) -> float:
    """
    Computes Mean Absolute Error (MAE) across RGB channels within a specific Region of Interest (ROI).
    `crop_box` is (left, top, right, bottom) in pixels.
    """
    with Image.open(img_path_a) as im1, Image.open(img_path_b) as im2:
        c1 = im1.convert("RGB").crop(crop_box)
        c2 = im2.convert("RGB").crop(crop_box)
        diff = ImageChops.difference(c1, c2)
        stat = ImageStat.Stat(diff)
        return sum(stat.mean) / len(stat.mean)


class MatrixRunner:
    def __init__(self, client: GameBridgeClient, out_dir: str):
        self.client = client
        self.out_dir = out_dir
        os.makedirs(self.out_dir, exist_ok=True)
        self.results: List[Dict[str, Any]] = []

    def record(self, test_id: str, category: str, name: str, passed: bool, details: str) -> None:
        status = "PASS" if passed else "FAIL"
        print(f"  [{status}] {test_id}: {name} - {details}")
        self.results.append({
            "id": test_id,
            "category": category,
            "name": name,
            "passed": bool(passed),
            "details": details,
        })

    def save_report(self) -> str:
        report_path = os.path.join(self.out_dir, "test_report.json")
        payload = {
            "all_passed": all(r["passed"] for r in self.results) and len(self.results) > 0,
            "results": self.results,
        }
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
        return report_path


def launch_game(use_scheduled_task: bool = True, game_exe_path: Optional[str] = None) -> None:
    if use_scheduled_task:
        print(f"[*] Launching {GAME_EXE_NAME} via Scheduled Task '{SCHEDULED_TASK_NAME}'...")
        subprocess.run(["schtasks", "/run", "/tn", SCHEDULED_TASK_NAME], check=True)
    elif game_exe_path:
        print(f"[*] Launching {game_exe_path} directly...")
        subprocess.Popen([game_exe_path], cwd=os.path.dirname(game_exe_path))
    else:
        raise ValueError("Either use_scheduled_task=True or game_exe_path must be provided.")


def kill_game() -> None:
    print(f"[*] Terminating {GAME_EXE_NAME}...")
    subprocess.run(["taskkill", "/F", "/IM", GAME_EXE_NAME], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print(f"[+] {GAME_EXE_NAME} terminated.")


def wait_for_world_ready(client: GameBridgeClient, timeout_s: float = 90.0) -> bool:
    print("[*] Waiting for game bridge to initialize...")
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        status = client.get_status()
        if status.get("ok"):
            if status.get("in_world"):
                print("[+] In-world gameplay active!")
                return True
            if status.get("pregame"):
                print("[+] Reached Main Menu. Triggering auto-load of test save...")
                client.request("load_save", {"slot": 0})
                time.sleep(2.0)
        time.sleep(1.0)
    return False


def run_test_matrix(runner: MatrixRunner) -> None:
    client = runner.client

    # 1. SYS-01: Smoke & Frame Loop
    ping_resp = client.ping()
    runner.record(
        "SYS-01",
        "Engine",
        "Bridge Ping & Frame Loop",
        ping_resp.get("ok", False) and ping_resp.get("frame", 0) > 0,
        f"Frame count: {ping_resp.get('frame', 0)}",
    )

    # Add project-specific CTX, TOG, FEAT, REV, SEQ, PER, and EDG test cases here...


def main() -> int:
    client = GameBridgeClient(PIPE_NAME)
    runner = MatrixRunner(client, OUTPUT_DIR)

    try:
        launch_game(use_scheduled_task=True)
        if not wait_for_world_ready(client):
            print("[!] Timeout waiting for in-world state.")
            return 1

        time.sleep(2.0)  # Allow graphics driver / scene to settle
        run_test_matrix(runner)
        report_file = runner.save_report()
        print(f"[+] Test report saved to: {report_file}")
        return 0 if all(r["passed"] for r in runner.results) else 1
    finally:
        # Strict Atomic Lifecycle: ALWAYS close the game immediately after capture
        kill_game()


if __name__ == "__main__":
    sys.exit(main())
