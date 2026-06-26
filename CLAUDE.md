# Text-to-Animation

根据文字描述生成卡通风格图片，并可将图片合成为 PPT。

## 快速开始

1. 安装依赖：`scripts/install.sh`
2. 在 `.env` 中填入 `DASHSCOPE_API_KEY`
3. 在项目根目录创建 `prompts.txt`，每段描述用空行分隔
4. 生成图片：`scripts/generate_images.sh prompts.txt`
5. 生成 PPT：`scripts/generate_ppt.sh`

## 项目结构

- `src/text2anim/` — 核心代码
- `images/` — 生成的图片（按子文件夹组织）
- `ppt/` — 生成的 PPT 文件
- `scripts/` — 运行脚本
