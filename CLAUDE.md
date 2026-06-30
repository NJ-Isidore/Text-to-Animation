# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

文字描述 → 卡通风格图片 → PPT 幻灯片的命令行工具。通过阿里云 DashScope 多模态 API（qwen-image-2.0-pro 模型）生成图片，再用 python-pptx 合成 16:9 宽屏 PPT。

## 常用命令

```bash
# 安装依赖
scripts/install.sh

# 生成图片（从文件读取，prompts 用空行分隔）
scripts/generate_images.sh prompts.txt

# 生成图片（交互输入模式）
scripts/generate_images.sh

# 指定子文件夹名称
scripts/generate_images.sh prompts.txt --name my-story

# 使用参考图保持人物一致性
scripts/generate_images.sh prompts.txt --ref reference_images/character.png

# 生成 PPT（自动选择/交互选择图片文件夹）
scripts/generate_ppt.sh

# 指定图片文件夹
scripts/generate_ppt.sh --folder 2026-06-27_my-story
```

## 环境配置

`.env` 文件中填写 API Key，支持两种变量名（优先读 `OPENAI_API_KEY`）：

```
OPENAI_API_KEY=sk-xxx
# 或
DASHSCOPE_API_KEY=sk-xxx
```

## 架构

```
main.py (CLI)
  ├── generate-images → image_generator.py
  │     读取 prompts → prompt_enhancer 增强 → 调用 DashScope API → 下载图片
  │     可选：选择参考图 → Base64 编码 → 放入 content 数组传入 API
  │     └── prompt_enhancer.py
  │           方案A 结构化重组 → 方案B LLM改写(qwen3.7-max) → 添加卡通前缀
  └── generate-ppt  → ppt_builder.py
        扫描 images/ 子文件夹 → 选择文件夹 → python-pptx 合成幻灯片
```

**五个核心模块：**

- `config.py` — 集中管理所有配置：API 端点（`token-plan.cn-beijing.maas.aliyuncs.com`）、图像模型名、文本模型名（`qwen3.7-max`）、目录路径。通过 `validate_config()` 在运行前校验。
- `prompt_enhancer.py` — Prompt 增强。`restructure_prompt()` 本地结构化重组（人物隔离、场景补全、构图建议）；`rewrite_prompt_with_llm()` 调用 qwen3.7-max 改写为丰富视觉描述；`enhance_prompt()` 串联两步并添加卡通前缀。
- `image_generator.py` — 图像生成。`call_image_api()` 支持可选参考图（Base64 编码放入 content 数组）保持人物一致性；`select_reference_images()` 交互选择参考图（支持多选）。
- `ppt_builder.py` — PPT 合成。使用空白布局（slide_layouts[6]），图片居中最大 10×6 英寸，底部附标题文字（从文件名提取）。
- `main.py` — 仅做 argparse 路由（`--ref` 参考图参数），延迟导入子模块以保持启动速度。

**关键数据流：**

- prompts 文件格式：段落间用**空行**分隔（`\n\n`），每段对应一张图片
- 图片命名格式：`{序号}_{描述摘要}.png`，序号用于 PPT 排序
- PPT 输出到 `ppt/{文件夹名}.pptx`

## 技术栈

- Python ≥3.12，构建工具 uv（uv_build 后端）
- 依赖：httpx（API 请求）、python-pptx（PPT 生成）、python-dotenv（环境变量）、questionary（交互式 CLI 选择）
- API：阿里云 DashScope — 图像生成 `qwen-image-2.0-pro`（输出 2048×2048，支持参考图）；文本生成 `qwen3.7-max`（OpenAI 兼容格式，用于 Prompt 增强）
