"""
대화 RAG (FAISS 없이): conv_samples.jsonl → 임베딩 → 코사인 유사도 상위 k건.

한글 Windows 경로에서 FAISS 파일 쓰기 실패를 피하고, 샘플만으로 동작하게 함.
"""
from __future__ import annotations

import json
from typing import TYPE_CHECKING

import numpy as np
import streamlit as st
from langchain_openai import OpenAIEmbeddings

from _paths import data_path

if TYPE_CHECKING:
    pass


@st.cache_resource(show_spinner="대화 샘플 임베딩을 불러오는 중…")
def _embedding_bundle():
    """JSONL 로드 + 문서 임베딩 행렬 (세션당 1회 API 호출)."""
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
    """현재 대화 맥락과 비슷한 샘플 대화 블록 문자열."""
    bundle = _embedding_bundle()
    if bundle is None:
        return ""
    texts, mat, emb = bundle
    q = np.asarray(emb.embed_query(query or "소개팅 대화"), dtype=np.float32)
    qn = q / (np.linalg.norm(q) + 1e-9)
    mn = mat / (np.linalg.norm(mat, axis=1, keepdims=True) + 1e-9)
    sims = mn @ qn
    idx = np.argsort(-sims)[: min(k, len(texts))]
    parts = [f"[참고 대화 예시 {i + 1}]\n{texts[j]}" for i, j in enumerate(idx)]
    return "\n\n---\n\n".join(parts)
