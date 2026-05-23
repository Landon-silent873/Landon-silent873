"""
SHEIN Auto-Lister Script

Automates the process of listing similar products on SHEIN seller center
by connecting to an already-running Chrome browser via CDP (Chrome DevTools
Protocol). Iterates over product subfolders, fills in product details, uploads
images, and publishes listings.
"""

import argparse
import asyncio
import glob
import logging
import random
import sys
import time
from pathlib import Path
from typing import List, Optional

from playwright.async_api import async_playwright, Browser, BrowserContext, Page

from config import (
    DEFAULT_CDP_URL,
    DEFAULT_DELAY_MAX,
    DEFAULT_DELAY_MIN,
    DEFAULT_PRICE,
    DEFAULT_SIZES,
    CATEGORY_CODES,
    COLOR_PREFIXES,
    IMAGE_PATTERNS,
    SHEIN_PRODUCT_LIST_URL,
    load_config,
    get_color_name,
    get_category_name,
)

# Module-level config dict; populated in main_async from load_config() so that
# YAML overrides (cdp_url, image_patterns, etc.) are respected at runtime.
_runtime_config: dict = {}
from sku_generator import generate_article_number, generate_all_skus
from title_generator import generate_title, generate_description

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
SCRIPT_VERSION: str = "1.0.0"


def detect_color_from_folder(folder_name: str) -> str:
    """
    Detect color prefix from a product subfolder name.

    If the folder name contains 'black' (case-insensitive), return 'B'.
    Otherwise, return 'W'.

    Args:
        folder_name: Name of the product subfolder.

    Returns:
        Color prefix string ('B' or 'W').
    """
    if "black" in folder_name.lower():
        return "B"
    return "W"

# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="SHEIN自动上架工具 - 通过CDP连接Chrome浏览器自动发布商品",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  python shein_auto_lister.py --folder ./products --category 3001 --color W --base-product-id 12345
  python shein_auto_lister.py --folder ./hoodies --category 8008 --color B --base-product-id 67890 --cdp-url ws://127.0.0.1:9223
        """,
    )
    parser.add_argument(
        "--folder",
        type=str,
        required=True,
        help="商品图片的父文件夹路径（每个子文件夹代表一个商品）",
    )
    parser.add_argument(
        "--category",
        type=str,
        required=True,
        choices=list(CATEGORY_CODES.keys()),
        help="商品类别代码 (3001=短袖T恤, 8008=连帽卫衣, ady000=圆领卫衣)",
    )
    parser.add_argument(
        "--color",
        type=str,
        required=False,
        default=None,
        choices=list(COLOR_PREFIXES.keys()),
        help="颜色前缀 (W=白色, B=黑色)",
    )
    parser.add_argument(
        "--auto-color",
        action="store_true",
        default=False,
        help="自动根据商品子文件夹名判断颜色（包含black/Black则为B，否则为W）",
    )
    parser.add_argument(
        "--base-product-id",
        type=str,
        required=True,
        help="基础商品的记录ID（用于定位商品并点击'发布类似商品'）",
    )
    parser.add_argument(
        "--cdp-url",
        type=str,
        default=DEFAULT_CDP_URL,
        help=f"Chrome DevTools Protocol URL (默认: {DEFAULT_CDP_URL})",
    )
    args = parser.parse_args()
    if not args.auto_color and not args.color:
        parser.error("必须指定 --color 或 --auto-color 其中一个")
    return args


async def random_delay(min_seconds: float = DEFAULT_DELAY_MIN, max_seconds: float = DEFAULT_DELAY_MAX) -> None:
    """Wait for a random duration to mimic human behavior."""
    delay = random.uniform(min_seconds, max_seconds)
    await asyncio.sleep(delay)


def get_product_subfolders(folder_path: Path) -> List[Path]:
    """
    Get all product subfolders from the parent folder, sorted by name.

    Args:
        folder_path: Path to the parent folder.

    Returns:
        Sorted list of subfolder paths.
    """
    if not folder_path.exists():
        logger.error(f"文件夹不存在: {folder_path}")
        return []

    subfolders = sorted([
        p for p in folder_path.iterdir()
        if p.is_dir() and not p.name.startswith(".")
    ])

    logger.info(f"找到 {len(subfolders)} 个商品子文件夹")
    return subfolders


def get_product_images(subfolder: Path) -> List[str]:
    """
    Get all product images from a subfolder, sorted by filename.

    Looks for files matching Main-01.*, Main-02.*, etc.
    Uses image_patterns from the runtime config (populated from YAML or defaults).

    Args:
        subfolder: Path to the product subfolder.

    Returns:
        Sorted list of absolute image file paths.
    """
    patterns = _runtime_config.get("image_patterns", IMAGE_PATTERNS)
    images: List[str] = []
    for pattern in patterns:
        found = glob.glob(str(subfolder / pattern))
        images.extend(found)

    # Remove duplicates and sort
    images = sorted(set(images))
    return images


async def connect_to_browser(cdp_url: str):
    """
    Connect to an already-running Chrome browser via CDP.

    Args:
        cdp_url: WebSocket URL for Chrome DevTools Protocol.

    Returns:
        Tuple of (playwright_instance, browser) or (None, None) if connection failed.
    """
    try:
        playwright = await async_playwright().start()
        browser = await playwright.chromium.connect_over_cdp(cdp_url)
        logger.info(f"成功连接到浏览器: {cdp_url}")
        return playwright, browser
    except Exception as e:
        logger.error(f"连接浏览器失败: {e}")
        logger.error("请确保Chrome已启动并开启了远程调试模式")
        logger.error(f"  Chrome启动参数: --remote-debugging-port=9222")
        return None, None


async def navigate_to_product_list(page: Page) -> bool:
    """
    Navigate to the product list page.

    Args:
        page: Playwright Page instance.

    Returns:
        True if navigation succeeded.
    """
    try:
        await page.goto(SHEIN_PRODUCT_LIST_URL, wait_until="networkidle")
        await random_delay()
        logger.info("已导航到商品列表页面")
        return True
    except Exception as e:
        logger.error(f"导航到商品列表页面失败: {e}")
        return False


async def find_and_click_publish_similar(page: Page, base_product_id: str) -> bool:
    """
    Find the base product in the list and click 'Publish Similar Product'.

    Args:
        page: Playwright Page instance.
        base_product_id: The product record ID to locate.

    Returns:
        True if the action succeeded.
    """
    try:
        # Search for the product by ID
        search_input = page.locator('input[placeholder*="商品"]').first
        if await search_input.is_visible():
            await search_input.fill(base_product_id)
            await random_delay()
            await page.keyboard.press("Enter")
            await random_delay(2, 4)

        # Find the product row and click the action menu
        product_row = page.locator(f'[data-id="{base_product_id}"]').first
        if not await product_row.is_visible(timeout=5000):
            # Try alternative selector
            product_row = page.locator(f'text="{base_product_id}"').first

        # Click the "Publish Similar" button/link
        publish_similar_btn = page.locator('text="发布类似商品"').first
        if not await publish_similar_btn.is_visible(timeout=5000):
            # Try English text
            publish_similar_btn = page.locator('text="Publish Similar"').first

        await publish_similar_btn.click()
        await random_delay(2, 4)
        logger.info(f"已点击'发布类似商品' (基础商品ID: {base_product_id})")
        return True
    except Exception as e:
        logger.error(f"查找并点击'发布类似商品'失败: {e}")
        return False


async def fill_product_form(
    page: Page,
    title: str,
    description: str,
    article_number: str,
    price: float,
    color_name: str,
    skus: List[str],
    sizes: List[str],
) -> bool:
    """
    Fill in the product listing form fields.

    Tracks which critical fields (title, article number) were populated
    and returns False if any critical field was missed.

    Args:
        page: Playwright Page instance.
        title: Product title/name.
        description: Product description.
        article_number: Product article number.
        price: Product price.
        color_name: Full color name.
        skus: List of SKU strings for all sizes.
        sizes: List of size strings.

    Returns:
        True if form filling succeeded (all critical fields populated).
    """
    # Track critical field population
    title_filled = False
    article_filled = False

    try:
        # Fill title
        # NOTE: Selectors are speculative placeholders. Adjust to match the
        # actual SHEIN seller-center DOM after real-browser testing.
        title_input = page.locator('input[placeholder*="标题"], input[placeholder*="title"], textarea[placeholder*="标题"]').first
        if await title_input.is_visible(timeout=5000):
            await title_input.fill(title)
            await random_delay()
            title_filled = True
            logger.info("已填写商品标题")

        # Fill description
        desc_input = page.locator('textarea[placeholder*="描述"], textarea[placeholder*="description"], [contenteditable="true"]').first
        if await desc_input.is_visible(timeout=5000):
            await desc_input.fill(description)
            await random_delay()
            logger.info("已填写商品描述")

        # Fill article number (货号)
        article_input = page.locator('input[placeholder*="货号"], input[placeholder*="article"]').first
        if await article_input.is_visible(timeout=5000):
            await article_input.fill(article_number)
            await random_delay()
            article_filled = True
            logger.info(f"已填写货号: {article_number}")

        # Fill price
        price_input = page.locator('input[placeholder*="价格"], input[placeholder*="price"], input[type="number"]').first
        if await price_input.is_visible(timeout=5000):
            await price_input.fill(str(price))
            await random_delay()
            logger.info(f"已填写价格: ${price}")

        # Fill color
        color_input = page.locator('input[placeholder*="颜色"], input[placeholder*="color"]').first
        if await color_input.is_visible(timeout=5000):
            await color_input.fill(color_name)
            await random_delay()
            logger.info(f"已填写颜色: {color_name}")

        # Fill sizes and SKUs
        for i, (size, sku) in enumerate(zip(sizes, skus)):
            try:
                size_input = page.locator(f'input[placeholder*="尺码"]:nth-of-type({i + 1}), input[placeholder*="size"]').nth(i)
                if await size_input.is_visible(timeout=3000):
                    await size_input.fill(size)

                sku_input = page.locator(f'input[placeholder*="SKU"], input[placeholder*="sku"]').nth(i)
                if await sku_input.is_visible(timeout=3000):
                    await sku_input.fill(sku)

                await random_delay(0.5, 1.5)
            except Exception:
                logger.warning(f"填写尺码/SKU失败 ({size}/{sku})，跳过")
                continue

        logger.info(f"已填写 {len(sizes)} 个尺码和SKU")

        # Fail if critical fields were not populated
        if not title_filled:
            logger.error("关键字段缺失: 商品标题未成功填写")
            return False
        if not article_filled:
            logger.error("关键字段缺失: 货号未成功填写")
            return False

        return True
    except Exception as e:
        logger.error(f"填写商品表单失败: {e}")
        return False


async def upload_images(page: Page, image_paths: List[str]) -> bool:
    """
    Upload product images to the listing form.

    Args:
        page: Playwright Page instance.
        image_paths: List of absolute paths to image files.

    Returns:
        True if upload succeeded.
    """
    if not image_paths:
        logger.warning("没有找到可上传的图片")
        return False

    try:
        # Find the file input element for image upload
        file_input = page.locator('input[type="file"]').first
        if await file_input.is_visible(timeout=5000):
            await file_input.set_input_files(image_paths)
            await random_delay(2, 5)
            logger.info(f"已上传 {len(image_paths)} 张图片")
            return True
        else:
            # Try clicking an upload button first to reveal the input
            upload_btn = page.locator('text="上传图片", text="Upload"').first
            if await upload_btn.is_visible(timeout=3000):
                await upload_btn.click()
                await random_delay()
                file_input = page.locator('input[type="file"]').first
                await file_input.set_input_files(image_paths)
                await random_delay(2, 5)
                logger.info(f"已上传 {len(image_paths)} 张图片")
                return True

        logger.warning("未找到图片上传入口")
        return False
    except Exception as e:
        logger.error(f"上传图片失败: {e}")
        return False


async def submit_product(page: Page) -> bool:
    """
    Click the publish/submit button and verify submission succeeded.

    After clicking, waits for success indicators (toast, redirect) or
    error banners. Returns False if an error is detected or no success
    confirmation is observed.

    Args:
        page: Playwright Page instance.

    Returns:
        True if submission succeeded with confirmation.
    """
    try:
        # Try various submit button selectors
        # NOTE: Selectors are speculative placeholders. Adjust to match the
        # actual SHEIN seller-center DOM after real-browser testing.
        submit_btn = page.locator('button:has-text("发布"), button:has-text("提交"), button:has-text("Publish"), button:has-text("Submit")').first
        if await submit_btn.is_visible(timeout=5000):
            await submit_btn.click()
            logger.info("已点击发布按钮，等待确认...")
        else:
            # Try save as draft as fallback
            draft_btn = page.locator('button:has-text("保存草稿"), button:has-text("Save Draft")').first
            if await draft_btn.is_visible(timeout=3000):
                await draft_btn.click()
                logger.info("已保存为草稿，等待确认...")
            else:
                logger.warning("未找到发布或保存按钮")
                return False

        # Wait for success or error indicators after submission
        # Check for error banner first (faster signal of failure)
        error_locator = page.locator(
            '.error-message, .alert-error, .toast-error, '
            '[class*="error"], [class*="fail"], '
            'text="失败", text="错误", text="Error", text="Failed"'
        ).first
        success_locator = page.locator(
            '.success-message, .alert-success, .toast-success, '
            '[class*="success"], '
            'text="成功", text="已发布", text="Success", text="Published"'
        ).first

        # Wait up to 10 seconds for either success or error signal
        try:
            # Race: whichever appears first
            result = await page.wait_for_selector(
                '.success-message, .alert-success, .toast-success, [class*="success"], '
                '.error-message, .alert-error, .toast-error, [class*="error-msg"], '
                ':text("成功"), :text("已发布"), :text("失败"), :text("错误")',
                timeout=10000,
            )
            if result:
                text_content = await result.text_content() or ""
                # Check if it looks like an error
                error_keywords = ["失败", "错误", "error", "failed", "fail"]
                if any(kw in text_content.lower() for kw in error_keywords):
                    logger.error(f"提交后检测到错误: {text_content.strip()[:200]}")
                    return False
                else:
                    logger.info(f"提交确认: {text_content.strip()[:100]}")
                    return True
        except Exception:
            # Timeout waiting for indicator - check if page URL changed (redirect)
            pass

        # Fallback: check if the URL changed (redirect to product list = success)
        await asyncio.sleep(3)
        current_url = page.url
        if "list" in current_url or "success" in current_url:
            logger.info(f"提交后页面跳转，视为成功: {current_url}")
            return True

        # No clear signal - log warning but treat as uncertain success
        logger.warning("未检测到明确的提交结果（无成功提示或错误信息），请手动确认")
        return True
    except Exception as e:
        logger.error(f"提交商品失败: {e}")
        return False


async def process_single_product(
    page: Page,
    subfolder: Path,
    category_code: str,
    color_prefix: str,
    base_product_id: str,
    price: float,
    sizes: List[str],
) -> bool:
    """
    Process a single product subfolder: generate data, fill form, upload, submit.

    Args:
        page: Playwright Page instance.
        subfolder: Path to the product subfolder.
        category_code: Category code string.
        color_prefix: Color prefix ('W' or 'B').
        base_product_id: Base product ID for "Publish Similar".
        price: Product price.
        sizes: List of available sizes.

    Returns:
        True if the product was successfully listed.
    """
    folder_name = subfolder.name
    logger.info(f"开始处理商品: {folder_name}")

    # Generate product data
    title = generate_title(folder_name, category_code)
    description = generate_description(folder_name, category_code)
    article_number = generate_article_number(category_code)
    color_name = get_color_name(color_prefix)
    skus = generate_all_skus(color_prefix, category_code, article_number)

    # Get images
    images = get_product_images(subfolder)
    if not images:
        logger.warning(f"商品文件夹中未找到图片: {subfolder}")
        return False

    logger.info(f"  货号: {article_number}")
    logger.info(f"  SKU数量: {len(skus)}")
    logger.info(f"  图片数量: {len(images)}")

    # Navigate to product list and click "Publish Similar"
    if not await navigate_to_product_list(page):
        return False

    if not await find_and_click_publish_similar(page, base_product_id):
        return False

    # Fill in the form
    if not await fill_product_form(
        page, title, description, article_number, price, color_name, skus, sizes
    ):
        return False

    # Upload images
    if not await upload_images(page, images):
        logger.warning("图片上传失败，但继续提交")

    # Submit
    if not await submit_product(page):
        return False

    logger.info(f"商品发布成功: {folder_name}")
    return True


async def main_async(args: argparse.Namespace) -> None:
    """Main async entry point for the auto-lister."""
    global _runtime_config
    config = load_config()
    _runtime_config = config

    folder_path = Path(args.folder).resolve()
    category_code = args.category
    auto_color = args.auto_color
    color_prefix = args.color  # May be None when --auto-color is used
    base_product_id = args.base_product_id
    # Use config cdp_url as base default; CLI arg overrides only if explicitly provided
    cdp_url = args.cdp_url if args.cdp_url != DEFAULT_CDP_URL else config.get("cdp_url", DEFAULT_CDP_URL)
    # If the user explicitly passed --cdp-url, prefer that
    if args.cdp_url != DEFAULT_CDP_URL:
        cdp_url = args.cdp_url

    price = config.get("price", DEFAULT_PRICE)
    sizes = config.get("sizes", DEFAULT_SIZES)
    delay_min = config.get("delay_min", DEFAULT_DELAY_MIN)
    delay_max = config.get("delay_max", DEFAULT_DELAY_MAX)

    logger.info("=" * 60)
    logger.info("SHEIN 自动上架工具启动")
    logger.info(f"  版本: {SCRIPT_VERSION}")
    logger.info(f"  商品文件夹: {folder_path}")
    logger.info(f"  类别: {get_category_name(category_code)} ({category_code})")
    if auto_color:
        logger.info("  颜色: 自动识别模式（根据文件夹名判断）")
    else:
        logger.info(f"  颜色: {get_color_name(color_prefix)} ({color_prefix})")
    logger.info(f"  基础商品ID: {base_product_id}")
    logger.info(f"  CDP地址: {cdp_url}")
    logger.info(f"  价格: ${price}")
    logger.info(f"  尺码: {', '.join(sizes)}")
    logger.info("=" * 60)

    # Get product subfolders
    subfolders = get_product_subfolders(folder_path)
    if not subfolders:
        logger.error("未找到任何商品子文件夹，脚本结束")
        return

    # Connect to browser
    playwright_instance, browser = await connect_to_browser(cdp_url)
    if not browser:
        logger.error("无法连接到浏览器，脚本结束")
        return

    try:
        # Get the first context and page
        try:
            contexts = browser.contexts
            if contexts:
                context = contexts[0]
                pages = context.pages
                if pages:
                    page = pages[0]
                else:
                    page = await context.new_page()
            else:
                context = await browser.new_context()
                page = await context.new_page()
        except Exception as e:
            logger.error(f"获取浏览器页面失败: {e}")
            return

        # Process each product
        success_count = 0
        fail_count = 0
        start_time = time.time()

        for i, subfolder in enumerate(subfolders, 1):
            logger.info(f"\n{'─' * 40}")
            logger.info(f"处理进度: {i}/{len(subfolders)}")
            logger.info(f"{'─' * 40}")

            try:
                # Determine color prefix for this product
                effective_color = color_prefix
                if auto_color:
                    effective_color = detect_color_from_folder(subfolder.name)
                    logger.info(f"  自动识别颜色: {get_color_name(effective_color)} ({effective_color})")

                success = await process_single_product(
                    page, subfolder, category_code, effective_color,
                    base_product_id, price, sizes
                )
                if success:
                    success_count += 1
                else:
                    fail_count += 1
            except Exception as e:
                logger.error(f"处理商品时发生异常: {subfolder.name} - {e}")
                fail_count += 1

            # Random delay between products
            if i < len(subfolders):
                wait_time = random.uniform(delay_min, delay_max)
                logger.info(f"等待 {wait_time:.1f} 秒后处理下一个商品...")
                await asyncio.sleep(wait_time)

        # Summary
        elapsed = time.time() - start_time
        logger.info("\n" + "=" * 60)
        logger.info("自动上架任务完成 - 执行摘要")
        logger.info("=" * 60)
        logger.info(f"  总商品数: {len(subfolders)}")
        logger.info(f"  成功发布: {success_count}")
        logger.info(f"  发布失败: {fail_count}")
        logger.info(f"  耗时: {elapsed:.1f} 秒")
        logger.info("=" * 60)
    finally:
        # Clean up: close browser connection and stop Playwright to avoid resource leaks
        try:
            await browser.close()
        except Exception as e:
            logger.warning(f"关闭浏览器连接时出错: {e}")
        try:
            await playwright_instance.stop()
        except Exception as e:
            logger.warning(f"停止Playwright时出错: {e}")


def main() -> None:
    """Main entry point."""
    args = parse_args()
    asyncio.run(main_async(args))


if __name__ == "__main__":
    main()
