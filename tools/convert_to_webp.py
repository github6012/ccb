#!/usr/bin/env python3
"""
图片转 WebP 格式工具。

支持将 JPG/PNG/JPEG/BMP/TIFF 图片转换为 WebP 格式，
可同时生成多尺寸版本：full / preview / thumbs / thumbs_mobile。

用法:
    python convert_to_webp.py <输入目录> <输出目录> [--quality 85]

    # 批量转换整个目录
    python convert_to_webp.py ./照片 ./photos

    # 转换单个文件
    python convert_to_webp.py ./照片/何洁.jpg ./photos
"""

import argparse
import os
import sys
from pathlib import Path

try:
    from PIL import Image, ImageOps
except ImportError:
    print("错误: 需要安装 Pillow 库。运行: pip install Pillow")
    sys.exit(1)


# 输出尺寸配置（宽度，保持宽高比）
SIZE_PRESETS = {
    "full": 1200,
    "preview": 800,
    "thumbs": 300,
    "thumbs_mobile": 200,
}

SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".tif", ".webp"}


def convert_image(
    input_path: Path,
    output_dir: Path,
    quality: int = 85,
    sizes: list[str] | None = None,
    base_name: str | None = None,
) -> list[Path]:
    """
    将单张图片转换为 WebP 格式的多尺寸版本。

    参数:
        input_path: 输入图片路径
        output_dir: 输出根目录（内部自动分 full/preview/thumbs/thumbs_mobile 子目录）
        quality: WebP 质量 (1-100)
        sizes: 需要生成的尺寸列表，默认全部
        base_name: 输出文件名（不含扩展名），默认使用输入文件名

    返回:
        生成的文件路径列表
    """
    if sizes is None:
        sizes = list(SIZE_PRESETS.keys())

    if base_name is None:
        base_name = input_path.stem

    img = Image.open(input_path)

    # 自动旋转（处理 EXIF 方向）
    img = ImageOps.exif_transpose(img)

    # 统一转为 RGB（WebP 不支持 CMYK 等模式）
    if img.mode in ("RGBA", "LA", "P", "PA"):
        if img.mode == "P":
            img = img.convert("RGBA")
        # 有透明通道的保留 RGBA，否则转 RGB
        if img.mode == "RGBA":
            has_alpha = img.getchannel("A").getextrema()[0] < 255
            if not has_alpha:
                img = img.convert("RGB")
    elif img.mode not in ("RGB", "RGBA"):
        img = img.convert("RGB")

    output_files = []

    for size_name in sizes:
        target_width = SIZE_PRESETS[size_name]
        sub_dir = output_dir / size_name
        sub_dir.mkdir(parents=True, exist_ok=True)

        # 计算等比缩放
        w_percent = target_width / float(img.size[0])
        target_height = int(float(img.size[1]) * w_percent)

        # 如果原图宽度已经小于目标宽度，不放大
        if img.size[0] <= target_width:
            resized = img.copy()
        else:
            resized = img.resize((target_width, target_height), Image.LANCZOS)

        out_path = sub_dir / f"{base_name}.webp"

        save_kwargs = {"quality": quality, "method": 6}
        if resized.mode == "RGBA":
            save_kwargs["lossless"] = False

        resized.save(str(out_path), "webp", **save_kwargs)
        output_files.append(out_path)

    return output_files


def batch_convert(
    input_dir: Path,
    output_dir: Path,
    quality: int = 85,
    sizes: list[str] | None = None,
    name_map: dict[str, str] | None = None,
) -> dict[str, list[Path]]:
    """
    批量转换目录中的图片。

    参数:
        input_dir: 输入目录
        output_dir: 输出根目录
        quality: WebP 质量
        sizes: 尺寸列表
        name_map: 文件名(不含扩展名) → 输出 basename 的映射，用于重命名

    返回:
        {输入文件名: [输出路径列表]}
    """
    results = {}
    files = sorted(
        f for f in input_dir.iterdir()
        if f.suffix.lower() in SUPPORTED_EXTENSIONS
    )

    for f in files:
        out_name = None
        if name_map:
            out_name = name_map.get(f.stem)
        out_files = convert_image(f, output_dir, quality, sizes, out_name)
        results[f.name] = out_files
        print(f"  {f.name} -> {', '.join(p.name for p in out_files)}")

    return results


def main():
    parser = argparse.ArgumentParser(
        description="图片转 WebP 格式工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python convert_to_webp.py ./照片 ./photos
  python convert_to_webp.py ./照片 ./photos --quality 90
  python convert_to_webp.py photo.jpg ./output --sizes full preview
        """,
    )
    parser.add_argument("input", help="输入图片路径或目录")
    parser.add_argument("output_dir", help="输出根目录")
    parser.add_argument(
        "--quality", "-q", type=int, default=85, help="WebP 质量 (1-100, 默认 85)"
    )
    parser.add_argument(
        "--sizes",
        nargs="+",
        choices=list(SIZE_PRESETS.keys()),
        default=list(SIZE_PRESETS.keys()),
        help="要生成的尺寸 (默认全部)",
    )
    parser.add_argument(
        "--name-map",
        help="JSON 文件路径，包含 {原文件名: 输出basename} 映射",
    )

    args = parser.parse_args()

    input_path = Path(args.input)
    output_dir = Path(args.output_dir)

    if not input_path.exists():
        print(f"错误: 输入路径不存在: {input_path}")
        sys.exit(1)

    name_map = None
    if args.name_map:
        import json
        with open(args.name_map, "r", encoding="utf-8") as f:
            name_map = json.load(f)

    print(f"WebP 质量: {args.quality}")
    print(f"输出尺寸: {', '.join(args.sizes)}")
    print()

    if input_path.is_file():
        out_files = convert_image(input_path, output_dir, args.quality, args.sizes)
        for p in out_files:
            print(f"  -> {p}")
    else:
        print(f"转换目录: {input_path}")
        batch_convert(input_path, output_dir, args.quality, args.sizes, name_map)

    print("\n完成。")


if __name__ == "__main__":
    main()
