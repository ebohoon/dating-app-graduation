"""
프로필 키워드 임베딩 기반 의미론적 유사도 모듈.

'커피' ↔ '카페', '헬스' ↔ '운동' 처럼 문자열이 달라도
의미가 비슷하면 높은 점수를 부여한다.
"""
from __future__ import annotations

import json

import numpy as np
import streamlit as st
from langchain_openai import OpenAIEmbeddings

from _paths import data_path

# 코사인 유사도가 이 값 미만인 키워드 쌍은 "의미 없음" 처리
_SIM_THRESHOLD = 0.70


# ──────────────────────────────────────────────
# 1. 프로필 DB 전체를 한 번만 임베딩 (세션 캐시)
# ──────────────────────────────────────────────
@st.cache_resource(show_spinner="프로필 의미 분석 중… (최초 1회)")
def _profile_bundle():
    """
    profile_db.jsonl 의 모든 keywords 를 임베딩한 뒤 행렬로 반환.
    반환값: (names, kw_texts, emb_matrix, embedder)
    """
    path = data_path("profile_db.jsonl")
    if not path.is_file():
        return None

    names: list[str] = []
    kw_texts: list[str] = []

    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            kws = obj.get("keywords") or []
            names.append(obj.get("name", ""))
            kw_texts.append(" ".join(kws))   # 키워드를 공백으로 연결해 하나의 문장으로

    if not kw_texts:
        return None

    embedder = OpenAIEmbeddings(model="text-embedding-3-small")
    matrix = np.asarray(
        embedder.embed_documents(kw_texts), dtype=np.float32
    )  # shape: (N, dim)
    return names, kw_texts, matrix, embedder


# ──────────────────────────────────────────────
# 2. 검색 키워드별 개별 임베딩 (세션 캐시)
# ──────────────────────────────────────────────
@st.cache_resource(show_spinner=False)
def _get_embedder() -> OpenAIEmbeddings:
    return OpenAIEmbeddings(model="text-embedding-3-small")


def _cosine(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-9))


# ──────────────────────────────────────────────
# 3. 공개 API
# ──────────────────────────────────────────────
def compute_embedding_scores(query_keywords: list[str]) -> dict[str, float]:
    """
    검색 키워드 리스트와 각 프로필 keywords 의 코사인 유사도를 반환.
    반환값: {프로필이름: 유사도(0~1)}

    - 검색 키워드 전체를 하나의 문장으로 붙여 쿼리 벡터 생성
    - 프로필 키워드 행렬과 코사인 유사도 계산
    """
    bundle = _profile_bundle()
    if bundle is None or not query_keywords:
        return {}

    names, _kw_texts, matrix, embedder = bundle

    query_text = " ".join(query_keywords)
    q_vec = np.asarray(
        embedder.embed_query(query_text), dtype=np.float32
    )

    # 행렬 방식으로 한 번에 계산 (속도 최적화)
    q_norm = q_vec / (np.linalg.norm(q_vec) + 1e-9)
    m_norm = matrix / (np.linalg.norm(matrix, axis=1, keepdims=True) + 1e-9)
    sims = m_norm @ q_norm  # shape: (N,)

    return {name: float(sim) for name, sim in zip(names, sims)}


def per_keyword_semantic_matches(
    query_keywords: list[str],
    profile_keywords: list[str],
) -> dict[str, str | None]:
    """
    query_keywords 각각에 대해, profile_keywords 중 의미적으로
    가장 가까운 키워드를 찾아 반환.

    반환값: {검색키워드: 매칭된_프로필키워드 또는 None}
    예: {"커피": "카페", "여행": "여행", "요리": None}

    UI에서 "커피 → 카페 (의미 매칭)" 뱃지를 보여줄 때 사용.
    """
    if not query_keywords or not profile_keywords:
        return {k: None for k in query_keywords}

    embedder = _get_embedder()

    q_vecs = np.asarray(
        embedder.embed_documents(query_keywords), dtype=np.float32
    )  # (Q, dim)
    p_vecs = np.asarray(
        embedder.embed_documents(profile_keywords), dtype=np.float32
    )  # (P, dim)

    # 정규화
    q_norm = q_vecs / (np.linalg.norm(q_vecs, axis=1, keepdims=True) + 1e-9)
    p_norm = p_vecs / (np.linalg.norm(p_vecs, axis=1, keepdims=True) + 1e-9)

    sim_matrix = q_norm @ p_norm.T  # (Q, P)

    result: dict[str, str | None] = {}
    for i, qk in enumerate(query_keywords):
        best_idx = int(np.argmax(sim_matrix[i]))
        best_sim = float(sim_matrix[i, best_idx])
        if best_sim >= _SIM_THRESHOLD:
            result[qk] = profile_keywords[best_idx]
        else:
            result[qk] = None

    return result


def profile_embedding_available() -> bool:
    """임베딩 모듈을 사용할 수 있는지 여부 (JSONL 파일 존재 확인)."""
    return data_path("profile_db.jsonl").is_file()
