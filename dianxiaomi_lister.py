"""
DianXiaoMi Auto-Listing Script

Automates product listing on SHEIN platform via DianXiaoMi (店小秘) backend.
Reads product data (title, description, SKU, images) from local folders and
fills the listing form using Playwright browser automation.
"""

import argparse
import asyncio
import json
import logging
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, ValidationError

# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
VALID_IMAGE_EXTENSIONS: set = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
DEFAULT_CONFIG_PATH: str = "dianxiaomi_config.json"
TYPING_DELAY_MS: int = 50  # Realistic typing delay in milliseconds
RETRY_BACKOFF_FACTOR: float = 1.0  # Exponential backoff base


# ---------------------------------------------------------------------------
# Configuration Models (Pydantic)
# ---------------------------------------------------------------------------
class LoginConfig(BaseModel):
    """Login credentials configuration.

    Credentials can be provided via environment variables DIANXIAOMI_USERNAME
    and DIANXIAOMI_PASSWORD, which take precedence over JSON config values.
    """

    username: str = Field(description="DianXiaoMi account username")
    password: str = Field(description="DianXiaoMi account password")

    def model_post_init(self, __context: Any) -> None:
        """Override credentials with environment variables if set."""
        env_username = os.environ.get("DIANXIAOMI_USERNAME")
        env_password = os.environ.get("DIANXIAOMI_PASSWORD")
        if env_username:
            self.username = env_username
        if env_password:
            self.password = env_password


class BrowserConfig(BaseModel):
    """Browser automation settings."""

    headless: bool = Field(default=False, description="Run browser in headless mode")
    slow_mo: int = Field(default=100, description="Slow down actions by ms")
    viewport_width: int = Field(default=1920, description="Browser viewport width")
    viewport_height: int = Field(default=1080, description="Browser viewport height")


class UploadConfig(BaseModel):
    """Upload behavior settings."""

    max_retries: int = Field(default=3, description="Max retries per operation")
    wait_timeout: int = Field(
        default=30000, description="Wait timeout in milliseconds"
    )
    delay_between_products: int = Field(
        default=5, description="Delay in seconds between product uploads"
    )


class SelectorsConfig(BaseModel):
    """CSS selectors for page elements (configurable for page changes)."""

    login_username: str = Field(default="input[name='username']")
    login_password: str = Field(default="input[name='password']")
    login_button: str = Field(default="button[type='submit']")
    title_input: str = Field(default="input.product-title")
    description_input: str = Field(default="textarea.product-description")
    sku_input: str = Field(default="input.product-sku")
    image_upload: str = Field(default="input[type='file']")
    submit_button: str = Field(default="button.submit-listing")


class AppConfig(BaseModel):
    """Top-level application configuration."""

    login: LoginConfig
    browser: BrowserConfig = Field(default_factory=BrowserConfig)
    dianxiaomi_url: str = Field(default="https://www.dianxiaomi.com")
    platform: str = Field(default="shein")
    products_folder: str = Field(default="./products")
    upload: UploadConfig = Field(default_factory=UploadConfig)
    selectors: SelectorsConfig = Field(default_factory=SelectorsConfig)


# ---------------------------------------------------------------------------
# Product Data
# ---------------------------------------------------------------------------
@dataclass
class ProductData:
    """Holds parsed product information from a product folder."""

    title: str
    description: str
    sku: str
    price: float
    category: str = ""
    image_paths: List[Path] = field(default_factory=list)
    folder_name: str = ""


# ---------------------------------------------------------------------------
# Product Data Reader
# ---------------------------------------------------------------------------
def read_products(products_folder: Path) -> List[ProductData]:
    """
    Scan the products folder and load product data from each subfolder.

    Each subfolder should contain a product.json and an images/ directory.
    Invalid or incomplete products are skipped with a warning.
    """
    products: List[ProductData] = []

    if not products_folder.exists():
        logger.error(f"商品目录不存在: {products_folder}")
        return products

    if not products_folder.is_dir():
        logger.error(f"商品路径不是一个目录: {products_folder}")
        return products

    subfolders = sorted(
        [d for d in products_folder.iterdir() if d.is_dir()]
    )

    if not subfolders:
        logger.warning(f"商品目录为空，未找到任何子文件夹: {products_folder}")
        return products

    logger.info(f"扫描商品目录: {products_folder} (找到 {len(subfolders)} 个子文件夹)")

    for folder in subfolders:
        product_json_path = folder / "product.json"

        if not product_json_path.exists():
            logger.warning(f"跳过文件夹 '{folder.name}': 缺少 product.json")
            continue

        try:
            with open(product_json_path, "r", encoding="utf-8") as f:
                data: Dict[str, Any] = json.load(f)
        except json.JSONDecodeError as e:
            logger.warning(f"跳过文件夹 '{folder.name}': product.json 格式错误 - {e}")
            continue
        except OSError as e:
            logger.warning(f"跳过文件夹 '{folder.name}': 读取文件失败 - {e}")
            continue

        # Validate required fields
        missing_fields = []
        for required_field in ("title", "description", "sku", "price"):
            if required_field not in data or not data[required_field]:
                missing_fields.append(required_field)

        if missing_fields:
            logger.warning(
                f"跳过文件夹 '{folder.name}': 缺少必填字段 {missing_fields}"
            )
            continue

        # Collect image paths
        images_dir = folder / "images"
        image_paths: List[Path] = []
        if images_dir.exists() and images_dir.is_dir():
            image_paths = sorted(
                [
                    img
                    for img in images_dir.iterdir()
                    if img.is_file()
                    and img.suffix.lower() in VALID_IMAGE_EXTENSIONS
                ]
            )

        if not image_paths:
            logger.warning(f"商品 '{folder.name}' 没有有效的图片文件")

        product = ProductData(
            title=str(data["title"]),
            description=str(data["description"]),
            sku=str(data["sku"]),
            price=float(data["price"]),
            category=str(data.get("category", "")),
            image_paths=image_paths,
            folder_name=folder.name,
        )
        products.append(product)
        logger.info(
            f"已加载商品: {product.folder_name} "
            f"(SKU: {product.sku}, 图片: {len(product.image_paths)} 张)"
        )

    logger.info(f"商品加载完成: 共 {len(products)} 个有效商品")
    return products


# ---------------------------------------------------------------------------
# DianXiaoMi Lister Class
# ---------------------------------------------------------------------------
class DianXiaoMiLister:
    """Encapsulates all browser automation logic for DianXiaoMi listing."""

    def __init__(self, config: AppConfig, dry_run: bool = False) -> None:
        """Initialize the lister with configuration."""
        self.config = config
        self.dry_run = dry_run
        self.browser: Optional[Any] = None
        self.context: Optional[Any] = None
        self.page: Optional[Any] = None
        self.success_count: int = 0
        self.failure_count: int = 0

    async def start(self, target_product: Optional[str] = None) -> None:
        """
        Main entry point: load products, launch browser, and process listings.

        Args:
            target_product: If specified, only upload this product folder name.
        """
        # Load products
        products_folder = Path(self.config.products_folder)
        products = read_products(products_folder)

        if not products:
            logger.warning("没有可上传的商品，脚本结束")
            return

        # Filter to specific product if requested
        if target_product:
            products = [p for p in products if p.folder_name == target_product]
            if not products:
                logger.error(f"未找到指定商品: {target_product}")
                return
            logger.info(f"已选定单个商品: {target_product}")

        # Dry-run mode: validate only
        if self.dry_run:
            logger.info("=" * 50)
            logger.info("试运行模式 - 仅验证商品数据，不启动浏览器")
            logger.info("=" * 50)
            self._validate_products(products)
            return

        # Launch browser and process
        try:
            await self._launch_browser()
            await self.login()
            await self.navigate_to_shein_listing()

            for idx, product in enumerate(products, 1):
                logger.info(f"正在处理第 {idx}/{len(products)} 个商品: {product.folder_name}")
                try:
                    await self.upload_product(product)
                    self.success_count += 1
                    logger.info(f"商品上传成功: {product.folder_name}")
                except Exception as e:
                    self.failure_count += 1
                    logger.error(f"商品上传失败: {product.folder_name} - {e}")

                # Navigate back to fresh form before next product
                if idx < len(products):
                    delay = self.config.upload.delay_between_products
                    logger.info(f"等待 {delay} 秒后继续下一个商品...")
                    await asyncio.sleep(delay)
                    try:
                        await self.navigate_to_shein_listing()
                    except Exception as e:
                        logger.error(f"导航到新表单失败: {e}，尝试继续...")
                        # Attempt a page reload as fallback
                        try:
                            await self.page.reload(wait_until="networkidle")
                        except Exception:
                            pass

        finally:
            await self.close()
            self._print_summary()

    def _validate_products(self, products: List[ProductData]) -> None:
        """Validate product data in dry-run mode."""
        valid_count = 0
        invalid_count = 0

        for product in products:
            issues: List[str] = []

            if not product.title.strip():
                issues.append("标题为空")
            if not product.description.strip():
                issues.append("描述为空")
            if not product.sku.strip():
                issues.append("SKU为空")
            if product.price <= 0:
                issues.append("价格无效")
            if not product.image_paths:
                issues.append("没有图片文件")

            # Validate image files exist and are readable
            for img_path in product.image_paths:
                if not img_path.exists():
                    issues.append(f"图片文件不存在: {img_path.name}")
                elif img_path.stat().st_size == 0:
                    issues.append(f"图片文件为空: {img_path.name}")

            if issues:
                invalid_count += 1
                logger.warning(
                    f"商品 '{product.folder_name}' 验证失败: {', '.join(issues)}"
                )
            else:
                valid_count += 1
                logger.info(
                    f"商品 '{product.folder_name}' 验证通过 "
                    f"(标题: {product.title[:30]}..., SKU: {product.sku}, "
                    f"图片: {len(product.image_paths)} 张)"
                )

        logger.info("=" * 50)
        logger.info(f"验证结果: {valid_count} 个通过, {invalid_count} 个失败")
        logger.info("=" * 50)

    async def _launch_browser(self) -> None:
        """Launch Playwright browser with configured settings."""
        from playwright.async_api import async_playwright

        logger.info("正在启动浏览器...")
        self._playwright = await async_playwright().start()
        self.browser = await self._playwright.chromium.launch(
            headless=self.config.browser.headless,
            slow_mo=self.config.browser.slow_mo,
        )
        self.context = await self.browser.new_context(
            viewport={
                "width": self.config.browser.viewport_width,
                "height": self.config.browser.viewport_height,
            }
        )
        self.page = await self.context.new_page()
        logger.info("浏览器已启动")

    async def login(self) -> None:
        """
        Navigate to DianXiaoMi login page and authenticate.

        Handles login failure cases: wrong credentials, captcha, timeout.
        """
        login_url = f"{self.config.dianxiaomi_url}/login"
        logger.info(f"正在登录店小秘: {login_url}")

        timeout = self.config.upload.wait_timeout

        try:
            await self.page.goto(login_url, wait_until="networkidle", timeout=timeout)
        except Exception as e:
            raise RuntimeError(f"无法访问登录页面: {e}")

        # Wait for login form
        try:
            await self.page.wait_for_selector(
                self.config.selectors.login_username, timeout=timeout
            )
        except Exception:
            raise RuntimeError("登录页面加载超时，未找到用户名输入框")

        # Fill credentials
        await self.page.fill(
            self.config.selectors.login_username, self.config.login.username
        )
        await self.page.fill(
            self.config.selectors.login_password, self.config.login.password
        )

        # Click login
        await self.page.click(self.config.selectors.login_button)

        # Wait for dashboard or detect errors
        try:
            await self.page.wait_for_url(
                "**/index**", timeout=timeout
            )
            logger.info("登录成功")
        except Exception:
            # Check for common error indicators
            error_text = await self.page.text_content("body")
            if error_text and ("验证码" in error_text or "captcha" in error_text.lower()):
                raise RuntimeError("登录失败: 需要验证码，请手动完成验证后重试")
            elif error_text and ("密码" in error_text and "错误" in error_text):
                raise RuntimeError("登录失败: 用户名或密码错误")
            else:
                raise RuntimeError("登录失败: 等待跳转超时，请检查网络连接或凭证")

    async def navigate_to_shein_listing(self) -> None:
        """Navigate to the SHEIN product listing page after login."""
        logger.info("正在导航到SHEIN商品发布页面...")

        timeout = self.config.upload.wait_timeout
        listing_url = f"{self.config.dianxiaomi_url}/listing/{self.config.platform}"

        try:
            await self.page.goto(listing_url, wait_until="networkidle", timeout=timeout)
        except Exception as e:
            raise RuntimeError(f"无法访问SHEIN发布页面: {e}")

        # Wait for the listing form to be ready
        try:
            await self.page.wait_for_selector(
                self.config.selectors.title_input, timeout=timeout
            )
            logger.info("SHEIN商品发布页面已就绪")
        except Exception:
            raise RuntimeError("商品发布页面加载超时，未找到表单元素")

    async def upload_product(self, product: ProductData) -> None:
        """
        Upload a single product: fill form fields and submit.

        Args:
            product: Product data to fill into the listing form.
        """
        logger.info(f"开始上传商品: {product.sku}")

        await self.fill_title(product.title)
        await self.fill_description(product.description)
        await self.fill_sku(product.sku)

        if product.image_paths:
            await self.upload_images(product.image_paths)

        await self.submit_listing()

    async def _fill_field(self, selector: str, value: str, label: str) -> None:
        """
        Generic helper to clear and fill a form field with retry logic.

        Uses page.fill('') to reliably clear the field (works across SPA
        frameworks), then types the value with realistic delays.

        Args:
            selector: CSS selector for the form field.
            value: The text value to type into the field.
            label: Human-readable field name for logging.
        """
        timeout = self.config.upload.wait_timeout
        max_retries = self.config.upload.max_retries

        for attempt in range(1, max_retries + 1):
            try:
                await self.page.wait_for_selector(selector, timeout=timeout)
                await self.page.fill(selector, "")  # Reliably clear field
                await self.page.type(selector, value, delay=TYPING_DELAY_MS)
                logger.info(f"已填写{label}: {value[:50]}{'...' if len(value) > 50 else ''}")
                return
            except Exception as e:
                if attempt < max_retries:
                    wait_time = RETRY_BACKOFF_FACTOR * (2 ** (attempt - 1))
                    logger.warning(
                        f"填写{label}失败，第{attempt}次尝试: {e}，"
                        f"等待 {wait_time} 秒后重试"
                    )
                    await asyncio.sleep(wait_time)
                else:
                    raise RuntimeError(f"填写{label}最终失败（已重试{max_retries}次）: {e}")

    async def fill_title(self, title: str) -> None:
        """
        Fill the product title field.

        Locates the title input, clears existing content, and types
        the new title with realistic delays.
        """
        await self._fill_field(self.config.selectors.title_input, title, "标题")

    async def fill_description(self, description: str) -> None:
        """
        Fill the product description field.

        Locates the description textarea, clears existing content,
        and types the new description.
        """
        await self._fill_field(self.config.selectors.description_input, description, "商品描述")

    async def fill_sku(self, sku: str) -> None:
        """
        Fill the product SKU field.

        Locates the SKU input, clears existing content, and types
        the new SKU value.
        """
        await self._fill_field(self.config.selectors.sku_input, sku, "SKU")

    async def upload_images(self, image_paths: List[Path]) -> None:
        """
        Upload product images using Playwright's set_input_files.

        Processes images sequentially, validates each file before upload,
        and waits for upload completion. Includes retry logic for transient
        DOM-ready races.

        Args:
            image_paths: List of Path objects pointing to image files.
        """
        selector = self.config.selectors.image_upload
        timeout = self.config.upload.wait_timeout
        max_retries = self.config.upload.max_retries

        logger.info(f"开始上传 {len(image_paths)} 张图片...")

        # Validate all images exist before starting
        valid_paths: List[Path] = []
        for img_path in image_paths:
            if not img_path.exists():
                logger.warning(f"图片文件不存在，已跳过: {img_path}")
                continue
            if img_path.stat().st_size == 0:
                logger.warning(f"图片文件为空，已跳过: {img_path}")
                continue
            if img_path.suffix.lower() not in VALID_IMAGE_EXTENSIONS:
                logger.warning(f"不支持的图片格式，已跳过: {img_path}")
                continue
            valid_paths.append(img_path)

        if not valid_paths:
            logger.warning("没有有效的图片可上传")
            return

        for attempt in range(1, max_retries + 1):
            try:
                await self.page.wait_for_selector(selector, timeout=timeout)
                # Upload all valid images at once using set_input_files
                file_paths = [str(p.resolve()) for p in valid_paths]
                await self.page.set_input_files(selector, file_paths)

                # Wait for uploads to process
                await asyncio.sleep(2)
                logger.info(f"已上传 {len(valid_paths)} 张图片")
                return
            except Exception as e:
                if attempt < max_retries:
                    wait_time = RETRY_BACKOFF_FACTOR * (2 ** (attempt - 1))
                    logger.warning(
                        f"图片上传失败，第{attempt}次尝试: {e}，"
                        f"等待 {wait_time} 秒后重试"
                    )
                    await asyncio.sleep(wait_time)
                else:
                    raise RuntimeError(f"图片上传最终失败（已重试{max_retries}次）: {e}")

    async def submit_listing(self) -> None:
        """
        Click the submit button and wait for confirmation or error.

        Uses scoped selectors (toast/modal) for result detection instead of
        searching the entire page body, which avoids false positives from
        unrelated page content like navigation menus or sidebar labels.
        """
        selector = self.config.selectors.submit_button
        timeout = self.config.upload.wait_timeout

        logger.info("正在提交商品...")

        try:
            await self.page.wait_for_selector(selector, timeout=timeout)
            await self.page.click(selector)
        except Exception as e:
            raise RuntimeError(f"无法点击提交按钮: {e}")

        # Wait for a toast/modal response indicator (scoped detection)
        toast_selectors = [
            ".toast-success",
            ".ant-message-success",
            ".el-message--success",
            ".ant-notification-notice",
            ".toast-error",
            ".ant-message-error",
            ".el-message--error",
            ".modal-body",
            ".ant-modal-content",
        ]
        combined_selector = ", ".join(toast_selectors)

        try:
            # First, try to detect a scoped toast/modal element
            toast = await self.page.wait_for_selector(
                combined_selector, timeout=5000
            )
            if toast:
                toast_text = await toast.text_content() or ""
                if "成功" in toast_text or "success" in toast_text.lower():
                    logger.info("商品提交成功")
                    return
                if "重复" in toast_text or "duplicate" in toast_text.lower():
                    raise RuntimeError("提交失败: SKU重复")
                if "必填" in toast_text or "required" in toast_text.lower():
                    raise RuntimeError("提交失败: 存在未填写的必填字段")
                if ("图片" in toast_text and "失败" in toast_text):
                    raise RuntimeError("提交失败: 图片上传异常")
                # Toast appeared but content not recognized
                logger.warning(f"检测到提示框但内容未识别: {toast_text[:100]}")
        except Exception:
            # No toast found within 5s, fall through to URL/network check
            pass

        # Fallback: check if URL changed (indicating successful navigation)
        try:
            await self.page.wait_for_timeout(2000)
            current_url = self.page.url
            if "success" in current_url or "result" in current_url:
                logger.info("商品提交成功（通过URL跳转确认）")
                return
        except Exception:
            pass

        # Final fallback: assume success with clear warning
        logger.warning(
            "提交后未检测到明确的成功/失败标识（toast/modal/URL均无响应），"
            "默认视为成功，请手动确认"
        )

    async def close(self) -> None:
        """Close browser and clean up resources."""
        try:
            if self.browser:
                await self.browser.close()
                logger.info("浏览器已关闭")
            if hasattr(self, "_playwright") and self._playwright:
                await self._playwright.stop()
        except Exception as e:
            logger.warning(f"关闭浏览器时出错: {e}")

    def _print_summary(self) -> None:
        """Print final upload summary."""
        total = self.success_count + self.failure_count
        logger.info("=" * 50)
        logger.info("上传任务完成")
        logger.info(f"总计: {total} 个商品")
        logger.info(f"成功: {self.success_count} 个")
        logger.info(f"失败: {self.failure_count} 个")
        logger.info("=" * 50)


# ---------------------------------------------------------------------------
# Configuration Loading
# ---------------------------------------------------------------------------
def load_config(config_path: Path) -> AppConfig:
    """
    Load and validate configuration from a JSON file.

    Args:
        config_path: Path to the configuration JSON file.

    Returns:
        Validated AppConfig instance.

    Raises:
        SystemExit: If configuration file is missing or invalid.
    """
    if not config_path.exists():
        logger.error(f"配置文件不存在: {config_path}")
        sys.exit(1)

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        logger.error(f"配置文件JSON格式错误: {e}")
        sys.exit(1)
    except OSError as e:
        logger.error(f"读取配置文件失败: {e}")
        sys.exit(1)

    try:
        config = AppConfig(**data)
    except ValidationError as e:
        logger.error(f"配置文件验证失败:")
        for error in e.errors():
            field = " -> ".join(str(loc) for loc in error["loc"])
            logger.error(f"  {field}: {error['msg']}")
        sys.exit(1)

    logger.info(f"配置文件加载成功: {config_path}")
    return config


# ---------------------------------------------------------------------------
# Main Entry Point
# ---------------------------------------------------------------------------
def parse_arguments() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="店小秘自动上架脚本 - SHEIN平台商品批量发布工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python dianxiaomi_lister.py                       # 使用默认配置上传所有商品
  python dianxiaomi_lister.py --dry-run             # 验证模式，不启动浏览器
  python dianxiaomi_lister.py --product my-product  # 仅上传指定商品
  python dianxiaomi_lister.py --config my_config.json  # 使用自定义配置文件
        """,
    )
    parser.add_argument(
        "--config",
        type=str,
        default=DEFAULT_CONFIG_PATH,
        help=f"配置文件路径 (默认: {DEFAULT_CONFIG_PATH})",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="试运行模式: 验证商品数据但不启动浏览器上传",
    )
    parser.add_argument(
        "--product",
        type=str,
        default=None,
        help="指定单个商品文件夹名称进行上传",
    )
    return parser.parse_args()


async def async_main(args: argparse.Namespace) -> None:
    """Async main function to orchestrate the listing process."""
    config_path = Path(args.config)
    config = load_config(config_path)

    lister = DianXiaoMiLister(config=config, dry_run=args.dry_run)
    await lister.start(target_product=args.product)


def main() -> None:
    """Main entry point for the DianXiaoMi auto-listing script."""
    args = parse_arguments()

    logger.info("=" * 50)
    logger.info("店小秘自动上架脚本启动")
    logger.info(f"平台: SHEIN | 模式: {'试运行' if args.dry_run else '正式上传'}")
    logger.info("=" * 50)

    try:
        asyncio.run(async_main(args))
    except KeyboardInterrupt:
        logger.info("用户中断，脚本已停止")
    except Exception as e:
        logger.error(f"脚本执行异常: {e}")
        sys.exit(1)

    logger.info("=" * 50)
    logger.info("店小秘自动上架脚本执行完毕")
    logger.info("=" * 50)


if __name__ == "__main__":
    main()
