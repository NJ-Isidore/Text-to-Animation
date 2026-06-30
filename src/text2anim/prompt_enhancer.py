"""Prompt 增强模块：结构化重组 + LLM 改写，提升图像生成质量"""

import logging
import re

import httpx

from text2anim.config import (
    API_BASE_URL,
    API_KEY,
    TEXT_API_PATH,
    TEXT_MODEL,
)

logger = logging.getLogger(__name__)

# LLM 改写超时时间（秒）
LLM_TIMEOUT = 60.0

# 卡通风格前缀（最终拼接到输出开头）
CARTOON_PREFIX = "卡通风格插画，色彩鲜明，可爱Q版，扁平化设计，线条简洁，无写实纹理，"

# LLM 系统提示词
SYSTEM_PROMPT = """你是一个专业的图像描述改写助手。将结构化的场景描述改写为适合图像生成模型的详细视觉描述。

核心风格要求：**必须生成卡通风格**，禁止写实风格。所有描述都要服务于卡通插画的视觉效果。

要求：
1. 保留所有关键元素（人物、服装、场景物件），不可遗漏
2. 用丰富的视觉细节扩展描述（颜色、材质、光影、氛围）
3. 明确标注人物的空间位置和朝向关系
4. 确保每个人的服装描述紧跟该人物，不要混淆
5. 输出为一段流畅的中文描述，不要分段
6. 不要添加原描述中不存在的人物或重要元素
7. 使用卡通/插画风格的描述词（如"圆润的脸庞"、"简洁的色块"、"夸张的表情"），避免写实词汇（如"真实质感"、"照片级"、"超高清"）"""

# ---- 方案A：本地结构化重组 ----

# 人物关键词
CHARACTER_KEYWORDS = [
    "男生", "女生", "男孩", "女孩", "男人", "女人",
    "男主", "女主", "他", "她", "我", "老婆", "老公",
]

def _detect_characters(prompt: str) -> list[str]:
    """检测 prompt 中出现的人物"""
    return [kw for kw in CHARACTER_KEYWORDS if kw in prompt]


def _split_sentences(text: str) -> list[str]:
    """按中文标点拆分句子"""
    parts = re.split(r'[,，。；;！!？?\n]+', text)
    return [s.strip() for s in parts if s.strip()]


def _associate_segments(
    sentences: list[str], characters: list[str]
) -> dict[str, list[str]]:
    """将句子片段关联到对应人物，无法关联的归入 _scene"""
    result: dict[str, list[str]] = {c: [] for c in characters}
    result["_scene"] = []

    for sent in sentences:
        matched = False
        for char in characters:
            if char in sent:
                result[char].append(sent)
                matched = True
                break
        if not matched:
            result["_scene"].append(sent)

    return result


# 场景物件关键词
SCENE_KEYWORDS = [
    "沙发", "茶几", "电视", "桌子", "椅子", "床",
    "窗户", "门", "墙", "地板", "地毯", "灯",
    "书", "花瓶", "画", "冰箱", "厨房", "阳台",
    "树", "花", "草", "天空", "云", "太阳", "月亮",
]


def _detect_scene(prompt: str) -> list[str]:
    """检测 prompt 中提到的场景物件"""
    return [kw for kw in SCENE_KEYWORDS if kw in prompt]


def _suggest_composition(prompt: str) -> str:
    """根据描述内容建议构图方式"""
    if any(kw in prompt for kw in ["特写", "近景", "脸"]):
        return "特写构图，聚焦人物面部表情"
    if any(kw in prompt for kw in ["全景", "远景", "大场景"]):
        return "全景构图，展示完整场景"
    if any(kw in prompt for kw in ["半身", "上半身"]):
        return "半身构图"
    return "中景构图，展示人物和环境"


def restructure_prompt(prompt: str) -> str:
    """
    方案A：本地结构化重组。

    将原始描述拆分为人物独立描述段 + 场景描述 + 构图指导，
    降低模型对多人物属性的混淆。
    """
    characters = _detect_characters(prompt)
    sentences = _split_sentences(prompt)

    if not characters:
        # 无人物场景，仅补充构图
        composition = _suggest_composition(prompt)
        scene = _detect_scene(prompt)
        parts = [f"【画面】{prompt}"]
        if scene:
            parts.append(f"【场景元素】{'、'.join(scene)}")
        parts.append(f"【构图】{composition}")
        return "\n".join(parts)

    # 多人物场景：隔离每个人物的描述
    segments = _associate_segments(sentences, characters)
    parts: list[str] = []

    for char in characters:
        desc = "，".join(segments[char]) if segments[char] else char
        parts.append(f"【{char}】{desc}")

    if segments["_scene"]:
        scene_desc = "，".join(segments["_scene"])
        parts.append(f"【场景】{scene_desc}")

    scene_objs = _detect_scene(prompt)
    if scene_objs:
        parts.append(f"【场景元素】{'、'.join(scene_objs)}")

    composition = _suggest_composition(prompt)
    parts.append(f"【构图】{composition}")

    return "\n".join(parts)


# ---- 方案B：LLM 改写 ----


def rewrite_prompt_with_llm(structured_prompt: str) -> str:
    """
    方案B：调用 qwen3.7-max 将结构化 prompt 改写为丰富的视觉描述。

    使用 OpenAI 兼容 API 格式。失败时回退返回原始输入。
    """
    url = f"{API_BASE_URL}{TEXT_API_PATH}"
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": TEXT_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"请改写以下场景描述：\n\n{structured_prompt}"},
        ],
        "temperature": 0.7,
        "max_tokens": 500,
    }

    try:
        with httpx.Client(timeout=LLM_TIMEOUT) as client:
            resp = client.post(url, json=payload, headers=headers)
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]
    except httpx.HTTPStatusError as e:
        logger.warning("LLM 改写失败 (HTTP %d): %s", e.response.status_code, str(e)[:200])
        return structured_prompt
    except (KeyError, IndexError, TypeError) as e:
        logger.warning("LLM 响应解析失败: %s", e)
        return structured_prompt
    except Exception as e:
        logger.warning("LLM 改写异常: %s", e)
        return structured_prompt


# ---- 串联入口 ----


def enhance_prompt(prompt: str) -> str:
    """
    两步 Prompt 增强：结构化重组 → LLM 改写 → 添加卡通前缀。

    流程：原始描述 → 方案A 结构化 → 方案B LLM改写 → 卡通前缀 → 输出
    """
    # 方案A：本地结构化
    structured = restructure_prompt(prompt)
    logger.info("结构化结果:\n%s", structured)

    # 方案B：LLM 改写
    rewritten = rewrite_prompt_with_llm(structured)
    logger.info("LLM 改写结果: %s", rewritten[:100])

    # 添加卡通风格前缀
    return CARTOON_PREFIX + rewritten
