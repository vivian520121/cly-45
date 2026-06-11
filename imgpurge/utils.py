"""通用工具函数"""

import os
from pathlib import Path
from typing import List, Set
import hashlib

from .logger import logger

SUPPORTED_EXTENSIONS: Set[str] = {".jpg", ".jpeg", ".png", ".webp", ".heic", ".heif"}

PROCESSED_MARKER = ".imgpurge_processed"


def get_image_files(path: str, recursive: bool = False) -> List[Path]:
    """获取指定路径下的所有图片文件

    Args:
        path: 文件或目录路径
        recursive: 是否递归遍历子目录

    Returns:
        图片文件路径列表
    """
    path_obj = Path(path)
    image_files: List[Path] = []

    if path_obj.is_file():
        if path_obj.suffix.lower() in SUPPORTED_EXTENSIONS:
            image_files.append(path_obj)
        return image_files

    if path_obj.is_dir():
        pattern = "**/*" if recursive else "*"
        for file in path_obj.glob(pattern):
            if file.is_file() and file.suffix.lower() in SUPPORTED_EXTENSIONS:
                image_files.append(file)

    return sorted(image_files)


def is_processed(file_path: Path, output_dir: Path = None) -> bool:
    """检查文件是否已处理过

    Args:
        file_path: 原始文件路径
        output_dir: 输出目录（如果有）

    Returns:
        是否已处理
    """
    marker_file = get_marker_path(file_path, output_dir)
    return marker_file.exists()


def mark_processed(file_path: Path, output_dir: Path = None) -> None:
    """标记文件为已处理

    Args:
        file_path: 原始文件路径
        output_dir: 输出目录（如果有）
    """
    marker_file = get_marker_path(file_path, output_dir)
    marker_file.parent.mkdir(parents=True, exist_ok=True)
    marker_file.write_text(file_path.as_posix())


def get_marker_path(file_path: Path, output_dir: Path = None) -> Path:
    """获取标记文件路径

    Args:
        file_path: 原始文件路径
        output_dir: 输出目录（如果有）

    Returns:
        标记文件路径
    """
    file_hash = hashlib.md5(str(file_path).encode()).hexdigest()[:8]
    base_dir = output_dir if output_dir else file_path.parent
    return base_dir / f".{file_path.stem}_{file_hash}{PROCESSED_MARKER}"


def get_output_path(file_path: Path, input_dir: Path, output_dir: Path) -> Path:
    """获取输出文件路径，保持相对目录结构

    Args:
        file_path: 原始文件路径
        input_dir: 输入目录
        output_dir: 输出目录

    Returns:
        输出文件路径
    """
    try:
        rel_path = file_path.relative_to(input_dir)
    except ValueError:
        rel_path = file_path.name
    return output_dir / rel_path


def ensure_dir(path: Path) -> None:
    """确保目录存在

    Args:
        path: 目录路径
    """
    path.mkdir(parents=True, exist_ok=True)
