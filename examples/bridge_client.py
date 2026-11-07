"""
Generic Named Pipe JSON-RPC Client & CLI Probe for In-Engine Game Mod Bridges.

Supports two workflows:
  1. Library import (`from bridge_client import GameBridgeClient`) for standalone test matrix runners.
  2. Direct CLI probing (`python bridge_client.py --pipe \\\\.\\pipe\\my_game_mcp_bridge get_status`)
     for rapid live discovery without needing MCP server registration.
"""

import argparse
import ctypes
from ctypes import wintypes
import json
import sys
import time
from typing import Any, Dict, Optional

GENERIC_READ = 0x80000000
GENERIC_WRITE = 0x40000000
OPEN_EXISTING = 3
INVALID_HANDLE_VALUE = wintypes.HANDLE(-1).value

kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)


class GameBridgeClient:
    def __init__(self, pipe_name: str = r"\\.\pipe\game_mcp_bridge"):
        self.pipe_name = pipe_name

    def request(self, cmd: str, args: Optional[Dict[str, Any]] = None, timeout_s: float = 5.0) -> Dict[str, Any]:
        payload = {"cmd": cmd}
        if args:
            payload.update(args)
        raw_req = json.dumps(payload).encode("utf-8")

        deadline = time.time() + timeout_s
        handle = INVALID_HANDLE_VALUE
        while time.time() < deadline:
            handle = kernel32.CreateFileW(
                self.pipe_name,
                GENERIC_READ | GENERIC_WRITE,
                0,
                None,
                OPEN_EXISTING,
                0,
                None,
            )
            if handle != INVALID_HANDLE_VALUE:
                break
            time.sleep(0.1)

        if handle == INVALID_HANDLE_VALUE:
            err = ctypes.get_last_error()
            return {"ok": False, "error": f"Failed to connect to pipe {self.pipe_name} (WinError {err})"}

        try:
            written = wintypes.DWORD(0)
            ok = kernel32.WriteFile(handle, raw_req, len(raw_req), ctypes.byref(written), None)
            if not ok:
                return {"ok": False, "error": f"WriteFile failed (WinError {ctypes.get_last_error()})"}

            buf = ctypes.create_string_buffer(65536)
            read_bytes = wintypes.DWORD(0)
            ok = kernel32.ReadFile(handle, buf, len(buf) - 1, ctypes.byref(read_bytes), None)
            if not ok or read_bytes.value == 0:
                return {"ok": False, "error": f"ReadFile failed (WinError {ctypes.get_last_error()})"}

            raw_resp = buf.raw[: read_bytes.value].decode("utf-8", errors="replace").strip()
            return json.loads(raw_resp)
        finally:
            kernel32.CloseHandle(handle)

    def ping(self) -> Dict[str, Any]:
        return self.request("ping")

    def get_status(self) -> Dict[str, Any]:
        return self.request("get_status")

    def inspect_state(self, target: str = "", **kwargs: Any) -> Dict[str, Any]:
        params = {"target": target, **kwargs}
        return self.request("inspect_state", params)

    def invoke_action(self, action: str, **kwargs: Any) -> Dict[str, Any]:
        params = {"action": action, **kwargs}
        return self.request("invoke_action", params)

    def capture_frame(self, out_path: str) -> Dict[str, Any]:
        return self.request("capture_frame", {"path": out_path})


def main() -> int:
    parser = argparse.ArgumentParser(description="CLI Probe for In-Engine Game Mod Named Pipe Bridge")
    parser.add_argument("--pipe", default=r"\\.\pipe\game_mcp_bridge", help="Named pipe path")
    parser.add_argument("cmd", help="Command name (e.g., ping, get_status, inspect_state, invoke_action)")
    parser.add_argument("--args", default="{}", help="JSON string of command arguments")
    parsed = parser.parse_args()

    client = GameBridgeClient(parsed.pipe)
    extra_args = json.loads(parsed.args)
    resp = client.request(parsed.cmd, extra_args)
    print(json.dumps(resp, indent=2))
    return 0 if resp.get("ok", False) else 1


if __name__ == "__main__":
    sys.exit(main())
