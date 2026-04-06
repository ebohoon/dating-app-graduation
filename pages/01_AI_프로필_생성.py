"""
① 관심 키워드 + 상세 입력 → 기본 정보는 그대로 반영, 자기소개·목적·이상형·라이프스타일만 AI 다듬기.
[G] 프로필 매력도 점수 기능 추가
"""
from __future__ import annotations

import streamlit as st
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate, HumanMessagePromptTemplate
from langchain_openai import ChatOpenAI
from openai import AuthenticationError
from pydantic import BaseModel, Field

from _interest_quick_tags import render_interest_quick_tags
from _match_context import (
    PF_INPUT_AGE,
    PF_INPUT_BIO_DRAFT,
    PF_INPUT_DATING_GOAL,
    PF_INPUT_DISPLAY_NAME,
    PF_INPUT_GENDER,
    PF_INPUT_IDEAL,
    PF_INPUT_JOB,
    PF_INPUT_LIFESTYLE,
    PF_INPUT_LOCATION,
    USER_AI_PROFILE_KEY,
    USER_KEYWORDS_SEED_KEY,
    USER_SELF_INTRO_KEY,
    apply_user_ai_profile_to_step1_form,
    mark_step1_form_synced_with_profile,
    maybe_restore_step1_form_from_saved_profile,
)
from _ui import (
    JOURNEY_PROFILE,
    openai_key_configured,
    render_page_header,
    render_page_shell,
    render_trust_footer,
)

# 프로필 반영 직후: 위젯이 그려지기 전에만 session_state[PF_*] 를 바꿀 수 있음 → 다음 실행 초반에 동기화
_PENDING_SYNC_FORM_KEY = "_pending_apply_profile_to_form"
_SHOW_PROFILE_OK_KEY = "_show_profile_saved_toast"


class ProfileTextRefine(BaseModel):
    """사용자 초안을 바탕으로 다듬은 네 구역만 LLM이 반환."""

    bio: str = Field(description="자기소개: 사용자 초안의 사실·톤 유지, 문장만 다듬기. 3~6문장 분량")
    dating_goal: str = Field(description="만남·연애 목적: 1~2문장")
    ideal_partner: str = Field(description="선호 상대: 2~3문장")
    lifestyle_summary: str = Field(description="라이프스타일: 2~4문장")


# ── [G] 매력도 분석 모델 ────────────────────────────────────
class ProfileScore(BaseModel):
    bio_score: int = Field(description="자기소개 매력도 0~100. 구체적이고 개성 있을수록 높음")
    keyword_diversity: int = Field(description="키워드 다양성 0~100. 넓고 풍부할수록 높음")
    goal_clarity: int = Field(description="연애 목적 명확성 0~100. 구체적일수록 높음")
    ideal_specificity: int = Field(description="이상형 구체성 0~100. 막연하지 않을수록 높음")
    overall: int = Field(description="종합 매력도 0~100")
    improvements: list[str] = Field(description="개선 제안 2~3개. 구체적이고 실행 가능하게")
    strengths: list[str] = Field(description="잘된 점 1~2개")


@st.cache_data(show_spinner=False)
def score_profile(
    bio: str,
    dating_goal: str,
    ideal_partner: str,
    lifestyle_summary: str,
    keywords_str: str,
) -> dict:
    """프로필 매력도를 LLM이 채점 (캐시 적용)."""
    model = ChatOpenAI(model="gpt-4o-mini", temperature=0.2)
    parser = JsonOutputParser(pydantic_object=ProfileScore)
    fmt = parser.get_format_instructions()

    prompt = ChatPromptTemplate.from_template(
        "소개팅 앱 프로필을 평가하라. 엄격하게, 하지만 건설적으로.\n\n"
        "자기소개: {bio}\n"
        "연애 목적: {goal}\n"
        "선호 상대: {ideal}\n"
        "라이프스타일: {lifestyle}\n"
        "키워드: {keywords}\n\n"
        "{format_instructions}"
    )
    chain = prompt.partial(format_instructions=fmt) | model | parser
    return chain.invoke({
        "bio": bio,
        "goal": dating_goal,
        "ideal": ideal_partner,
        "lifestyle": lifestyle_summary,
        "keywords": keywords_str,
    })


def _ensure_pf_defaults() -> None:
    if USER_KEYWORDS_SEED_KEY not in st.session_state:
        st.session_state[USER_KEYWORDS_SEED_KEY] = ""
    if PF_INPUT_DISPLAY_NAME not in st.session_state:
        st.session_state[PF_INPUT_DISPLAY_NAME] = ""
    if PF_INPUT_AGE not in st.session_state:
        st.session_state[PF_INPUT_AGE] = 28
    if PF_INPUT_GENDER not in st.session_state:
        st.session_state[PF_INPUT_GENDER] = "남자"
    elif st.session_state[PF_INPUT_GENDER] not in ("남자", "여자"):
        st.session_state[PF_INPUT_GENDER] = "남자"
    if PF_INPUT_LOCATION not in st.session_state:
        st.session_state[PF_INPUT_LOCATION] = ""
    if PF_INPUT_JOB not in st.session_state:
        st.session_state[PF_INPUT_JOB] = ""
    if PF_INPUT_BIO_DRAFT not in st.session_state:
        st.session_state[PF_INPUT_BIO_DRAFT] = ""
    if PF_INPUT_DATING_GOAL not in st.session_state:
        st.session_state[PF_INPUT_DATING_GOAL] = ""
    if PF_INPUT_IDEAL not in st.session_state:
        st.session_state[PF_INPUT_IDEAL] = ""
    if PF_INPUT_LIFESTYLE not in st.session_state:
        st.session_state[PF_INPUT_LIFESTYLE] = ""


def _split_keywords(raw: str) -> list[str]:
    return [x.strip() for x in (raw or "").replace("，", ",").split(",") if x.strip()]


def validate_profile_inputs(st0) -> list[str]:
    """입력 조건 위반 시 한국어 메시지 리스트."""
    err: list[str] = []

    raw_kw = (st0.session_state.get(USER_KEYWORDS_SEED_KEY) or "").strip()
    kw_parts = _split_keywords(raw_kw)
    if len(kw_parts) < 2:
        err.append("관심 키워드: **쉼표로 구분해 2개 이상** 입력해 주세요. (각 1~14자)")
    if len(kw_parts) > 20:
        err.append("관심 키워드: **20개 이하**로 입력해 주세요.")
    for k in kw_parts:
        if len(k) > 14:
            err.append(f"관심 키워드「{k[:12]}…」: **14자 이하**로 짧게 나눠 주세요.")

    name = (st0.session_state.get(PF_INPUT_DISPLAY_NAME) or "").strip()
    if not name:
        err.append("이름(표시명): **1~20자**로 입력해 주세요.")
    elif len(name) > 20:
        err.append("이름(표시명): **20자 이하**로 입력해 주세요.")

    age = int(st0.session_state.get(PF_INPUT_AGE) or 0)
    if age < 18 or age > 60:
        err.append("나이: **18~60** 범위여야 합니다.")

    g = str(st0.session_state.get(PF_INPUT_GENDER) or "")
    if g not in ("남자", "여자"):
        err.append("성별: **남자** 또는 **여자**를 선택해 주세요.")

    loc = (st0.session_state.get(PF_INPUT_LOCATION) or "").strip()
    if len(loc) < 2:
        err.append("거주 지역: **2~40자**로 입력해 주세요. (예: 서울 강남구)")
    elif len(loc) > 40:
        err.append("거주 지역: **40자 이하**로 입력해 주세요.")

    job = (st0.session_state.get(PF_INPUT_JOB) or "").strip()
    if len(job) < 2:
        err.append("직업: **2~40자**로 입력해 주세요.")
    elif len(job) > 40:
        err.append("직업: **40자 이하**로 입력해 주세요.")

    bio = (st0.session_state.get(PF_INPUT_BIO_DRAFT) or "").strip()
    if len(bio) < 30:
        err.append("자기소개 초안: **30자 이상** 구체적으로 적어 주세요. (최대 1,200자)")
    elif len(bio) > 1200:
        err.append("자기소개 초안: **1,200자 이하**로 줄여 주세요.")

    goal = (st0.session_state.get(PF_INPUT_DATING_GOAL) or "").strip()
    if len(goal) < 10:
        err.append("만남·연애 목적: **10자 이상** 적어 주세요. (최대 500자)")
    elif len(goal) > 500:
        err.append("만남·연애 목적: **500자 이하**로 줄여 주세요.")

    ideal = (st0.session_state.get(PF_INPUT_IDEAL) or "").strip()
    if len(ideal) < 10:
        err.append("선호하는 상대: **10자 이상** 적어 주세요. (최대 800자)")
    elif len(ideal) > 800:
        err.append("선호하는 상대: **800자 이하**로 줄여 주세요.")

    life = (st0.session_state.get(PF_INPUT_LIFESTYLE) or "").strip()
    if len(life) < 10:
        err.append("라이프스타일: **10자 이상** 적어 주세요. (최대 800자)")
    elif len(life) > 800:
        err.append("라이프스타일: **800자 이하**로 줄여 주세요.")

    memo = (st0.session_state.get(USER_SELF_INTRO_KEY) or "").strip()
    if memo and len(memo) > 600:
        err.append("추가 메모: **600자 이하**로 줄여 주세요.")

    return err


def refine_profile_texts_ai(
    *,
    display_name: str,
    age: int,
    gender: str,
    location: str,
    job: str,
    keywords: list[str],
    bio_draft: str,
    dating_goal_draft: str,
    ideal_draft: str,
    lifestyle_draft: str,
    extra_memo: str,
) -> dict:
    """자기소개·목적·이상형·라이프스타일만 다듬어 반환 (나머지 필드는 호출부에서 병합)."""
    model = ChatOpenAI(model="gpt-4o-mini", temperature=0.45)
    parser = JsonOutputParser(pydantic_object=ProfileTextRefine)
    fmt = parser.get_format_instructions()
    kw_line = ", ".join(keywords) if keywords else "(없음)"

    human = HumanMessagePromptTemplate.from_template(
        "너는 소개팅 앱용 프로필 **문장 편집자**다. 아래 **고정 정보**와 사용자 **초안**이 있다.\n\n"
        "## 고정 정보 (절대 바꾸거나 반박하지 말 것 — 다듬은 문장에 새로운 사실을 지어내지 말 것)\n"
        "- 표시명: {display_name}\n"
        "- 나이/성별: {age}세, {gender}\n"
        "- 지역: {location}\n"
        "- 직업: {job}\n"
        "- 관심 키워드: {keywords_line}\n\n"
        "## 추가 톤·힌트 (선택)\n{extra_memo}\n\n"
        "## 사용자 초안 (의미·사실 유지)\n"
        "[자기소개 초안]\n{bio_draft}\n\n"
        "[만남·연애 목적]\n{goal_draft}\n\n"
        "[선호하는 상대]\n{ideal_draft}\n\n"
        "[라이프스타일]\n{lifestyle_draft}\n\n"
        "## 할 일\n"
        "1) 위 네 블록만 각각 **자연스러운 한국어**로 다듬는다. 오탈자·어색한 표현을 고친다.\n"
        "2) 사용자가 쓴 **내용·사실·취향을 바꾸거나 삭제하지 않는다.** 없던 취미·경력·약속을 추가하지 않는다.\n"
        "3) 네 필드가 서로 **역할이 겹치지 않게** 정리한다 (소개/목적/이상형/일상).\n"
        "4) 완전히 새 프로필을 짓지 말고, **반드시 초안을 기반**으로 한다.\n"
        "{format_instructions}"
    )
    chain = ChatPromptTemplate.from_messages([human]).partial(format_instructions=fmt) | model | parser
    raw = chain.invoke(
        {
            "display_name": display_name,
            "age": age,
            "gender": gender,
            "location": location,
            "job": job,
            "keywords_line": kw_line,
            "extra_memo": (extra_memo or "").strip() or "(없음)",
            "bio_draft": bio_draft.strip(),
            "goal_draft": dating_goal_draft.strip(),
            "ideal_draft": ideal_draft.strip(),
            "lifestyle_draft": lifestyle_draft.strip(),
        }
    )
    return ProfileTextRefine.model_validate(raw).model_dump()


def build_profile_from_session(st0) -> dict:
    """검증 통과 후: 고정 필드 + 키워드는 입력 그대로, 네 텍스트는 AI 다듬기."""
    kw = _split_keywords(st0.session_state.get(USER_KEYWORDS_SEED_KEY) or "")
    seen: set[str] = set()
    keywords: list[str] = []
    for k in kw:
        if k not in seen:
            seen.add(k)
            keywords.append(k)

    display_name = (st0.session_state.get(PF_INPUT_DISPLAY_NAME) or "").strip()
    age = int(st0.session_state.get(PF_INPUT_AGE) or 28)
    gender = str(st0.session_state.get(PF_INPUT_GENDER) or "남자")
    location = (st0.session_state.get(PF_INPUT_LOCATION) or "").strip()
    job = (st0.session_state.get(PF_INPUT_JOB) or "").strip()
    bio_draft = (st0.session_state.get(PF_INPUT_BIO_DRAFT) or "").strip()
    goal_d = (st0.session_state.get(PF_INPUT_DATING_GOAL) or "").strip()
    ideal_d = (st0.session_state.get(PF_INPUT_IDEAL) or "").strip()
    life_d = (st0.session_state.get(PF_INPUT_LIFESTYLE) or "").strip()
    memo = (st0.session_state.get(USER_SELF_INTRO_KEY) or "").strip()

    refined = refine_profile_texts_ai(
        display_name=display_name,
        age=age,
        gender=gender,
        location=location,
        job=job,
        keywords=keywords,
        bio_draft=bio_draft,
        dating_goal_draft=goal_d,
        ideal_draft=ideal_d,
        lifestyle_draft=life_d,
        extra_memo=memo,
    )

    return {
        "display_name": display_name,
        "age": age,
        "gender": gender,
        "location": location,
        "job": job,
        "keywords": keywords,
        "bio": refined["bio"],
        "dating_goal": refined["dating_goal"],
        "ideal_partner": refined["ideal_partner"],
        "lifestyle_summary": refined["lifestyle_summary"],
    }


# ════════════════════════════════════════════════════
# UI
# ════════════════════════════════════════════════════

st.set_page_config(page_title="통합 데이팅 AI", layout="wide", page_icon="💗")
render_page_shell(journey_step=JOURNEY_PROFILE)
_ensure_pf_defaults()
maybe_restore_step1_form_from_saved_profile()

if st.session_state.pop(_PENDING_SYNC_FORM_KEY, False):
    _sync_prof = st.session_state.get(USER_AI_PROFILE_KEY)
    if isinstance(_sync_prof, dict):
        apply_user_ai_profile_to_step1_form(_sync_prof)
        mark_step1_form_synced_with_profile(_sync_prof)

render_page_header(
    kicker="Step ① · 프로필",
    title="AI 프로필 만들기",
    subtitle="**이름·나이·성별·지역·직업·관심 키워드**는 입력한 그대로 저장됩니다. "
    "**자기소개·만남 목적·선호 상대·라이프스타일**만 AI가 문장만 다듬습니다. "
    "성별은 ② 매칭에서 **이성** 필터에 쓰입니다.",
)

if not openai_key_configured():
    st.warning("OpenAI API 키가 없으면 생성할 수 없습니다. 홈의 **API 키 설정**을 확인해 주세요.")

if st.session_state.pop(_SHOW_PROFILE_OK_KEY, False):
    st.success(
        "이름·나이·성별·지역·직업·키워드는 **입력 그대로** 저장했고, "
        "자기소개·목적·이상형·라이프스타일은 **AI로 다듬었**어요. 아래에서 확인해 보세요."
    )

st.markdown('<p class="ux-section-title">입력</p>', unsafe_allow_html=True)

st.markdown(
    '<p class="ux-section-lead">관심 키워드를 입력하세요. 쉼표로 여러 개 입력할 수 있습니다.</p>',
    unsafe_allow_html=True,
)
render_interest_quick_tags(draft_key=USER_KEYWORDS_SEED_KEY)

st.text_area(
    "관심 키워드",
    key=USER_KEYWORDS_SEED_KEY,
    height=90,
    placeholder="예: 커피, 여행, 영화",
)

c1, c2 = st.columns(2)
with c1:
    st.text_input("이름 (표시명)", key=PF_INPUT_DISPLAY_NAME)
    st.number_input("나이", min_value=18, max_value=60, key=PF_INPUT_AGE)
    st.selectbox("성별", ["남자", "여자"], key=PF_INPUT_GENDER)
    st.text_input("거주 지역", key=PF_INPUT_LOCATION, placeholder="예: 서울 마포구")
    st.text_input("직업", key=PF_INPUT_JOB, placeholder="예: IT 기획")
with c2:
    st.text_area("자기소개 초안", key=PF_INPUT_BIO_DRAFT, height=120)
    st.text_area("만남·연애 목적", key=PF_INPUT_DATING_GOAL, height=70)
    st.text_area("선호하는 상대", key=PF_INPUT_IDEAL, height=70)
    st.text_area("라이프스타일", key=PF_INPUT_LIFESTYLE, height=70)

st.text_area("추가 메모 (선택)", key=USER_SELF_INTRO_KEY, height=70)

if st.button("프로필 반영 (문장 다듬기)", type="primary", use_container_width=True):
    if not openai_key_configured():
        st.warning("API 키를 먼저 설정해 주세요.")
    else:
        _errs = validate_profile_inputs(st)
        if _errs:
            st.warning(
                "입력 조건을 확인해 주세요.\n\n"
                + "\n".join(f"- {_e}" for _e in _errs)
            )
        else:
            with st.spinner("기본 정보는 그대로 두고, 네 항목만 문장을 다듬는 중…"):
                try:
                    prof = build_profile_from_session(st)
                    st.session_state[USER_AI_PROFILE_KEY] = prof
                    st.session_state[_PENDING_SYNC_FORM_KEY] = True
                    st.session_state[_SHOW_PROFILE_OK_KEY] = True
                    st.session_state.pop("_profile_score", None)
                    st.rerun()
                except AuthenticationError:
                    st.error("OpenAI 인증에 실패했습니다. API 키를 확인하세요.")
                except Exception as e:
                    st.error(f"처리 오류: {e}")

me = st.session_state.get(USER_AI_PROFILE_KEY)
if isinstance(me, dict) and me.get("display_name"):
    st.markdown('<p class="ux-section-title">저장된 프로필</p>', unsafe_allow_html=True)
    with st.container(border=True):
        st.markdown(
            f"**{me.get('display_name')}** · {me.get('age')}세 · {me.get('gender')} · "
            f"{me.get('location', '')} · {me.get('job', '')}"
        )
        st.caption("관심 키워드: " + ", ".join(me.get("keywords") or []))
        with st.expander("자기소개", expanded=True):
            st.write(me.get("bio", ""))
        with st.expander("만남 목적·선호·라이프스타일"):
            st.write(me.get("dating_goal", ""))
            st.write(me.get("ideal_partner", ""))
            st.write(me.get("lifestyle_summary", ""))

    # ── [G] 프로필 매력도 점수 ─────────────────────────
    st.markdown('<p class="ux-section-title">📊 프로필 매력도 분석</p>', unsafe_allow_html=True)
    st.caption("AI가 내 프로필을 소개팅 앱 관점에서 채점하고 개선안을 제안합니다.")

    if st.button("매력도 분석하기", use_container_width=True):
        with st.spinner("AI가 프로필을 분석 중…"):
            try:
                score_result = score_profile(
                    bio=me.get("bio", ""),
                    dating_goal=me.get("dating_goal", ""),
                    ideal_partner=me.get("ideal_partner", ""),
                    lifestyle_summary=me.get("lifestyle_summary", ""),
                    keywords_str=", ".join(me.get("keywords") or []),
                )
                st.session_state["_profile_score"] = score_result
            except Exception as e:
                st.error(f"분석 오류: {e}")

    score_data = st.session_state.get("_profile_score")
    if score_data:
        overall = score_data.get("overall", 0)
        if overall >= 80:
            overall_color = "#16a34a"
            overall_label = "우수"
        elif overall >= 60:
            overall_color = "#d97706"
            overall_label = "보통"
        else:
            overall_color = "#dc2626"
            overall_label = "개선 필요"

        st.markdown(
            f'<div style="text-align:center;padding:16px;">'
            f'<span style="font-size:2.5rem;font-weight:800;color:{overall_color};">'
            f'{overall}점</span>'
            f'<span style="font-size:1rem;color:{overall_color};margin-left:8px;">{overall_label}</span>'
            f'</div>',
            unsafe_allow_html=True,
        )

        dims = [
            ("자기소개 매력도", "bio_score"),
            ("키워드 다양성", "keyword_diversity"),
            ("연애 목적 명확성", "goal_clarity"),
            ("이상형 구체성", "ideal_specificity"),
        ]
        dc = st.columns(len(dims))
        for i, (label, key) in enumerate(dims):
            val = score_data.get(key, 0)
            with dc[i]:
                st.metric(label, f"{val}점")
                st.progress(val / 100)

        col_good, col_improve = st.columns(2)
        with col_good:
            st.markdown("#### ✅ 잘된 점")
            for s in score_data.get("strengths", []):
                st.success(s)
        with col_improve:
            st.markdown("#### 💡 개선 제안")
            for imp in score_data.get("improvements", []):
                st.warning(imp)

    st.page_link(
        "pages/02_프로필_매칭_검색.py",
        label="다음: ② 매칭 검색",
        use_container_width=True,
    )

render_trust_footer()
