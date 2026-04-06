"""
Step ③ 인사말 생성
[D] 인사말 품질 자동 평가 기능 추가
"""
import streamlit as st
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate, HumanMessagePromptTemplate
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from _match_context import MATCHED_PROFILE_KEY, USER_AI_PROFILE_KEY, journey_can_access
from _ui import (
    JOURNEY_GREETING,
    openai_key_configured,
    render_page_header,
    render_page_shell,
    render_trust_footer,
)


class IntroList(BaseModel):
    intro_list: list[str] = Field(description="소개팅 첫 메시지 후보 리스트")


# ── [D] 인사말 품질 평가 모델 ─────────────────────────────
class GreetingEval(BaseModel):
    naturalness: int = Field(description="자연스러움 0~100. 딱딱하지 않고 실제 대화처럼 느껴지는 정도")
    personalization: int = Field(description="개인화 0~100. 상대 프로필을 얼마나 구체적으로 반영했는가")
    interest_trigger: int = Field(description="흥미 유발 0~100. 상대가 답하고 싶어지는 정도")
    overall: int = Field(description="종합 점수 0~100")
    feedback: str = Field(description="한 줄 피드백. 구체적 개선 포인트 포함")


@st.cache_data(show_spinner=False)
def evaluate_greeting(
    greeting: str,
    partner_name: str,
    partner_keywords: str,
    partner_bio: str,
) -> dict:
    """인사말 품질을 LLM이 채점 (캐시 적용)."""
    model = ChatOpenAI(model="gpt-4o-mini", temperature=0.2)
    parser = JsonOutputParser(pydantic_object=GreetingEval)
    fmt = parser.get_format_instructions()
    prompt = ChatPromptTemplate.from_template(
        "소개팅 앱의 첫 메시지를 평가하라.\n\n"
        "상대: {partner_name} (키워드: {keywords}, 소개: {bio})\n"
        "평가할 메시지: {greeting}\n\n"
        "엄격하고 구체적으로 평가하라.\n"
        "{format_instructions}"
    )
    chain = prompt.partial(format_instructions=fmt) | model | parser
    return chain.invoke({
        "partner_name": partner_name,
        "keywords": partner_keywords,
        "bio": partner_bio,
        "greeting": greeting,
    })


def _my_profile_narrative(me: dict) -> str:
    kw = me.get("keywords") or []
    kw_str = ", ".join(kw) if isinstance(kw, list) else str(kw)
    chunks = [
        f"이름: {me.get('display_name', '')}",
        f"나이/성별: {me.get('age', '')}세, {me.get('gender', '')}",
        f"지역/직업: {me.get('location', '')} / {me.get('job', '')}",
        f"자기소개: {me.get('bio', '')}",
        f"만남·연애 목적: {me.get('dating_goal', '')}",
        f"선호하는 상대: {me.get('ideal_partner', '')}",
        f"라이프스타일: {me.get('lifestyle_summary', '')}",
        f"관심 키워드: {kw_str}",
    ]
    return "\n".join(chunks)


def generate_opening_to_partner(my_profile: dict, partner: dict) -> list[str]:
    model = ChatOpenAI(model="gpt-4o-mini", temperature=1.0)
    parser = JsonOutputParser(pydantic_object=IntroList)
    format_instructions = parser.get_format_instructions()

    p_kw = partner.get("keywords") or []
    partner_kw = ", ".join(p_kw) if isinstance(p_kw, list) else str(p_kw)

    human_prompt_template = HumanMessagePromptTemplate.from_template(
        "# 나(보내는 사람) — ① AI 프로필에서 온 정보\n"
        "{my_side}\n\n"
        "# 상대방 프로필\n"
        "이름: {partner_name}, 나이: {partner_age}, 성별: {partner_gender}, 직업: {partner_job}\n"
        "자기소개: {partner_bio}\n"
        "관심 키워드: {partner_kw}\n\n"
        "소개팅 앱에서 **상대방에게 보내는 첫 메시지** 후보를 3개 만들어줘. "
        "나의 프로필(목적·취향·라이프스타일)을 자연스럽게 반영하고, 상대 프로필을 한두 군데 짚어 줘. "
        "각각 톤이 조금씩 다르게(차분 / 가벼움 / 질문 중심). 짧게, 한국어.\n"
        "{format_instructions}"
    )

    prompt_template = ChatPromptTemplate.from_messages([human_prompt_template])
    prompt_template = prompt_template.partial(format_instructions=format_instructions)
    intro_gen_chain = prompt_template | model | parser

    out = intro_gen_chain.invoke(
        {
            "my_side": _my_profile_narrative(my_profile),
            "partner_name": str(partner.get("name", "")),
            "partner_age": int(partner.get("age") or 0),
            "partner_gender": str(partner.get("gender", "")),
            "partner_job": str(partner.get("job", "")),
            "partner_bio": str(partner.get("bio", "")),
            "partner_kw": partner_kw,
        }
    )
    return out["intro_list"]


# ════════════════════════════════════════════════════
# UI
# ════════════════════════════════════════════════════

st.set_page_config(page_title="통합 데이팅 AI", layout="wide", page_icon="💌")
render_page_shell(journey_step=JOURNEY_GREETING)

_ok3, _msg3 = journey_can_access("greeting")
if not _ok3:
    st.error(_msg3)
    c_a, c_b = st.columns(2)
    with c_a:
        st.page_link("pages/01_AI_프로필_생성.py", label="① AI 프로필", use_container_width=True)
    with c_b:
        st.page_link("pages/02_프로필_매칭_검색.py", label="② 매칭·상대 선택", use_container_width=True)
    render_trust_footer()
    st.stop()

render_page_header(
    kicker="Step ③ · 인사말",
    title="첫 인사·첫 멘트",
    subtitle="**나의 정보**는 **① AI 프로필**에 저장된 내용을 씁니다. "
    "②에서 고른 **상대 프로필**을 바탕으로 첫 메시지 초안만 만듭니다.",
)

if not openai_key_configured():
    st.warning("OpenAI API 키가 없으면 생성할 수 없습니다. 홈에서 키를 설정해 주세요.")

match = st.session_state.get(MATCHED_PROFILE_KEY)
me = st.session_state.get(USER_AI_PROFILE_KEY)

if match:
    st.subheader("연결된 상대 프로필")
    with st.container(border=True):
        st.markdown(f"**{match.get('name')}** · {match.get('age')}세 · {match.get('gender')}")
        st.caption(f"직업: {match.get('job')}")
        with st.expander("상대 자기소개", expanded=True):
            st.write(match.get("bio") or "")
        st.caption("관심: " + ", ".join(match.get("keywords") or []))

    if not (isinstance(me, dict) and me.get("display_name")):
        st.error("나의 프로필이 없어요. 먼저 **① AI 프로필**에서 입력·생성해 주세요.")
        st.page_link("pages/01_AI_프로필_생성.py", label="① AI 프로필 만들기 →", use_container_width=True)
    else:
        with st.expander("나의 프로필 (①에서 저장됨)", expanded=False):
            st.markdown(_my_profile_narrative(me).replace("\n", "\n\n"))
        st.page_link(
            "pages/01_AI_프로필_생성.py",
            label="나의 프로필 수정하기",
            use_container_width=False,
        )

        if st.button("첫 인사말 후보 생성", type="primary", use_container_width=True):
            with st.spinner("첫 메시지 초안을 만드는 중…"):
                try:
                    lines = generate_opening_to_partner(me, match)
                    st.session_state["_last_intro_lines"] = lines
                    # 이전 평가 초기화
                    st.session_state.pop("_greeting_scores", None)
                except Exception as e:
                    st.error(f"생성 오류: {e}")

        lines = st.session_state.get("_last_intro_lines")
        if lines:
            st.subheader("생성된 첫 인사말 후보")

            tone_labels = ["🤍 차분한 톤", "😄 가벼운 톤", "❓ 질문 중심"]
            for i, line in enumerate(lines, 0):
                with st.container(border=True):
                    tone = tone_labels[i] if i < len(tone_labels) else f"후보 {i+1}"
                    st.markdown(f"**후보 {i+1}** &nbsp; {tone}")
                    st.write(line)

                    # [D] 품질 점수 표시 (평가 실행 후)
                    scores = st.session_state.get("_greeting_scores")
                    if scores and i < len(scores):
                        s = scores[i]
                        overall = s.get("overall", 0)
                        if overall >= 80:
                            badge_color = "#16a34a"
                        elif overall >= 60:
                            badge_color = "#d97706"
                        else:
                            badge_color = "#dc2626"

                        st.markdown(
                            f'<span style="background:{badge_color};color:#fff;'
                            f'border-radius:6px;padding:2px 10px;font-size:0.82rem;font-weight:700;">'
                            f"⭐ 종합 {overall}점</span>",
                            unsafe_allow_html=True,
                        )
                        sc1, sc2, sc3 = st.columns(3)
                        with sc1:
                            st.caption(f"자연스러움: {s.get('naturalness', 0)}점")
                            st.progress(s.get("naturalness", 0) / 100)
                        with sc2:
                            st.caption(f"개인화: {s.get('personalization', 0)}점")
                            st.progress(s.get("personalization", 0) / 100)
                        with sc3:
                            st.caption(f"흥미 유발: {s.get('interest_trigger', 0)}점")
                            st.progress(s.get("interest_trigger", 0) / 100)
                        st.info(f"💬 {s.get('feedback', '')}")

            # [D] 품질 평가 버튼
            st.divider()
            if st.button("📊 인사말 품질 평가하기", use_container_width=True):
                with st.spinner("AI가 3개 인사말을 동시에 채점 중…"):
                    try:
                        partner_kw_str = ", ".join(match.get("keywords") or [])
                        partner_bio_str = str(match.get("bio") or "")
                        partner_name_str = str(match.get("name") or "")

                        scores = []
                        for line in lines:
                            s = evaluate_greeting(
                                greeting=line,
                                partner_name=partner_name_str,
                                partner_keywords=partner_kw_str,
                                partner_bio=partner_bio_str,
                            )
                            scores.append(s)
                        st.session_state["_greeting_scores"] = scores
                        st.rerun()
                    except Exception as e:
                        st.error(f"평가 오류: {e}")

            # 평가 완료 후 최고 추천
            scores = st.session_state.get("_greeting_scores")
            if scores:
                best_idx = max(range(len(scores)), key=lambda i: scores[i].get("overall", 0))
                best_score = scores[best_idx].get("overall", 0)
                st.success(
                    f"🏆 **추천 인사말: 후보 {best_idx + 1}** ({tone_labels[best_idx] if best_idx < len(tone_labels) else ''}) "
                    f"— 종합 {best_score}점"
                )

            n1, n2 = st.columns(2)
            with n1:
                st.page_link(
                    "pages/04_대화_도우미.py",
                    label="다음: 대화 연습 →",
                    use_container_width=True,
                )
            with n2:
                st.caption("대화 도우미에서 같은 상대와 채팅 연습이 이어집니다.")

else:
    st.info(
        "아직 **매칭에서 상대를 고르지 않았어요.** 먼저 ①에서 프로필을 만든 뒤 ② 매칭에서 상대를 선택해 주세요."
    )
    c1, c2 = st.columns(2)
    with c1:
        st.page_link("pages/01_AI_프로필_생성.py", label="① AI 프로필", use_container_width=True)
    with c2:
        st.page_link("pages/02_프로필_매칭_검색.py", label="② 매칭 검색", use_container_width=True)

render_trust_footer()
