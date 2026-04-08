"""
프로필 키워드 임베딩 기반 의미론적 유사도 모듈.

'커피' ↔ '카페', '헬스' ↔ '운동' 처럼 문자열이 달라도
의미가 비슷하면 높은 점수를 부여한다.

임베딩 문서 텍스트는 keywords만이 아니라 bio·직업·라이프스타일·연애/대화 성향·tags를
합친 풍부한 프로필 설명을 사용한다 (exact 키워드 매칭은 ② 페이지 로직이 유지).
"""
from __future__ import annotations

import json

import numpy as np
import streamlit as st
from langchain_openai import OpenAIEmbeddings

from _paths import data_path

# 코사인 유사도가 이 값 미만인 키워드 쌍은 "의미 없음" 처리
_SIM_THRESHOLD = 0.70


def _profile_db_mtime_ns() -> int:
    path = data_path("profile_db.jsonl")
    try:
        return path.stat().st_mtime_ns
    except OSError:
        return 0


def _profile_rich_embed_text(obj: dict) -> str:
    """임베딩용: 자기소개 + 관심 + 생활/연애/대화 성향까지 한 덩어리."""
    chunks: list[str] = []
    job = str(obj.get("job") or "").strip()
    if job:
        chunks.append(f"직업: {job}")
    bio = str(obj.get("bio") or obj.get("intro") or "").strip()
    if bio:
        chunks.append(bio)
    kws = obj.get("keywords") or []
    if isinstance(kws, list) and kws:
        chunks.append("관심 키워드: " + ", ".join(str(x).strip() for x in kws if str(x).strip()))
    interests = obj.get("interests")
    if isinstance(interests, list) and interests:
        chunks.append("관심사: " + ", ".join(str(x) for x in interests if str(x).strip()))
    elif isinstance(interests, str) and interests.strip():
        chunks.append("관심사: " + interests.strip())
    for fld, label in (
        ("lifestyle", "라이프스타일"),
        ("dating_style", "연애 스타일"),
        ("conversation_style", "대화 스타일"),
    ):
        v = obj.get(fld)
        if isinstance(v, str) and v.strip():
            chunks.append(f"{label}: {v.strip()}")
    tags = obj.get("tags")
    if isinstance(tags, list) and tags:
        chunks.append("태그: " + ", ".join(str(t) for t in tags if str(t).strip()))
    elif isinstance(tags, str) and tags.strip():
        chunks.append("태그: " + tags.strip())
    out = "\n".join(chunks).strip()
    return out if out else " "


# ──────────────────────────────────────────────
# 1. 프로필 DB 전체를 한 번만 임베딩 (세션 캐시)
# ──────────────────────────────────────────────
@st.cache_resource(show_spinner="프로필 의미 분석 중… (최초 1회)")
def _profile_bundle(_file_mtime_ns: int):
    """
    profile_db.jsonl 각 행의 풍부 텍스트를 임베딩한 뒤 행렬로 반환.
    반환값: (profile_ids, embed_texts, emb_matrix, embedder)
    """
    path = data_path("profile_db.jsonl")
    if not path.is_file():
        return None

    profile_ids: list[str] = []
    embed_texts: list[str] = []

    with open(path, encoding="utf-8") as f:
        for i, line in enumerate(f):
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            pid = str(obj.get("id") or "").strip() or f"row{i}"
            profile_ids.append(pid)
            embed_texts.append(_profile_rich_embed_text(obj))

    if not embed_texts:
        return None

    embedder = OpenAIEmbeddings(model="text-embedding-3-small")
    matrix = np.asarray(
        embedder.embed_documents(embed_texts), dtype=np.float32
    )  # shape: (N, dim)
    return profile_ids, embed_texts, matrix, embedder


# ──────────────────────────────────────────────
# 2. 검색 키워드별 개별 임베딩 (세션 캐시)
# ──────────────────────────────────────────────
@st.cache_resource(show_spinner=False)
def _get_embedder() -> OpenAIEmbeddings:
    return OpenAIEmbeddings(model="text-embedding-3-small")


# ──────────────────────────────────────────────
# 3. 공개 API
# ──────────────────────────────────────────────
def compute_embedding_scores(query_keywords: list[str]) -> dict[str, float]:
    """
    검색 키워드와 각 프로필(풍부 텍스트 임베딩)의 코사인 유사도.
    반환값: {프로필 id: 유사도(0~1)} — 동명이인이 있어도 id로 구분.
    """
    bundle = _profile_bundle(_profile_db_mtime_ns())
    if bundle is None or not query_keywords:
        return {}

    profile_ids, _embed_texts, matrix, embedder = bundle

    query_text = "소개팅·매칭 관심 키워드: " + " ".join(str(k).strip() for k in query_keywords if str(k).strip())
    q_vec = np.asarray(
        embedder.embed_query(query_text), dtype=np.float32
    )

    q_norm = q_vec / (np.linalg.norm(q_vec) + 1e-9)
    m_norm = matrix / (np.linalg.norm(matrix, axis=1, keepdims=True) + 1e-9)
    sims = m_norm @ q_norm  # shape: (N,)

    return {pid: float(sim) for pid, sim in zip(profile_ids, sims)}


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
