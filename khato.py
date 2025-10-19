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
from time import sleep
from typing import Dict, Optional

def check_lib():
    while True: 
        try:
            os.system("pip install -r requirements.txt")
            break
        except ModuleNotFoundError:
            print("Download Fail, Retrying...")
            sleep(2)
            os.system("pip install -r requirements.txt")

from colorama import Fore, Style, init
init(autoreset=True)

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
    "ssh2john": "john",
    "gobuster": "gobuster",
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

print("Checking operating system and Python version...")
check_operating_system_and_version()
print("Starting tool check and installation process...")
check()
print("Checking required libraries...")
check_lib()

def inchu():
    chu = r""" 
    __  __ _             _____
    | |/ /| |__    __ _ |_   _|  ___
    | ' / | '_ \  / _` |  | |   / _ \
    | . \ | | | || (_| |  | |  | (_) |
    |_|\_\|_| |_| \__,_|  |_|   \___/
"""
    print(Fore.MAGENTA + chu + Fore.RESET)

def chuc_nang(chuc_nang):
    if chuc_nang == 1:
        while True:
            try:
                os.system("clear")
                inchu()
                print("\n\nCác chức năng trong mục Website: ")
                print(Fore.CYAN + "=" * 75 + Fore.RESET)
                print(Fore.CYAN + "|| 1. Kiểm tra thông tin website                                             ||")
                print(Fore.CYAN + "|| 2. Quét cổng mở của website                                               ||")
                print(Fore.CYAN + "|| 3. Quét lỗ hổng máy chủ                                                   ||")
                print(Fore.CYAN + "|| 4. Quét lỗ hổng website                                                   ||")
                print(Fore.CYAN + "|| 99. Quay lại menu chính                                                   ||")
                print(Fore.CYAN + "=" * 75 + Fore.RESET)
                choice = int(input("Chọn chức năng: "))
                chuc_nang_1(choice)
            except KeyboardInterrupt:
                print(Fore.RED + "\nĐã thoát chức năng Website" + Fore.RESET)
                sleep(0.8)
                return
            except ValueError:
                print(Fore.YELLOW + "Đầu vào phải là số" + Fore.RESET)
                sleep(0.8)
    elif chuc_nang == 2:
        while True:
            try:
                os.system("clear")
                inchu()
                print("\n\nCác chức năng trong mục WiFi - Network: ")
                print(Fore.CYAN + "=" * 75 + Fore.RESET)
                print(Fore.CYAN + "|| 1. Quét các IP trong mạng LAN (có thể quét cổng mở của thiết bị)                     ||")
                print(Fore.CYAN + "|| 2. Bắt gói tin WiFi                                                                  ||")
                print(Fore.CYAN + "|| 3. Bẻ khóa mật khẩu WiFi WPA/WPA2                                                    ||")
                print(Fore.CYAN + "|| 4. Bẻ khóa mật khẩu WiFi WPS                                                         ||")
                print(Fore.CYAN + "|| 99. Quay lại menu chính                                                              ||")
                print(Fore.CYAN + "=" * 75 + Fore.RESET)
                choice = int(input("Chọn chức năng: "))
                chuc_nang_2(choice)
            except KeyboardInterrupt:
                print(Fore.RED + "\nĐã thoát chức năng WiFi - Network" + Fore.RESET)
                sleep(0.8)
                return
            except ValueError:
                print(Fore.YELLOW + "Đầu vào phải là số" + Fore.RESET)
                sleep(0.8)
    elif chuc_nang == 3:
        print("Chức năng đang được phát triển...")

def chuc_nang_1(chuc_nang):
    if not chuc_nang in [1, 2, 3, 99]:
        print(Fore.YELLOW + "Vui lòng chọn các chức năng có trong danh sách." + Fore.RESET)
        sleep(0.8)
        chuc_nang(1)
    elif chuc_nang == 1:
        pass
    elif chuc_nang == 2:
        pass
    elif chuc_nang == 3:
        pass
    elif chuc_nang == 99:
        menu()

def chuc_nang_2(chuc_nang):
    if not chuc_nang in [1, 2, 3, 4, 99]:
        print(Fore.YELLOW + "Vui lòng chọn các chức năng có trong danh sách." + Fore.RESET)
        sleep(0.8)
        chuc_nang(2)
    elif chuc_nang == 1:
        pass
    elif chuc_nang == 2:
        pass
    elif chuc_nang == 3:
        pass
    elif chuc_nang == 4:
        pass
    elif chuc_nang == 99:
        menu()
    
def menu():
    while True:
        try:
            os.system("clear")
            inchu()
            print(Fore.CYAN + "\n\nCác chức năng trong chương trình phiên bản này:" + Fore.RESET)
            print(Fore.CYAN + "=" * 75 + Fore.RESET)
            print(Fore.CYAN + "|| 1. Website                                                            ||")
            print(Fore.CYAN + "|| 2. WiFi - Network                                                     ||")
            print(Fore.CYAN + "|| 3. Malware                                                            ||")
            print(Fore.CYAN + "|| 99. Exit                                                              ||")
            print(Fore.CYAN + "=" * 75 + Fore.RESET)
            chuc_nang = int(input("Chọn chức năng: "))
            if chuc_nang == 1:
                chuc_nang(1)
            elif chuc_nang == 2:
                chuc_nang(2)
            elif chuc_nang == 3:
                chuc_nang(3)
            elif chuc_nang == 99:
                print(Fore.RED + "Đã thoát chương trình" + Fore.RESET)
                sys.exit(0)
            else:
                print(Fore.YELLOW + "Vui lòng chọn các chức năng có trong danh sách." + Fore.RESET)
                sleep(0.8)
        except KeyboardInterrupt:
            os.system("pip uninstall -r requirements.txt") if (input("Bạn có muốn xóa hết thư viện vừa cài không? (y / n) : ").strip().lower() == "y") else (print("Đang thoát..."))
            print(Fore.RED + "\nĐã thoát chương trình" + Fore.RESET)
            sys.exit(0)
        except ValueError:
            print(Fore.YELLOW + "Đầu vào phải là số" + Fore.RESET)
            sleep(0.8)
if __name__ == "__main__":
    menu()
