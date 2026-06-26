#!/bin/bash
# 安装项目依赖
cd "$(dirname "$0")/.." || exit 1
uv sync
