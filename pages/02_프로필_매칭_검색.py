"""
Step ② 프로필 매칭 검색
개선사항:
  A. 매칭 이유 AI 설명
  B. 키워드 전용 vs 하이브리드 비교 탭
  C. 프로필 궁합 레이더 차트
  F. 좋아요 / 관심없음 버튼
"""
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
    USER_MATCH_KEYWORDS_KEY,
)
from _paths import data_path
from _rag_profile import (
    compute_embedding_scores,
    per_keyword_semantic_matches,
    profile_embedding_available,
)
from _ui import render_match_page_styles, render_page_header, render_trust_footer

st.set_page_config(layout="wide", page_icon="💕")
render_match_page_styles()

render_page_header(
    kicker="Step ② · 매칭",
    title="맞는 상대 찾기",
    subtitle="관심 키워드의 **의미**까지 분석합니다. '커피'로 검색하면 '카페'를 키워드로 가진 상대도 찾아줍니다. "
    "나이·성별로 범위를 줄인 뒤 카드에서 **인사말** 또는 **대화 연습**으로 연결하세요.",
)

_me_card = st.session_state.get(USER_AI_PROFILE_KEY)
if isinstance(_me_card, dict) and _me_card.get("display_name"):
    with st.expander("나의 AI 프로필 (①에서 생성됨)", expanded=True):
        st.markdown(
            f"**{_me_card.get('display_name')}** · {_me_card.get('age')}세 · {_me_card.get('gender')} · "
            f"{_me_card.get('location', '')} · {_me_card.get('job', '')}"
        )
        st.caption("관심: " + ", ".join(_me_card.get("keywords") or []))

if "interest_draft" not in st.session_state:
    st.session_state["interest_draft"] = ""
_me = st.session_state.get(USER_AI_PROFILE_KEY)
if isinstance(_me, dict) and _me.get("keywords") and not (st.session_state.get("interest_draft") or "").strip():
    st.session_state["interest_draft"] = ", ".join(_me["keywords"])
else:
    kw_legacy = st.session_state.get(USER_MATCH_KEYWORDS_KEY)
    if kw_legacy and isinstance(kw_legacy, list) and not (st.session_state.get("interest_draft") or "").strip():
        st.session_state["interest_draft"] = ", ".join(kw_legacy)


@st.cache_data
def load_profiles() -> pd.DataFrame:
    path = data_path("profile_db.jsonl")
    return pd.read_json(str(path), lines=True)


profiles = load_profiles()

m1, m2, m3 = st.columns(3)
with m1:
    st.metric("DB 프로필 수", f"{len(profiles)}명")
with m2:
    _df = st.session_state.get(MATCH_RESULTS_DF_KEY)
    if isinstance(_df, pd.DataFrame):
        st.metric("직전 검색 결과", f"{len(_df)}명")
    else:
        st.metric("직전 검색 결과", "—")
with m3:
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

st.markdown('<p class="ux-section-lead">관심 키워드를 입력하세요. 쉼표로 여러 개 입력할 수 있습니다.</p>', unsafe_allow_html=True)
st.markdown('<p class="ux-section-title">빠른 태그</p>', unsafe_allow_html=True)
st.caption("누르면 입력란에 이어 붙습니다.")
qc = st.columns(8)
quick_tags = ["여행", "커피", "독서", "영화", "요리", "음악", "운동", "코딩"]
for i, tag in enumerate(quick_tags):
    with qc[i]:
        if st.button(tag, key=f"quick_{tag}", use_container_width=True):
            cur = st.session_state.get("interest_draft", "").strip()
            parts = [x.strip() for x in cur.split(",") if x.strip()]
            if tag not in parts:
                parts.append(tag)
            st.session_state["interest_draft"] = ", ".join(parts)
            st.rerun()

st.text_input(
    "관심사 입력",
    key="interest_draft",
    placeholder="예: 커피, 여행, 산책 (쉼표로 구분)",
    help="키워드의 의미를 분석하여 비슷한 단어도 매칭됩니다.",
)

with st.form("search_form"):
    st.markdown("##### 검색 조건")
    age_range = st.slider("선호하는 나이대", 20, 50, (20, 30))
    gender_preference = st.radio("성별", ("모두", "남자", "여자"), horizontal=True)
    submitted = st.form_submit_button("검색하기", type="primary", use_container_width=True)


# ════════════════════════════════════════════════════
# 매칭 알고리즘
# ════════════════════════════════════════════════════

def filter_profiles_keyword_only(
    profiles_df: pd.DataFrame,
    interests_list: list[str],
    age_range_tuple: tuple[int, int],
    gender_pref: str,
) -> pd.DataFrame:
    """[B] 기존 키워드 정확 매칭 전용 (비교용)."""
    filtered = profiles_df[
        (profiles_df["age"] >= age_range_tuple[0]) & (profiles_df["age"] <= age_range_tuple[1])
    ].copy()
    if gender_pref != "모두":
        filtered = filtered[filtered["gender"] == gender_pref].copy()
    if not interests_list:
        return filtered.iloc[0:0]

    def count_matches(keywords: list) -> int:
        return sum(1 for interest in interests_list if interest in keywords)

    filtered["match_count"] = filtered["keywords"].apply(count_matches)
    filtered["keyword_score"] = filtered["match_count"].apply(lambda x: x / len(interests_list))
    filtered["emb_score"] = 0.0
    filtered["match_score"] = filtered["keyword_score"]
    filtered["use_embedding"] = False
    return filtered[filtered["match_count"] > 0].sort_values("match_count", ascending=False)


def filter_profiles_hybrid(
    profiles_df: pd.DataFrame,
    interests_list: list[str],
    age_range_tuple: tuple[int, int],
    gender_pref: str,
) -> pd.DataFrame:
    """하이브리드: 키워드 50% + 임베딩 50%."""
    filtered = profiles_df[
        (profiles_df["age"] >= age_range_tuple[0]) & (profiles_df["age"] <= age_range_tuple[1])
    ].copy()
    if gender_pref != "모두":
        filtered = filtered[filtered["gender"] == gender_pref].copy()
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
        THRESHOLD = 0.35
    else:
        filtered["emb_score"] = 0.0
        filtered["match_score"] = filtered["keyword_score"]
        THRESHOLD = 0.0

    result = filtered[filtered["match_score"] >= THRESHOLD].copy()
    result["use_embedding"] = use_embedding
    return result.sort_values("match_score", ascending=False)


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
    interests_text = (st.session_state.get("interest_draft") or "").strip()
    interests = [i.strip() for i in interests_text.split(",") if i.strip()]

    with st.spinner("의미 분석 중… 잠깐만요 🔍"):
        result_hybrid = filter_profiles_hybrid(profiles, interests, age_range, gender_preference)
        result_kw_only = filter_profiles_keyword_only(profiles, interests, age_range, gender_preference)

    st.session_state[MATCH_RESULTS_DF_KEY] = result_hybrid
    st.session_state["_kw_only_results"] = result_kw_only
    st.session_state[MATCH_FILTER_META_KEY] = {
        "interests": interests,
        "age_range": age_range,
        "gender_preference": gender_preference,
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

# [F] 좋아요 / 관심없음 세션 초기화
if "liked_profiles" not in st.session_state:
    st.session_state["liked_profiles"] = set()
if "disliked_profiles" not in st.session_state:
    st.session_state["disliked_profiles"] = set()

liked_set: set[str] = st.session_state["liked_profiles"]
disliked_set: set[str] = st.session_state["disliked_profiles"]

if result_hybrid is not None:
    if result_hybrid.empty and (result_kw_only is None or result_kw_only.empty):
        st.warning("조건에 맞는 프로필이 없어요. 관심사·나이 범위를 바꿔 다시 검색해 보세요.")
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

            # 버튼 행 — tab_prefix 로 탭별 key 충돌 방지
            btn_key = f"{tab_prefix}_{name_str}_{row['age']}"
            bc1, bc2, bc3, bc4 = st.columns([2, 2, 1, 1])
            with bc1:
                if st.button("💌 인사말 만들기", key=f"greet_{btn_key}"):
                    st.session_state[MATCHED_PROFILE_KEY] = profile_dict_from_row(row)
                    st.switch_page("pages/03_인사말_생성.py")
            with bc2:
                if st.button("💬 바로 대화 연습", key=f"chat_{btn_key}", type="primary"):
                    st.session_state[MATCHED_PROFILE_KEY] = profile_dict_from_row(row)
                    st.switch_page("pages/04_대화_도우미.py")
            with bc3:
                # [F] 좋아요
                like_label = "❤️ 취소" if name_str in liked_set else "👍 관심"
                if st.button(like_label, key=f"like_{btn_key}"):
                    if name_str in liked_set:
                        liked_set.discard(name_str)
                    else:
                        liked_set.add(name_str)
                        disliked_set.discard(name_str)
                    st.session_state["liked_profiles"] = liked_set
                    st.rerun()
            with bc4:
                # [F] 관심없음
                dis_label = "🚫 취소" if name_str in disliked_set else "👎 패스"
                if st.button(dis_label, key=f"dis_{btn_key}"):
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
                st.success(
                    f"조건: 관심사 **{', '.join(intr)}** · 나이 **{ar[0]}–{ar[1]}** · 성별 **{gp}** ({mode_label})"
                )
                for _, row in result_hybrid.iterrows():
                    with st.container(border=True):
                        render_card(row, show_enhanced=True, tab_prefix="hyb")

        # ── Tab 2: 키워드만 결과 ────────────────────────
        with tab_kw:
            if result_kw_only is None or result_kw_only.empty:
                st.warning("키워드 정확 매칭 결과가 없습니다. 키워드를 다시 확인하세요.")
            else:
                st.success(
                    f"조건: 관심사 **{', '.join(intr)}** · 나이 **{ar[0]}–{ar[1]}** · 성별 **{gp}** (키워드 일치만)"
                )
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
