"""配置管理：从 .env 读取 API Key 和项目配置"""

import os
from pathlib import Path

from dotenv import load_dotenv

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent.parent
load_dotenv(PROJECT_ROOT / ".env")

# API 配置（优先读 OPENAI_API_KEY，兼容 DASHSCOPE_API_KEY）
API_KEY = os.getenv("OPENAI_API_KEY") or os.getenv("DASHSCOPE_API_KEY", "")
API_BASE_URL = "https://token-plan.cn-beijing.maas.aliyuncs.com"
IMAGE_API_PATH = "/api/v1/services/aigc/multimodal-generation/generation"
IMAGE_MODEL = "wan2.7-image-pro"

# 目录配置
IMAGES_DIR = PROJECT_ROOT / "images"
PPT_DIR = PROJECT_ROOT / "ppt"
LOGS_DIR = PROJECT_ROOT / "logs"

# 卡通风格 prompt 增强前缀
CARTOON_STYLE_PREFIX = "卡通风格，色彩鲜明，可爱，扁平化设计，"


def validate_config() -> None:
    """校验必要配置是否已填写"""
    if not API_KEY or API_KEY == "xxx":
        raise ValueError(
            "请先在 .env 文件中填写 OPENAI_API_KEY\n"
            f"文件路径: {PROJECT_ROOT / '.env'}"
        )
