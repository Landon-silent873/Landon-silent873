"""
Configuration Module

Provides default settings for the SHEIN auto-lister system. Supports
overriding defaults via a config.yaml file.
"""

import logging
from pathlib import Path
from typing import Any, Dict, List

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
CONFIG_FILE: str = "config.yaml"

# SHEIN Seller Center URLs
SHEIN_SELLER_CENTER_URL: str = "https://seller.shein.com"
SHEIN_PRODUCT_LIST_URL: str = "https://seller.shein.com/product/list"
SHEIN_PUBLISH_URL: str = "https://seller.shein.com/product/publish"

# ---------------------------------------------------------------------------
# Default Settings
# ---------------------------------------------------------------------------
DEFAULT_PRICE: float = 20.0
DEFAULT_CURRENCY: str = "USD"
DEFAULT_SIZES: List[str] = ["S", "M", "L", "XL", "XXL", "XXXL"]
DEFAULT_DELAY_MIN: float = 1.0
DEFAULT_DELAY_MAX: float = 3.0
DEFAULT_CDP_URL: str = "ws://127.0.0.1:9222"

# Color prefix mapping
COLOR_PREFIXES: Dict[str, str] = {
    "W": "White",
    "B": "Black",
}

# Category code mapping with display names
CATEGORY_CODES: Dict[str, str] = {
    "3001": "短袖T恤 (Short-Sleeve T-Shirt)",
    "8008": "连帽卫衣 (Hoodie)",
    "ady000": "圆领卫衣 (Crewneck Sweatshirt)",
}

# Image file patterns to look for
IMAGE_PATTERNS: List[str] = ["Main-*.jpg", "Main-*.png", "Main-*.jpeg", "Main-*.webp"]

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def load_config(config_path: str = CONFIG_FILE) -> Dict[str, Any]:
    """
    Load configuration from a YAML file, falling back to defaults
    if the file does not exist.

    Args:
        config_path: Path to the YAML configuration file.

    Returns:
        Dict containing all configuration values.
    """
    config: Dict[str, Any] = {
        "price": DEFAULT_PRICE,
        "currency": DEFAULT_CURRENCY,
        "sizes": DEFAULT_SIZES,
        "delay_min": DEFAULT_DELAY_MIN,
        "delay_max": DEFAULT_DELAY_MAX,
        "cdp_url": DEFAULT_CDP_URL,
        "color_prefixes": COLOR_PREFIXES,
        "category_codes": CATEGORY_CODES,
        "image_patterns": IMAGE_PATTERNS,
        "seller_center_url": SHEIN_SELLER_CENTER_URL,
        "product_list_url": SHEIN_PRODUCT_LIST_URL,
        "publish_url": SHEIN_PUBLISH_URL,
    }

    yaml_path = Path(config_path)
    if yaml_path.exists():
        try:
            import yaml
            with open(yaml_path, "r", encoding="utf-8") as f:
                yaml_config = yaml.safe_load(f)

            if yaml_config and isinstance(yaml_config, dict):
                # Override defaults with YAML values
                for key, value in yaml_config.items():
                    if value is not None:
                        config[key] = value
                logger.info(f"已加载配置文件: {yaml_path}")
            else:
                logger.info(f"配置文件为空，使用默认配置: {yaml_path}")
        except ImportError:
            logger.warning("未安装pyyaml，无法读取配置文件，使用默认配置")
        except Exception as e:
            logger.warning(f"读取配置文件失败，使用默认配置: {e}")
    else:
        logger.info("未找到配置文件，使用默认配置")

    return config


def get_color_name(prefix: str) -> str:
    """
    Get the full color name from a color prefix.

    Args:
        prefix: Color prefix code (e.g. 'W', 'B').

    Returns:
        Full color name string.
    """
    return COLOR_PREFIXES.get(prefix.upper(), "Unknown")


def get_category_name(code: str) -> str:
    """
    Get the display name for a category code.

    Args:
        code: Category code (e.g. '3001', '8008').

    Returns:
        Category display name string.
    """
    return CATEGORY_CODES.get(code, f"Unknown ({code})")


if __name__ == "__main__":
    # Demo usage
    cfg = load_config()
    print("Current configuration:")
    for key, value in cfg.items():
        print(f"  {key}: {value}")
