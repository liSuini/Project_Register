import mimetypes
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO


class StorageError(Exception):
    pass


@dataclass
class StoredFile:
    original_name: str
    stored_path: str
    size: int
    mime: str | None


class LocalFilesystemStorage:
    """附件本机存储：{root}/{project_id}/{uuid}{ext}，原名仅记录元数据（ADR-0003）。"""

    def __init__(self, root: Path):
        self.root = Path(root)

    def save(self, fileobj: BinaryIO, filename: str, project_id: int) -> StoredFile:
        original = Path(filename.replace("\\", "/")).name  # 去路径成分、防注入
        ext = Path(original).suffix[:20]
        rel = f"{project_id}/{uuid.uuid4().hex}{ext}"
        dest = self.root / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        content = fileobj.read()
        if isinstance(content, str):
            content = content.encode("utf-8")
        dest.write_bytes(content)
        return StoredFile(original_name=original, stored_path=rel,
                          size=len(content), mime=mimetypes.guess_type(original)[0])

    def open_path(self, stored_path: str) -> Path:
        root = self.root.resolve()
        p = (self.root / stored_path).resolve()
        if root != p and root not in p.parents:
            raise StorageError("非法存储路径")
        return p

    def remove(self, stored_path: str) -> None:
        try:
            self.open_path(stored_path).unlink(missing_ok=True)
        except (StorageError, OSError):
            pass  # 物理缺失容忍：以元数据为准
