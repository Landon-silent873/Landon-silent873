"""
SHEIN Auto-Lister Launcher

A Python-based launcher that replaces the Chinese-heavy batch file menus.
Since Python handles UTF-8 natively, this avoids the GBK/UTF-8 encoding
conflicts that occur in Windows cmd batch files with Chinese characters.

Usage:
    python launcher.py          # Interactive menu mode
    python launcher.py --auto   # Full auto mode (all categories)
"""

import os
import socket
import subprocess
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
SCRIPT_DIR = Path(__file__).parent.resolve()
IMAGE_DIR = r"D:\A今日上架"
CDP_PORT = 9222
BASE_PRODUCT_ID_TSHIRT = "SPMPA4202605222803370"
BASE_PRODUCT_ID_HOODIE = "SPMPA4202605222803370"

# Category folder mapping: folder_name -> (category_code, base_product_id)
CATEGORIES = {
    "T\u6064": ("3001", BASE_PRODUCT_ID_TSHIRT),       # T恤
    "\u536b\u8863": ("8008", BASE_PRODUCT_ID_HOODIE),  # 卫衣
    "ady000": ("ady000", BASE_PRODUCT_ID_HOODIE),
}


def check_python():
    """Verify Python version is adequate."""
    version = sys.version_info
    if version < (3, 9):
        print(f"[WARNING] Python {version.major}.{version.minor} detected.")
        print("          Python 3.9+ is recommended.")
        print()
    else:
        print(f"[OK] Python {version.major}.{version.minor}.{version.micro}")


def check_dependencies():
    """Check if required packages are installed."""
    try:
        import playwright  # noqa: F401
        print("[OK] Playwright installed")
        return True
    except ImportError:
        print("[WARNING] Playwright not found!")
        print("          Please run install.bat first, or:")
        print("          pip install -r requirements.txt")
        print("          playwright install chromium")
        return False


def is_port_open(port):
    """Check if a TCP port is open on localhost."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(1)
        result = s.connect_ex(("127.0.0.1", port))
        return result == 0


def start_chrome_debug():
    """Check if Chrome remote debugging is available."""
    if is_port_open(CDP_PORT):
        print(f"[OK] Chrome remote debugging detected (port {CDP_PORT})")
        return True

    print(f"[WARNING] Chrome remote debugging not detected on port {CDP_PORT}")
    print()
    print("  Please follow these steps:")
    print("  1. Close ALL Chrome windows completely")
    print("  2. Double-click 'chrome_debug.bat' (or 'SHEIN Chrome' on desktop)")
    print("  3. Log in to SHEIN seller center in the browser")
    print("  4. Come back here and press Enter")
    print()

    while True:
        try:
            input("Press Enter after Chrome is ready...")
        except (EOFError, KeyboardInterrupt):
            return False

        if is_port_open(CDP_PORT):
            print(f"[OK] Chrome remote debugging detected (port {CDP_PORT})")
            return True
        else:
            print("[WARNING] Still not detected. Make sure you used chrome_debug.bat to open Chrome.")
            print("          (Normal Chrome shortcut won't work)")
            print()


def run_lister(folder, category_code, color=None, auto_color=False, base_product_id=None):
    """Run the shein_auto_lister.py script with the given parameters."""
    script = str(SCRIPT_DIR / "shein_auto_lister.py")
    cmd = [sys.executable, script, "--folder", folder, "--category", category_code]

    if auto_color:
        cmd.append("--auto-color")
    elif color:
        cmd.extend(["--color", color])

    if base_product_id:
        cmd.extend(["--base-product-id", base_product_id])

    print(f"\n[RUN] {' '.join(cmd)}\n")
    result = subprocess.run(cmd)
    return result.returncode == 0


def show_menu():
    """Display the interactive menu and return user's choice."""
    print()
    print("=" * 56)
    print("       SHEIN Auto-Lister - Menu")
    print("=" * 56)
    print()
    print("  1. Upload T-shirts (White)  / \u4e0a\u67b6T\u6064\uff08\u767d\u8272\uff09")
    print("  2. Upload T-shirts (Black)  / \u4e0a\u67b6T\u6064\uff08\u9ed1\u8272\uff09")
    print("  3. Upload Hoodies (White)   / \u4e0a\u67b6\u536b\u8863\uff08\u767d\u8272\uff09")
    print("  4. Upload Hoodies (Black)   / \u4e0a\u67b6\u536b\u8863\uff08\u9ed1\u8272\uff09")
    print("  5. Upload Crewneck (White)  / \u4e0a\u67b6\u5706\u9886\u536b\u8863\uff08\u767d\u8272\uff09")
    print("  6. Upload Crewneck (Black)  / \u4e0a\u67b6\u5706\u9886\u536b\u8863\uff08\u9ed1\u8272\uff09")
    print("  7. Auto mode (detect color) / \u5168\u81ea\u52a8\u6a21\u5f0f")
    print("  0. Exit / \u9000\u51fa")
    print()
    print("=" * 56)
    print()
    try:
        choice = input("Enter option number: ").strip()
    except (EOFError, KeyboardInterrupt):
        choice = "0"
    return choice


def run_auto_mode():
    """Run all categories in automatic color detection mode."""
    print()
    print("=" * 56)
    print("       SHEIN Auto-Lister - Full Auto Mode")
    print("=" * 56)
    print()
    print(f"[INFO] Image directory: {IMAGE_DIR}")
    print()

    if not os.path.isdir(IMAGE_DIR):
        print(f"[ERROR] Image directory not found: {IMAGE_DIR}")
        print("        Please make sure the folder exists and contains product images.")
        return

    total = 0
    success = 0

    for folder_name, (cat_code, base_id) in CATEGORIES.items():
        folder_path = os.path.join(IMAGE_DIR, folder_name)
        if os.path.isdir(folder_path):
            total += 1
            print(f"\n[PROCESSING] Category: {folder_name} | Code: {cat_code}")
            print(f"[PATH] {folder_path}")
            print()
            ok = run_lister(folder_path, cat_code, auto_color=True, base_product_id=base_id)
            if ok:
                success += 1
                print(f"[DONE] {folder_name} completed successfully")
            else:
                print(f"[WARNING] {folder_name} had errors during processing")
            print()

    print()
    print("=" * 56)
    print("       Auto mode finished")
    print("=" * 56)
    print(f"  Total categories: {total}")
    print(f"  Successful: {success}")
    print()

    if total == 0:
        print("[WARNING] No category folders found!")
        print("          Expected folders in", IMAGE_DIR + ":")
        for name in CATEGORIES:
            print(f"            {name}")


def interactive_mode():
    """Run the interactive menu loop."""
    while True:
        choice = show_menu()

        if choice == "0":
            print("\nExiting. Goodbye!")
            break
        elif choice == "1":
            folder = os.path.join(IMAGE_DIR, "T\u6064")
            run_lister(folder, "3001", color="W", base_product_id=BASE_PRODUCT_ID_TSHIRT)
        elif choice == "2":
            folder = os.path.join(IMAGE_DIR, "T\u6064")
            run_lister(folder, "3001", color="B", base_product_id=BASE_PRODUCT_ID_TSHIRT)
        elif choice == "3":
            folder = os.path.join(IMAGE_DIR, "\u536b\u8863")
            run_lister(folder, "8008", color="W", base_product_id=BASE_PRODUCT_ID_HOODIE)
        elif choice == "4":
            folder = os.path.join(IMAGE_DIR, "\u536b\u8863")
            run_lister(folder, "8008", color="B", base_product_id=BASE_PRODUCT_ID_HOODIE)
        elif choice == "5":
            folder = os.path.join(IMAGE_DIR, "ady000")
            run_lister(folder, "ady000", color="W", base_product_id=BASE_PRODUCT_ID_HOODIE)
        elif choice == "6":
            folder = os.path.join(IMAGE_DIR, "ady000")
            run_lister(folder, "ady000", color="B", base_product_id=BASE_PRODUCT_ID_HOODIE)
        elif choice == "7":
            run_auto_mode()
        else:
            print("[ERROR] Invalid option, please try again.")

        print()
        try:
            input("Press Enter to return to menu...")
        except (EOFError, KeyboardInterrupt):
            break


def main():
    """Main entry point."""
    # Set console encoding for proper display
    if sys.platform == "win32":
        try:
            sys.stdout.reconfigure(encoding="utf-8")
            sys.stderr.reconfigure(encoding="utf-8")
        except Exception:
            pass

    print()
    print("=" * 56)
    print("       SHEIN Auto-Lister Launcher v1.0")
    print("=" * 56)
    print()

    # Environment checks
    check_python()
    if not check_dependencies():
        print()
        input("Press Enter to exit...")
        sys.exit(1)

    # Start Chrome if needed
    start_chrome_debug()

    # Determine mode
    if "--auto" in sys.argv:
        run_auto_mode()
    else:
        interactive_mode()


if __name__ == "__main__":
    main()
