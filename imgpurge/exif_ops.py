"""EXIF 操作模块"""

import csv
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from PIL import Image
import piexif
import pillow_heif

from .logger import logger
from .utils import ensure_dir

pillow_heif.register_heif_opener()

PRIVACY_TAGS = [
    "GPSInfo",
    "Make",
    "Model",
    "Software",
    "Artist",
    "Copyright",
    "DateTime",
    "DateTimeOriginal",
    "DateTimeDigitized",
    "ExposureTime",
    "FNumber",
    "ISOSpeedRatings",
    "FocalLength",
    "LensMake",
    "LensModel",
    "LensSerialNumber",
    "BodySerialNumber",
    "OwnerName",
    "UserComment",
    "ImageDescription",
    "HostComputer",
]


def read_exif(file_path: Path) -> Dict:
    """读取图片的 EXIF 信息

    Args:
        file_path: 图片文件路径

    Returns:
        EXIF 信息字典
    """
    try:
        with Image.open(file_path) as img:
            exif_dict = {}
            if "exif" in img.info:
                try:
                    exif_dict = piexif.load(img.info["exif"])
                except Exception:
                    exif_dict = {"raw": img.info["exif"]}
            return exif_dict
    except Exception as e:
        logger.error(f"读取 EXIF 失败 {file_path}: {e}")
        return {}


def clear_exif(file_path: Path, output_path: Optional[Path] = None, dry_run: bool = False) -> bool:
    """清除图片的 EXIF 隐私信息

    Args:
        file_path: 输入图片路径
        output_path: 输出图片路径，None 表示覆盖原图
        dry_run: 是否为预览模式

    Returns:
        是否成功
    """
    if output_path is None:
        output_path = file_path

    if dry_run:
        logger.dry_run(f"将清除 EXIF 信息: {file_path} -> {output_path}")
        return True

    try:
        with Image.open(file_path) as img:
            data = list(img.getdata())
            new_img = Image.new(img.mode, img.size)
            new_img.putdata(data)

            ensure_dir(output_path.parent)

            if file_path.suffix.lower() in [".jpg", ".jpeg"]:
                new_img.save(output_path, "JPEG", quality=95, optimize=True)
            elif file_path.suffix.lower() == ".png":
                new_img.save(output_path, "PNG", optimize=True)
            elif file_path.suffix.lower() == ".webp":
                new_img.save(output_path, "WEBP", quality=95)
            elif file_path.suffix.lower() in [".heic", ".heif"]:
                new_img.save(output_path, "HEIF", quality=95)
            else:
                new_img.save(output_path)

        logger.success(f"已清除 EXIF: {file_path}")
        return True

    except Exception as e:
        logger.error(f"清除 EXIF 失败 {file_path}: {e}")
        return False


def exif_to_dict(exif_data: Dict) -> Dict[str, str]:
    """将 EXIF 数据转换为可序列化的字典

    Args:
        exif_data: piexif 格式的 EXIF 数据

    Returns:
        扁平化的 EXIF 字典
    """
    result = {}

    if not exif_data or "raw" in exif_data:
        return result

    tag_mappings = {
        "0th": piexif.TAGS["0th"],
        "Exif": piexif.TAGS["Exif"],
        "GPS": piexif.TAGS["GPS"],
        "1st": piexif.TAGS["1st"],
    }

    for ifd_name, tags in tag_mappings.items():
        if ifd_name not in exif_data:
            continue
        for tag_id, value in exif_data[ifd_name].items():
            if tag_id in tags:
                tag_name = tags[tag_id]["name"]
                try:
                    if isinstance(value, bytes):
                        value = value.decode("utf-8", errors="ignore")
                    elif isinstance(value, tuple):
                        value = str(value)
                    result[f"{ifd_name}.{tag_name}"] = str(value)
                except Exception:
                    result[f"{ifd_name}.{tag_name}"] = str(value)

    return result


def extract_exif_to_csv(file_paths: List[Path], output_csv: Path, dry_run: bool = False) -> bool:
    """批量提取 EXIF 信息并导出为 CSV

    Args:
        file_paths: 图片文件路径列表
        output_csv: 输出 CSV 文件路径
        dry_run: 是否为预览模式

    Returns:
        是否成功
    """
    if dry_run:
        logger.dry_run(f"将导出 {len(file_paths)} 个文件的 EXIF 信息到: {output_csv}")
        return True

    try:
        all_exif_data = []
        all_keys = set()

        for file_path in file_paths:
            logger.info(f"正在提取: {file_path}")
            exif_data = read_exif(file_path)
            exif_dict = exif_to_dict(exif_data)
            exif_dict["FilePath"] = str(file_path)
            exif_dict["FileName"] = file_path.name
            all_exif_data.append(exif_dict)
            all_keys.update(exif_dict.keys())

        fieldnames = ["FilePath", "FileName"] + sorted([k for k in all_keys if k not in ["FilePath", "FileName"]])

        ensure_dir(output_csv.parent)

        with open(output_csv, "w", newline="", encoding="utf-8-sig") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            for row in all_exif_data:
                writer.writerow(row)

        logger.success(f"EXIF 信息已导出到: {output_csv}")
        return True

    except Exception as e:
        logger.error(f"导出 CSV 失败: {e}")
        return False
