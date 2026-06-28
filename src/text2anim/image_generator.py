"""图像生成模块：调用 wan2.7-image-pro 生成卡通图片"""

import base64
import logging
from datetime import datetime
from pathlib import Path

import httpx
import questionary

from text2anim.config import (
    API_BASE_URL,
    API_KEY,
    CARTOON_STYLE_PREFIX,
    IMAGE_API_PATH,
    IMAGE_MODEL,
    IMAGES_DIR,
    LOGS_DIR,
    REFERENCE_IMAGE_DIR,
    validate_config,
)

logger = logging.getLogger(__name__)

# 图像生成 API 超时时间（秒）
GENERATE_TIMEOUT = 120.0
DOWNLOAD_TIMEOUT = 60.0


def setup_logging() -> None:
    """配置日志输出到 logs/ 目录"""
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    log_file = LOGS_DIR / "generate_images.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )


def read_prompts(file_path: str) -> list[str]:
    """从文本文件读取多段描述（空行分隔）"""
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"找不到文件: {path}")

    content = path.read_text(encoding="utf-8").strip()
    prompts = [p.strip() for p in content.split("\n\n") if p.strip()]

    if not prompts:
        raise ValueError(f"文件为空或没有有效描述: {path}")

    return prompts


def interactive_input() -> list[str]:
    """交互模式：逐条输入描述，空行结束"""
    print("请逐条输入图片描述（每条一句话，直接回车结束输入）：")
    prompts: list[str] = []
    while True:
        line = input(f"  [{len(prompts) + 1}] ").strip()
        if not line:
            break
        prompts.append(line)

    if not prompts:
        raise ValueError("没有输入任何描述")

    return prompts


def create_output_folder(name: str | None, use_existing: bool = False) -> Path:
    """
    在 images/ 下创建或使用子文件夹。

    参数:
        name: 文件夹名称
        use_existing: True 时直接使用已有文件夹，不创建新的
    """
    IMAGES_DIR.mkdir(parents=True, exist_ok=True)

    if use_existing and name:
        folder = IMAGES_DIR / name
        if folder.exists():
            logger.info("使用已有目录: %s", folder)
            return folder

    date_str = datetime.now().strftime("%Y-%m-%d")
    folder_name = f"{date_str}_{name}" if name else date_str

    folder = IMAGES_DIR / folder_name

    # 避免覆盖已有文件夹
    counter = 1
    original = folder_name
    while folder.exists():
        folder_name = f"{original}_{counter}"
        folder = IMAGES_DIR / folder_name
        counter += 1

    folder.mkdir(parents=True)
    logger.info("输出目录: %s", folder)
    return folder


def enhance_prompt(prompt: str) -> str:
    """为原始描述添加卡通风格增强"""
    return CARTOON_STYLE_PREFIX + prompt


def sanitize_filename(text: str, max_len: int = 20) -> str:
    """将描述文本转换为安全的文件名"""
    safe = "".join(c for c in text if c.isalnum() or c in ("_", "-"))
    if len(safe) > max_len:
        safe = safe[:max_len]
    return safe or "image"


def encode_image_to_base64(image_path: Path) -> str:
    """将本地图片编码为 Base64 字符串，供 API content 数组使用"""
    data = image_path.read_bytes()
    b64 = base64.b64encode(data).decode()
    suffix = image_path.suffix.lower().lstrip(".")
    mime = f"image/{'jpeg' if suffix in ('jpg', 'jpeg') else suffix}"
    return f"data:{mime};base64,{b64}"


def download_image(url: str, save_path: Path) -> None:
    """下载图片到本地"""
    with httpx.Client(timeout=DOWNLOAD_TIMEOUT) as client:
        resp = client.get(url)
        resp.raise_for_status()
        save_path.write_bytes(resp.content)


def call_image_api(prompt: str, ref_img_paths: list[Path] | None = None) -> str | None:
    """
    调用图像生成 API，返回图片 URL。

    参数:
        prompt: 增强后的图片描述
        ref_img_paths: 参考图本地路径列表（可选），模型会参考其中的人物特征
    """
    url = f"{API_BASE_URL}{IMAGE_API_PATH}"
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    }

    # 构建 content 数组：text + 可选的多张参考图
    content: list[dict] = [{"text": prompt}]
    if ref_img_paths:
        for img_path in ref_img_paths:
            content.append({"image": encode_image_to_base64(img_path)})

    payload = {
        "model": IMAGE_MODEL,
        "input": {
            "messages": [
                {
                    "role": "user",
                    "content": content,
                }
            ]
        },
        "parameters": {"size": "2048*2048", "watermark": False},
    }

    with httpx.Client(timeout=GENERATE_TIMEOUT) as client:
        resp = client.post(url, json=payload, headers=headers)

    if resp.status_code != 200:
        logger.error("API 返回错误 (status=%d): %s", resp.status_code, resp.text[:200])
        return None

    data = resp.json()
    try:
        image_url = data["output"]["choices"][0]["message"]["content"][0]["image"]
        return image_url
    except (KeyError, IndexError, TypeError) as e:
        logger.error("解析响应失败: %s, 响应: %s", e, str(data)[:300])
        return None


def generate_single_image(
    prompt: str, index: int, folder: Path, ref_img_paths: list[Path] | None = None
) -> Path | None:
    """生成单张图片，返回保存路径"""
    enhanced = enhance_prompt(prompt)
    logger.info("[%d] 正在生成: %s", index + 1, prompt[:50])
    if ref_img_paths:
        names = ", ".join(p.name for p in ref_img_paths)
        logger.info("[%d] 使用参考图: %s", index + 1, names)

    image_url = call_image_api(enhanced, ref_img_paths)
    if not image_url:
        logger.error("[%d] 生成失败", index + 1)
        return None

    # 构造文件名并下载
    desc_part = sanitize_filename(prompt)
    filename = f"{index + 1:02d}_{desc_part}.png"
    save_path = folder / filename

    try:
        download_image(image_url, save_path)
        logger.info("[%d] 已保存: %s", index + 1, save_path.name)
        return save_path
    except Exception as e:
        logger.error("[%d] 下载失败: %s", index + 1, e)
        return None


def _find_reference_images() -> list[Path]:
    """在 reference_images/ 目录下查找所有图片"""
    REFERENCE_IMAGE_DIR.mkdir(parents=True, exist_ok=True)
    image_extensions = {".png", ".jpg", ".jpeg", ".webp"}
    return [
        f for f in sorted(REFERENCE_IMAGE_DIR.iterdir())
        if f.is_file() and f.suffix.lower() in image_extensions
    ]


def select_reference_images(ref_imgs: list[str] | None) -> list[Path] | None:
    """
    选择参考图列表，返回本地路径列表。

    参数:
        ref_imgs: 参考图本地路径列表（可选，由 CLI --ref 传入）
    返回:
        参考图本地路径列表，如果不使用参考图则返回 None
    """
    if ref_imgs:
        paths: list[Path] = []
        for r in ref_imgs:
            path = Path(r)
            if not path.exists():
                logger.error("参考图文件不存在: %s", path)
                return None
            paths.append(path)
        return paths

    # 交互模式：使用 questionary 光标选择
    auto_paths = _find_reference_images()
    if not auto_paths:
        logger.info("reference_images/ 目录下没有找到参考图")
        return None

    # 构建选项列表：每张参考图 + "不使用参考图"
    choices = [
        questionary.Choice(p.name, value=p) for p in auto_paths
    ]
    choices.append(questionary.Choice("不使用参考图", value=None))

    selected = questionary.checkbox(
        "选择参考图（空格勾选，回车确认）:",
        choices=choices,
    ).ask()

    if selected is None:
        raise KeyboardInterrupt("用户取消了选择")

    # 过滤掉"不使用参考图"选项
    paths = [p for p in selected if p is not None]

    if not paths:
        logger.info("未选择参考图，将不使用参考图生成")
        return None

    logger.info("已选择 %d 张参考图", len(paths))
    return paths


def ask_folder_name() -> tuple[str | None, bool]:
    """
    交互模式：光标选择已有文件夹或创建新文件夹。

    返回:
        (文件夹名称, 是否为已有文件夹)
    """
    # 列出 images/ 下已有的子文件夹
    existing: list[Path] = []
    if IMAGES_DIR.exists():
        existing = [f for f in sorted(IMAGES_DIR.iterdir()) if f.is_dir()]

    # 构建选项：已有文件夹 + "创建新文件夹"
    choices: list[questionary.Choice] = [
        questionary.Choice(f.name, value=f.name) for f in existing
    ]
    choices.append(questionary.Choice("创建新文件夹", value="__new__"))

    selected = questionary.select("选择图片文件夹:", choices=choices).ask()
    if selected is None:
        raise KeyboardInterrupt("用户取消了选择")

    if selected == "__new__":
        name = input("请输入新文件夹名称（直接回车使用日期）: ").strip()
        return (name if name else None, False)

    # 选择了已有文件夹
    return (selected, True)


def run_generate_images(
    prompts_file: str | None,
    name: str | None,
    ref_imgs: list[str] | None = None,
) -> None:
    """CLI 入口：从文件读取或交互输入生成图片"""
    setup_logging()
    validate_config()

    # 交互模式：先确定配置项，再输入 prompts
    use_existing = False
    if not prompts_file:
        if not name:
            name, use_existing = ask_folder_name()
        ref_img_paths = select_reference_images(ref_imgs)
        prompts = interactive_input()
    else:
        ref_img_paths = select_reference_images(ref_imgs)
        prompts = read_prompts(prompts_file)

    folder = create_output_folder(name, use_existing)

    logger.info("共 %d 段描述，开始生成图片...", len(prompts))
    if ref_img_paths:
        logger.info(
            "已启用参考图模式（%d 张），人物一致性将得到保持",
            len(ref_img_paths),
        )

    success_count = 0
    for i, prompt in enumerate(prompts):
        result = generate_single_image(prompt, i, folder, ref_img_paths)
        if result:
            success_count += 1

    logger.info(
        "完成！成功 %d/%d 张，保存在: %s",
        success_count, len(prompts), folder,
    )
