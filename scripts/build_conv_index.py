"""
대화 샘플(JSONL) → FAISS 인덱스 생성 → indexes/conv_index/

한 번 실행하면 ④ 대화 도우미의 「비슷한 대화 참고」에 사용됩니다.
OpenAI 임베딩 API가 필요합니다 (비용 소량 발생).

사용:
  cd 프로젝트 루트
  pip install python-dotenv langchain-openai langchain-community faiss-cpu
  python scripts/build_conv_index.py
"""
from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

# 프로젝트 루트
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

try:
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env")
except ImportError:
    pass

from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings

DATA = ROOT / "data" / "conv_samples.jsonl"
OUT = ROOT / "indexes" / "conv_index"


def main() -> None:
    if not DATA.is_file():
        raise SystemExit(f"데이터 파일이 없습니다: {DATA}")

    docs: list[Document] = []
    with open(DATA, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            text = (obj.get("text") or obj.get("content") or "").strip()
            if not text:
                continue
            meta = {k: v for k, v in obj.items() if k not in ("text", "content")}
            docs.append(Document(page_content=text, metadata=meta))

    if not docs:
        raise SystemExit("문서가 비어 있습니다.")

    print(f"문서 {len(docs)}건 임베딩 중… (OpenAI text-embedding-3-small)")
    emb = OpenAIEmbeddings(model="text-embedding-3-small")
    vs = FAISS.from_documents(docs, emb)

    # Windows: 사용자명 등 한글 경로에서 faiss.write_index 가 실패하는 경우가 있어
    # ASCII-only 임시 폴더에 저장 후 복사합니다.
    OUT.parent.mkdir(parents=True, exist_ok=True)
    os.makedirs(OUT, exist_ok=True)
    tmp = Path(tempfile.mkdtemp(prefix="faiss_conv_"))
    try:
        vs.save_local(str(tmp))
        for f in tmp.iterdir():
            if f.is_file():
                shutil.copy2(f, OUT / f.name)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print(f"저장 완료: {OUT}")
    for name in ("index.faiss", "index.pkl"):
        p = OUT / name
        print(f"  {'✓' if p.is_file() else '✗'} {name}")


if __name__ == "__main__":
    main()
