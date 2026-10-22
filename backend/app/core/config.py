import os
from dataclasses import dataclass
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parent.parent.parent


@dataclass
class Settings:
    data_dir: Path

    @property
    def db_path(self) -> Path:
        return self.data_dir / "ledger.db"

    @property
    def db_url(self) -> str:
        return f"sqlite:///{self.db_path}"

    @property
    def upload_root(self) -> Path:
        return self.data_dir / "uploads"


def make_settings(data_dir: str | None = None) -> Settings:
    dd = data_dir or os.environ.get("LEDGER_DATA_DIR", str(BACKEND_ROOT / "data"))
    return Settings(data_dir=Path(dd))
