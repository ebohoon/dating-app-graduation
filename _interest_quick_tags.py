"""
① 프로필 · ② 매칭 공통: 관심 키워드 빠른 태그 줄(동일 UI·동일 세션 키).
"""
from __future__ import annotations

import json
import random
import re
import time

import streamlit as st
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

QUICK_TAGS_BASE = ["여행", "커피", "독서", "영화", "요리", "음악", "운동", "코딩"]

FALLBACK_EXTRA_TAG_POOL = [
    "전시", "러닝", "산책", "사진", "등산", "캠핑", "와인", "맛집",
    "댄스", "악기", "드라마", "웹툰", "게임", "반려동물", "봉사", "테니스",
    "필라테스", "요가", "클라이밍", "스키", "서핑", "독서모임", "보드게임",
    "브런치", "베이킹", "카페투어", "미술", "공연", "뮤지컬", "재테크",
    "언어교환", "스터디", "드라이브", "노래방", "방탈출", "골프", "배드민턴",
]


def _parse_tag_json_array(text: str) -> list[str]:
    raw = (text or "").strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```\w*\n?", "", raw)
        raw = re.sub(r"\n?```\s*$", "", raw).strip()
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, TypeError, ValueError):
        return []
    if not isinstance(data, list):
        return []
    out: list[str] = []
    for x in data:
        s = str(x).strip()
        if 1 <= len(s) <= 14:
            out.append(s)
    return _dedupe_keep_order(out)[:8]


def _dedupe_keep_order(tags: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for t in tags:
        s = str(t).strip()
        if s and s not in seen:
            seen.add(s)
            out.append(s)
    return out


def generate_extra_quick_tags_llm(avoid: set[str], hint: str) -> list[str]:
    model = ChatOpenAI(model="gpt-4o-mini", temperature=0.85)
    avoid_s = ", ".join(sorted(avoid)[:40]) if avoid else "(없음)"
    prompt = ChatPromptTemplate.from_template(
        "소개팅 프로필의 **관심 키워드** 후보를 JSON **문자열 배열**로만 출력하라.\n"
        "규칙:\n"
        "- 정확히 8개.\n"
        "- 각 항목은 한국어 2~6자 정도의 짧은 명사(쉼표·설명 금지).\n"
        "- 아래 금지 목록과 **같거나 거의 같은 의미**인 단어는 쓰지 마라.\n"
        "- 다양한 생활·취미 영역을 섞어라.\n"
        "금지·회피 단어: {avoid}\n"
        "사용자 입력 맥락(참고): {hint}\n"
        '출력 예: ["갤러리","러닝","반려동물"]'
    )
    chain = prompt | model | StrOutputParser()
    text = chain.invoke({"avoid": avoid_s, "hint": (hint or "").strip() or "(없음)"})
    return _parse_tag_json_array(text)


def suggest_extra_quick_tags(avoid: set[str], hint: str) -> list[str]:
    from _ui import openai_key_configured

    tags: list[str] = []
    if openai_key_configured():
        try:
            tags = _dedupe_keep_order(generate_extra_quick_tags_llm(avoid, hint))
        except Exception:
            tags = []
    if len(tags) < 6:
        pool = [t for t in FALLBACK_EXTRA_TAG_POOL if t not in avoid and t not in tags]
        random.seed((int(time.time() * 1000) ^ hash(tuple(sorted(avoid)[:20]))) % (2**32))
        random.shuffle(pool)
        for t in pool:
            tags.append(t)
            if len(tags) >= 8:
                break
    return _dedupe_keep_order(tags)[:8]


def append_tag_to_comma_field(widget_key: str, tag: str) -> None:
    cur = (st.session_state.get(widget_key) or "").strip()
    parts = [x.strip() for x in cur.split(",") if x.strip()]
    if tag not in parts:
        parts.append(tag)
    st.session_state[widget_key] = ", ".join(parts)


def render_interest_quick_tags(*, draft_key: str) -> None:
    """
    빠른 태그 8칸 + 다른 태그 추천. 입력값은 session_state[draft_key] (쉼표 구분 문자열).
    interest_quick_gen / interest_quick_extra_tags 는 ①·② 공유.
    """
    st.markdown('<p class="ux-section-title">빠른 태그</p>', unsafe_allow_html=True)
    st.caption(
        "누르면 아래 관심 키워드 입력란에 이어 붙입니다. **다른 태그 추천**은 같은 줄을 새 태그로 바꿉니다."
    )

    if "interest_quick_gen" not in st.session_state:
        st.session_state["interest_quick_gen"] = 0
    if "interest_quick_extra_tags" not in st.session_state:
        st.session_state["interest_quick_extra_tags"] = []

    _extra_list = st.session_state.get("interest_quick_extra_tags") or []
    _using_extra_row = bool(_extra_list)
    row_tags = list(_extra_list[:8]) if _using_extra_row else list(QUICK_TAGS_BASE)
    _gen_id = int(st.session_state.get("interest_quick_gen", 0))

    qc = st.columns(8)
    for i in range(8):
        with qc[i]:
            if i < len(row_tags):
                tag = row_tags[i]
                _btn_key = f"quick_row_e{_gen_id}_{i}" if _using_extra_row else f"quick_row_b_{i}"
                if st.button(tag, key=_btn_key, use_container_width=True):
                    append_tag_to_comma_field(draft_key, tag)
                    st.rerun()

    if st.button(
        "다른 태그 추천 ✨",
        key="btn_suggest_more_quick_tags",
        use_container_width=True,
        help="입력란·현재 줄 태그와 겹치지 않게 새 태그 8개로 이 줄을 바꿉니다. (API 키가 있으면 AI 생성)",
    ):
        cur_hint = (st.session_state.get(draft_key) or "").strip()
        parts_set = {x.strip() for x in cur_hint.split(",") if x.strip()}
        avoid = parts_set | set(QUICK_TAGS_BASE) | set(st.session_state.get("interest_quick_extra_tags") or [])
        with st.spinner("태그를 만들고 있어요…"):
            try:
                new_tags = suggest_extra_quick_tags(avoid, cur_hint)
                st.session_state["interest_quick_extra_tags"] = new_tags
                st.session_state["interest_quick_gen"] = _gen_id + 1
                st.session_state.pop("_quick_tag_err", None)
            except Exception as e:
                st.session_state["_quick_tag_err"] = str(e)
        st.rerun()

    _err_qt = st.session_state.pop("_quick_tag_err", None)
    if _err_qt:
        st.warning(f"태그 추천 중 오류: {_err_qt}")
