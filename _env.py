"""
선택: 프로젝트 루트 `.env` 파일에 `OPENAI_API_KEY` 가 있으면 환경 변수로 불러옵니다.
(`python-dotenv` 설치 시에만 동작 — `pip install python-dotenv`)
"""
from __future__ import annotations

_loaded = False


def load_optional_dotenv() -> None:
    """한 번만 실행. `.env` 가 있으면 OS 환경에 키를 넣어 LangChain/OpenAI가 읽게 함."""
    global _loaded
    if _loaded:
        return
    _loaded = True
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    from pathlib import Path

    root = Path(__file__).resolve().parent
    env_path = root / ".env"
    if env_path.is_file():
        load_dotenv(env_path, override=False)
