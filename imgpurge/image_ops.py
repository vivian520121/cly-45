"""图片操作模块 - 压缩、水印等"""

from pathlib import Path
from typing import Optional, Tuple

from PIL import Image, ImageDraw, ImageFont
import pillow_heif

from .logger import logger
from .utils import ensure_dir

pillow_heif.register_heif_opener()

WATERMARK_POSITIONS = [
    "top-left",
    "top-center",
    "top-right",
    "center-left",
    "center",
    "center-right",
    "bottom-left",
    "bottom-center",
    "bottom-right",
]


def resize_image(
    file_path: Path,
    output_path: Optional[Path] = None,
    width: Optional[int] = None,
    height: Optional[int] = None,
    quality: int = 85,
    dry_run: bool = False,
) -> bool:
    """调整图片大小

    Args:
        file_path: 输入图片路径
        output_path: 输出图片路径，None 表示覆盖原图
        width: 目标宽度（像素），None 则按比例自适应
        height: 目标高度（像素），None 则按比例自适应
        quality: 输出质量 (1-100)
        dry_run: 是否为预览模式

    Returns:
        是否成功
    """
    if output_path is None:
        output_path = file_path

    if dry_run:
        size_str = f"{width or 'auto'}x{height or 'auto'}"
        logger.dry_run(f"将调整大小: {file_path} -> {output_path} ({size_str}, quality={quality})")
        return True

    try:
        with Image.open(file_path) as img:
            orig_width, orig_height = img.size

            if width and height:
                new_width, new_height = width, height
            elif width:
                ratio = width / orig_width
                new_width, new_height = width, int(orig_height * ratio)
            elif height:
                ratio = height / orig_height
                new_width, new_height = int(orig_width * ratio), height
            else:
                new_width, new_height = orig_width, orig_height

            if new_width >= orig_width and new_height >= orig_height:
                logger.skip(f"目标尺寸大于原图，跳过: {file_path}")
                return True

            resized_img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)

            ensure_dir(output_path.parent)

            ext = file_path.suffix.lower()
            if ext in [".jpg", ".jpeg"]:
                resized_img.save(output_path, "JPEG", quality=quality, optimize=True)
            elif ext == ".png":
                resized_img.save(output_path, "PNG", optimize=True)
            elif ext == ".webp":
                resized_img.save(output_path, "WEBP", quality=quality)
            elif ext in [".heic", ".heif"]:
                resized_img.save(output_path, "HEIF", quality=quality)
            else:
                resized_img.save(output_path)

        logger.success(f"已调整大小: {file_path} ({orig_width}x{orig_height} -> {new_width}x{new_height})")
        return True

    except Exception as e:
        logger.error(f"调整大小失败 {file_path}: {e}")
        return False


def add_watermark(
    file_path: Path,
    output_path: Optional[Path] = None,
    text: str = "",
    font_size: int = 36,
    opacity: float = 0.5,
    position: str = "bottom-right",
    margin: int = 20,
    dry_run: bool = False,
) -> bool:
    """添加文字水印

    Args:
        file_path: 输入图片路径
        output_path: 输出图片路径，None 表示覆盖原图
        text: 水印文字
        font_size: 字体大小
        opacity: 透明度 (0.0-1.0)
        position: 水印位置，见 WATERMARK_POSITIONS
        margin: 边距（像素）
        dry_run: 是否为预览模式

    Returns:
        是否成功
    """
    if output_path is None:
        output_path = file_path

    if not text:
        logger.warning("水印文字为空，跳过")
        return False

    if position not in WATERMARK_POSITIONS:
        logger.error(f"无效的水印位置: {position}，可选值: {', '.join(WATERMARK_POSITIONS)}")
        return False

    if dry_run:
        logger.dry_run(
            f"将添加水印: {file_path} -> {output_path} (text='{text}', pos={position}, opacity={opacity})"
        )
        return True

    try:
        with Image.open(file_path) as img:
            img = img.convert("RGBA")
            overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
            draw = ImageDraw.Draw(overlay)

            try:
                font = ImageFont.truetype("arial.ttf", font_size)
            except Exception:
                try:
                    font = ImageFont.truetype("msyh.ttc", font_size)
                except Exception:
                    font = ImageFont.load_default()

            bbox = draw.textbbox((0, 0), text, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]

            img_width, img_height = img.size

            x, y = _get_watermark_position(
                position, img_width, img_height, text_width, text_height, margin
            )

            alpha = int(255 * opacity)
            draw.text((x, y), text, font=font, fill=(255, 255, 255, alpha))

            combined = Image.alpha_composite(img, overlay)
            combined = combined.convert("RGB") if file_path.suffix.lower() != ".png" else combined

            ensure_dir(output_path.parent)

            ext = file_path.suffix.lower()
            if ext in [".jpg", ".jpeg"]:
                combined.save(output_path, "JPEG", quality=95, optimize=True)
            elif ext == ".png":
                combined.save(output_path, "PNG", optimize=True)
            elif ext == ".webp":
                combined.save(output_path, "WEBP", quality=95)
            elif ext in [".heic", ".heif"]:
                combined.save(output_path, "HEIF", quality=95)
            else:
                combined.save(output_path)

        logger.success(f"已添加水印: {file_path}")
        return True

    except Exception as e:
        logger.error(f"添加水印失败 {file_path}: {e}")
        return False


def _get_watermark_position(
    position: str,
    img_width: int,
    img_height: int,
    text_width: int,
    text_height: int,
    margin: int,
) -> Tuple[int, int]:
    """计算水印位置坐标

    Args:
        position: 位置字符串
        img_width: 图片宽度
        img_height: 图片高度
        text_width: 文字宽度
        text_height: 文字高度
        margin: 边距

    Returns:
        (x, y) 坐标
    """
    if position == "top-left":
        return margin, margin
    elif position == "top-center":
        return (img_width - text_width) // 2, margin
    elif position == "top-right":
        return img_width - text_width - margin, margin
    elif position == "center-left":
        return margin, (img_height - text_height) // 2
    elif position == "center":
        return (img_width - text_width) // 2, (img_height - text_height) // 2
    elif position == "center-right":
        return img_width - text_width - margin, (img_height - text_height) // 2
    elif position == "bottom-left":
        return margin, img_height - text_height - margin
    elif position == "bottom-center":
        return (img_width - text_width) // 2, img_height - text_height - margin
    elif position == "bottom-right":
        return img_width - text_width - margin, img_height - text_height - margin
    else:
        return img_width - text_width - margin, img_height - text_height - margin
