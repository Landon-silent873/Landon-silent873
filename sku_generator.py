"""
SKU Generator Module

Generates product article numbers and merchant SKU strings for SHEIN
seller center. Persists state in a JSON file to prevent duplicate
article numbers across runs.
"""

import json
import logging
import os
import random
import sys
from pathlib import Path
from typing import List

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
STATE_FILE: str = "sku_state.json"
SIZES: List[str] = ["S", "M", "L", "XL", "XXL", "XXXL"]

# Maximum number of entries to keep in used_numbers to prevent unbounded growth
MAX_USED_NUMBERS: int = 10000

# Category code mapping
CATEGORY_CODES = {
    "3001": "短袖T恤 (Short-Sleeve T-Shirt)",
    "8008": "连帽卫衣 (Hoodie)",
    "ady000": "圆领卫衣 (Crewneck Sweatshirt)",
}

# Color prefix mapping
COLOR_PREFIXES = {
    "W": "White",
    "B": "Black",
}

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# File locking helpers (cross-platform)
# ---------------------------------------------------------------------------
def _lock_file(f):
    """Acquire an exclusive lock on the file. Uses fcntl on Unix, msvcrt on Windows."""
    if sys.platform == "win32":
        import msvcrt
        msvcrt.locking(f.fileno(), msvcrt.LK_LOCK, 1)
    else:
        import fcntl
        fcntl.flock(f.fileno(), fcntl.LOCK_EX)


def _unlock_file(f):
    """Release the file lock."""
    if sys.platform == "win32":
        import msvcrt
        msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1)
    else:
        import fcntl
        fcntl.flock(f.fileno(), fcntl.LOCK_UN)


def _load_state() -> dict:
    """Load the persisted state from the JSON file."""
    state_path = Path(STATE_FILE)
    if state_path.exists():
        try:
            with open(state_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            logger.warning(f"读取状态文件失败，将重新初始化: {e}")
    return {"last_numbers": {}, "used_numbers": []}


def _save_state(state: dict) -> None:
    """Persist the current state to the JSON file."""
    state_path = Path(STATE_FILE)
    try:
        with open(state_path, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2, ensure_ascii=False)
    except OSError as e:
        logger.error(f"保存状态文件失败: {e}")


def generate_article_number(category_code: str) -> str:
    """
    Generate a unique article number in format: category_code + random
    incrementing number (4 digits).

    Uses file locking to prevent race conditions under concurrent execution.
    Caps the used_numbers list to MAX_USED_NUMBERS to prevent unbounded growth.

    Args:
        category_code: The product category code (e.g. '3001', '8008').

    Returns:
        A unique article number string, e.g. '30014608'.
    """
    state_path = Path(STATE_FILE)
    lock_path = Path(STATE_FILE + ".lock")

    # Ensure the lock file exists
    lock_path.touch(exist_ok=True)

    # Acquire file lock for atomic read-modify-write
    lock_file = open(lock_path, "r")
    try:
        _lock_file(lock_file)

        # Load state while holding lock
        state = _load_state()
        last_numbers = state.get("last_numbers", {})
        used_numbers = state.get("used_numbers", [])

        # Get the last used number for this category, or start from a random base
        # NOTE: The initial seed is non-deterministic (random.randint). This is
        # acceptable for a single-user tool but means two fresh installs may
        # overlap. The used_numbers check prevents duplicates within one install.
        last_num = last_numbers.get(category_code, random.randint(1000, 5000))

        # Increment with a random step to appear more natural
        new_num = last_num + random.randint(1, 50)

        article_number = f"{category_code}{new_num}"

        # Ensure no duplicates
        while article_number in used_numbers:
            new_num += random.randint(1, 10)
            article_number = f"{category_code}{new_num}"

        # Update state
        last_numbers[category_code] = new_num
        used_numbers.append(article_number)

        # Cap used_numbers to prevent unbounded growth
        if len(used_numbers) > MAX_USED_NUMBERS:
            used_numbers = used_numbers[-MAX_USED_NUMBERS:]

        state["last_numbers"] = last_numbers
        state["used_numbers"] = used_numbers
        _save_state(state)
    finally:
        _unlock_file(lock_file)
        lock_file.close()

    logger.info(f"生成货号: {article_number}")
    return article_number


def generate_sku(color_prefix: str, category_code: str, article_number_suffix: str, size: str) -> str:
    """
    Generate a merchant SKU string.

    Format: {color_prefix}-{category_code}-{article_number_suffix}-{size}
    Example: W-3001-4608-S

    Args:
        color_prefix: Color code ('W' for White, 'B' for Black).
        category_code: Category code (e.g. '3001').
        article_number_suffix: The numeric suffix from the article number.
        size: Size string (e.g. 'S', 'M', 'L').

    Returns:
        Formatted SKU string.
    """
    # Extract the suffix (numeric part after category code)
    if article_number_suffix.startswith(category_code):
        suffix = article_number_suffix[len(category_code):]
    else:
        suffix = article_number_suffix

    sku = f"{color_prefix}-{category_code}-{suffix}-{size}"
    return sku


def generate_all_skus(color_prefix: str, category_code: str, article_number: str) -> List[str]:
    """
    Generate SKUs for all standard sizes.

    Args:
        color_prefix: Color code ('W' for White, 'B' for Black).
        category_code: Category code (e.g. '3001').
        article_number: The full article number string.

    Returns:
        List of SKU strings for all sizes.
    """
    skus = []
    for size in SIZES:
        sku = generate_sku(color_prefix, category_code, article_number, size)
        skus.append(sku)
    return skus


if __name__ == "__main__":
    # Demo usage
    article = generate_article_number("3001")
    print(f"Article Number: {article}")
    all_skus = generate_all_skus("W", "3001", article)
    for s in all_skus:
        print(f"  SKU: {s}")
