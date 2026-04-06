"""
대화 RAG (FAISS 없이): conv_samples.jsonl → 임베딩 + 키워드 겹침 하이브리드 순위.

샘플 수가 적을 때는 코사인 상위 k개를 그대로 쓰면 맥락과 동떨어진 예시가 섞이기 쉬워,
1) 질의에 토큰 겹침 점수를 섞고 2) 1위 대비 상대적으로 너무 낮은 점수는 제외한다.
"""
from __future__ import annotations

import json
import re
from typing import TYPE_CHECKING

import numpy as np
import streamlit as st
from langchain_openai import OpenAIEmbeddings

from _paths import data_path

if TYPE_CHECKING:
    pass

_TOKEN_RE = re.compile(r"[\w가-힣]{2,}", re.UNICODE)


def _keyword_overlap_score(query: str, doc: str) -> float:
    """질의 토큰이 문서에 등장하는 비율 (0~1). 한글·영단어 2글자 이상."""
    q = set(t.lower() for t in _TOKEN_RE.findall(query or ""))
    if not q:
        return 0.0
    dlow = (doc or "").lower()
    hits = sum(1 for t in q if t in dlow)
    return hits / len(q)


def _rag_query_text(raw: str) -> str:
    """짧은 대화도 임베딩에 도메인 힌트를 붙임."""
    q = (raw or "").strip()
    if not q:
        return "소개팅·첫만남에서 나누는 대화"
    if len(q) < 60:
        return "소개팅·첫만남 대화 맥락:\n" + q
    return q


def _conv_samples_mtime_ns() -> int:
    path = data_path("conv_samples.jsonl")
    try:
        return path.stat().st_mtime_ns
    except OSError:
        return 0


@st.cache_resource(show_spinner="대화 샘플 임베딩을 불러오는 중…")
def _embedding_bundle(_file_mtime_ns: int):
    """JSONL 로드 + 문서 임베딩 행렬. 파일이 바뀌면 mtime으로 캐시 무효화."""
    path = data_path("conv_samples.jsonl")
    if not path.is_file():
        return None
    texts: list[str] = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            t = (obj.get("text") or obj.get("content") or "").strip()
            if t:
                texts.append(t)
    if not texts:
        return None
    emb = OpenAIEmbeddings(model="text-embedding-3-small")
    vecs = np.asarray(emb.embed_documents(texts), dtype=np.float32)
    return texts, vecs, emb


def conv_rag_available() -> bool:
    return data_path("conv_samples.jsonl").is_file()


def retrieve_similar_conversations(query: str, k: int = 4) -> str:
    """현재 대화와 맞는 샘플만 골라 블록 문자열로 반환 (하이브리드 + 상대 컷)."""
    bundle = _embedding_bundle(_conv_samples_mtime_ns())
    if bundle is None:
        return ""
    texts, mat, emb = bundle
    n = len(texts)
    if n == 0:
        return ""

    q_text = _rag_query_text(query)
    q = np.asarray(emb.embed_query(q_text), dtype=np.float32)
    qn = q / (np.linalg.norm(q) + 1e-9)
    mn = mat / (np.linalg.norm(mat, axis=1, keepdims=True) + 1e-9)
    cos = (mn @ qn).astype(np.float64)
    kw = np.array([_keyword_overlap_score(q_text, t) for t in texts], dtype=np.float64)
    # 키워드가 맞으면 주제 일치 가능성↑, 임베딩만으로는 소량 코퍼스에서 오탐이 잦음
    hybrid = 0.55 * cos + 0.45 * kw

    order = np.argsort(-hybrid)
    j0 = int(order[0])
    best_h = float(hybrid[j0])
    best_c = float(cos[j0])

    # 1위는 항상 포함. 나머지는 1위 대비 너무 낮으면 제외 (엉뚱한 예시 감소)
    cut_h = max(0.1, best_h * 0.86)
    cut_c = max(0.17, best_c * 0.78)

    picked: list[int] = [j0]
    for j in order[1:]:
        if len(picked) >= min(k, n):
            break
        jj = int(j)
        if hybrid[jj] >= cut_h and cos[jj] >= cut_c:
            picked.append(jj)

    parts = [f"[참고 대화 예시 {i + 1}]\n{texts[j]}" for i, j in enumerate(picked)]
    return "\n\n---\n\n".join(parts)
