"""
Product Selector Script

Fetches product data from a configured API, filters items listed within the
last 7 days that have sales volume > 0, saves a CSV summary, and downloads
product images concurrently.
"""

import asyncio
import csv
import logging
import os
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List

import aiofiles
import aiohttp
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# ---------------------------------------------------------------------------
# Configuration placeholders - replace with your actual values
# ---------------------------------------------------------------------------
API_URL: str = "https://your-api-endpoint.example.com/products"
API_KEY: str = "your-api-key-here"

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
OUTPUT_DIR: str = "近7天潜力品"
CSV_FILENAME: str = "选品清单.csv"
MAX_RETRIES: int = 3
RETRY_BACKOFF_FACTOR: float = 1.0  # Exponential backoff: 1s, 2s, 4s
REQUEST_TIMEOUT: int = 30  # seconds
IMAGE_DOWNLOAD_TIMEOUT: int = 60  # seconds
CONCURRENT_DOWNLOADS: int = 5  # Max concurrent image downloads

# ---------------------------------------------------------------------------
# Logging setup - Chinese messages for user-facing output
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def sanitize_filename(name: str) -> str:
    """Remove or replace characters that are invalid in filenames."""
    sanitized = re.sub(r'[\\/*?:"<>|]', "_", name)
    sanitized = sanitized.strip(". ")
    # Limit length to avoid filesystem issues
    if len(sanitized) > 200:
        sanitized = sanitized[:200]
    return sanitized


def create_output_directory(base_path: Path) -> Path:
    """Create the output directory. Handle permission errors gracefully."""
    output_path = base_path / OUTPUT_DIR
    try:
        output_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"输出目录已就绪: {output_path}")
        return output_path
    except PermissionError:
        logger.error(f"权限不足，无法创建目录: {output_path}")
        sys.exit(1)
    except OSError as e:
        logger.error(f"创建目录时出错: {e}")
        sys.exit(1)


def build_session() -> requests.Session:
    """Build a requests session with retry strategy and exponential backoff."""
    session = requests.Session()
    retry_strategy = Retry(
        total=MAX_RETRIES,
        backoff_factor=RETRY_BACKOFF_FACTOR,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET", "POST"],
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


def fetch_products(session: requests.Session) -> List[Dict[str, Any]]:
    """Fetch product data from the API with retry logic."""
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    }
    logger.info("正在从API获取商品数据...")
    try:
        response = session.get(
            API_URL, headers=headers, timeout=REQUEST_TIMEOUT
        )
        response.raise_for_status()
        data = response.json()
        logger.info(f"成功获取 {len(data)} 条商品数据")
        return data
    except requests.exceptions.Timeout:
        logger.error("请求超时，已重试多次仍然失败")
        return []
    except requests.exceptions.ConnectionError:
        logger.error("网络连接失败，请检查网络设置")
        return []
    except requests.exceptions.HTTPError as e:
        logger.error(f"API返回错误状态码: {e.response.status_code}")
        return []
    except requests.exceptions.JSONDecodeError:
        logger.error("API返回的数据格式异常，无法解析JSON")
        return []
    except requests.exceptions.RequestException as e:
        logger.error(f"请求发生未知错误: {e}")
        return []


def filter_products(products: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Filter products that meet both criteria:
    1. listing_date is within the last 7 days
    2. sales_volume is greater than 0
    """
    today = datetime.now().date()
    seven_days_ago = today - timedelta(days=7)
    filtered = []

    for product in products:
        try:
            listing_date = datetime.strptime(
                product.get("listing_date", ""), "%Y-%m-%d"
            ).date()
        except (ValueError, TypeError):
            logger.warning(
                f"商品 {product.get('id', '未知')} 的上架日期格式无效，已跳过"
            )
            continue

        sales_volume = product.get("sales_volume", 0)
        if not isinstance(sales_volume, (int, float)):
            logger.warning(
                f"商品 {product.get('id', '未知')} 的销量数据格式无效，已跳过"
            )
            continue

        if listing_date >= seven_days_ago and sales_volume > 0:
            filtered.append(product)

    logger.info(f"筛选完成: 共 {len(filtered)} 件商品符合条件（7天内上架且有销量）")
    return filtered


def write_csv(products: List[Dict[str, Any]], output_path: Path) -> None:
    """Write filtered product data to a CSV file."""
    csv_path = output_path / CSV_FILENAME
    fieldnames = ["title", "price", "listing_date", "sales_volume"]
    header_labels = ["商品标题", "价格", "上架日期", "销量"]

    try:
        with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow(header_labels)
            for product in products:
                writer.writerow(
                    [
                        product.get("title", ""),
                        product.get("price", ""),
                        product.get("listing_date", ""),
                        product.get("sales_volume", ""),
                    ]
                )
        logger.info(f"选品清单已保存: {csv_path}")
    except PermissionError:
        logger.error(f"权限不足，无法写入文件: {csv_path}")
    except OSError as e:
        logger.error(f"写入CSV文件时出错: {e}")


async def download_single_image(
    session: aiohttp.ClientSession,
    semaphore: asyncio.Semaphore,
    product: Dict[str, Any],
    output_path: Path,
) -> None:
    """Download a single product image with retry logic."""
    image_url = product.get("image_url", "")
    product_id = product.get("id", "unknown")

    if not image_url:
        logger.warning(f"商品 {product_id} 没有图片URL，已跳过")
        return

    # Determine file extension from URL
    url_path = image_url.split("?")[0]
    ext = os.path.splitext(url_path)[1]
    if ext.lower() not in (".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"):
        ext = ".jpg"  # Default to jpg if extension is unclear

    filename = sanitize_filename(str(product_id)) + ext
    filepath = output_path / filename

    async with semaphore:
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                timeout = aiohttp.ClientTimeout(total=IMAGE_DOWNLOAD_TIMEOUT)
                async with session.get(
                    image_url, timeout=timeout
                ) as response:
                    if response.status == 200:
                        async with aiofiles.open(filepath, "wb") as f:
                            content = await response.read()
                            await f.write(content)
                        logger.info(f"图片已下载: {filename}")
                        return
                    else:
                        logger.warning(
                            f"下载图片失败 (HTTP {response.status}): {filename}"
                            f" [第{attempt}次尝试]"
                        )
            except asyncio.TimeoutError:
                logger.warning(
                    f"下载图片超时: {filename} [第{attempt}次尝试]"
                )
            except aiohttp.ClientError as e:
                logger.warning(
                    f"下载图片网络错误: {filename} - {e} [第{attempt}次尝试]"
                )
            except PermissionError:
                logger.error(f"权限不足，无法保存图片: {filepath}")
                return
            except OSError as e:
                logger.error(f"保存图片时出错: {filepath} - {e}")
                return

            # Exponential backoff before retry
            if attempt < MAX_RETRIES:
                wait_time = RETRY_BACKOFF_FACTOR * (2 ** (attempt - 1))
                await asyncio.sleep(wait_time)

        logger.error(f"图片下载最终失败（已重试{MAX_RETRIES}次）: {filename}")


async def download_images(
    products: List[Dict[str, Any]], output_path: Path
) -> None:
    """Download all product images concurrently with a semaphore limit."""
    if not products:
        logger.info("没有需要下载的图片")
        return

    logger.info(f"开始批量下载 {len(products)} 张商品图片...")
    semaphore = asyncio.Semaphore(CONCURRENT_DOWNLOADS)

    async with aiohttp.ClientSession() as session:
        tasks = [
            download_single_image(session, semaphore, product, output_path)
            for product in products
        ]
        await asyncio.gather(*tasks)

    logger.info("图片批量下载完成")


def main() -> None:
    """Main entry point for the product selector script."""
    logger.info("=" * 50)
    logger.info("自动选品脚本启动")
    logger.info("=" * 50)

    # Determine base path (same directory as this script)
    base_path = Path(__file__).resolve().parent

    # Step 1: Create output directory
    output_path = create_output_directory(base_path)

    # Step 2: Fetch products from API
    session = build_session()
    products = fetch_products(session)
    if not products:
        logger.warning("未获取到任何商品数据，脚本结束")
        return

    # Step 3: Filter products
    filtered = filter_products(products)
    if not filtered:
        logger.warning("没有符合条件的商品，脚本结束")
        return

    # Step 4: Write CSV
    write_csv(filtered, output_path)

    # Step 5: Download images concurrently
    asyncio.run(download_images(filtered, output_path))

    logger.info("=" * 50)
    logger.info("自动选品脚本执行完毕")
    logger.info(f"结果已保存至: {output_path}")
    logger.info("=" * 50)


if __name__ == "__main__":
    main()
