#!/bin/bash
# 根据文字描述生成卡通图片
# 用法: ./scripts/generate_images.sh [prompts文件] [--name 子文件夹名称]
# 不传文件参数则进入交互输入模式
cd "$(dirname "$0")/.." || exit 1

uv run text2anim generate-images "$@"
