#!usr/bin/env python3
from __future__ import annotations
import platform
import os
import sys
import shutil
import subprocess
import platform
import argparse
import json
import sys
from typing import Dict, Optional

COMMON_TOOLS = [
    "nmap",
    "hydra",
    "sqlmap",
    "john",
    "aircrack-ng",
    "nikto",
    "msfconsole",
    "tcpdump",
    "nc",
    "netcat",
    "masscan",
    "ssh2john",
    "gobuster",
]

PKG_NAME_MAP = {
    "nmap": "nmap",
    "hydra": "hydra",
    "sqlmap": "sqlmap",
    "john": "john",
    "aircrack-ng": "aircrack-ng",
    "nikto": "nikto",
    "msfconsole": "metasploit-framework",
    "tcpdump": "tcpdump",
    "nc": "netcat",
    "netcat": "netcat",
    "masscan": "masscan",
}

VERSION_FLAGS = ["--version", "-V", "-v", "version", "-h", "--help"]

def detect_pkg_managers() -> Dict[str, str]:
    """Return detected package managers and a short code"""
    mgrs = {}
    if shutil.which("apt"):
        mgrs["apt"] = "apt"
    if shutil.which("apt-get"):
        mgrs["apt-get"] = "apt-get"
    if shutil.which("pacman"):
        mgrs["pacman"] = "pacman"
    if shutil.which("brew"):
        mgrs["brew"] = "brew"
    if shutil.which("choco"):
        mgrs["choco"] = "choco"
    if shutil.which("winget"):
        mgrs["winget"] = "winget"
    return mgrs

def which_tool(tool: str) -> Optional[str]:
    path = shutil.which(tool)
    if path:
        return path
    alt = {
        "hydra": ["thc-hydra"],
        "nc": ["netcat", "ncat"],
        "netcat": ["nc", "ncat"],
        "john": ["john"],
    }
    for a in alt.get(tool, []):
        p = shutil.which(a)
        if p:
            return p
    return None

def try_version(tool: str, timeout: float = 2.0) -> Optional[str]:
    for flag in VERSION_FLAGS:
        try:
            proc = subprocess.run([tool, flag], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=timeout)
            out = proc.stdout.decode(errors="ignore").strip()
            if out:
                for line in out.splitlines():
                    l = line.strip()
                    if l:
                        return l
        except FileNotFoundError:
            return None
        except subprocess.TimeoutExpired:
            continue
        except Exception:
            continue
    try:
        proc = subprocess.run([tool], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=timeout)
        out = proc.stdout.decode(errors="ignore").strip()
        if out:
            for line in out.splitlines():
                l = line.strip()
                if l:
                    return l
    except Exception:
        pass
    return None

def build_install_cmd(pkg_mgr: str, pkg_name: str) -> Optional[str]:
    if pkg_mgr in ("apt", "apt-get"):
        pm = "apt-get" if shutil.which("apt-get") else "apt"
        return f"sudo {pm} update && sudo {pm} install -y {pkg_name}"
    if pkg_mgr == "pacman":
        return f"sudo pacman -Sy --noconfirm {pkg_name}"
    if pkg_mgr == "brew":
        return f"brew install {pkg_name}"
    if pkg_mgr == "choco":
        return f"choco install -y {pkg_name}"
    if pkg_mgr == "winget":
        return f"winget install --accept-package-agreements --accept-source-agreements --silent {pkg_name}"
        return None

def run_shell(cmd: str) -> tuple[int, str]:
    try:
        proc = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        out = proc.stdout.decode(errors="ignore")
        return proc.returncode, out
    except Exception as e:
        return 1, f"Exception when running command: {e}"

def prompt_yes_no(prompt: str, default_no: bool = True, auto: bool = False) -> bool:
    if auto:
        return True
    while True:
        ans = input(prompt + " [y/N]: ").strip().lower()
        if ans == "" and default_no:
            return False
        if ans in ("y", "yes"):
            return True
        if ans in ("n", "no", ""):
            return False
        print("Vui lòng trả lời y hoặc n.")

def try_install(pkg_name: str, pkg_mgrs: Dict[str, str]) -> tuple[bool, str]:
    preferred = ["apt-get", "apt", "pacman", "brew", "choco", "winget"]
    for key in preferred:
        if key in pkg_mgrs:
            cmd = build_install_cmd(key, pkg_name)
            if not cmd:
                continue
            print(f"Chạy lệnh cài với {key}: {cmd}")
            code, out = run_shell(cmd)
            success = (code == 0)
            return success, f"returncode={code}\n{out}"
    return False, "Không tìm thấy package manager phù hợp trên hệ thống (apt/pacman/brew/choco/winget)."

def check():
    parser = argparse.ArgumentParser(description="Kiểm tra và (tuỳ chọn) cài các tool pentest mặc định.")
    parser.add_argument("--timeout", type=float, default=2.0, help="Timeout (giây) khi lấy banner/version")
    parser.add_argument("--json", type=str, default=None, help="Ghi kết quả ra file JSON")
    parser.add_argument("--auto", action="store_true", help="Tự động đồng ý cài tất cả tool thiếu (không hỏi)")
    args = parser.parse_args()
    system = platform.system()
    pkg_mgrs = detect_pkg_managers()
    results = {}
    print(f"Hệ thống: {system}")
    if pkg_mgrs:
        print("Detected package managers:", ", ".join(pkg_mgrs.keys()))
    else:
        print("Không tìm thấy package manager phổ biến trong PATH (apt/pacman/brew/choco/winget).")
    for tool in COMMON_TOOLS:
        info = {"installed": False, "path": None, "banner": None, "attempted_install": False, "install_success": None, "install_output": None}
        path = which_tool(tool)
        if path:
            info["installed"] = True
            info["path"] = path
            info["banner"] = try_version(path, timeout=args.timeout)
            print(f"{tool}: OK (path: {path})")
        else:
            print(f"{tool}: CHƯA CÓ")
            want = prompt_yes_no(f"Bạn có muốn cài '{tool}' không?", auto=args.auto)
            if not want:
                info["attempted_install"] = False
            else:
                info["attempted_install"] = True
                pkg_name = PKG_NAME_MAP.get(tool, tool)
                success, out = try_install(pkg_name, pkg_mgrs)
                info["install_success"] = success
                info["install_output"] = out
                if success:
                    new_path = which_tool(tool)
                    if new_path:
                        info["installed"] = True
                        info["path"] = new_path
                        info["banner"] = try_version(new_path, timeout=args.timeout)
                        print(f"  Cài xong: {tool} đã cài tại {new_path}")
                    else:
                        print(f"  Cài xong nhưng không tìm thấy binary trong PATH. Có thể package khác tên hoặc cần mở terminal mới.")
                else:
                    print(f"  Cài thất bại hoặc không thực hiện được: {out.splitlines()[0] if out else 'No output'}")
        results[tool] = info
    installed_count = sum(1 for v in results.values() if v["installed"])
    total = len(results)
    print(f"\nTổng: {installed_count}/{total} installed.")
    if args.json:
        try:
            with open(args.json, "w", encoding="utf-8") as f:
                json.dump({"system": system, "pkg_managers": list(pkg_mgrs.keys()), "results": results}, f, indent=2, ensure_ascii=False)
            print(f"JSON viết ra {args.json}")
        except Exception as e:
            print("Lỗi khi ghi JSON:", e, file=sys.stderr)

def check_operating_system_and_version():
    operating_system = platform.system()
    if operating_system == "Linux":
        print("BT")
    else:
        print("He dieu hanh cua ban khong duoc ho tro!")
        sys.exit(0)
    version = f"{sys.version_info.major}.{sys.version_info.minor}"
    if not version == "3.12":
        print("Vui long su dung Python 3.12 de chay chuong trinh nay!")
        sys.exit(0)

def full_check():
    check_operating_system_and_version()
    check()