"""
통합 대화 도우미 — 멘트 추천, RAG, 투표형 조언.
[E] 대화 위험 신호 감지 기능 추가
"""
from __future__ import annotations

import os

import pandas as pd
import streamlit as st
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import JsonOutputParser, StrOutputParser
from langchain_core.prompts import ChatPromptTemplate, HumanMessagePromptTemplate
from openai import OpenAI
from pydantic import BaseModel, Field

from _match_context import MATCHED_PROFILE_KEY, ensure_chat_session, partner_context_for_llm
from _rag_conv import conv_rag_available, retrieve_similar_conversations
from _ui import JOURNEY_COACH, openai_key_configured, render_page_header, render_page_shell, render_trust_footer

MESSAGES_KEY = "messages_coach"

MODE_DEFS = [
    ("ment", "💬 짧은 멘트만", "지금 이어갈 **한두 문장**만 빠르게 추천해요."),
    (
        "rag",
        "📚 대화 예시 참고 → 조언",
        "먼저 저장된 **대화 스크립트** 중 비슷한 걸 찾고, 그걸 근거로 **코칭 조언**을 씁니다. (참고=대화, 결과=조언)",
    ),
    ("vote", "🗳️ 여러 조언 후 고르기", "여러 조언을 만든 뒤 가장 나은 하나를 골라요."),
    ("danger", "🚨 위험 신호 감지", "대화에서 주의해야 할 패턴을 분석합니다."),
]


class MentOut(BaseModel):
    sentiment: str = Field(description="대화의 분위기 한 단어(예: 인사, 가벼운 대화)")
    suggestion_text: str = Field(
        description="추천 발화: 위 대화에 실제로 등장한 주제에만 맞출 것"
    )


def run_ment_suggestion(user_label: str, partner_label: str) -> dict:
    messages = st.session_state[MESSAGES_KEY]
    match = st.session_state.get(MATCHED_PROFILE_KEY)
    conv = ""
    for message in messages[1:]:
        name = user_label if message["role"] == "user" else partner_label
        conv += f"{name}: {message['content']}\n"

    model = ChatOpenAI(model="gpt-4o-mini", temperature=0.45)
    parser = JsonOutputParser(pydantic_object=MentOut)
    fmt = parser.get_format_instructions()
    partner_ctx = partner_context_for_llm(match, user_label)
    tpl = HumanMessagePromptTemplate.from_template(
        "{partner_ctx}\n\n"
        "아래는 지금까지의 대화 전체이다.\n"
        "{conv}\n"
        "---\n"
        "위 대화는 소개팅에서 처음 만나는 두 사람의 대화이다.\n"
        "【반드시 지킬 것】\n"
        "1) **대화에 실제로 나온 말에만** 이어 붙인다. 여행·취미·음식·영화 등 **아무도 언급하지 않은 주제를 새로 꺼내지 마라.**\n"
        "2) 아직 인사·안부·짧은 질문만 오갔다면, 상대의 **마지막 발화에 답하거나** 같은 톤으로 짧게 반응하는 멘트만 추천한다. "
        "(예: 상대가 \"어떻게 지내셨어요?\"라고 했으면 그 질문에 답하는 한두 문장)\n"
        "3) 위에 있는 **상대 프로필**(관심 키워드·소개 등)은 참고용이다. 대화가 아직 인사·첫 질문 단계이면 "
        "**프로필에 나온 취미·여행 등을 멘트에 끌어오지 마라.** (대화에서 그 주제가 나온 뒤에만 자연스럽게 연결 가능)\n"
        "4) 추천 멘트는 한두 문장, 과장·설정 추가 금지.\n"
        "{name}가 지금 이어서 하면 좋을 **짧은 멘트 한 가지**를 추천하라.\n"
        "{format_instructions}"
    )
    chain = ChatPromptTemplate.from_messages([tpl]).partial(format_instructions=fmt) | model | parser
    return chain.invoke({"conv": conv, "name": user_label, "partner_ctx": partner_ctx})


class Suggestion(BaseModel):
    sentiment: str = Field(description="Positive, Negative, Neutral")
    suggestion_text: str = Field(description="markdown 형식의 조언")


def stream_vote_suggestion(messages: list[dict], user_label: str, partner_label: str, num_candi: int = 5):
    match = st.session_state.get(MATCHED_PROFILE_KEY)
    partner_ctx = partner_context_for_llm(match, user_label)
    conv = ""
    for message in messages[1:]:
        name = user_label if message["role"] == "user" else partner_label
        conv += f"{name}: {message['content']}\n"

    eval_model = ChatOpenAI(model="gpt-4o", temperature=0.8)
    basic_model = ChatOpenAI(model="gpt-4o-mini", temperature=0.8)

    parser = JsonOutputParser(pydantic_object=Suggestion)
    fmt = parser.get_format_instructions()
    human1 = HumanMessagePromptTemplate.from_template(
        "{partner_ctx}\n\n"
        "{conv}\n"
        "위 소개팅 대화를 분석하고 {name}에게 markdown으로 적절한 조언을 하라.\n"
        "{format_instructions}"
    )
    gen_chain = ChatPromptTemplate.from_messages([human1]).partial(format_instructions=fmt) | basic_model | parser

    class VoteCoT(BaseModel):
        thought: str = Field(description="선택한 번호의 이유")
        voting_num: int = Field(description="voting number")

    vparser = JsonOutputParser(pydantic_object=VoteCoT)
    vfmt = vparser.get_format_instructions()
    human2 = HumanMessagePromptTemplate.from_template(
        "{partner_ctx}\n\n"
        "{conv}\n"
        "아래는 {name}에게 하면 좋을 조언 후보들이다. 가장 좋은 것 하나를 고르고 번호를 응답하라.\n"
        "{candidates}\n"
        "{format_instructions}"
    )
    vote_chain = ChatPromptTemplate.from_messages([human2]).partial(format_instructions=vfmt) | eval_model | vparser

    suggestion_list = gen_chain.batch(
        [{"conv": conv, "name": user_label, "partner_ctx": partner_ctx}] * num_candi
    )
    yield "### 조언 후보\n"
    yield "\n---\n".join(
        [f"**후보 {i}** · {s['sentiment']}\n{s['suggestion_text']}\n" for i, s in enumerate(suggestion_list)]
    )
    cand_text = "\n\n".join(
        [
            f"후보 {i}.\n감정: {s.get('sentiment', '')}\n{s.get('suggestion_text', '')}"
            for i, s in enumerate(suggestion_list)
        ]
    )
    votes = vote_chain.batch(
        [{"conv": conv, "name": user_label, "candidates": cand_text, "partner_ctx": partner_ctx}] * num_candi
    )
    df = pd.DataFrame(votes)
    yield "### 투표 요약\n"
    yield df
    if df.empty or "voting_num" not in df.columns:
        yield "투표 결과를 집계할 수 없습니다."
        return
    mode_vals = df["voting_num"].dropna().astype(int)
    if mode_vals.empty:
        yield "유효한 투표 번호가 없습니다."
        return
    best_n = int(mode_vals.mode().iloc[0])
    best_n = max(0, min(best_n, len(suggestion_list) - 1))
    best = suggestion_list[best_n]
    yield "### ✅ 추천 조언\n"
    yield f"**선택: 후보 {best_n}** ({best['sentiment']})\n\n{best['suggestion_text']}"


def prepare_rag_suggestion(user_label: str, partner_label: str) -> tuple[str, str, str]:
    match = st.session_state.get(MATCHED_PROFILE_KEY)
    partner_ctx = partner_context_for_llm(match, user_label)
    conv = ""
    for message in st.session_state[MESSAGES_KEY][1:]:
        name = user_label if message["role"] == "user" else partner_label
        conv += f"{name}: {message['content']}\n"

    query = conv.strip() or "소개팅에서 처음 만나는 대화"
    context = retrieve_similar_conversations(query, k=4)
    if not context.strip():
        context = "(유사 샘플을 찾지 못했습니다. 일반적인 조언만 해 주세요.)"
    return partner_ctx, conv, context


def stream_rag_suggestion_prepared(partner_ctx: str, conv: str, context: str):
    model = ChatOpenAI(model="gpt-4o", temperature=0.8)
    template = """
{partner_ctx}

# 현재 대화
{conv}

# 검색으로 붙인 유사 대화 예시 (참고용 스크립트)
{context}

위 **유사 대화 예시**를 한두 문장으로 짚어 왜 참고가 됐는지 말한 뒤,
현재 대화에 맞는 **짧은 코칭 조언**(다음에 할 말·태도)을 해줘.
조언은 불릿 2~3개 정도로.
"""
    prompt = ChatPromptTemplate.from_template(template).partial(
        partner_ctx=partner_ctx, conv=conv, context=context
    )
    chain = prompt | model | StrOutputParser()
    return chain.stream({})


# ── [E] 위험 신호 감지 ─────────────────────────────────────

class DangerReport(BaseModel):
    risk_level: str = Field(description="위험 수준: '낮음' / '주의' / '높음'")
    one_sided_ratio: int = Field(description="한쪽 대화 쏠림 정도 0~100. 한 사람이 대화를 독점할수록 높음")
    privacy_risk: int = Field(description="개인정보 요청 위험도 0~100")
    tone_risk: int = Field(description="부적절한 어조 위험도 0~100. 공격적·강압적일수록 높음")
    disconnect_risk: int = Field(description="대화 단절 위험도 0~100. 답변이 짧고 관심 없어 보일수록 높음")
    warnings: list[str] = Field(description="감지된 위험 패턴 목록. 없으면 빈 리스트")
    suggestions: list[str] = Field(description="개선 제안 목록. 없으면 빈 리스트")
    positive_signals: list[str] = Field(description="긍정적인 대화 패턴 목록")


@st.cache_data(show_spinner=False)
def analyze_danger_signals(conv_text: str, user_label: str) -> dict:
    """대화에서 위험 신호 감지 (캐시 적용)."""
    model = ChatOpenAI(model="gpt-4o-mini", temperature=0.1)
    parser = JsonOutputParser(pydantic_object=DangerReport)
    fmt = parser.get_format_instructions()

    prompt = ChatPromptTemplate.from_template(
        "소개팅 대화를 분석하여 위험 신호를 감지하라. {user_label} 관점에서 평가.\n\n"
        "대화:\n{conv}\n\n"
        "분석 기준:\n"
        "1. 한쪽 쏠림: 한 사람이 질문·발화를 독점하는 정도\n"
        "2. 개인정보 위험: 전화번호·주소·직장 등 민감 정보 요구\n"
        "3. 어조 위험: 강압적·공격적·과도하게 친밀한 표현\n"
        "4. 대화 단절 위험: 무응답·단답·관심 없는 신호\n\n"
        "대화가 짧거나 아직 인사 단계라면 위험 수준을 '낮음'으로 평가하라.\n"
        "{format_instructions}"
    )
    chain = prompt.partial(format_instructions=fmt) | model | parser
    return chain.invoke({"conv": conv_text, "user_label": user_label})


def render_danger_panel(user_label: str, partner_label: str):
    """[E] 위험 신호 분석 패널."""
    messages = st.session_state.get(MESSAGES_KEY, [])
    conv = ""
    for message in messages[1:]:
        name = user_label if message["role"] == "user" else partner_label
        conv += f"{name}: {message['content']}\n"

    if not conv.strip():
        st.info("대화가 없습니다. 먼저 채팅을 시작해 보세요.")
        return

    if st.button("🚨 위험 신호 분석 실행", type="primary", use_container_width=True):
        with st.spinner("대화 패턴을 분석 중…"):
            try:
                report = analyze_danger_signals(conv, user_label)
                st.session_state["_danger_report"] = report
                st.rerun()
            except Exception as e:
                st.error(f"분석 오류: {e}")

    report = st.session_state.get("_danger_report")
    if not report:
        st.caption("버튼을 눌러 현재 대화를 분석하세요.")
        return

    risk_level = report.get("risk_level", "낮음")
    risk_colors = {"낮음": "#16a34a", "주의": "#d97706", "높음": "#dc2626"}
    risk_emoji = {"낮음": "🟢", "주의": "🟡", "높음": "🔴"}
    risk_color = risk_colors.get(risk_level, "#6b7280")
    risk_icon = risk_emoji.get(risk_level, "⚪")

    st.markdown(
        f'<div style="text-align:center;padding:12px;border-radius:8px;'
        f'background:{risk_color}22;border:2px solid {risk_color};">'
        f'<span style="font-size:1.5rem;">{risk_icon}</span>'
        f'<span style="font-size:1.2rem;font-weight:700;color:{risk_color};margin-left:8px;">'
        f'종합 위험 수준: {risk_level}</span>'
        f'</div>',
        unsafe_allow_html=True,
    )
    st.write("")

    # 세부 지표
    dims = [
        ("한쪽 쏠림", "one_sided_ratio"),
        ("개인정보 위험", "privacy_risk"),
        ("어조 위험", "tone_risk"),
        ("단절 위험", "disconnect_risk"),
    ]
    dc = st.columns(2)
    for i, (label, key) in enumerate(dims):
        val = report.get(key, 0)
        bar_color = "#dc2626" if val >= 70 else ("#d97706" if val >= 40 else "#16a34a")
        with dc[i % 2]:
            st.caption(f"{label}: **{val}점**")
            st.progress(val / 100)

    # 경고 / 제안 / 긍정 신호
    warnings = report.get("warnings", [])
    suggestions = report.get("suggestions", [])
    positives = report.get("positive_signals", [])

    if warnings:
        st.markdown("#### ⚠️ 감지된 위험 패턴")
        for w in warnings:
            st.error(w)

    if suggestions:
        st.markdown("#### 💡 개선 제안")
        for s in suggestions:
            st.warning(s)

    if positives:
        st.markdown("#### ✅ 긍정적 신호")
        for p in positives:
            st.success(p)

    if not warnings and not suggestions:
        st.success("현재 대화에서 특별한 위험 신호가 감지되지 않았습니다. 자연스럽게 이어가세요!")


# ════════════════════════════════════════════════════
# UI
# ════════════════════════════════════════════════════

st.set_page_config(layout="wide", page_icon="💬")
render_page_shell("대화 도우미", journey_step=JOURNEY_COACH)

render_page_header(
    kicker="Step ④ · 대화",
    title="대화 연습 · 코칭",
    subtitle="왼쪽은 상대 역할과의 채팅, 오른쪽은 **짧은 멘트 · 대화 예시 참고 조언(RAG) · 투표형 조언 · 위험 신호 감지** 패널입니다.",
)

if not openai_key_configured():
    st.error("OpenAI API 키가 설정되어 있지 않습니다. 홈의 **API 키 설정**을 확인해 주세요.")
    st.page_link("app.py", label="홈으로 가기", use_container_width=True)
    st.stop()

try:
    from _env import load_optional_dotenv
    load_optional_dotenv()
except ImportError:
    pass

user_label, partner_name, ai_avatar = ensure_chat_session(st, MESSAGES_KEY)
messages = st.session_state[MESSAGES_KEY]

match = st.session_state.get(MATCHED_PROFILE_KEY)
if match:
    st.caption(f"연결된 상대: **{match.get('name')}** · {ai_avatar}")
else:
    st.info("매칭 프로필이 없으면 기본 페르소나(수연)로 대화합니다. ②에서 상대를 고르면 연결됩니다.")

col_chat, col_panel = st.columns([3, 2], gap="large")

with col_chat:
    st.subheader("대화")

    # 대화 턴 수 카운터 (위험 신호 자동 알림용)
    user_turns = sum(1 for m in messages[1:] if m["role"] == "user")
    if user_turns >= 5 and not st.session_state.get("_danger_alerted"):
        st.toast("💡 대화가 5턴을 넘었습니다. 오른쪽 패널에서 위험 신호를 분석해 보세요!", icon="🚨")
        st.session_state["_danger_alerted"] = True

    for m in messages[1:]:
        role = "user" if m["role"] == "user" else "assistant"
        with st.chat_message(role):
            st.markdown(m["content"])

    if prompt := st.chat_input(f"{user_label}의 메시지…"):
        messages.append({"role": "user", "content": prompt})
        # 새 메시지 입력 시 위험 신호 캐시 초기화 (재분석 유도)
        st.session_state.pop("_danger_report", None)

        api_key = os.environ.get("OPENAI_API_KEY", "").strip()
        client = OpenAI(api_key=api_key) if api_key else OpenAI()
        api_msgs = [{"role": x["role"], "content": x["content"]} for x in messages]
        with st.spinner("응답 생성 중…"):
            try:
                resp = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=api_msgs,
                    temperature=0.9,
                )
                text = resp.choices[0].message.content or ""
                messages.append({"role": "assistant", "content": text})
            except Exception as e:
                st.error(f"대화 오류: {e}")
        st.rerun()

with col_panel:
    st.subheader("도우미 패널")
    mode = st.radio(
        "모드",
        [m[0] for m in MODE_DEFS],
        format_func=lambda x: next(d[1] for d in MODE_DEFS if d[0] == x),
        horizontal=False,
    )
    st.caption(next(d[2] for d in MODE_DEFS if d[0] == mode))

    if mode == "ment":
        if st.button("짧은 멘트 추천", type="primary", use_container_width=True):
            with st.spinner("멘트 생성…"):
                try:
                    out = run_ment_suggestion(user_label, partner_name)
                    st.session_state["_coach_side_out"] = (
                        f"**{out['sentiment']}**\n\n{out['suggestion_text']}"
                    )
                except Exception as e:
                    st.session_state["_coach_side_out"] = f"오류: {e}"
        if "_coach_side_out" in st.session_state:
            st.markdown(st.session_state["_coach_side_out"])

    elif mode == "rag":
        if not conv_rag_available():
            st.error("`data/conv_samples.jsonl` 이 없습니다.")
        else:
            st.caption(
                "아래 버튼은 **① 유사 대화 예시 검색** → **② 그걸 바탕으로 조언 생성** 순서예요. "
                "검색 결과는 펼쳐서 확인할 수 있습니다. **첫 실행**에 임베딩 API가 잠깐 호출될 수 있어요."
            )
        if conv_rag_available() and st.button("유사 대화 예시 찾기 → 조언 받기", type="primary", use_container_width=True):
            try:
                partner_ctx, conv, ctx_block = prepare_rag_suggestion(user_label, partner_name)
                with st.expander("참고로 붙인 유사 대화 예시 (검색 결과)", expanded=True):
                    st.markdown(ctx_block)
                st.markdown("**코칭 조언**")
                with st.spinner("조언 생성…"):
                    st.write_stream(stream_rag_suggestion_prepared(partner_ctx, conv, ctx_block))
            except Exception as e:
                st.error(str(e))

    elif mode == "vote":
        if st.button("여러 조언 생성 후 투표", type="primary", use_container_width=True):
            with st.spinner("시간이 조금 걸릴 수 있어요…"):
                try:
                    for chunk in stream_vote_suggestion(messages, user_label, partner_name):
                        if isinstance(chunk, pd.DataFrame):
                            st.dataframe(chunk, use_container_width=True)
                        else:
                            st.write(chunk)
                except Exception as e:
                    st.error(str(e))

    elif mode == "danger":
        # [E] 위험 신호 감지 패널
        render_danger_panel(user_label, partner_name)

    st.divider()
    st.page_link("pages/02_프로필_매칭_검색.py", label="← 매칭으로 돌아가기", use_container_width=True)

render_trust_footer()
