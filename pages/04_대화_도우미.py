"""
통합 대화 도우미 — 멘트 추천, RAG, 투표형 조언.
[E] 대화 위험 신호 감지
[F] 참고 맥락: 붙여넣기 / 스크린샷 추출(비전) 각각 분리된 도우미·저장
"""
from __future__ import annotations

import base64
import html
import os
import re

import pandas as pd
import streamlit as st
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import JsonOutputParser, StrOutputParser
from langchain_core.prompts import ChatPromptTemplate, HumanMessagePromptTemplate
from openai import OpenAI
from pydantic import BaseModel, Field

from _match_context import (
    MATCHED_PROFILE_KEY,
    SELECTED_OPENING_MATCH_SIG_KEY,
    SELECTED_OPENING_MESSAGE_KEY,
    USER_AI_PROFILE_KEY,
    build_system_prompt,
    ensure_chat_session,
    journey_can_access,
    matched_profile_sig_str,
    partner_context_for_llm,
)
from _rag_conv import conv_rag_available, retrieve_similar_conversations
from _ui import JOURNEY_COACH, openai_key_configured, render_page_header, render_page_shell, render_trust_footer

MESSAGES_KEY = "messages_coach"
COACH_EXTERNAL_PASTE_KEY = "coach_external_paste"
COACH_EXTERNAL_PASTE_DRAFT_KEY = "coach_external_paste_draft"
COACH_VISION_TRANSCRIPT_KEY = "coach_vision_transcript"
COACH_VISION_TRANSCRIPT_DRAFT_KEY = "coach_vision_transcript_draft"
_CLEAR_COACH_PASTE_REQUEST = "_clear_coach_paste_request"
_CLEAR_COACH_VISION_REQUEST = "_clear_coach_vision_request"
COACH_OUT_PRACTICE = "_coach_side_out_practice"
COACH_OUT_REFERENCE_PASTE = "_coach_side_out_reference_paste"
COACH_OUT_REFERENCE_VISION = "_coach_side_out_reference_vision"
DANGER_REPORT_PRACTICE = "_danger_report_practice"
DANGER_REPORT_REFERENCE_PASTE = "_danger_report_reference_paste"
DANGER_REPORT_REFERENCE_VISION = "_danger_report_reference_vision"
COACH_SCENARIO_PRACTICE_KEY = "coach_scenario_context_practice"
COACH_SCENARIO_REFERENCE_KEY = "coach_scenario_context_reference"
COACH_DOMAIN_PRACTICE_KEY = "coach_conversation_domain_practice"
COACH_DOMAIN_REFERENCE_KEY = "coach_conversation_domain_reference"
COACH_DOMAIN_OTHER_HINT_PRACTICE = "coach_domain_other_hint_practice"
COACH_DOMAIN_OTHER_HINT_REFERENCE = "coach_domain_other_hint_reference"

OTHER_DOMAIN_ID = "other"

VOTE_UI_HTML = "vote_ui_html"

RAG_MODE_CAPTION = (
    "비슷한 **대화 샘플**을 찾은 뒤 코칭합니다. 시나리오에 샘플 **카테고리**(예: 답장 지연, 반응 애매함)를 쓰면 그 유형 위주로만 골라요. "
    "**첫 실행**에 임베딩 API가 잠깐 호출될 수 있어요."
)

# (id, UI 라벨, LLM용 코칭 규칙) — 멘트·투표·RAG·위험 분석에 공통 주입
CONVERSATION_DOMAINS: tuple[tuple[str, str, str], ...] = (
    (
        "dating_first_meet",
        "첫 만남·대면 (1:1)",
        "- **1:1** 소개팅·첫 만남 장면으로 해석한다.\n"
        "- 인사와 서로 알아가는 톤이 자연스럽다.\n"
        "- 상대 프로필(취미·관심사)은 **대화에서 그 주제가 나온 뒤**에만 짧게 연결한다.\n",
    ),
    (
        "dating_messenger",
        "만나기 전 카톡·DM",
        "- **만나기 전** 메신저로 연락하는 단계로 본다.\n"
        "- 짧고 예의 있는 문장, 과한 친밀·강요는 피한다.\n"
        "- **대화에 실제로 나온 내용**(약속, 장소, 시간)에만 맞춘다.\n",
    ),
    (
        "dating_after_meet",
        "만남 후 재연락",
        "- 이미 **한번 만난 뒤** 후속 연락 톤으로 본다.\n"
        "- 감사·인상·다음 만남 제안이 자연스러울 수 있다.\n"
        "- **대화에 언급된 것**에만 반응하고, 없는 일을 지어내지 않는다.\n",
    ),
    (
        "group_or_social_chat",
        "단체·오픈채·가벼운 메신저",
        "- **1:1 데이트**가 아니라 여럿이 오가는 방·모임·가벼운 단체맥락일 수 있다.\n"
        "- 짧은 응원·공감·안부가 어울릴 수 있으며, **로맨틱 1:1 소개팅 코칭 톤**으로 바꾸지 마라.\n"
        "- 프로필·소개팅 상대 정보는 **이 맥락과 무관하면 쓰지 마라.**\n",
    ),
    (
        "support_serious",
        "위로·건강·기도·진지한 주제",
        "- **통증, 가족, 건강, 기도 제목** 등 진지한 주제일 수 있다.\n"
        "- 가볍게 넘기거나 데이트용 농담으로 바꾸지 마라. **공감·경청·신중한 한두 문장**이 맞다.\n"
        "- 종교적 표현은 **대화에 그런 맥락이 있을 때만** 자연스럽게 허용한다.\n",
    ),
    (
        "tension_repair",
        "오해·갈등·사과",
        "- **오해, 실망, 거리두기** 등 민감한 구간으로 본다.\n"
        "- 방어·공격적 표현은 피하고, **사실 확인·사과·경청** 쪽을 우선한다.\n"
        "- 없었던 일·과장된 약속을 만들어내지 마라.\n",
    ),
    (
        OTHER_DOMAIN_ID,
        "기타",
        "- 아래 **사용자가 적은 기타 설명**(있다면)과 **실제 대화**를 근거로 톤·목표를 정한다.\n"
        "- 소개팅·1:1 데이트로 단정하지 말고, 설명이 비어 있으면 대화만 보고 중립적으로 맞춘다.\n"
        "- 대화에 없는 설정·주제를 만들어 붙이지 마라.\n",
    ),
)

_DOMAIN_IDS = [d[0] for d in CONVERSATION_DOMAINS]
_DOMAIN_LABELS = {d[0]: d[1] for d in CONVERSATION_DOMAINS}


def normalize_coach_domain_id(raw: str | None) -> str:
    rid = (raw or "").strip()
    if rid in _DOMAIN_IDS:
        return rid
    return CONVERSATION_DOMAINS[0][0]


def domain_instructions_block(domain_id: str | None, *, other_hint: str = "") -> str:
    did = normalize_coach_domain_id(domain_id)
    for xdid, _lab, instr in CONVERSATION_DOMAINS:
        if xdid == did:
            lab = _DOMAIN_LABELS.get(did, did)
            block = f"# 코칭 기준: 대화 유형\n(선택: {lab})\n{instr}\n\n"
            if did == OTHER_DOMAIN_ID:
                oh = (other_hint or "").strip()
                if oh:
                    block += f"## 사용자 지정(기타) 보조 설명\n{oh}\n\n"
            return block
    return domain_instructions_block(CONVERSATION_DOMAINS[0][0])


def domain_label(domain_id: str | None, other_hint: str = "") -> str:
    did = normalize_coach_domain_id(domain_id)
    base = _DOMAIN_LABELS.get(did, _DOMAIN_LABELS[CONVERSATION_DOMAINS[0][0]])
    if did != OTHER_DOMAIN_ID:
        return base
    oh = (other_hint or "").strip().replace("\n", " ")
    if oh:
        if len(oh) > 72:
            oh = oh[:69] + "…"
        return f"기타 ({oh})"
    return base


def ensure_coach_domain_session(key: str) -> None:
    if key not in st.session_state:
        st.session_state[key] = CONVERSATION_DOMAINS[0][0]
    elif st.session_state[key] not in _DOMAIN_IDS:
        st.session_state[key] = CONVERSATION_DOMAINS[0][0]


def render_coach_domain_expander(
    *,
    domain_session_key: str,
    other_hint_key: str,
    title: str,
    caption: str,
    other_placeholder: str = "예: 직장 동료와 업무 외 짧은 잡담, 선배–후배 관계",
) -> None:
    """배경·상황 설명과 동일하게 접이식 헤더 안에 대화 유형 선택을 둡니다."""
    ensure_coach_domain_session(domain_session_key)
    with st.expander(title, expanded=False):
        st.caption(caption)
        st.selectbox(
            "유형 선택",
            options=_DOMAIN_IDS,
            format_func=lambda x: _DOMAIN_LABELS[x],
            key=domain_session_key,
            label_visibility="collapsed",
        )
        if st.session_state.get(domain_session_key) == OTHER_DOMAIN_ID:
            st.text_area(
                "기타 — 코칭에 참고할 설명 (선택)",
                key=other_hint_key,
                height=72,
                placeholder=other_placeholder,
            )


def coach_scenario_plain(state_key: str) -> str:
    return (st.session_state.get(state_key) or "").strip()


def coach_scenario_section(state_key: str) -> str:
    s = coach_scenario_plain(state_key)
    if not s:
        return ""
    return f"# 사용자가 알려준 배경·상황\n{s}\n\n"


def _sentiment_chip_style(sentiment: str) -> str:
    """감정 라벨용 칩(버튼형) 인라인 스타일."""
    s = (sentiment or "").strip().lower()
    if "negative" in s:
        return (
            "background:linear-gradient(180deg,#fef2f2,#fecaca);color:#991b1b;"
            "border:1px solid #f87171;box-shadow:0 1px 3px rgba(185,28,28,0.15);"
        )
    if "positive" in s:
        return (
            "background:linear-gradient(180deg,#ecfdf5,#bbf7d0);color:#047857;"
            "border:1px solid #4ade80;box-shadow:0 1px 3px rgba(4,120,87,0.12);"
        )
    return (
        "background:linear-gradient(180deg,#f8fafc,#e2e8f0);color:#475569;"
        "border:1px solid #cbd5e1;box-shadow:0 1px 3px rgba(71,85,105,0.12);"
    )


def _vote_body_html(text: str) -> str:
    return html.escape(text or "").replace("\n", "<br/>")


def _ment_mood_chip_style(sentiment: str) -> str:
    """짧은 멘트의 분위기 한 단어용 칩. 영문 Positive 등은 투표 칩 색상 재사용."""
    if re.search(r"positive|negative|neutral", sentiment or "", re.I):
        return _sentiment_chip_style(sentiment)
    return (
        "background:linear-gradient(180deg,#fff7ed,#ffedd5);color:#9a3412;"
        "border:1px solid #fdba74;box-shadow:0 1px 3px rgba(154,52,18,0.12);"
    )


def format_ment_suggestion_html(sentiment: str, suggestion_text: str) -> str:
    """짧은 멘트: 분위기 칩 + 추천 문장 말풍선."""
    sent = (sentiment or "").strip()
    chip = _ment_mood_chip_style(sent)
    label = html.escape(sent or "—")
    inner = _vote_body_html(suggestion_text)
    return (
        '<div style="margin-top:6px;">'
        '<div style="margin-bottom:10px;">'
        f'<span style="display:inline-flex;align-items:center;justify-content:center;'
        f'padding:6px 16px;border-radius:9999px;font-size:0.8rem;font-weight:700;'
        f'letter-spacing:0.02em;user-select:none;{chip}\">{label}</span>'
        "</div>"
        '<div style="position:relative;display:inline-block;max-width:100%;">'
        '<div style="background:linear-gradient(165deg,#fffefb 0%,#fff5f5 100%);'
        "border:1px solid #edd8d8;border-radius:22px 22px 22px 10px;"
        "padding:16px 18px 18px;box-shadow:0 4px 18px rgba(124,45,18,0.08);"
        f'color:#3f2e1f;line-height:1.6;font-size:1rem;">{inner}</div>'
        '<span style="position:absolute;left:22px;bottom:-7px;width:12px;height:12px;'
        "background:linear-gradient(165deg,#fffefb 0%,#fff5f5 100%);"
        "border-right:1px solid #edd8d8;border-bottom:1px solid #edd8d8;"
        'transform:rotate(45deg);display:block;"></span>'
        "</div></div>"
    )


def render_coach_ment_output(state_key: str) -> None:
    """세션에 저장된 짧은 멘트( dict·구버전 문자열·오류 ) 표시."""
    raw = st.session_state.get(state_key)
    if raw is None:
        return
    if isinstance(raw, dict) and raw.get("_ment") is True:
        st.markdown(
            format_ment_suggestion_html(
                str(raw.get("sentiment", "") or ""),
                str(raw.get("text", "") or ""),
            ),
            unsafe_allow_html=True,
        )
        return
    if isinstance(raw, str):
        if raw.startswith("오류:"):
            st.error(raw)
        else:
            st.markdown(raw)
        return
    st.markdown(str(raw))


def _suggestion_field(s: object, key: str, default: str = "") -> str:
    if isinstance(s, dict):
        v = s.get(key, default)
    else:
        v = getattr(s, key, default)
    if v is None:
        return default
    return str(v)


def format_vote_candidates_html(suggestion_list: list) -> str:
    """투표 후보: 말풍선 + 감정 칩."""
    parts: list[str] = [
        '<p style="font-size:1.12rem;font-weight:800;color:#5c2c2c;margin:0 0 18px 0;">'
        "조언 후보</p>"
    ]
    for i, s in enumerate(suggestion_list):
        sent = _suggestion_field(s, "sentiment", "Neutral") or "Neutral"
        body = _suggestion_field(s, "suggestion_text", "")
        chip = _sentiment_chip_style(str(sent))
        label = html.escape(str(sent).strip() or "Neutral")
        inner = _vote_body_html(str(body))
        parts.append(
            f'<div style="margin-bottom:22px;">'
            f'<div style="display:flex;align-items:center;gap:10px;margin-bottom:10px;flex-wrap:wrap;">'
            f'<span style="font-weight:700;font-size:1rem;color:#7c2d12;">후보 {i}</span>'
            f'<span style="display:inline-flex;align-items:center;justify-content:center;'
            f"padding:6px 16px;border-radius:9999px;font-size:0.8rem;font-weight:700;"
            f"letter-spacing:0.02em;user-select:none;{chip}\">{label}</span>"
            f"</div>"
            f'<div style="position:relative;display:inline-block;max-width:100%;">'
            f'<div style="background:linear-gradient(165deg,#fffefb 0%,#fff5f5 100%);'
            f"border:1px solid #edd8d8;border-radius:22px 22px 22px 10px;"
            f"padding:16px 18px 18px;box-shadow:0 4px 18px rgba(124,45,18,0.08);"
            f'color:#3f2e1f;line-height:1.6;font-size:0.95rem;">{inner}</div>'
            f'<span style="position:absolute;left:22px;bottom:-7px;width:12px;height:12px;'
            f"background:linear-gradient(165deg,#fffefb 0%,#fff5f5 100%);"
            f"border-right:1px solid #edd8d8;border-bottom:1px solid #edd8d8;"
            f'transform:rotate(45deg);display:block;z-index:0;"></span>'
            f"</div></div>"
        )
    return "".join(parts)


def format_vote_best_html(best_n: int, best: object) -> str:
    """최종 추천: 말풍선 + 감정 칩 (강조 색)."""
    sent = _suggestion_field(best, "sentiment", "Neutral") or "Neutral"
    body = _suggestion_field(best, "suggestion_text", "")
    chip = _sentiment_chip_style(str(sent))
    label = html.escape(str(sent).strip() or "Neutral")
    inner = _vote_body_html(str(body))
    return (
        '<p style="font-size:1.12rem;font-weight:800;color:#15803d;margin:20px 0 14px 0;">'
        "추천 조언</p>"
        '<div style="margin-bottom:8px;">'
        '<div style="display:flex;align-items:center;gap:10px;margin-bottom:10px;flex-wrap:wrap;">'
        f'<span style="font-weight:700;color:#14532d;">선택: 후보 {best_n}</span>'
        f'<span style="display:inline-flex;align-items:center;justify-content:center;'
        f"padding:6px 16px;border-radius:9999px;font-size:0.8rem;font-weight:700;"
        f"letter-spacing:0.02em;user-select:none;{chip}\">{label}</span>"
        "</div>"
        '<div style="position:relative;display:inline-block;max-width:100%;">'
        '<div style="background:linear-gradient(165deg,#f0fdf4 0%,#ecfccb 100%);'
        "border:1px solid #86efac;border-radius:22px 22px 22px 10px;"
        "padding:16px 18px 18px;box-shadow:0 4px 18px rgba(21,128,61,0.12);"
        f'color:#14532d;line-height:1.6;font-size:0.95rem;">{inner}</div>'
        '<span style="position:absolute;left:22px;bottom:-7px;width:12px;height:12px;'
        "background:linear-gradient(165deg,#f0fdf4 0%,#ecfccb 100%);"
        "border-right:1px solid #86efac;border-bottom:1px solid #86efac;"
        'transform:rotate(45deg);display:block;"></span>'
        "</div></div>"
    )


def write_vote_suggestion_chunk(chunk) -> None:
    """투표형 조언 스트림 청크 렌더링 (HTML 말풍선 / 마크다운 / 표)."""
    if isinstance(chunk, pd.DataFrame):
        st.dataframe(chunk, use_container_width=True)
    elif isinstance(chunk, tuple) and len(chunk) == 2 and chunk[0] == VOTE_UI_HTML:
        st.markdown(chunk[1], unsafe_allow_html=True)
    else:
        st.markdown(str(chunk))


MODE_DEFS = [
    ("ment", "💬 한마디 추천", "지금 분위기에 맞는 **짧은 문장** 한두 개만 골라 줍니다."),
    (
        "rag",
        "📚 예시 대화 · 코칭",
        "비슷한 **대화 샘플**을 찾아 붙인 뒤, 그걸 참고해 **다음 멘트·태도**를 조언합니다.",
    ),
    ("vote", "🗳️ 조언 후보 비교", "여러 스타일의 **조언 초안**을 만든 다음, 가장 나은 하나를 고릅니다."),
    ("danger", "⚠️ 대화 패턴 점검", "한쪽 쏠림·무응·어조 등 **주의할 흐름**을 짚어 봅니다."),
]


def build_practice_conv(messages: list, user_label: str, partner_label: str) -> str:
    """연습 채팅 탭 전용: 앱 안 모의 대화만."""
    conv = ""
    for message in messages[1:]:
        name = user_label if message["role"] == "user" else partner_label
        conv += f"{name}: {message['content']}\n"
    return conv.strip()


def reset_practice_chat_messages() -> None:
    """연습 채팅을 시스템 프롬프트만 남기고 비우고, 연습 도우미 출력도 초기화."""
    match = st.session_state.get(MATCHED_PROFILE_KEY)
    user_me = st.session_state.get(USER_AI_PROFILE_KEY)
    if not isinstance(user_me, dict):
        user_me = None
    st.session_state[MESSAGES_KEY] = [
        {"role": "system", "content": build_system_prompt(match, user_me)},
    ]
    st.session_state.pop(DANGER_REPORT_PRACTICE, None)
    st.session_state.pop(COACH_OUT_PRACTICE, None)
    st.session_state.pop("_danger_alerted", None)
    st.session_state.pop("_practice_opening_seeded_sig", None)


def maybe_seed_practice_opening_from_step3(messages: list) -> None:
    """
    ③에서 고른 첫 인사말로 사용자 첫 턴을 넣고, 상대(assistant) 첫 답장을 한 번 생성한다.
    시스템 메시지만 있을 때 한 번만 수행한다.
    """
    if len(messages) != 1:
        return
    opening = (st.session_state.get(SELECTED_OPENING_MESSAGE_KEY) or "").strip()
    if not opening:
        return
    match = st.session_state.get(MATCHED_PROFILE_KEY)
    if not isinstance(match, dict):
        return
    msig = matched_profile_sig_str(match)
    if st.session_state.get(SELECTED_OPENING_MATCH_SIG_KEY) != msig:
        return
    seed_key = f"{msig}\n{opening}"
    if st.session_state.get("_practice_opening_seeded_sig") == seed_key:
        return

    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    client = OpenAI(api_key=api_key) if api_key else OpenAI()
    base_sys = messages[0]["content"]
    sc_chat = coach_scenario_plain(COACH_SCENARIO_PRACTICE_KEY)
    sys_content = (
        f"{base_sys}\n\n[이번 연습의 배경·상황]\n{sc_chat}" if sc_chat else base_sys
    )
    api_msgs = [
        {"role": "system", "content": sys_content},
        {"role": "user", "content": opening},
    ]
    try:
        with st.spinner("③에서 고른 인사말로 첫 대화를 준비하는 중…"):
            resp = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=api_msgs,
                temperature=0.9,
            )
            reply = (resp.choices[0].message.content or "").strip() or "…"
    except Exception as e:
        st.error(f"첫 답장 생성 실패: {e}")
        return

    messages.append({"role": "user", "content": opening})
    messages.append({"role": "assistant", "content": reply})
    st.session_state["_practice_opening_seeded_sig"] = seed_key
    st.rerun()


def build_reference_paste_conv() -> str:
    """참고 맥락 · 붙여넣기 전용."""
    return (st.session_state.get(COACH_EXTERNAL_PASTE_KEY) or "").strip()


def build_reference_vision_conv() -> str:
    """참고 맥락 · 스크린샷: 편집창(드래프트)에 글자가 있으면 그 내용을, 없으면 적용된 스크립트를 쓴다."""
    draft = (st.session_state.get(COACH_VISION_TRANSCRIPT_DRAFT_KEY) or "").strip()
    if draft:
        return draft
    return (st.session_state.get(COACH_VISION_TRANSCRIPT_KEY) or "").strip()


def run_vision_transcribe_screenshot(image_bytes: bytes, mime: str) -> str:
    """메신저 캡처에서 대화 텍스트를 읽어 옴 (gpt-4o 멀티모달)."""
    if not mime or mime == "application/octet-stream":
        mime = "image/jpeg"
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    client = OpenAI(api_key=api_key) if api_key else OpenAI()
    b64 = base64.standard_b64encode(image_bytes).decode("ascii")
    data_url = f"data:{mime};base64,{b64}"
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": (
                            "이 이미지는 모바일/PC 메신저 대화 캡처일 수 있다. "
                            "보이는 말풍선·대화를 읽어, 화자를 구분해 그대로 옮겨 적어라. "
                            "형식은 한 줄에 한 발화, 앞에 'A:' 'B:' 또는 앱에 보이는 이름을 붙여도 된다. "
                            "대화 텍스트가 거의 없으면 한 문장으로 그 사실만 알려라."
                        ),
                    },
                    {"type": "image_url", "image_url": {"url": data_url}},
                ],
            }
        ],
        max_tokens=1200,
        temperature=0.2,
    )
    return (resp.choices[0].message.content or "").strip()


class MentOut(BaseModel):
    sentiment: str = Field(
        description="분위기 한 단어(예: 인사, 가벼운 톤, 진지함, 위로, 단체·응원, 갈등·신중, 애매함)"
    )
    suggestion_text: str = Field(
        description="추천 발화: 위 대화에 실제로 등장한 주제·선택한 대화 유형에만 맞출 것"
    )


def run_ment_suggestion(
    user_label: str,
    partner_label: str,
    *,
    conv: str,
    source_blurb: str,
    scenario_section: str = "",
    domain_section: str = "",
) -> dict:
    match = st.session_state.get(MATCHED_PROFILE_KEY)

    model = ChatOpenAI(model="gpt-4o-mini", temperature=0.45)
    parser = JsonOutputParser(pydantic_object=MentOut)
    fmt = parser.get_format_instructions()
    partner_ctx = partner_context_for_llm(match, user_label)
    tpl = HumanMessagePromptTemplate.from_template(
        "{partner_ctx}\n\n"
        "{scenario_section}"
        "{domain_section}"
        "아래는 {source_blurb}\n"
        "{conv}\n"
        "---\n"
        "앱의 **전체 목적**은 만남·인간관계 연습이다. 위 **대화 유형**·배경·**실제 대화 텍스트**를 최우선으로 해석하고, "
        "유형과 어긋나게 '카페 소개팅 한 장면'만 상상하지 마라.\n\n"
        "【반드시 지킬 것】\n"
        "1) **대화에 실제로 나온 말에만** 이어 붙인다. 아무도 언급하지 않은 주제를 새로 꺼내지 마라.\n"
        "2) 아직 인사·안부·짧은 질문만 오갔다면, 상대의 **마지막 발화에 답하거나** 그 유형에 맞는 짧은 반응만 추천한다.\n"
        "3) **상대 프로필**은 참고용이다. 인사·첫 질문 단계이거나 단체·위로 맥락이면 프로필을 멘트에 끌어오지 마라.\n"
        "4) 추천 멘트는 한두 문장, 과장·추가 설정 금지.\n"
        "{name}가 지금 이어서 하면 좋을 **짧은 멘트 한 가지**를 추천하라.\n"
        "{format_instructions}"
    )
    chain = ChatPromptTemplate.from_messages([tpl]).partial(format_instructions=fmt) | model | parser
    return chain.invoke(
        {
            "conv": conv,
            "name": user_label,
            "partner_ctx": partner_ctx,
            "source_blurb": source_blurb,
            "scenario_section": scenario_section or "",
            "domain_section": domain_section or "",
        }
    )


class Suggestion(BaseModel):
    sentiment: str = Field(description="Positive, Negative, Neutral")
    suggestion_text: str = Field(description="markdown 형식의 조언")


def stream_vote_suggestion(
    conv: str,
    user_label: str,
    partner_label: str,
    num_candi: int = 5,
    *,
    scenario_section: str = "",
    domain_section: str = "",
    source_blurb: str = "",
):
    match = st.session_state.get(MATCHED_PROFILE_KEY)
    partner_ctx = partner_context_for_llm(match, user_label)

    eval_model = ChatOpenAI(model="gpt-4o", temperature=0.8)
    basic_model = ChatOpenAI(model="gpt-4o-mini", temperature=0.8)

    parser = JsonOutputParser(pydantic_object=Suggestion)
    fmt = parser.get_format_instructions()
    human1 = HumanMessagePromptTemplate.from_template(
        "{partner_ctx}\n\n"
        "{scenario_section}"
        "{domain_section}"
        "아래는 {source_blurb}\n\n"
        "{conv}\n\n"
        "**반드시:** 조언은 **위에 인용한 대화 텍스트만** 근거로 한다. 앱의 **연습 채팅**이나 **다른 참고 맥락 탭**의 대화를 상상·인용하지 마라.\n"
        "위 대화를 **선택한 대화 유형**에 맞게 분석하고 {name}에게 markdown으로 적절한 조언을 하라. "
        "1:1 소개팅만 전제로 하지 마라.\n"
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
        "{scenario_section}"
        "{domain_section}"
        "아래는 {source_blurb}\n\n"
        "{conv}\n\n"
        "후보 선택 시에도 **위 인용 대화만** 기준으로 삼는다. 연습 채팅 등 다른 출처를 끌어오지 마라.\n"
        "아래는 {name}에게 하면 좋을 조언 후보들이다. **대화 유형**에 가장 잘 맞는 하나를 고르고 번호를 응답하라.\n"
        "{candidates}\n"
        "{format_instructions}"
    )
    vote_chain = ChatPromptTemplate.from_messages([human2]).partial(format_instructions=vfmt) | eval_model | vparser

    batch_common = {
        "conv": conv,
        "name": user_label,
        "partner_ctx": partner_ctx,
        "scenario_section": scenario_section or "",
        "domain_section": domain_section or "",
        "source_blurb": source_blurb or "제시된 대화 로그이다.",
    }
    suggestion_list = gen_chain.batch([dict(batch_common) for _ in range(num_candi)])
    yield (VOTE_UI_HTML, format_vote_candidates_html(suggestion_list))
    cand_text = "\n\n".join(
        [
            f"후보 {i}.\n감정: {s.get('sentiment', '')}\n{s.get('suggestion_text', '')}"
            for i, s in enumerate(suggestion_list)
        ]
    )
    vote_row = {
        "conv": conv,
        "name": user_label,
        "candidates": cand_text,
        "partner_ctx": partner_ctx,
        "scenario_section": scenario_section or "",
        "domain_section": domain_section or "",
        "source_blurb": batch_common["source_blurb"],
    }
    votes = vote_chain.batch([dict(vote_row) for _ in range(num_candi)])
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
    yield (VOTE_UI_HTML, format_vote_best_html(best_n, best))


def prepare_rag_suggestion(
    user_label: str,
    partner_label: str,
    conv: str,
    *,
    scenario_hint: str = "",
    domain_id: str | None = None,
    domain_other_hint: str = "",
) -> tuple[str, str, str]:
    match = st.session_state.get(MATCHED_PROFILE_KEY)
    partner_ctx = partner_context_for_llm(match, user_label)

    base = conv.strip() or "소개팅에서 처음 만나는 대화"
    sh = (scenario_hint or "").strip()
    query = f"{base}\n{sh}" if sh else base
    dom_lab = domain_label(domain_id, domain_other_hint)
    query = f"{query}\n(코칭 맥락: {dom_lab})"
    context = retrieve_similar_conversations(query, k=4)
    if not context.strip():
        context = "(유사 샘플을 찾지 못했습니다. 일반적인 조언만 해 주세요.)"
    return partner_ctx, conv, context


def stream_rag_suggestion_prepared(
    partner_ctx: str,
    conv: str,
    context: str,
    *,
    scenario_section: str = "",
    domain_section: str = "",
):
    model = ChatOpenAI(model="gpt-4o", temperature=0.8)
    template = """
{partner_ctx}

{scenario_section}{domain_section}# 현재 대화
{conv}

# 검색으로 붙인 유사 대화 예시 (참고용 스크립트)
{context}

위 **유사 대화 예시**를 한두 문장으로 짚어 왜 참고가 됐는지 말한 뒤,
**선택한 대화 유형**·배경·현재 대화에 맞는 **짧은 코칭 조언**(다음에 할 말·태도)을 해줘.
1:1 소개팅만 전제로 하지 마라. 조언은 불릿 2~3개 정도로.
"""
    prompt = ChatPromptTemplate.from_template(template).partial(
        partner_ctx=partner_ctx,
        conv=conv,
        context=context,
        scenario_section=scenario_section or "",
        domain_section=domain_section or "",
    )
    chain = prompt | model | StrOutputParser()
    return chain.stream({})


def parse_rag_context_blocks(context: str) -> list[tuple[str, str]]:
    """`retrieve_similar_conversations` 문자열 → (헤더 키, 본문). 헤더 없으면 ('plain', 전체)."""
    c = (context or "").strip()
    if not c:
        return []
    chunks = re.split(r"\n\n---\n\n", c)
    out: list[tuple[str, str]] = []
    for ch in chunks:
        ch = ch.strip()
        if not ch:
            continue
        lines = ch.split("\n", 1)
        first = lines[0].strip()
        if first.startswith("[참고 대화 예시"):
            rest = lines[1].strip() if len(lines) > 1 else ""
            out.append((first, rest))
        else:
            out.append(("plain", ch))
    return out


def _rag_example_badge_label(header: str) -> str:
    m = re.match(r"\[참고 대화 예시\s*(\d+)\]", header.strip())
    if m:
        return f"예시 {m.group(1)}"
    return "참고"


def format_rag_examples_html(context: str) -> str:
    """유사 대화 예시: 칩 라벨 + 말풍선 카드."""
    blocks = parse_rag_context_blocks(context)
    if not blocks:
        return '<p style="color:#64748b;margin:0;">검색 결과가 없습니다.</p>'

    if len(blocks) == 1 and blocks[0][0] == "plain":
        body = blocks[0][1]
        if "찾지 못했" in body:
            esc = html.escape(body)
            return (
                '<div style="padding:14px 16px;border-radius:14px;background:#fffbeb;'
                'border:1px solid #fcd34d;color:#78350f;line-height:1.55;font-size:0.92rem;">'
                f"{esc}</div>"
            )

    parts: list[str] = [
        '<p style="font-size:1.02rem;font-weight:800;color:#3730a3;margin:0 0 14px 0;">'
        "검색 유사 대화</p>"
    ]
    for header, body in blocks:
        if header == "plain":
            badge = "참고"
            text = body
        else:
            badge = _rag_example_badge_label(header)
            text = body
        body_esc = html.escape(text or "").replace("\n", "<br/>")
        badge_esc = html.escape(badge)
        parts.append(
            f'<div style="margin-bottom:20px;">'
            f'<div style="margin-bottom:8px;">'
            f'<span style="display:inline-flex;align-items:center;justify-content:center;'
            f'padding:6px 14px;border-radius:9999px;font-size:0.78rem;font-weight:700;'
            f'letter-spacing:0.02em;user-select:none;'
            f'background:linear-gradient(180deg,#eef2ff,#e0e7ff);color:#3730a3;'
            f'border:1px solid #a5b4fc;box-shadow:0 1px 3px rgba(55,48,163,0.12);">'
            f"{badge_esc}</span></div>"
            f'<div style="position:relative;display:inline-block;max-width:100%;">'
            f'<div style="background:linear-gradient(165deg,#f8fafc 0%,#f1f5f9 100%);'
            f"border:1px solid #cbd5e1;border-radius:22px 22px 22px 10px;"
            f"padding:15px 17px 17px;box-shadow:0 4px 16px rgba(51,65,85,0.1);"
            f'color:#1e293b;line-height:1.6;font-size:0.93rem;">{body_esc}</div>'
            f'<span style="position:absolute;left:22px;bottom:-7px;width:12px;height:12px;'
            f"background:linear-gradient(165deg,#f8fafc 0%,#f1f5f9 100%);"
            f"border-right:1px solid #cbd5e1;border-bottom:1px solid #cbd5e1;"
            f'transform:rotate(45deg);display:block;"></span>'
            f"</div></div>"
        )
    return "".join(parts)


def render_rag_examples_panel(context: str) -> None:
    st.markdown(format_rag_examples_html(context), unsafe_allow_html=True)


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
def analyze_danger_signals(
    conv_text: str,
    user_label: str,
    scenario_hint: str = "",
    domain_section: str = "",
) -> dict:
    """대화에서 위험 신호 감지 (캐시 적용)."""
    model = ChatOpenAI(model="gpt-4o-mini", temperature=0.1)
    parser = JsonOutputParser(pydantic_object=DangerReport)
    fmt = parser.get_format_instructions()
    scen = (scenario_hint or "").strip() or "(없음)"
    dom = (domain_section or "").strip()

    prompt = ChatPromptTemplate.from_template(
        "대화에서 위험·불균형 신호를 감지하라. {user_label} 관점에서 평가.\n\n"
        "{domain_section}"
        "사용자가 알려준 배경·상황(있다면 참고):\n{scenario}\n\n"
        "대화:\n{conv}\n\n"
        "**대화 유형**에 맞게 '위험'의 의미를 조정하라. "
        "(예: 단체·위로 맥락에서는 가벼운 응원을 데이트 실패처럼 과대평가하지 마라. "
        "1:1 만남·사적 연락에서는 프라이버시·과도한 친밀·강요를 더 엄격히 본다.)\n\n"
        "분석 기준:\n"
        "1. 한쪽 쏠림: 한 사람이 질문·발화를 독점하는 정도\n"
        "2. 개인정보 위험: 전화번호·주소·직장 등 민감 정보 요구\n"
        "3. 어조 위험: 강압적·공격적·과도하게 친밀한 표현\n"
        "4. 대화 단절 위험: 무응답·단답·관심 없는 신호\n\n"
        "대화가 짧거나 아직 인사 단계라면 위험 수준을 '낮음'으로 평가하라.\n"
        "{format_instructions}"
    )
    chain = prompt.partial(format_instructions=fmt) | model | parser
    return chain.invoke(
        {
            "conv": conv_text,
            "user_label": user_label,
            "scenario": scen,
            "domain_section": dom + "\n\n" if dom else "",
        }
    )


def render_danger_panel(
    user_label: str,
    partner_label: str,
    *,
    conv: str,
    report_state_key: str,
    analyze_button_key: str,
    empty_hint: str,
    scenario_hint: str = "",
    domain_section: str = "",
):
    """[E] 위험 신호 분석 패널 (연습/참고 탭별로 키 분리)."""
    if not conv.strip():
        st.info(empty_hint)
        return

    if st.button(
        "⚠️ 대화 패턴 분석",
        type="primary",
        use_container_width=True,
        key=analyze_button_key,
    ):
        with st.spinner("대화 패턴을 분석 중…"):
            try:
                report = analyze_danger_signals(
                    conv,
                    user_label,
                    scenario_hint=scenario_hint,
                    domain_section=domain_section,
                )
                st.session_state[report_state_key] = report
                st.rerun()
            except Exception as e:
                st.error(f"분석 오류: {e}")

    report = st.session_state.get(report_state_key)
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

st.set_page_config(page_title="통합 데이팅 AI", layout="wide", page_icon="💬")
render_page_shell(journey_step=JOURNEY_COACH)

_ok4, _msg4 = journey_can_access("coach")
if not _ok4:
    st.error(_msg4)
    ca, cb, cc = st.columns(3)
    with ca:
        st.page_link("pages/01_AI_프로필_생성.py", label="① 프로필", use_container_width=True)
    with cb:
        st.page_link("pages/02_프로필_매칭_검색.py", label="② 매칭", use_container_width=True)
    with cc:
        st.page_link("pages/03_인사말_생성.py", label="③ 인사말", use_container_width=True)
    render_trust_footer()
    st.stop()

MENT_SOURCE_PRACTICE = "앱 안 **연습 채팅**에서 주고받은 대화이다."
MENT_SOURCE_REFERENCE_PASTE = "**카톡·메신저 등에서 붙여넣은** 대화 텍스트이다 (연습·스크린샷 추출과 별도)."
MENT_SOURCE_REFERENCE_VISION = "**스크린샷에서 추출·편집한** 대화 텍스트이다 (연습·붙여넣기와 별도)."

render_page_header(
    kicker="Step ④ · 대화",
    title="대화 연습 · 코칭",
    subtitle="**연습 채팅**과 **참고 맥락**은 분리되어 있으며, 각 탭의 **배경·상황** 입력이 도우미·연습 상대 응답에 반영됩니다. 참고 맥락에서는 **붙여넣기**와 **스크린샷 추출**이 전용 도우미·저장으로 나뉩니다.",
)

if not openai_key_configured():
    st.error("OpenAI API 키가 설정되어 있지 않습니다. 홈의 **API 키 설정**을 확인해 주세요.")
    st.page_link("app.py", label="홈으로 가기", use_container_width=True)
    try:
        from _persistence import save_session_to_disk

        save_session_to_disk()
    except Exception:
        pass
    st.stop()

try:
    from _env import load_optional_dotenv
    load_optional_dotenv()
except ImportError:
    pass

user_label, partner_name, ai_avatar = ensure_chat_session(st, MESSAGES_KEY)
messages = st.session_state[MESSAGES_KEY]
maybe_seed_practice_opening_from_step3(messages)

# 위젯(key) 생성 전에만 외부 맥락 키를 지울 수 있음 (내용 지우기 버튼은 플래그 + rerun 후 여기서 처리)
if st.session_state.pop(_CLEAR_COACH_PASTE_REQUEST, False):
    st.session_state.pop(COACH_EXTERNAL_PASTE_KEY, None)
    st.session_state.pop(COACH_EXTERNAL_PASTE_DRAFT_KEY, None)
    st.session_state.pop(COACH_OUT_REFERENCE_PASTE, None)
    st.session_state.pop(DANGER_REPORT_REFERENCE_PASTE, None)
if st.session_state.pop(_CLEAR_COACH_VISION_REQUEST, False):
    st.session_state.pop(COACH_VISION_TRANSCRIPT_KEY, None)
    st.session_state.pop(COACH_VISION_TRANSCRIPT_DRAFT_KEY, None)
    st.session_state.pop(COACH_OUT_REFERENCE_VISION, None)
    st.session_state.pop(DANGER_REPORT_REFERENCE_VISION, None)

match = st.session_state.get(MATCHED_PROFILE_KEY)
if match:
    st.caption(f"연결된 상대: **{match.get('name')}** · {ai_avatar}")
else:
    st.info("매칭 프로필이 없으면 기본 페르소나(수연)로 대화합니다. ②에서 상대를 고르면 연결됩니다.")

if COACH_VISION_TRANSCRIPT_KEY not in st.session_state:
    st.session_state[COACH_VISION_TRANSCRIPT_KEY] = ""
if COACH_VISION_TRANSCRIPT_DRAFT_KEY not in st.session_state:
    st.session_state[COACH_VISION_TRANSCRIPT_DRAFT_KEY] = (
        st.session_state.get(COACH_VISION_TRANSCRIPT_KEY) or ""
    )

if COACH_EXTERNAL_PASTE_DRAFT_KEY not in st.session_state:
    st.session_state[COACH_EXTERNAL_PASTE_DRAFT_KEY] = (
        st.session_state.get(COACH_EXTERNAL_PASTE_KEY) or ""
    )

tab_practice, tab_reference = st.tabs(["연습 채팅", "참고 맥락"])

# ── 연습 채팅 탭 ─────────────────────────────────────────
with tab_practice:
    st.caption("이 탭의 도우미는 **앱 안 연습 대화**만 사용합니다. 참고 맥락 탭 데이터와 섞이지 않습니다.")
    conv_p = build_practice_conv(messages, user_label, partner_name)
    col_chat, col_panel = st.columns([3, 2], gap="large")

    with col_chat:
        with st.container(border=True):
            rh1, rh2 = st.columns([2, 1])
            with rh1:
                st.markdown("**🎭 상대 역할과 주고받기**")
            with rh2:
                if st.button(
                    "연습 초기화",
                    use_container_width=True,
                    key="practice_chat_reset",
                    help="대화를 지우고 현재 매칭·프로필 기준으로 처음부터 연습합니다.",
                ):
                    reset_practice_chat_messages()
                    st.toast("연습 대화를 초기화했습니다.", icon="🔄")
                    st.rerun()
            st.caption("아래 입력은 **연습 전용**입니다. 카톡 로그는 **참고 맥락** 탭에서 다룹니다.")
            with st.expander("배경·상황 설명 (선택)", expanded=False):
                st.caption(
                    "장소, 관계(첫만남·재회), 분위기 등을 적으면 **연습 상대(챗) 응답**과 오른쪽 **도우미**가 맞춰집니다."
                )
                st.text_area(
                    "연습 배경 맥락",
                    key=COACH_SCENARIO_PRACTICE_KEY,
                    height=88,
                    placeholder="예: 첫 소개팅, 조용한 카페, 서로 어색한 편",
                )

            render_coach_domain_expander(
                domain_session_key=COACH_DOMAIN_PRACTICE_KEY,
                other_hint_key=COACH_DOMAIN_OTHER_HINT_PRACTICE,
                title="대화 유형 (선택)",
                caption=(
                    "첫만남·카톡·단체·위로 등 **맥락**에 맞춰 멘트·코칭 톤이 달라집니다. "
                    "오른쪽 도우미에도 동일하게 적용됩니다."
                ),
            )

            user_turns = sum(1 for m in messages[1:] if m["role"] == "user")
            if user_turns >= 5 and not st.session_state.get("_danger_alerted"):
                st.toast("💡 연습이 5턴을 넘었습니다. 오른쪽에서 대화 패턴 점검을 써 보세요!", icon="⚠️")
                st.session_state["_danger_alerted"] = True

            for m in messages[1:]:
                role = "user" if m["role"] == "user" else "assistant"
                with st.chat_message(role):
                    st.markdown(m["content"])

            if prompt := st.chat_input(f"연습 · {user_label}의 메시지…", key="chat_input_practice"):
                messages.append({"role": "user", "content": prompt})
                st.session_state.pop(DANGER_REPORT_PRACTICE, None)

                api_key = os.environ.get("OPENAI_API_KEY", "").strip()
                client = OpenAI(api_key=api_key) if api_key else OpenAI()
                base_sys = messages[0]["content"]
                sc_chat = coach_scenario_plain(COACH_SCENARIO_PRACTICE_KEY)
                sys_content = (
                    f"{base_sys}\n\n[이번 연습의 배경·상황]\n{sc_chat}" if sc_chat else base_sys
                )
                api_msgs = [{"role": "system", "content": sys_content}] + [
                    {"role": x["role"], "content": x["content"]} for x in messages[1:]
                ]
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
        sc_sec_practice = coach_scenario_section(COACH_SCENARIO_PRACTICE_KEY)
        sc_plain_practice = coach_scenario_plain(COACH_SCENARIO_PRACTICE_KEY)
        ensure_coach_domain_session(COACH_DOMAIN_PRACTICE_KEY)
        dom_id_practice = normalize_coach_domain_id(st.session_state.get(COACH_DOMAIN_PRACTICE_KEY))
        _hint_p = (st.session_state.get(COACH_DOMAIN_OTHER_HINT_PRACTICE) or "").strip()
        dom_sec_practice = domain_instructions_block(
            dom_id_practice,
            other_hint=_hint_p if dom_id_practice == OTHER_DOMAIN_ID else "",
        )
        st.subheader("도우미 (연습)")
        st.caption(
            "맥락: **연습 채팅만** · 왼쪽 **대화 유형·배경·상황**이 있으면 함께 반영됩니다."
        )
        mode_p = st.radio(
            "모드",
            [m[0] for m in MODE_DEFS],
            format_func=lambda x: next(d[1] for d in MODE_DEFS if d[0] == x),
            horizontal=False,
            key="coach_mode_practice",
        )
        st.caption(next(d[2] for d in MODE_DEFS if d[0] == mode_p))

        if mode_p == "ment":
            if st.button("한마디 추천", type="primary", use_container_width=True, key="ment_practice"):
                if not conv_p:
                    st.warning("먼저 왼쪽에서 **연습 채팅**을 이어 가 주세요.")
                else:
                    with st.spinner("멘트 생성…"):
                        try:
                            out = run_ment_suggestion(
                                user_label,
                                partner_name,
                                conv=conv_p,
                                source_blurb=MENT_SOURCE_PRACTICE,
                                scenario_section=sc_sec_practice,
                                domain_section=dom_sec_practice,
                            )
                            st.session_state[COACH_OUT_PRACTICE] = {
                                "_ment": True,
                                "sentiment": out["sentiment"],
                                "text": out["suggestion_text"],
                            }
                        except Exception as e:
                            st.session_state[COACH_OUT_PRACTICE] = f"오류: {e}"
            render_coach_ment_output(COACH_OUT_PRACTICE)

        elif mode_p == "rag":
            if not conv_rag_available():
                st.error("`data/conv_samples.jsonl` 이 없습니다.")
            else:
                st.caption(RAG_MODE_CAPTION)
            if conv_rag_available() and st.button(
                "예시 찾고 코칭 받기",
                type="primary",
                use_container_width=True,
                key="rag_practice",
            ):
                if not conv_p:
                    st.warning("먼저 왼쪽에서 **연습 채팅**을 이어 가 주세요.")
                else:
                    try:
                        partner_ctx, conv_r, ctx_block = prepare_rag_suggestion(
                            user_label,
                            partner_name,
                            conv_p,
                            scenario_hint=sc_plain_practice,
                            domain_id=dom_id_practice,
                            domain_other_hint=_hint_p if dom_id_practice == OTHER_DOMAIN_ID else "",
                        )
                        with st.expander("유사 대화 예시 · 검색 결과", expanded=True):
                            render_rag_examples_panel(ctx_block)
                        with st.container(border=True):
                            st.markdown("**코칭 조언**")
                            with st.spinner("조언 생성…"):
                                st.write_stream(
                                    stream_rag_suggestion_prepared(
                                        partner_ctx,
                                        conv_r,
                                        ctx_block,
                                        scenario_section=sc_sec_practice,
                                        domain_section=dom_sec_practice,
                                    )
                                )
                    except Exception as e:
                        st.error(str(e))

        elif mode_p == "vote":
            if st.button(
                "조언 후보 만들고 투표",
                type="primary",
                use_container_width=True,
                key="vote_practice",
            ):
                if not conv_p:
                    st.warning("먼저 왼쪽에서 **연습 채팅**을 이어 가 주세요.")
                else:
                    with st.spinner("시간이 조금 걸릴 수 있어요…"):
                        try:
                            for chunk in stream_vote_suggestion(
                                conv_p,
                                user_label,
                                partner_name,
                                scenario_section=sc_sec_practice,
                                domain_section=dom_sec_practice,
                                source_blurb=MENT_SOURCE_PRACTICE,
                            ):
                                write_vote_suggestion_chunk(chunk)
                        except Exception as e:
                            st.error(str(e))

        elif mode_p == "danger":
            render_danger_panel(
                user_label,
                partner_name,
                conv=conv_p,
                report_state_key=DANGER_REPORT_PRACTICE,
                analyze_button_key="danger_analyze_practice",
                empty_hint="분석할 **연습 대화**가 없습니다. 왼쪽에서 채팅을 시작해 주세요.",
                scenario_hint=sc_plain_practice,
                domain_section=dom_sec_practice,
            )

# ── 참고 맥락 탭 (붙여넣기 / 스크린샷 분리) ─────────────────
with tab_reference:
    st.caption(
        "연습 채팅과 섞이지 않습니다. 아래 **붙여넣기**와 **스크린샷**은 서로 다른 맥락·도우미 결과로 관리됩니다."
    )
    with st.expander("배경·상황 설명 (선택)", expanded=False):
        st.caption(
            "대화가 나온 **상황**(예: 약속 조율, 첫 인사, 오해)을 적으면 붙여넣기·스크린샷 **도우미**가 더 맞춰집니다."
        )
        st.text_area(
            "참고 맥락 배경",
            key=COACH_SCENARIO_REFERENCE_KEY,
            height=88,
            placeholder="예: 카톡으로 약속 잡는 중, 상대가 답이 짧음",
        )
    render_coach_domain_expander(
        domain_session_key=COACH_DOMAIN_REFERENCE_KEY,
        other_hint_key=COACH_DOMAIN_OTHER_HINT_REFERENCE,
        title="대화 유형 (선택)",
        caption="붙여넣기·스크린샷 **도우미**에 공통 적용됩니다. 맥락에 맞는 유형을 고르면 코칭 톤이 맞춰집니다.",
        other_placeholder="예: 가족 단톡에서 건강 이야기 중",
    )
    sc_sec_ref = coach_scenario_section(COACH_SCENARIO_REFERENCE_KEY)
    sc_plain_ref = coach_scenario_plain(COACH_SCENARIO_REFERENCE_KEY)
    ensure_coach_domain_session(COACH_DOMAIN_REFERENCE_KEY)
    dom_id_ref = normalize_coach_domain_id(st.session_state.get(COACH_DOMAIN_REFERENCE_KEY))
    _hint_r = (st.session_state.get(COACH_DOMAIN_OTHER_HINT_REFERENCE) or "").strip()
    dom_sec_ref = domain_instructions_block(
        dom_id_ref,
        other_hint=_hint_r if dom_id_ref == OTHER_DOMAIN_ID else "",
    )
    sub_paste, sub_vision = st.tabs(["붙여넣기", "스크린샷"])

    with sub_paste:
        cp1, cp2 = st.columns([3, 2], gap="large")
        with cp1:
            with st.container(border=True):
                st.markdown("**📋 붙여넣기 맥락**")
                st.caption(
                    "카톡·메신저 로그를 붙인 뒤 **적용**을 눌러야 오른쪽 도우미 맥락에 반영됩니다. "
                    "스크린샷 탭과 데이터가 섞이지 않습니다."
                )
                st.text_area(
                    "붙여넣기",
                    key=COACH_EXTERNAL_PASTE_DRAFT_KEY,
                    height=180,
                    placeholder="예: 나: 오늘 시간 돼?\n상대: 응 7시 어때",
                )
                ap1, ap2 = st.columns(2)
                with ap1:
                    if st.button(
                        "적용",
                        type="primary",
                        use_container_width=True,
                        key="coach_apply_paste_ref",
                    ):
                        st.session_state[COACH_EXTERNAL_PASTE_KEY] = (
                            st.session_state.get(COACH_EXTERNAL_PASTE_DRAFT_KEY) or ""
                        )
                        st.session_state.pop(COACH_OUT_REFERENCE_PASTE, None)
                        st.session_state.pop(DANGER_REPORT_REFERENCE_PASTE, None)
                        st.toast("도우미 맥락에 반영되었습니다.", icon="✅")
                        st.rerun()
                with ap2:
                    if st.button(
                        "내용 지우기",
                        use_container_width=True,
                        key="coach_clear_paste_ref",
                    ):
                        st.session_state[_CLEAR_COACH_PASTE_REQUEST] = True
                        st.rerun()

        conv_paste = build_reference_paste_conv()
        with cp2:
            st.subheader("도우미 (붙여넣기)")
            st.caption("맥락: **적용**한 붙여넣기 · 위 **배경·상황**이 있으면 함께 반영됩니다.")
            mode_rp = st.radio(
                "모드",
                [m[0] for m in MODE_DEFS],
                format_func=lambda x: next(d[1] for d in MODE_DEFS if d[0] == x),
                horizontal=False,
                key="coach_mode_ref_paste",
            )
            st.caption(next(d[2] for d in MODE_DEFS if d[0] == mode_rp))

            if mode_rp == "ment":
                if st.button("한마디 추천", type="primary", use_container_width=True, key="ment_ref_paste"):
                    if not conv_paste:
                        st.warning("왼쪽에 대화를 붙인 뒤 **적용**을 눌러 주세요.")
                    else:
                        with st.spinner("멘트 생성…"):
                            try:
                                out = run_ment_suggestion(
                                    user_label,
                                    partner_name,
                                    conv=conv_paste,
                                    source_blurb=MENT_SOURCE_REFERENCE_PASTE,
                                    scenario_section=sc_sec_ref,
                                    domain_section=dom_sec_ref,
                                )
                                st.session_state[COACH_OUT_REFERENCE_PASTE] = {
                                    "_ment": True,
                                    "sentiment": out["sentiment"],
                                    "text": out["suggestion_text"],
                                }
                            except Exception as e:
                                st.session_state[COACH_OUT_REFERENCE_PASTE] = f"오류: {e}"
                render_coach_ment_output(COACH_OUT_REFERENCE_PASTE)

            elif mode_rp == "rag":
                if not conv_rag_available():
                    st.error("`data/conv_samples.jsonl` 이 없습니다.")
                else:
                    st.caption(RAG_MODE_CAPTION)
                if conv_rag_available() and st.button(
                    "예시 찾고 코칭 받기",
                    type="primary",
                    use_container_width=True,
                    key="rag_ref_paste",
                ):
                    if not conv_paste:
                        st.warning("왼쪽에 대화를 붙인 뒤 **적용**을 눌러 주세요.")
                    else:
                        try:
                            partner_ctx, conv_rb, ctx_block = prepare_rag_suggestion(
                                user_label,
                                partner_name,
                                conv_paste,
                                scenario_hint=sc_plain_ref,
                                domain_id=dom_id_ref,
                                domain_other_hint=_hint_r if dom_id_ref == OTHER_DOMAIN_ID else "",
                            )
                            with st.expander("유사 대화 예시 · 검색 결과", expanded=True):
                                render_rag_examples_panel(ctx_block)
                            with st.container(border=True):
                                st.markdown("**코칭 조언**")
                                with st.spinner("조언 생성…"):
                                    st.write_stream(
                                        stream_rag_suggestion_prepared(
                                            partner_ctx,
                                            conv_rb,
                                            ctx_block,
                                            scenario_section=sc_sec_ref,
                                            domain_section=dom_sec_ref,
                                        )
                                    )
                        except Exception as e:
                            st.error(str(e))

            elif mode_rp == "vote":
                if st.button(
                    "조언 후보 만들고 투표",
                    type="primary",
                    use_container_width=True,
                    key="vote_ref_paste",
                ):
                    if not conv_paste:
                        st.warning("왼쪽에 대화를 붙인 뒤 **적용**을 눌러 주세요.")
                    else:
                        with st.spinner("시간이 조금 걸릴 수 있어요…"):
                            try:
                                for chunk in stream_vote_suggestion(
                                    conv_paste,
                                    user_label,
                                    partner_name,
                                    scenario_section=sc_sec_ref,
                                    domain_section=dom_sec_ref,
                                    source_blurb=MENT_SOURCE_REFERENCE_PASTE,
                                ):
                                    write_vote_suggestion_chunk(chunk)
                            except Exception as e:
                                st.error(str(e))

            elif mode_rp == "danger":
                render_danger_panel(
                    user_label,
                    partner_name,
                    conv=conv_paste,
                    report_state_key=DANGER_REPORT_REFERENCE_PASTE,
                    analyze_button_key="danger_analyze_ref_paste",
                    empty_hint="분석할 텍스트가 없습니다. 왼쪽에 붙인 뒤 **적용**을 눌러 주세요.",
                    scenario_hint=sc_plain_ref,
                    domain_section=dom_sec_ref,
                )

    with sub_vision:
        cv1, cv2 = st.columns([3, 2], gap="large")
        with cv1:
            with st.container(border=True):
                st.markdown("**🖼 스크린샷 맥락**")
                st.caption(
                    "이미지에서 대화를 읽어 옵니다. **추출·편집** 내용은 **적용** 후에 도우미 맥락에 반영됩니다. "
                    "붙여넣기 탭과 데이터가 섞이지 않습니다."
                )
                up_v = st.file_uploader(
                    "스크린샷",
                    type=["png", "jpg", "jpeg", "webp"],
                    help="OpenAI 비전 API로 텍스트를 읽습니다.",
                    key="coach_upload_ref_vision",
                )
                ev1, ev2 = st.columns(2)
                with ev1:
                    do_vis_v = st.button(
                        "스크린샷에서 텍스트 추출",
                        use_container_width=True,
                        key="coach_vision_btn_ref_v",
                    )
                with ev2:
                    if st.button("내용 지우기", use_container_width=True, key="coach_clear_vision_ref"):
                        st.session_state[_CLEAR_COACH_VISION_REQUEST] = True
                        st.rerun()

                if do_vis_v:
                    if up_v is None:
                        st.warning("먼저 이미지 파일을 선택한 뒤 다시 눌러 주세요.")
                    else:
                        with st.spinner("이미지에서 대화를 읽는 중…"):
                            try:
                                mime = up_v.type or "image/jpeg"
                                txt = run_vision_transcribe_screenshot(up_v.getvalue(), mime)
                                st.session_state[COACH_VISION_TRANSCRIPT_DRAFT_KEY] = txt
                                st.session_state[COACH_VISION_TRANSCRIPT_KEY] = txt
                                st.session_state.pop(COACH_OUT_REFERENCE_VISION, None)
                                st.session_state.pop(DANGER_REPORT_REFERENCE_VISION, None)
                                st.success(
                                    "추출했습니다. 수정한 뒤 **적용**을 누르면 도우미 맥락에 반영됩니다."
                                )
                            except Exception as e:
                                st.error(f"추출 실패: {e}")

                st.text_area(
                    "추출·편집",
                    key=COACH_VISION_TRANSCRIPT_DRAFT_KEY,
                    height=140,
                    help="스크린샷 추출 결과를 고치거나 직접 입력한 뒤, 아래 **적용**으로 도우미에 넘깁니다.",
                )
                if st.button(
                    "적용",
                    type="primary",
                    use_container_width=True,
                    key="coach_apply_vision_ref",
                ):
                    st.session_state[COACH_VISION_TRANSCRIPT_KEY] = (
                        st.session_state.get(COACH_VISION_TRANSCRIPT_DRAFT_KEY) or ""
                    )
                    st.session_state.pop(COACH_OUT_REFERENCE_VISION, None)
                    st.session_state.pop(DANGER_REPORT_REFERENCE_VISION, None)
                    st.toast("도우미 맥락에 반영되었습니다.", icon="✅")
                    st.rerun()

        conv_vis = build_reference_vision_conv()
        with cv2:
            st.subheader("도우미 (스크린샷)")
            st.caption("맥락: **적용**한 추출·편집 · 위 **배경·상황**이 있으면 함께 반영됩니다.")
            mode_rv = st.radio(
                "모드",
                [m[0] for m in MODE_DEFS],
                format_func=lambda x: next(d[1] for d in MODE_DEFS if d[0] == x),
                horizontal=False,
                key="coach_mode_ref_vision",
            )
            st.caption(next(d[2] for d in MODE_DEFS if d[0] == mode_rv))

            if mode_rv == "ment":
                if st.button("한마디 추천", type="primary", use_container_width=True, key="ment_ref_vision"):
                    if not conv_vis:
                        st.warning("왼쪽에서 **추출**하거나 입력한 뒤 **적용**을 눌러 주세요.")
                    else:
                        with st.spinner("멘트 생성…"):
                            try:
                                out = run_ment_suggestion(
                                    user_label,
                                    partner_name,
                                    conv=conv_vis,
                                    source_blurb=MENT_SOURCE_REFERENCE_VISION,
                                    scenario_section=sc_sec_ref,
                                    domain_section=dom_sec_ref,
                                )
                                st.session_state[COACH_OUT_REFERENCE_VISION] = {
                                    "_ment": True,
                                    "sentiment": out["sentiment"],
                                    "text": out["suggestion_text"],
                                }
                            except Exception as e:
                                st.session_state[COACH_OUT_REFERENCE_VISION] = f"오류: {e}"
                render_coach_ment_output(COACH_OUT_REFERENCE_VISION)

            elif mode_rv == "rag":
                if not conv_rag_available():
                    st.error("`data/conv_samples.jsonl` 이 없습니다.")
                else:
                    st.caption(RAG_MODE_CAPTION)
                if conv_rag_available() and st.button(
                    "예시 찾고 코칭 받기",
                    type="primary",
                    use_container_width=True,
                    key="rag_ref_vision",
                ):
                    if not conv_vis:
                        st.warning("왼쪽에서 **추출**하거나 입력한 뒤 **적용**을 눌러 주세요.")
                    else:
                        try:
                            partner_ctx, conv_rb, ctx_block = prepare_rag_suggestion(
                                user_label,
                                partner_name,
                                conv_vis,
                                scenario_hint=sc_plain_ref,
                                domain_id=dom_id_ref,
                                domain_other_hint=_hint_r if dom_id_ref == OTHER_DOMAIN_ID else "",
                            )
                            with st.expander("유사 대화 예시 · 검색 결과", expanded=True):
                                render_rag_examples_panel(ctx_block)
                            with st.container(border=True):
                                st.markdown("**코칭 조언**")
                                with st.spinner("조언 생성…"):
                                    st.write_stream(
                                        stream_rag_suggestion_prepared(
                                            partner_ctx,
                                            conv_rb,
                                            ctx_block,
                                            scenario_section=sc_sec_ref,
                                            domain_section=dom_sec_ref,
                                        )
                                    )
                        except Exception as e:
                            st.error(str(e))

            elif mode_rv == "vote":
                if st.button(
                    "조언 후보 만들고 투표",
                    type="primary",
                    use_container_width=True,
                    key="vote_ref_vision",
                ):
                    conv_vote = build_reference_vision_conv()
                    if not conv_vote:
                        st.warning("왼쪽에서 **추출**하거나 입력한 뒤 **적용**을 눌러 주세요.")
                    else:
                        with st.spinner("시간이 조금 걸릴 수 있어요…"):
                            try:
                                for chunk in stream_vote_suggestion(
                                    conv_vote,
                                    user_label,
                                    partner_name,
                                    scenario_section=sc_sec_ref,
                                    domain_section=dom_sec_ref,
                                    source_blurb=MENT_SOURCE_REFERENCE_VISION,
                                ):
                                    write_vote_suggestion_chunk(chunk)
                            except Exception as e:
                                st.error(str(e))

            elif mode_rv == "danger":
                render_danger_panel(
                    user_label,
                    partner_name,
                    conv=conv_vis,
                    report_state_key=DANGER_REPORT_REFERENCE_VISION,
                    analyze_button_key="danger_analyze_ref_vision",
                    empty_hint="분석할 텍스트가 없습니다. 왼쪽에서 **적용**을 눌러 주세요.",
                    scenario_hint=sc_plain_ref,
                    domain_section=dom_sec_ref,
                )

st.divider()
st.page_link("pages/02_프로필_매칭_검색.py", label="← 매칭으로 돌아가기", use_container_width=True)

render_trust_footer()
