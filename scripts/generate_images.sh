#!/bin/bash
# 根据文字描述生成卡通图片
# 用法: ./scripts/generate_images.sh [prompts文件] [--name 子文件夹名称] [--ref 参考图路径...]
# 不传文件参数则进入交互输入模式
# --ref: 参考图路径，支持多张，用于保持人物一致性
cd "$(dirname "$0")/.." || exit 1

uv run text2anim generate-images "$@"
