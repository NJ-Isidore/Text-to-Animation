#!/bin/bash
# 将图片合成为 PPT
# 用法: ./scripts/generate_ppt.sh [--folder 子文件夹名称]
cd "$(dirname "$0")/.." || exit 1

uv run text2anim generate-ppt "$@"
