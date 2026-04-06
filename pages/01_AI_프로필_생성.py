"""
① 관심 키워드 + 상세 입력 → AI가 나의 데이팅 프로필을 생성·보완.
[G] 프로필 매력도 점수 기능 추가
"""
import streamlit as st
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate, HumanMessagePromptTemplate
from langchain_openai import ChatOpenAI
from openai import AuthenticationError
from pydantic import BaseModel, Field

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
)
from _ui import (
    JOURNEY_PROFILE,
    openai_key_configured,
    render_page_header,
    render_page_shell,
    render_trust_footer,
)


class AiUserProfile(BaseModel):
    display_name: str = Field(description="한글 닉네임 또는 이름")
    age: int = Field(description="20~40")
    gender: str = Field(description="반드시 '남자' 또는 '여자'")
    job: str = Field(description="직업 또는 직군 한 줄")
    location: str = Field(description="거주 지역")
    bio: str = Field(description="소개팅 앱용 자기소개 3~6문장. 입력이 있으면 반영·다듬기")
    dating_goal: str = Field(description="만남·연애 목적 1~2문장")
    ideal_partner: str = Field(description="선호하는 상대 스타일·분위기 2~3문장")
    lifestyle_summary: str = Field(description="일상·주말 루틴·취미 생활 2~4문장")
    keywords: list[str] = Field(
        description="관심 키워드 6~14개. 사용자 입력 키워드를 모두 포함하고 매칭용 짧은 한글 단어 추가"
    )


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
        st.session_state[PF_INPUT_GENDER] = "미입력 (AI가 설정)"
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


def _gender_for_prompt(g: str) -> str:
    if g in ("남자", "여자"):
        return g
    return "미정 — 적절히 '남자' 또는 '여자' 중 하나로 설정하라."


def generate_profile_ai(st0) -> dict:
    model = ChatOpenAI(model="gpt-4o-mini", temperature=0.82)
    parser = JsonOutputParser(pydantic_object=AiUserProfile)
    fmt = parser.get_format_instructions()

    raw_kw = (st0.session_state.get(USER_KEYWORDS_SEED_KEY) or "").strip()
    parts = [x.strip() for x in raw_kw.replace("，", ",").split(",") if x.strip()]
    keywords_line = ", ".join(parts) if parts else "(없음)"

    block = f"""[관심 키워드 — 반드시 keywords에 반영]
{keywords_line}

[닉네임 — 비어 있으면 알아서 지어도 됨]
{st0.session_state.get(PF_INPUT_DISPLAY_NAME) or "(미입력)"}

[나이 — 사용자가 넣은 값 우선, 없으면 적절히 설정]
{st0.session_state.get(PF_INPUT_AGE)}

[성별 — 아래가 '남자'/'여자'가 아니면 프로필에 맞게 하나 선택]
{_gender_for_prompt(str(st0.session_state.get(PF_INPUT_GENDER) or ""))}

[지역]
{st0.session_state.get(PF_INPUT_LOCATION) or "(미입력)"}

[직업]
{st0.session_state.get(PF_INPUT_JOB) or "(미입력)"}

[자기소개 초안 — 사용자가 쓴 내용이 있으면 반영·문장 다듬기, 없으면 키워드 기반으로 작성]
{st0.session_state.get(PF_INPUT_BIO_DRAFT) or "(미입력)"}

[만남·연애 목적]
{st0.session_state.get(PF_INPUT_DATING_GOAL) or "(미입력)"}

[선호하는 상대]
{st0.session_state.get(PF_INPUT_IDEAL) or "(미입력)"}

[라이프스타일·주말·일상]
{st0.session_state.get(PF_INPUT_LIFESTYLE) or "(미입력)"}

[추가 메모·성격 힌트]
{st0.session_state.get(USER_SELF_INTRO_KEY) or "(없음)"}
"""

    human = HumanMessagePromptTemplate.from_template(
        "너는 소개팅 앱용 **나의 프로필**을 작성하는 작가다. 아래는 사용자가 입력한 정보다.\n\n"
        "{block}\n\n"
        "규칙:\n"
        "1) **데모용 가상 프로필**이지만 자연스러운 한국어로.\n"
        "2) 키워드가 있으면 keywords 리스트에 **입력과 동일하거나 아주 유사한 단어**를 모두 넣어라.\n"
        "3) 매칭 DB와 맞추기 위해 여행·커피·독서·영화·요리·음악·운동·코딩 등 흔한 태그를 섞어도 좋다.\n"
        "4) 사용자가 나이·성별·지역·직업을 적었으면 **모순 없이** 반영하라. 비어 있으면 합리적으로 채운다.\n"
        "5) bio, dating_goal, ideal_partner, lifestyle_summary는 서로 **겹치지 않게** 역할을 나눠라.\n"
        "{format_instructions}"
    )
    chain = ChatPromptTemplate.from_messages([human]).partial(format_instructions=fmt) | model | parser
    raw = chain.invoke({"block": block})
    return AiUserProfile.model_validate(raw).model_dump()


# ════════════════════════════════════════════════════
# UI
# ════════════════════════════════════════════════════

st.set_page_config(page_title="통합 데이팅 AI", layout="wide", page_icon="💗")
render_page_shell(journey_step=JOURNEY_PROFILE)
_ensure_pf_defaults()

render_page_header(
    kicker="Step ① · 프로필",
    title="AI 프로필 만들기",
    subtitle="**관심 키워드**가 있으면 매칭과 잘 맞고, 상세 항목을 채울수록 소개가 구체적입니다. "
    "여기서 만든 카드는 **② 매칭 · ③ 인사말 · ④ 대화**에 그대로 연결됩니다.",
)

if not openai_key_configured():
    st.warning("OpenAI API 키가 없으면 생성할 수 없습니다. 홈의 **API 키 설정**을 확인해 주세요.")

st.markdown('<p class="ux-section-title">입력</p>', unsafe_allow_html=True)
st.markdown(
    '<p class="ux-section-lead">이전에 입력해 둔 키워드가 있으면 그대로 이어집니다. 쉼표로 여러 개 넣을 수 있어요.</p>',
    unsafe_allow_html=True,
)
st.text_area(
    "관심 키워드",
    key=USER_KEYWORDS_SEED_KEY,
    height=90,
    placeholder="예: 커피, 여행, 영화",
    help="매칭 DB keywords와 겹치면 유리합니다.",
)

c1, c2 = st.columns(2)
with c1:
    st.text_input("닉네임 / 이름", key=PF_INPUT_DISPLAY_NAME)
    st.number_input("나이", min_value=18, max_value=60, key=PF_INPUT_AGE)
    st.selectbox(
        "성별",
        ["미입력 (AI가 설정)", "남자", "여자"],
        key=PF_INPUT_GENDER,
    )
    st.text_input("거주 지역", key=PF_INPUT_LOCATION)
    st.text_input("직업", key=PF_INPUT_JOB)
with c2:
    st.text_area("자기소개 초안", key=PF_INPUT_BIO_DRAFT, height=120)
    st.text_area("만남·연애 목적", key=PF_INPUT_DATING_GOAL, height=70)
    st.text_area("선호하는 상대", key=PF_INPUT_IDEAL, height=70)
    st.text_area("라이프스타일", key=PF_INPUT_LIFESTYLE, height=70)

st.text_area("추가 메모 (선택)", key=USER_SELF_INTRO_KEY, height=70, help="톤·분위기 등 짧게 적어 주세요.")

if st.button("프로필 생성", type="primary", use_container_width=True):
    if not openai_key_configured():
        st.warning("API 키를 먼저 설정해 주세요.")
    else:
        with st.spinner("프로필을 생성하는 중…"):
            try:
                prof = generate_profile_ai(st)
                st.session_state[USER_AI_PROFILE_KEY] = prof
                # 이전 점수 캐시 초기화
                st.session_state.pop("_profile_score", None)
                st.success("프로필을 만들었어요. 아래에서 내용을 확인한 뒤 매칭으로 이동해 보세요.")
            except AuthenticationError:
                st.error("OpenAI 인증에 실패했습니다. API 키를 확인하세요.")
            except Exception as e:
                st.error(f"생성 오류: {e}")

me = st.session_state.get(USER_AI_PROFILE_KEY)
if isinstance(me, dict) and me.get("display_name"):
    st.markdown('<p class="ux-section-title">생성된 프로필</p>', unsafe_allow_html=True)
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

    n1, n2 = st.columns(2)
    with n1:
        st.page_link("pages/02_프로필_매칭_검색.py", label="다음: 매칭 검색", use_container_width=True)
    with n2:
        st.page_link("pages/03_인사말_생성.py", label="③ 인사말로", use_container_width=True)

render_trust_footer()
