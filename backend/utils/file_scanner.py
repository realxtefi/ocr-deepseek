import logging
from dataclasses import dataclass
from pathlib import Path

from backend.pipeline.converter import SUPPORTED_EXTENSIONS, get_file_type

logger = logging.getLogger(__name__)


@dataclass
class FileInfo:
    path: Path
    file_type: str
    size_bytes: int


def scan_path(path: str | Path, recursive: bool = True) -> list[FileInfo]:
    path = Path(path)

    if path.is_file():
        if path.suffix.lower() in SUPPORTED_EXTENSIONS:
            return [FileInfo(
                path=path,
                file_type=get_file_type(path),
                size_bytes=path.stat().st_size,
            )]
        return []

    if not path.is_dir():
        raise FileNotFoundError(f"Path not found: {path}")

    files = []
    pattern = "**/*" if recursive else "*"

    for file_path in sorted(path.glob(pattern)):
        if not file_path.is_file():
            continue
        if file_path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            continue
        files.append(FileInfo(
            path=file_path,
            file_type=get_file_type(file_path),
            size_bytes=file_path.stat().st_size,
        ))

    logger.info(f"Found {len(files)} supported files in {path}")
    return files
