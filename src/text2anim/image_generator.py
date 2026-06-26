"""图像生成模块：调用 wan2.7-image-pro 生成卡通图片"""

import logging
from datetime import datetime
from pathlib import Path

import httpx

from text2anim.config import (
    API_BASE_URL,
    API_KEY,
    CARTOON_STYLE_PREFIX,
    IMAGE_API_PATH,
    IMAGE_MODEL,
    IMAGES_DIR,
    LOGS_DIR,
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


def create_output_folder(name: str | None) -> Path:
    """在 images/ 下创建子文件夹"""
    IMAGES_DIR.mkdir(parents=True, exist_ok=True)

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


def download_image(url: str, save_path: Path) -> None:
    """下载图片到本地"""
    with httpx.Client(timeout=DOWNLOAD_TIMEOUT) as client:
        resp = client.get(url)
        resp.raise_for_status()
        save_path.write_bytes(resp.content)


def call_image_api(prompt: str) -> str | None:
    """调用图像生成 API，返回图片 URL"""
    url = f"{API_BASE_URL}{IMAGE_API_PATH}"
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": IMAGE_MODEL,
        "input": {
            "messages": [
                {
                    "role": "user",
                    "content": [{"text": prompt}],
                }
            ]
        },
        "parameters": {
            "size": "1024*1024",
        },
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


def generate_single_image(prompt: str, index: int, folder: Path) -> Path | None:
    """生成单张图片，返回保存路径"""
    enhanced = enhance_prompt(prompt)
    logger.info("[%d] 正在生成: %s", index + 1, prompt[:50])

    image_url = call_image_api(enhanced)
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


def run_generate_images(prompts_file: str | None, name: str | None) -> None:
    """CLI 入口：从文件读取或交互输入生成图片"""
    setup_logging()
    validate_config()

    if prompts_file:
        prompts = read_prompts(prompts_file)
    else:
        prompts = interactive_input()

    folder = create_output_folder(name)

    logger.info("共 %d 段描述，开始生成图片...", len(prompts))

    success_count = 0
    for i, prompt in enumerate(prompts):
        result = generate_single_image(prompt, i, folder)
        if result:
            success_count += 1

    logger.info(
        "完成！成功 %d/%d 张，保存在: %s",
        success_count, len(prompts), folder,
    )
