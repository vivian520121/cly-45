"""Click CLI 主入口"""

import sys
from pathlib import Path
from typing import Optional

import click

from . import __version__
from .logger import logger
from .utils import (
    get_image_files,
    is_processed,
    mark_processed,
    get_output_path,
    ensure_dir,
    SUPPORTED_EXTENSIONS,
)
from .exif_ops import clear_exif, extract_exif_to_csv, read_exif, exif_to_dict
from .image_ops import resize_image, add_watermark, WATERMARK_POSITIONS


def common_options(f):
    """通用选项装饰器"""
    f = click.option(
        "-r",
        "--recursive",
        is_flag=True,
        default=False,
        help="递归处理子目录",
    )(f)
    f = click.option(
        "-o",
        "--output",
        type=click.Path(),
        default=None,
        help="输出目录，不指定则覆盖原图",
    )(f)
    f = click.option(
        "--dry-run",
        is_flag=True,
        default=False,
        help="预览模式，不实际修改文件",
    )(f)
    f = click.option(
        "--skip-processed",
        is_flag=True,
        default=True,
        help="跳过已处理的文件",
    )(f)
    f = click.option(
        "--force",
        is_flag=True,
        default=False,
        help="强制处理，不跳过已处理文件",
    )(f)
    return f


@click.group()
@click.version_option(__version__, "-v", "--version")
def cli():
    """ImgPurge - 图片元数据处理工具

    批量离线清除照片隐私信息，支持 EXIF 清除、图片压缩、水印添加等功能。
    """
    pass


@cli.group()
def exif():
    """EXIF 元数据操作"""
    pass


@exif.command("clear")
@click.argument("path", type=click.Path(exists=True))
@common_options
def exif_clear(path, recursive, output, dry_run, skip_processed, force):
    """清除图片 EXIF 隐私信息

    PATH 为图片文件或目录路径
    """
    image_files = get_image_files(path, recursive)
    if not image_files:
        logger.error(f"未找到支持的图片文件，支持格式: {', '.join(sorted(SUPPORTED_EXTENSIONS))}")
        sys.exit(1)

    logger.info(f"找到 {len(image_files)} 个图片文件")

    input_dir = Path(path).parent if Path(path).is_file() else Path(path)
    output_dir = Path(output) if output else None

    success_count = 0
    for file_path in image_files:
        if not force and skip_processed and is_processed(file_path, output_dir):
            logger.skip(f"已处理过，跳过: {file_path}")
            continue

        file_output = None
        if output_dir:
            file_output = get_output_path(file_path, input_dir, output_dir)

        if clear_exif(file_path, file_output, dry_run):
            success_count += 1
            if not dry_run:
                mark_processed(file_path, output_dir)

    logger.info(f"处理完成: {success_count}/{len(image_files)} 成功")


@exif.command("show")
@click.argument("path", type=click.Path(exists=True, dir_okay=False))
def exif_show(path):
    """显示图片的 EXIF 信息"""
    file_path = Path(path)
    exif_data = read_exif(file_path)
    exif_dict = exif_to_dict(exif_data)

    if not exif_dict:
        logger.info(f"{file_path} 无 EXIF 信息")
        return

    logger.info(f"{file_path} 的 EXIF 信息:")
    for key, value in sorted(exif_dict.items()):
        click.echo(f"  {key}: {value}")


@cli.command()
@click.argument("path", type=click.Path(exists=True))
@click.option(
    "-o",
    "--output",
    type=click.Path(),
    default="exif_report.csv",
    help="输出 CSV 文件路径",
)
@click.option("-r", "--recursive", is_flag=True, default=False, help="递归处理子目录")
@click.option("--dry-run", is_flag=True, default=False, help="预览模式")
def extract(path, output, recursive, dry_run):
    """提取 EXIF 信息导出为 CSV 报表"""
    image_files = get_image_files(path, recursive)
    if not image_files:
        logger.error(f"未找到支持的图片文件")
        sys.exit(1)

    logger.info(f"找到 {len(image_files)} 个图片文件")

    output_csv = Path(output)
    extract_exif_to_csv(image_files, output_csv, dry_run)


@cli.command()
@click.argument("path", type=click.Path(exists=True))
@click.option("-w", "--width", type=int, default=None, help="目标宽度（像素）")
@click.option("-h", "--height", type=int, default=None, help="目标高度（像素）")
@click.option("-q", "--quality", type=int, default=85, help="输出质量 (1-100)")
@common_options
def resize(path, width, height, quality, recursive, output, dry_run, skip_processed, force):
    """批量调整图片大小/压缩

    仅指定宽度或高度时自动保持比例
    """
    if not width and not height:
        logger.error("必须至少指定 --width 或 --height 中的一个")
        sys.exit(1)

    if quality < 1 or quality > 100:
        logger.error("质量参数必须在 1-100 之间")
        sys.exit(1)

    image_files = get_image_files(path, recursive)
    if not image_files:
        logger.error(f"未找到支持的图片文件")
        sys.exit(1)

    logger.info(f"找到 {len(image_files)} 个图片文件")

    input_dir = Path(path).parent if Path(path).is_file() else Path(path)
    output_dir = Path(output) if output else None

    success_count = 0
    for file_path in image_files:
        if not force and skip_processed and is_processed(file_path, output_dir):
            logger.skip(f"已处理过，跳过: {file_path}")
            continue

        file_output = None
        if output_dir:
            file_output = get_output_path(file_path, input_dir, output_dir)

        if resize_image(file_path, file_output, width, height, quality, dry_run):
            success_count += 1
            if not dry_run:
                mark_processed(file_path, output_dir)

    logger.info(f"处理完成: {success_count}/{len(image_files)} 成功")


@cli.command()
@click.argument("path", type=click.Path(exists=True))
@click.option("-t", "--text", required=True, help="水印文字")
@click.option("-s", "--font-size", type=int, default=36, help="字体大小")
@click.option(
    "-a",
    "--opacity",
    type=float,
    default=0.5,
    help="透明度 (0.0-1.0)",
)
@click.option(
    "-p",
    "--position",
    type=click.Choice(WATERMARK_POSITIONS),
    default="bottom-right",
    help="水印位置",
)
@click.option("-m", "--margin", type=int, default=20, help="边距（像素）")
@common_options
def watermark(path, text, font_size, opacity, position, margin, recursive, output, dry_run, skip_processed, force):
    """添加文字水印"""
    if opacity < 0.0 or opacity > 1.0:
        logger.error("透明度参数必须在 0.0-1.0 之间")
        sys.exit(1)

    image_files = get_image_files(path, recursive)
    if not image_files:
        logger.error(f"未找到支持的图片文件")
        sys.exit(1)

    logger.info(f"找到 {len(image_files)} 个图片文件")

    input_dir = Path(path).parent if Path(path).is_file() else Path(path)
    output_dir = Path(output) if output else None

    success_count = 0
    for file_path in image_files:
        if not force and skip_processed and is_processed(file_path, output_dir):
            logger.skip(f"已处理过，跳过: {file_path}")
            continue

        file_output = None
        if output_dir:
            file_output = get_output_path(file_path, input_dir, output_dir)

        if add_watermark(file_path, file_output, text, font_size, opacity, position, margin, dry_run):
            success_count += 1
            if not dry_run:
                mark_processed(file_path, output_dir)

    logger.info(f"处理完成: {success_count}/{len(image_files)} 成功")


@cli.command()
@click.argument("path", type=click.Path(exists=True))
@click.option("--clear-exif/--no-clear-exif", "clear_exif_flag", default=True, help="是否清除 EXIF")
@click.option("-w", "--width", type=int, default=None, help="压缩宽度")
@click.option("-q", "--quality", type=int, default=85, help="压缩质量")
@click.option("-t", "--watermark-text", default=None, help="水印文字")
@common_options
def batch(
    path,
    clear_exif_flag,
    width,
    quality,
    watermark_text,
    recursive,
    output,
    dry_run,
    skip_processed,
    force,
):
    """批量处理：清除EXIF + 压缩 + 水印"""
    image_files = get_image_files(path, recursive)
    if not image_files:
        logger.error(f"未找到支持的图片文件")
        sys.exit(1)

    logger.info(f"找到 {len(image_files)} 个图片文件")

    input_dir = Path(path).parent if Path(path).is_file() else Path(path)
    output_dir = Path(output) if output else None

    success_count = 0
    for file_path in image_files:
        if not force and skip_processed and is_processed(file_path, output_dir):
            logger.skip(f"已处理过，跳过: {file_path}")
            continue

        file_output = None
        if output_dir:
            file_output = get_output_path(file_path, input_dir, output_dir)

        current_input = file_path
        current_output = file_output

        success = True

        if clear_exif_flag:
            if not clear_exif(current_input, current_output, dry_run):
                success = False

        if success and width:
            if not resize_image(current_input, current_output, width=width, quality=quality, dry_run=dry_run):
                success = False

        if success and watermark_text:
            if not add_watermark(current_input, current_output, watermark_text, dry_run=dry_run):
                success = False

        if success:
            success_count += 1
            if not dry_run:
                mark_processed(file_path, output_dir)

    logger.info(f"批量处理完成: {success_count}/{len(image_files)} 成功")


if __name__ == "__main__":
    cli()
