"""
Step ② 프로필 매칭 검색
개선사항:
  A. 매칭 이유 AI 설명
  B. 키워드 전용 vs 하이브리드 비교 탭
  C. 프로필 궁합 레이더 차트
  F. 좋아요 / 관심없음 버튼
"""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from _match_context import (
    MATCHED_PROFILE_KEY,
    MATCH_FILTER_META_KEY,
    MATCH_RESULTS_DF_KEY,
    USER_AI_PROFILE_KEY,
    USER_KEYWORDS_SEED_KEY,
    USER_MATCH_KEYWORDS_KEY,
    journey_can_access,
    opposite_gender_for_match,
)
from _paths import data_path
from _rag_profile import (
    compute_embedding_scores,
    per_keyword_semantic_matches,
    profile_embedding_available,
)
from _ui import render_match_page_styles, render_page_header, render_trust_footer

st.set_page_config(page_title="통합 데이팅 AI", layout="wide", page_icon="💕")
render_match_page_styles()

_gate_ok, _gate_msg = journey_can_access("match")
if not _gate_ok:
    st.error(_gate_msg)
    st.page_link("pages/01_AI_프로필_생성.py", label="① AI 프로필로 이동", use_container_width=True)
    render_trust_footer()
    st.stop()

_me_for_gender = st.session_state.get(USER_AI_PROFILE_KEY)
_opposite_gender = (
    opposite_gender_for_match(str(_me_for_gender.get("gender", "")))
    if isinstance(_me_for_gender, dict)
    else None
)
_gender_preference = _opposite_gender if _opposite_gender else "모두"

render_page_header(
    kicker="Step ② · 매칭",
    title="맞는 상대 찾기",
    subtitle="관심 키워드는 **① 프로필과 동일**하게 쓰입니다. **의미** 기반 매칭과 함께 나이·직업·소개글 등으로 좁힐 수 있습니다. "
    "①에서 고른 **내 성별** 기준으로 **이성** 후보만 검색합니다.",
)

_me_card = st.session_state.get(USER_AI_PROFILE_KEY)
if isinstance(_me_card, dict) and _me_card.get("display_name"):
    with st.expander("나의 AI 프로필 (①에서 생성됨)", expanded=True):
        st.markdown(
            f"**{_me_card.get('display_name')}** · {_me_card.get('age')}세 · {_me_card.get('gender')} · "
            f"{_me_card.get('location', '')} · {_me_card.get('job', '')}"
        )
        st.caption("관심: " + ", ".join(_me_card.get("keywords") or []))

def _match_interests_from_step1() -> list[str]:
    """① AI 프로필 키워드 → (없으면) 구버전 키워드 → (없으면) ① 시드 문자열."""
    me = st.session_state.get(USER_AI_PROFILE_KEY)
    if isinstance(me, dict):
        kw = me.get("keywords") or []
        if isinstance(kw, list) and kw:
            return [str(x).strip() for x in kw if str(x).strip()]
    leg = st.session_state.get(USER_MATCH_KEYWORDS_KEY)
    if isinstance(leg, list) and leg:
        return [str(x).strip() for x in leg if str(x).strip()]
    seed = (st.session_state.get(USER_KEYWORDS_SEED_KEY) or "").strip()
    if seed:
        return [x.strip() for x in seed.replace("，", ",").split(",") if x.strip()]
    return []


@st.cache_data
def load_profiles() -> pd.DataFrame:
    path = data_path("profile_db.jsonl")
    return pd.read_json(str(path), lines=True)


profiles = load_profiles()

if "liked_profiles" not in st.session_state:
    st.session_state["liked_profiles"] = set()
if "disliked_profiles" not in st.session_state:
    st.session_state["disliked_profiles"] = set()

if st.button("검색 결과 지우기", help="목록만 초기화합니다"):
    for k in (MATCH_RESULTS_DF_KEY, MATCH_FILTER_META_KEY,
              "_kw_only_results", "liked_profiles", "disliked_profiles"):
        st.session_state.pop(k, None)
    st.rerun()

if profile_embedding_available():
    st.info(
        "🧠 **의미 기반 매칭 활성화** — 문자가 달라도 비슷한 의미의 키워드를 가진 상대를 찾아드립니다.\n\n"
        "예) `커피` → `카페`, `헬스` → `운동`, `음식` → `요리`",
        icon="✨",
    )

_match_kw = _match_interests_from_step1()
st.markdown('<p class="ux-section-title">매칭에 쓰는 관심 키워드</p>', unsafe_allow_html=True)
if _match_kw:
    st.info("① 프로필과 **동일한** 키워드로 관심사 매칭합니다: **" + "**, **".join(_match_kw) + "**")
else:
    st.warning(
        "①에서 **관심 키워드**를 넣고 **프로필 반영**을 해 주세요. "
        "(키워드가 없으면 매칭 점수를 계산할 수 없습니다.)"
    )

with st.form("search_form"):
    st.markdown("##### 검색 조건")
    age_range = st.slider("선호하는 상대 나이대", 20, 50, (20, 30))
    if _opposite_gender:
        st.caption(f"상대 성별: **{_opposite_gender}** 만 표시 (① 프로필의 내 성별 기준 이성)")
    else:
        st.warning("① 프로필에 성별(남/여)이 없어 전체 성별로 검색합니다. 프로필을 다시 만들어 주세요.")

    st.markdown("###### 상대 프로필 텍스트 조건 (선택)")
    job_needle = st.text_input(
        "직업에 포함",
        placeholder="예: 디자인, 개발, 의사 (비우면 조건 없음)",
        help="상대 `직업` 필드에 이 문자열이 **포함**된 사람만 남깁니다.",
    )
    bio_needle = st.text_input(
        "자기소개에 포함",
        placeholder="예: 여행, 운동, 책 (비우면 조건 없음)",
        help="상대 소개글에 이 문자열이 **포함**된 사람만 남깁니다.",
    )

    _nk = len(_match_kw)
    _max_min = max(_nk, 1)
    min_exact = st.slider(
        "최소 정확 키워드 일치 개수",
        min_value=0,
        max_value=_max_min,
        value=0 if _nk == 0 else 1,
        help="0 = 제한 없음. ①에서 넣은 관심 키워드가 상대 태그와 **글자 그대로** 겹치는 개수 하한입니다.",
    )

    semantic_floor = st.slider(
        "의미 매칭 포함 기준 (하이브리드)",
        min_value=0.15,
        max_value=0.55,
        value=0.35,
        step=0.05,
        help="낮출수록 의미만 비슷해도 후보에 더 많이 남습니다. (임베딩이 꺼져 있으면 효과 없음)",
    )

    sort_mode = st.radio(
        "정렬",
        options=["match", "age_near"],
        format_func=lambda x: "매칭 점수 높은 순" if x == "match" else "내 나이와 가까운 순",
        horizontal=True,
    )

    max_show = st.selectbox(
        "한 번에 보여 줄 최대 인원",
        options=[10, 20, 30, 50, 0],
        format_func=lambda n: "전체" if n == 0 else f"{n}명까지",
        index=1,
    )

    hide_passed = st.checkbox(
        "👎 패스한 사람은 결과에서 제외",
        value=False,
        help="이번 세션에서 관심없음을 누른 상대는 목록에 나오지 않습니다.",
    )

    submitted = st.form_submit_button("검색하기", type="primary", use_container_width=True)


# ════════════════════════════════════════════════════
# 매칭 알고리즘
# ════════════════════════════════════════════════════

def _apply_profile_text_filters(
    df: pd.DataFrame,
    job_needle: str,
    bio_needle: str,
) -> pd.DataFrame:
    out = df.copy()
    j = (job_needle or "").strip()
    b = (bio_needle or "").strip()
    if j:
        out = out[out["job"].astype(str).str.contains(j, case=False, na=False, regex=False)]
    if b:
        out = out[out["bio"].astype(str).str.contains(b, case=False, na=False, regex=False)]
    return out


def filter_profiles_keyword_only(
    profiles_df: pd.DataFrame,
    interests_list: list[str],
    age_range_tuple: tuple[int, int],
    gender_pref: str,
    *,
    job_needle: str = "",
    bio_needle: str = "",
    min_exact_matches: int = 0,
) -> pd.DataFrame:
    """[B] 기존 키워드 정확 매칭 전용 (비교용)."""
    filtered = profiles_df[
        (profiles_df["age"] >= age_range_tuple[0]) & (profiles_df["age"] <= age_range_tuple[1])
    ].copy()
    if gender_pref != "모두":
        filtered = filtered[filtered["gender"] == gender_pref].copy()
    filtered = _apply_profile_text_filters(filtered, job_needle, bio_needle)
    if not interests_list:
        return filtered.iloc[0:0]

    def count_matches(keywords: list) -> int:
        return sum(1 for interest in interests_list if interest in keywords)

    filtered["match_count"] = filtered["keywords"].apply(count_matches)
    filtered["keyword_score"] = filtered["match_count"].apply(lambda x: x / len(interests_list))
    filtered["emb_score"] = 0.0
    filtered["match_score"] = filtered["keyword_score"]
    filtered["use_embedding"] = False
    result = filtered[filtered["match_count"] > 0].copy()
    if min_exact_matches > 0:
        result = result[result["match_count"] >= min_exact_matches]
    return result.sort_values("match_count", ascending=False)


def filter_profiles_hybrid(
    profiles_df: pd.DataFrame,
    interests_list: list[str],
    age_range_tuple: tuple[int, int],
    gender_pref: str,
    *,
    job_needle: str = "",
    bio_needle: str = "",
    hybrid_threshold: float = 0.35,
    min_exact_matches: int = 0,
) -> pd.DataFrame:
    """하이브리드: 키워드 50% + 임베딩 50%."""
    filtered = profiles_df[
        (profiles_df["age"] >= age_range_tuple[0]) & (profiles_df["age"] <= age_range_tuple[1])
    ].copy()
    if gender_pref != "모두":
        filtered = filtered[filtered["gender"] == gender_pref].copy()
    filtered = _apply_profile_text_filters(filtered, job_needle, bio_needle)
    if not interests_list:
        return filtered.iloc[0:0]

    def exact_count(keywords: list) -> int:
        return sum(1 for interest in interests_list if interest in keywords)

    filtered["match_count"] = filtered["keywords"].apply(exact_count)
    filtered["keyword_score"] = filtered["match_count"].apply(lambda x: x / len(interests_list))

    emb_scores: dict[str, float] = {}
    use_embedding = False
    try:
        if profile_embedding_available():
            emb_scores = compute_embedding_scores(interests_list)
            use_embedding = bool(emb_scores)
    except Exception:
        pass

    if use_embedding:
        filtered["emb_score"] = filtered["name"].map(emb_scores).fillna(0.0).clip(0.0, 1.0)
        filtered["match_score"] = 0.5 * filtered["keyword_score"] + 0.5 * filtered["emb_score"]
        threshold = float(hybrid_threshold)
    else:
        filtered["emb_score"] = 0.0
        filtered["match_score"] = filtered["keyword_score"]
        threshold = 0.0

    result = filtered[filtered["match_score"] >= threshold].copy()
    if min_exact_matches > 0:
        result = result[result["match_count"] >= min_exact_matches]
    result["use_embedding"] = use_embedding
    return result.sort_values("match_score", ascending=False)


def _sort_match_results(
    df: pd.DataFrame | None,
    mode: str,
    user_age: int | None,
) -> pd.DataFrame | None:
    if df is None or df.empty:
        return df
    out = df.copy()
    if mode == "age_near" and user_age is not None:
        try:
            ua = int(user_age)
            out["_age_dist"] = (out["age"].astype(int) - ua).abs()
            out = out.sort_values(["_age_dist", "match_score"], ascending=[True, False]).drop(
                columns=["_age_dist"]
            )
        except (TypeError, ValueError, KeyError):
            out = out.sort_values("match_score", ascending=False)
    else:
        out = out.sort_values("match_score", ascending=False)
    return out


def _drop_disliked_names(df: pd.DataFrame | None, disliked: set[str]) -> pd.DataFrame | None:
    if df is None or df.empty or not disliked:
        return df
    return df[~df["name"].astype(str).isin(disliked)].copy()


def _limit_rows(df: pd.DataFrame | None, max_rows: int) -> pd.DataFrame | None:
    if df is None or df.empty or max_rows <= 0:
        return df
    if len(df) <= max_rows:
        return df
    return df.head(max_rows).copy()


# ════════════════════════════════════════════════════
# [A] 매칭 이유 AI 설명
# ════════════════════════════════════════════════════

@st.cache_data(show_spinner=False)
def generate_match_reason(
    interests: tuple[str, ...],
    profile_name: str,
    profile_keywords: tuple[str, ...],
    profile_job: str,
    hybrid_pct: int,
) -> str:
    """왜 이 프로필이 추천됐는지 LLM이 2문장으로 설명 (캐시)."""
    model = ChatOpenAI(model="gpt-4o-mini", temperature=0.3)
    prompt = ChatPromptTemplate.from_template(
        "사용자의 관심사는 [{interests}]이다. "
        "{name}({job})의 키워드는 [{keywords}]이며 {score}% 점수로 매칭됐다. "
        "왜 이 사람이 잘 맞는지 **2문장**으로 자연스러운 한국어로 설명하라. "
        "알고리즘·점수 언급 금지. 공통 관심사와 대화 잠재력 위주로."
    )
    result = (prompt | model).invoke({
        "interests": ", ".join(interests),
        "name": profile_name,
        "job": profile_job,
        "keywords": ", ".join(profile_keywords),
        "score": hybrid_pct,
    })
    return result.content


# ════════════════════════════════════════════════════
# [C] 궁합 레이더 차트
# ════════════════════════════════════════════════════

def compute_radar_scores(
    user_interests: list[str],
    profile_row: pd.Series,
    emb_score: float,
) -> dict[str, int]:
    profile_kws: list[str] = profile_row["keywords"]
    if hasattr(profile_kws, "tolist"):
        profile_kws = profile_kws.tolist()

    # ① 관심사 일치
    overlap = sum(1 for k in user_interests if k in profile_kws)
    interest_match = min(100, int(overlap / max(len(user_interests), 1) * 100))

    # ② 의미 유사도 (임베딩)
    semantic_sim = int(min(emb_score, 1.0) * 100)

    # ③ 연령 적합도
    me = st.session_state.get(USER_AI_PROFILE_KEY)
    user_age = me.get("age", 28) if isinstance(me, dict) else 28
    age_diff = abs(user_age - int(profile_row["age"]))
    if age_diff == 0:
        age_compat = 100
    elif age_diff <= 2:
        age_compat = 90
    elif age_diff <= 5:
        age_compat = 75
    elif age_diff <= 8:
        age_compat = 55
    else:
        age_compat = 30

    # ④ 대화 주제 풍부도 (합집합 키워드 수)
    combined = set(user_interests) | set(profile_kws)
    topic_richness = min(100, int(len(combined) / 15 * 100))

    # ⑤ 프로필 완성도 (bio 길이 기준)
    bio_len = len(str(profile_row.get("bio", "") or ""))
    completeness = min(100, int(bio_len / 120 * 100))

    return {
        "관심사 일치": interest_match,
        "의미 유사도": semantic_sim,
        "연령 적합도": age_compat,
        "대화 주제 풍부도": topic_richness,
        "프로필 완성도": completeness,
    }


def render_radar_chart(scores: dict[str, int], name: str):
    categories = list(scores.keys())
    values = list(scores.values())
    categories_closed = categories + [categories[0]]
    values_closed = values + [values[0]]

    fig = go.Figure(
        data=go.Scatterpolar(
            r=values_closed,
            theta=categories_closed,
            fill="toself",
            name=name,
            line_color="#e11d48",
            fillcolor="rgba(225, 29, 72, 0.18)",
        )
    )
    fig.update_layout(
        polar=dict(
            radialaxis=dict(visible=True, range=[0, 100], tickfont=dict(size=9)),
            angularaxis=dict(tickfont=dict(size=11)),
        ),
        showlegend=False,
        height=280,
        margin=dict(l=50, r=50, t=30, b=30),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    return fig


# ════════════════════════════════════════════════════
# 검색 실행
# ════════════════════════════════════════════════════

if submitted:
    interests = _match_interests_from_step1()
    _me_state = st.session_state.get(USER_AI_PROFILE_KEY)
    user_age_for_sort: int | None = None
    if isinstance(_me_state, dict) and _me_state.get("age") is not None:
        try:
            user_age_for_sort = int(_me_state["age"])
        except (TypeError, ValueError):
            user_age_for_sort = None

    _raw_dis = st.session_state.get("disliked_profiles")
    disliked_for_filter: set[str] = set(_raw_dis) if _raw_dis else set()

    with st.spinner("의미 분석 중… 잠깐만요 🔍"):
        result_hybrid = filter_profiles_hybrid(
            profiles,
            interests,
            age_range,
            _gender_preference,
            job_needle=(job_needle or "").strip(),
            bio_needle=(bio_needle or "").strip(),
            hybrid_threshold=float(semantic_floor),
            min_exact_matches=int(min_exact),
        )
        result_kw_only = filter_profiles_keyword_only(
            profiles,
            interests,
            age_range,
            _gender_preference,
            job_needle=(job_needle or "").strip(),
            bio_needle=(bio_needle or "").strip(),
            min_exact_matches=int(min_exact),
        )

    if hide_passed:
        result_hybrid = _drop_disliked_names(result_hybrid, disliked_for_filter)
        result_kw_only = _drop_disliked_names(result_kw_only, disliked_for_filter)

    result_hybrid = _sort_match_results(result_hybrid, sort_mode, user_age_for_sort)
    result_kw_only = _sort_match_results(result_kw_only, sort_mode, user_age_for_sort)

    result_hybrid = _limit_rows(result_hybrid, int(max_show))
    result_kw_only = _limit_rows(result_kw_only, int(max_show))

    st.session_state[MATCH_RESULTS_DF_KEY] = result_hybrid
    st.session_state["_kw_only_results"] = result_kw_only
    st.session_state[MATCH_FILTER_META_KEY] = {
        "interests": interests,
        "age_range": age_range,
        "gender_preference": _gender_preference,
        "job_needle": (job_needle or "").strip(),
        "bio_needle": (bio_needle or "").strip(),
        "min_exact_matches": int(min_exact),
        "semantic_floor": float(semantic_floor),
        "sort_mode": sort_mode,
        "max_show": int(max_show),
        "hide_passed": bool(hide_passed),
    }


def profile_dict_from_row(r: pd.Series) -> dict:
    kw = r["keywords"]
    if hasattr(kw, "tolist"):
        kw = kw.tolist()
    elif isinstance(kw, tuple):
        kw = list(kw)
    elif not isinstance(kw, list):
        kw = []
    return {
        "name": str(r["name"]),
        "age": int(r["age"]) if pd.notna(r["age"]) else 0,
        "gender": str(r["gender"]),
        "job": str(r["job"]),
        "bio": str(r["bio"]),
        "keywords": [str(x) for x in kw],
    }


# ════════════════════════════════════════════════════
# 결과 렌더링 — [B] 탭 구성
# ════════════════════════════════════════════════════

result_hybrid = st.session_state.get(MATCH_RESULTS_DF_KEY)
result_kw_only = st.session_state.get("_kw_only_results")
meta = st.session_state.get(MATCH_FILTER_META_KEY, {})
intr: list[str] = meta.get("interests", [])
ar = meta.get("age_range", (20, 30))
gp = meta.get("gender_preference", "모두")
_meta_job = (meta.get("job_needle") or "").strip()
_meta_bio = (meta.get("bio_needle") or "").strip()
_meta_min_ex = int(meta.get("min_exact_matches") or 0)
_meta_sem = float(meta.get("semantic_floor") or 0.35)
_meta_sort = meta.get("sort_mode") or "match"
_meta_max = int(meta.get("max_show") or 0)
_meta_hide = bool(meta.get("hide_passed"))

def _match_conditions_caption() -> str:
    parts = [
        f"관심 키워드 **{', '.join(intr) if intr else '(없음)'}**",
        f"나이 **{ar[0]}–{ar[1]}**",
        f"성별 **{gp}**",
    ]
    if _meta_job:
        parts.append(f"직업 포함「{_meta_job}」")
    if _meta_bio:
        parts.append(f"소개 포함「{_meta_bio}」")
    if _meta_min_ex > 0:
        parts.append(f"정확 일치 ≥{_meta_min_ex}개")
    if _meta_sem != 0.35:
        parts.append(f"의미 기준 {_meta_sem:.2f}")
    if _meta_sort == "age_near":
        parts.append("정렬: 나이 가까운 순")
    if _meta_max > 0:
        parts.append(f"상한 {_meta_max}명")
    if _meta_hide:
        parts.append("패스 제외")
    return " · ".join(parts)

liked_set: set[str] = st.session_state["liked_profiles"]
disliked_set: set[str] = st.session_state["disliked_profiles"]

if result_hybrid is not None:
    if result_hybrid.empty and (result_kw_only is None or result_kw_only.empty):
        st.warning(
            "조건에 맞는 프로필이 없어요. ① 키워드·**프로필 반영**을 확인하거나, "
            "나이·직업·소개글·최소 일치 개수·의미 기준을 완화해 다시 검색해 보세요."
        )
    else:
        use_emb = (
            bool(result_hybrid.get("use_embedding", pd.Series([False])).iloc[0])
            if not result_hybrid.empty and "use_embedding" in result_hybrid.columns
            else False
        )

        tab_hybrid, tab_kw, tab_compare = st.tabs([
            f"🔀 하이브리드 결과 ({len(result_hybrid)}명)",
            f"🔤 키워드만 결과 ({len(result_kw_only) if result_kw_only is not None else 0}명)",
            "📊 비교 분석",
        ])

        # ── 공통 카드 렌더 함수 ──────────────────────────
        def render_card(row: pd.Series, show_enhanced: bool = True, tab_prefix: str = "h"):
            """show_enhanced=True → A·C·F 기능 포함, False → 기본 카드.
            tab_prefix: 탭별 고유 prefix (버튼 key 중복 방지)."""
            profile_kws: list[str] = row["keywords"]
            if hasattr(profile_kws, "tolist"):
                profile_kws = profile_kws.tolist()

            hybrid_pct = int(round(float(row.get("match_score", 0)) * 100))
            exact_cnt = int(row.get("match_count", 0))
            emb_score = float(row.get("emb_score", 0.0))
            name_str = str(row["name"])

            # 점수 색상
            if hybrid_pct >= 75:
                score_color = "#16a34a"
            elif hybrid_pct >= 50:
                score_color = "#d97706"
            else:
                score_color = "#6b7280"

            score_badge = (
                f'<span style="background:{score_color};color:#fff;'
                f'border-radius:6px;padding:2px 10px;font-size:0.85rem;font-weight:700;">'
                f"🎯 {hybrid_pct}% 매칭</span>"
            )

            # [F] 좋아요/관심없음 아이콘 표시
            fav_icon = " ❤️" if name_str in liked_set else (" 🚫" if name_str in disliked_set else "")

            st.markdown(
                f"##### {name_str}{fav_icon} · {row['age']}세 · {row['gender']} &nbsp; {score_badge}",
                unsafe_allow_html=True,
            )

            if show_enhanced:
                sc1, sc2 = st.columns(2)
                with sc1:
                    st.caption(f"키워드 정확 일치: {exact_cnt}/{max(len(intr),1)}개")
                    st.progress(float(row.get("keyword_score", 0)))
                with sc2:
                    if use_emb:
                        st.caption(f"의미 유사도: {int(emb_score * 100)}%")
                        st.progress(emb_score)

            st.markdown(f"**직업:** {row['job']}")
            with st.expander("자기소개 보기", expanded=False):
                st.write(row["bio"])

            # 키워드 뱃지 (정확/의미 구분)
            sem_map: dict[str, str | None] = {}
            if show_enhanced and use_emb and intr:
                try:
                    sem_map = per_keyword_semantic_matches(intr, profile_kws)
                except Exception:
                    pass

            matched_via_sem: set[str] = {
                pk for qk, pk in sem_map.items() if pk and pk not in intr
            }
            kw_parts: list[str] = []
            for kw in profile_kws:
                if kw in intr:
                    kw_parts.append(f"**🏷 {kw}**")
                elif kw in matched_via_sem:
                    kw_parts.append(f"〰️ {kw}")
                else:
                    kw_parts.append(kw)

            kw_caption = "관심 키워드: " + " · ".join(kw_parts)
            sem_explains = [
                f"`{qk}` → `{pk}`"
                for qk, pk in sem_map.items()
                if pk and pk not in intr
            ]
            if sem_explains:
                kw_caption += "  \n💡 의미 매칭: " + ", ".join(sem_explains)
            st.caption(kw_caption)

            if show_enhanced:
                # [A] 매칭 이유 AI 설명
                with st.expander("🤔 왜 추천됐나요? (AI 설명)"):
                    reason_key = f"_reason_{name_str}_{hybrid_pct}"
                    if reason_key not in st.session_state:
                        if st.button("설명 생성", key=f"reason_btn_{tab_prefix}_{name_str}_{hybrid_pct}"):
                            with st.spinner("AI가 이유를 분석 중…"):
                                try:
                                    reason = generate_match_reason(
                                        tuple(intr),
                                        name_str,
                                        tuple(profile_kws),
                                        str(row["job"]),
                                        hybrid_pct,
                                    )
                                    st.session_state[reason_key] = reason
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"설명 생성 실패: {e}")
                    if reason_key in st.session_state:
                        st.info(st.session_state[reason_key])

                # [C] 궁합 레이더 차트
                with st.expander("💑 궁합 분석 (레이더 차트)"):
                    radar_scores = compute_radar_scores(intr, row, emb_score)
                    avg_score = int(sum(radar_scores.values()) / len(radar_scores))
                    st.caption(f"종합 궁합 점수: **{avg_score}점** / 100")
                    fig = render_radar_chart(radar_scores, name_str)
                    st.plotly_chart(fig, use_container_width=True)
                    radar_cols = st.columns(len(radar_scores))
                    for i, (dim, val) in enumerate(radar_scores.items()):
                        with radar_cols[i]:
                            st.metric(dim, f"{val}점")

            # 버튼 행 — 순서: ③ 인사말 → ④ 대화는 ③ 이후. 열 3개·좁은 gap 으로 한 덩어리처럼 배치
            btn_key = f"{tab_prefix}_{name_str}_{row['age']}"
            try:
                bc1, bc2, bc3 = st.columns([2.4, 1, 1], gap="small")
            except TypeError:
                bc1, bc2, bc3 = st.columns([2.4, 1, 1])
            with bc1:
                if st.button(
                    "💌 인사말 만들기",
                    key=f"greet_{btn_key}",
                    type="primary",
                    use_container_width=True,
                ):
                    st.session_state[MATCHED_PROFILE_KEY] = profile_dict_from_row(row)
                    st.switch_page("pages/03_인사말_생성.py")
            with bc2:
                like_label = "❤️ 취소" if name_str in liked_set else "👍 관심"
                if st.button(like_label, key=f"like_{btn_key}", use_container_width=True):
                    if name_str in liked_set:
                        liked_set.discard(name_str)
                    else:
                        liked_set.add(name_str)
                        disliked_set.discard(name_str)
                    st.session_state["liked_profiles"] = liked_set
                    st.rerun()
            with bc3:
                dis_label = "🚫 취소" if name_str in disliked_set else "👎 패스"
                if st.button(dis_label, key=f"dis_{btn_key}", use_container_width=True):
                    if name_str in disliked_set:
                        disliked_set.discard(name_str)
                    else:
                        disliked_set.add(name_str)
                        liked_set.discard(name_str)
                    st.session_state["disliked_profiles"] = disliked_set
                    st.rerun()

        # ── Tab 1: 하이브리드 결과 ──────────────────────
        with tab_hybrid:
            if result_hybrid.empty:
                st.warning("하이브리드 매칭 결과가 없습니다.")
            else:
                mode_label = "의미 유사도 + 키워드 혼합 순" if use_emb else "키워드 매칭 순"
                st.success(f"조건: {_match_conditions_caption()} — {mode_label}")
                for _, row in result_hybrid.iterrows():
                    with st.container(border=True):
                        render_card(row, show_enhanced=True, tab_prefix="hyb")

        # ── Tab 2: 키워드만 결과 ────────────────────────
        with tab_kw:
            if result_kw_only is None or result_kw_only.empty:
                st.warning("키워드 정확 매칭 결과가 없습니다. 키워드를 다시 확인하세요.")
            else:
                st.success(f"조건: {_match_conditions_caption()} — 키워드 일치만")
                for _, row in result_kw_only.iterrows():
                    with st.container(border=True):
                        render_card(row, show_enhanced=False, tab_prefix="kw")

        # ── Tab 3: 비교 분석 ────────────────────────────
        with tab_compare:
            st.subheader("📊 하이브리드 vs 키워드 전용 비교")

            hybrid_names = set(result_hybrid["name"].tolist()) if not result_hybrid.empty else set()
            kw_names = set(result_kw_only["name"].tolist()) if (result_kw_only is not None and not result_kw_only.empty) else set()

            only_hybrid = hybrid_names - kw_names
            only_kw = kw_names - hybrid_names
            both = hybrid_names & kw_names

            col_a, col_b, col_c = st.columns(3)
            with col_a:
                st.metric("두 방식 모두 포함", f"{len(both)}명")
            with col_b:
                st.metric("🆕 하이브리드만 추가 발굴", f"{len(only_hybrid)}명",
                          delta=f"+{len(only_hybrid)}" if only_hybrid else None,
                          delta_color="normal")
            with col_c:
                st.metric("키워드 전용에만 있음", f"{len(only_kw)}명")

            if only_hybrid:
                st.markdown("#### 하이브리드가 새로 발굴한 상대 (의미 매칭 덕분)")
                st.caption("키워드가 정확히 일치하지 않아도 의미 유사도로 찾아낸 사람들입니다.")
                for name in only_hybrid:
                    row_data = result_hybrid[result_hybrid["name"] == name].iloc[0]
                    pct = int(round(float(row_data["match_score"]) * 100))
                    emb_pct = int(float(row_data.get("emb_score", 0)) * 100)
                    st.success(f"**{name}** — 하이브리드 {pct}% | 의미 유사도 {emb_pct}%")

            # 전체 비교 테이블
            st.markdown("#### 전체 비교 테이블")
            all_names = hybrid_names | kw_names
            compare_rows = []
            for name in all_names:
                h_row = result_hybrid[result_hybrid["name"] == name]
                k_row = result_kw_only[result_kw_only["name"] == name] if result_kw_only is not None else pd.DataFrame()
                h_pct = int(round(float(h_row["match_score"].iloc[0]) * 100)) if not h_row.empty else "—"
                k_pct = int(round(float(k_row["match_score"].iloc[0]) * 100)) if not k_row.empty else "—"
                compare_rows.append({
                    "이름": name,
                    "하이브리드 점수": f"{h_pct}%" if h_pct != "—" else "미포함",
                    "키워드 전용 점수": f"{k_pct}%" if k_pct != "—" else "미포함",
                    "비고": "🆕 의미 매칭" if name in only_hybrid else ("📌 공통" if name in both else "키워드만"),
                })
            if compare_rows:
                st.dataframe(pd.DataFrame(compare_rows), use_container_width=True, hide_index=True)

        # [F] 관심 목록 요약
        if liked_set or disliked_set:
            st.divider()
            fl1, fl2 = st.columns(2)
            with fl1:
                if liked_set:
                    st.markdown(f"❤️ **관심 있음** ({len(liked_set)}명): " + ", ".join(liked_set))
            with fl2:
                if disliked_set:
                    st.markdown(f"🚫 **패스** ({len(disliked_set)}명): " + ", ".join(disliked_set))

render_trust_footer()
