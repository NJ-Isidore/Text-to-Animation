"""CLI 入口：generate-images 和 generate-ppt 两个子命令"""

import argparse
import sys


def main() -> None:
    parser = argparse.ArgumentParser(
        description="文字描述 → 卡通图片 → PPT",
    )
    subparsers = parser.add_subparsers(dest="command", help="可用命令")

    # generate-images 子命令
    img_parser = subparsers.add_parser(
        "generate-images",
        help="根据文字描述生成卡通图片",
    )
    img_parser.add_argument(
        "prompts_file",
        nargs="?",
        default=None,
        help="文字描述文件路径（可选，不传则进入交互输入模式）",
    )
    img_parser.add_argument(
        "--name",
        default=None,
        help="子文件夹名称（默认使用文件名）",
    )
    img_parser.add_argument(
        "--ref",
        nargs="+",
        default=None,
        help="参考图本地路径，支持多张（用于保持人物一致性）",
    )

    # generate-ppt 子命令
    ppt_parser = subparsers.add_parser(
        "generate-ppt",
        help="将图片合成为 PPT",
    )
    ppt_parser.add_argument(
        "--folder",
        default=None,
        help="指定 images/ 下的子文件夹名称",
    )

    args = parser.parse_args()

    if args.command == "generate-images":
        from text2anim.image_generator import run_generate_images
        run_generate_images(args.prompts_file, args.name, args.ref)
    elif args.command == "generate-ppt":
        from text2anim.ppt_builder import run_generate_ppt
        run_generate_ppt(args.folder)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
