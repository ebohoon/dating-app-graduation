from __future__ import annotations

from pathlib import Path


APP_DIR = Path(__file__).resolve().parent
REPO_DIR = APP_DIR.parent


def asset_path(*parts: str) -> Path:
    return APP_DIR / "assets" / Path(*parts)


def data_path(*parts: str) -> Path:
    return APP_DIR / "data" / Path(*parts)


def index_path(*parts: str) -> Path:
    return APP_DIR / "indexes" / Path(*parts)


def faiss_load_path(folder: Path) -> str:
    """FAISS.load_local 에 넘길 경로 문자열 (Windows 호환)."""
    return str(folder.resolve())

