# SHEIN 自动上架工具

通过 Chrome DevTools Protocol (CDP) 连接已登录的 Chrome 浏览器，自动批量发布商品到 SHEIN 卖家中心。

## 前置条件

1. **Chrome 浏览器** - 需要以远程调试模式启动
2. **Python 3.9+** - 运行环境
3. **已登录 SHEIN 卖家中心** - 手动登录后再运行脚本

## 安装依赖

```bash
pip install -r requirements.txt
```

## 启动 Chrome 远程调试模式

脚本需要连接到一个已经运行的 Chrome 浏览器实例。请按照以下命令启动 Chrome：

### Windows

```cmd
"C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222
```

### macOS

```bash
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome --remote-debugging-port=9222
```

### Linux

```bash
google-chrome --remote-debugging-port=9222
```

> 注意: 启动后请手动在浏览器中登录 SHEIN 卖家中心 (https://seller.shein.com)，确保已经登录成功再运行脚本。

## 手动登录 SHEIN 卖家中心

1. 在启动的 Chrome 中打开 https://seller.shein.com
2. 输入账号密码登录
3. 确认已进入卖家后台主页
4. 保持浏览器打开，不要关闭

## 命令行使用

### 基本用法

```bash
python shein_auto_lister.py --folder ./商品图片 --category 3001 --color W --base-product-id 12345
```

### 参数说明

| 参数 | 必填 | 说明 |
|------|------|------|
| `--folder` | 是 | 商品图片的父文件夹路径 |
| `--category` | 是 | 类别代码: 3001(短袖T恤), 8008(连帽卫衣), ady000(圆领卫衣) |
| `--color` | 是 | 颜色前缀: W(白色), B(黑色) |
| `--base-product-id` | 是 | 基础商品ID(用于点击"发布类似商品") |
| `--cdp-url` | 否 | CDP连接地址 (默认: ws://127.0.0.1:9222) |

### 使用示例

```bash
# 白色短袖T恤
python shein_auto_lister.py --folder ./白色T恤 --category 3001 --color W --base-product-id 98765

# 黑色连帽卫衣，自定义CDP端口
python shein_auto_lister.py --folder ./黑色卫衣 --category 8008 --color B --base-product-id 54321 --cdp-url ws://127.0.0.1:9223

# 圆领卫衣
python shein_auto_lister.py --folder ./圆领系列 --category ady000 --color W --base-product-id 11111
```

## 商品图片文件夹结构

```
商品图片/                      <-- --folder 指向这里
├── Black Dad Dope T-Shirt/   <-- 子文件夹 = 一个商品
│   ├── Main-01.jpg           <-- 商品主图
│   ├── Main-02.jpg           <-- 详情图
│   └── Main-03.png           <-- 详情图
├── Funny Quote Hoodie/       <-- 另一个商品
│   ├── Main-01.png
│   ├── Main-02.png
│   └── Main-03.jpg
└── ...
```

### 图片命名规则

- 文件名格式: `Main-01.jpg`, `Main-02.png` 等
- 支持格式: `.jpg`, `.jpeg`, `.png`, `.webp`
- 图片按文件名排序上传
- 每个子文件夹代表一个独立商品

## 配置选项

可以通过 `config.yaml` 文件自定义配置。复制 `config.example.yaml` 为 `config.yaml` 即可：

```bash
cp config.example.yaml config.yaml
```

### 可配置项

- `price` - 商品价格 (默认: 20 USD)
- `sizes` - 尺码列表 (默认: S, M, L, XL, XXL, XXXL)
- `delay_min` / `delay_max` - 操作间随机延迟范围 (默认: 1-3秒)
- `cdp_url` - Chrome CDP 连接地址
- `color_prefixes` - 颜色前缀映射
- `category_codes` - 类别代码映射

## SKU 生成规则

- **货号格式**: `{类别代码}{递增数字}` 例如 `30014608`
- **SKU格式**: `{颜色前缀}-{类别代码}-{数字后缀}-{尺码}` 例如 `W-3001-4608-S`
- 每次运行自动生成不重复的货号，状态保存在 `sku_state.json`

## 常见问题

### 连接浏览器失败

**问题**: 提示 "连接浏览器失败"

**解决方案**:
1. 确认 Chrome 已以 `--remote-debugging-port=9222` 参数启动
2. 检查端口是否被占用: `netstat -an | grep 9222`
3. 确保没有其他 Chrome 实例占用该端口
4. 尝试关闭所有 Chrome 窗口后重新启动

### 找不到商品

**问题**: 提示 "查找并点击'发布类似商品'失败"

**解决方案**:
1. 确认 `--base-product-id` 参数正确
2. 确认该商品在卖家中心的商品列表中可见
3. 手动在浏览器中验证商品是否存在

### 图片上传失败

**问题**: 图片无法上传

**解决方案**:
1. 检查图片文件是否存在且格式正确
2. 确认图片文件命名符合 `Main-XX.jpg/png` 格式
3. 检查图片文件大小是否超过 SHEIN 限制

### 页面元素定位失败

**问题**: 填写表单时报错

**解决方案**:
1. SHEIN 卖家中心页面可能已更新，需要检查页面元素选择器
2. 确保网络连接正常，页面已完全加载
3. 适当增加 `delay_max` 配置值以等待页面加载

### 频繁操作被限制

**问题**: 操作过快被系统限制

**解决方案**:
1. 增加 `config.yaml` 中的 `delay_min` 和 `delay_max` 值
2. 减少单次运行的商品数量
3. 分多次运行，每次间隔一段时间
