"""
프로필 매칭 → 대화 보조 페이지 연동용 공통 유틸.
"""
from __future__ import annotations

import json
from typing import Any

import streamlit as st

MATCHED_PROFILE_KEY = "matched_profile"
"""사용자가 매칭으로 고른 상대 프로필."""

# ② 매칭 페이지 세션 (임시저장·복원용 — _persistence.py 와 동일 키)
MATCH_RESULTS_DF_KEY = "match_results_df"
MATCH_FILTER_META_KEY = "match_filter_meta"

USER_SELF_INTRO_KEY = "user_self_intro"
"""선택: AI 프로필 생성 시 참고할 추가 메모(취향·스타일 등)."""

USER_KEYWORDS_SEED_KEY = "user_keywords_seed"
"""관심 키워드 쉼표 입력 — 홈·① 페이지에서 공유."""

USER_AI_PROFILE_KEY = "user_ai_profile"
"""AI·사용자가 채운 나의 프로필 dict(아래 필드 + 확장)."""

# ① 프로필 생성 폼 초안 — 인사말 페이지 입력을 여기로 통합
PF_INPUT_DISPLAY_NAME = "pf_input_display_name"
PF_INPUT_AGE = "pf_input_age"
PF_INPUT_GENDER = "pf_input_gender"
PF_INPUT_LOCATION = "pf_input_location"
PF_INPUT_JOB = "pf_input_job"
PF_INPUT_BIO_DRAFT = "pf_input_bio_draft"
PF_INPUT_DATING_GOAL = "pf_input_dating_goal"
PF_INPUT_IDEAL = "pf_input_ideal_partner"
PF_INPUT_LIFESTYLE = "pf_input_lifestyle"

# 하위 호환(이전 버전 세션). 신규 흐름에서는 USER_AI_PROFILE_KEY만 사용.
USER_MATCH_KEYWORDS_KEY = "user_match_keywords"

USER_NAME = "철수"

STEP1_FORM_PROFILE_SIG_KEY = "_step1_form_profile_sig"
"""① 편집 폼이 USER_AI_PROFILE_KEY 와 맞춰졌는지 추적(단계 이동 후 복원용)."""


def _profile_signature(match: dict[str, Any] | None) -> tuple[Any, ...]:
    if not match:
        return ("none",)
    return (
        match.get("name"),
        match.get("age"),
        match.get("job"),
        match.get("bio"),
        tuple(match.get("keywords") or []) if isinstance(match.get("keywords"), list) else match.get("keywords"),
    )


def _user_profile_signature(me: dict[str, Any] | None) -> tuple[Any, ...]:
    if not me:
        return ("none",)
    kw = me.get("keywords")
    if isinstance(kw, list):
        tkw = tuple(kw)
    else:
        tkw = kw
    return (
        me.get("display_name"),
        me.get("age"),
        me.get("gender"),
        me.get("job"),
        me.get("bio"),
        me.get("dating_goal"),
        me.get("ideal_partner"),
        me.get("lifestyle_summary"),
        tkw,
    )


def _step1_profile_sync_token(me: dict[str, Any]) -> str:
    return json.dumps(_user_profile_signature(me), ensure_ascii=False, default=str)


def apply_user_ai_profile_to_step1_form(me: dict[str, Any]) -> None:
    """저장된 AI 프로필 dict → ① 페이지 입력 위젯 세션 키에 반영."""
    if not isinstance(me, dict):
        return
    st.session_state[PF_INPUT_DISPLAY_NAME] = str(me.get("display_name") or "")
    try:
        st.session_state[PF_INPUT_AGE] = int(me.get("age") or 28)
    except (TypeError, ValueError):
        st.session_state[PF_INPUT_AGE] = 28
    g = str(me.get("gender") or "남자")
    st.session_state[PF_INPUT_GENDER] = g if g in ("남자", "여자") else "남자"
    st.session_state[PF_INPUT_LOCATION] = str(me.get("location") or "")
    st.session_state[PF_INPUT_JOB] = str(me.get("job") or "")
    kw = me.get("keywords") or []
    if isinstance(kw, list):
        st.session_state[USER_KEYWORDS_SEED_KEY] = ", ".join(
            str(x).strip() for x in kw if str(x).strip()
        )
    else:
        st.session_state[USER_KEYWORDS_SEED_KEY] = ""
    st.session_state[PF_INPUT_BIO_DRAFT] = str(me.get("bio") or "")
    st.session_state[PF_INPUT_DATING_GOAL] = str(me.get("dating_goal") or "")
    st.session_state[PF_INPUT_IDEAL] = str(me.get("ideal_partner") or "")
    st.session_state[PF_INPUT_LIFESTYLE] = str(me.get("lifestyle_summary") or "")


def mark_step1_form_synced_with_profile(me: dict[str, Any]) -> None:
    st.session_state[STEP1_FORM_PROFILE_SIG_KEY] = _step1_profile_sync_token(me)


def maybe_restore_step1_form_from_saved_profile() -> None:
    """
    다른 단계를 다녀온 뒤 입력칸이 비었거나, 저장 프로필만 갱신된 경우
    user_ai_profile 내용으로 ① 입력란을 맞춘다.
    """
    me = st.session_state.get(USER_AI_PROFILE_KEY)
    if not isinstance(me, dict) or not str(me.get("display_name") or "").strip():
        return
    token = _step1_profile_sync_token(me)
    prev = st.session_state.get(STEP1_FORM_PROFILE_SIG_KEY)
    name_empty = not str(st.session_state.get(PF_INPUT_DISPLAY_NAME) or "").strip()
    if name_empty:
        apply_user_ai_profile_to_step1_form(me)
        st.session_state[STEP1_FORM_PROFILE_SIG_KEY] = token
        return
    if prev is not None and token != prev:
        apply_user_ai_profile_to_step1_form(me)
    st.session_state[STEP1_FORM_PROFILE_SIG_KEY] = token


def user_play_name(st: Any) -> str:
    """채팅·프롬프트에 쓰는 사용자 호칭."""
    me = st.session_state.get(USER_AI_PROFILE_KEY)
    if isinstance(me, dict) and me.get("display_name"):
        return str(me["display_name"])
    return USER_NAME


def partner_context_for_llm(match: dict[str, Any] | None, user_name: str = "나") -> str:
    """멘트/조언 프롬프트에 넣을 상대 프로필 설명."""
    if not match:
        return "상대방은 일반적인 소개팅 상대이며, 별도 프로필 정보는 없다."
    kw = match.get("keywords", [])
    kw_str = ", ".join(kw) if isinstance(kw, list) else str(kw)
    return (
        f"아래는 사용자({user_name})가 매칭 검색으로 선택한 상대방 프로필이다. "
        "조언·멘트 추천 시 이 성격·관심사에 맞춰 자연스럽게 제안하라.\n"
        f"- 이름: {match.get('name', '')}\n"
        f"- 나이: {match.get('age', '')}, 성별: {match.get('gender', '')}\n"
        f"- 직업: {match.get('job', '')}\n"
        f"- 소개: {match.get('bio', '')}\n"
        f"- 관심 키워드: {kw_str}"
    )


def _user_me_blurb(me: dict[str, Any]) -> str:
    kw = me.get("keywords", [])
    kw_str = ", ".join(kw) if isinstance(kw, list) else str(kw)
    extra = ""
    if me.get("dating_goal"):
        extra += f"- 만남·연애 목적: {me.get('dating_goal')}\n"
    if me.get("ideal_partner"):
        extra += f"- 선호하는 상대: {me.get('ideal_partner')}\n"
    if me.get("lifestyle_summary"):
        extra += f"- 라이프스타일: {me.get('lifestyle_summary')}\n"
    return (
        f"- 이름: {me.get('display_name', '')}\n"
        f"- 나이: {me.get('age', '')}, 성별: {me.get('gender', '')}\n"
        f"- 지역: {me.get('location', '')}\n"
        f"- 직업: {me.get('job', '')}\n"
        f"- 자기소개: {me.get('bio', '')}\n"
        f"- 관심 키워드: {kw_str}\n"
        f"{extra}"
    )


def build_system_prompt(match: dict[str, Any] | None, user_me: dict[str, Any] | None = None) -> str:
    """채팅에서 AI 연기용 시스템 프롬프트. 매칭 없으면 기존 수연 페르소나."""
    user_block = ""
    if user_me and isinstance(user_me, dict) and user_me.get("display_name"):
        user_block = (
            "\n\n대화를 건 사람(사용자)의 프로필은 아래와 같다. 상대 역할을 연기할 때 이 맥락을 참고하라.\n"
            + _user_me_blurb(user_me)
        )

    if not match:
        base = """\
너는 20대 여성 AI 개발자이고 아래의 프로필을 따라 응답한다.
- 이름: 수연
- 나이: 29
- '처음' 만나는 1:1 소개팅 상황이다. 커피집에서 만났다.
- 소개팅이기에 너무 도움을 주려고 대화하지 않는다. 자연스러운 대화를한다.
- 너무 적극적으로 이야기하지는 않는다.
- 대화를 리드하지 않는다.
- 수동적으로 대답한다.
"""
        return base + user_block

    name = match.get("name", "상대")
    age = match.get("age", "")
    gender = match.get("gender", "")
    job = match.get("job", "")
    bio = match.get("bio", "")
    kw = match.get("keywords", [])
    kw_str = ", ".join(kw) if isinstance(kw, list) else str(kw)
    return f"""\
너는 소개팅 상황에서 상대방 역할을 연기한다. 아래 프로필을 따라 대답한다.
- 이름: {name}
- 나이: {age}, 성별: {gender}
- 직업: {job}
- 자기소개: {bio}
- 관심사: {kw_str}
- '처음' 만나는 1:1 소개팅이다. 커피집에서 만났다.
- 소개팅이기에 너무 도움을 주려고 대화하지 않는다. 자연스러운 대화를 한다.
- 너무 적극적으로 이야기하지는 않는다.
- 대화를 리드하지 않는다.
- 수동적으로 대답한다.
{user_block}
"""


def ensure_chat_session(st: Any, messages_key: str) -> tuple[str, str, str]:
    """
    매칭 프로필 또는 나의 AI 프로필이 바뀌면 대화를 초기화하고 시스템 메시지를 다시 설정.
    Returns: (user_label, ai_name, ai_avatar)
    """
    match = st.session_state.get(MATCHED_PROFILE_KEY)
    user_me = st.session_state.get(USER_AI_PROFILE_KEY)
    if not isinstance(user_me, dict):
        user_me = None

    sig = (_profile_signature(match), _user_profile_signature(user_me))
    init_key = f"{messages_key}_init_sig"
    if messages_key not in st.session_state or st.session_state.get(init_key) != sig:
        st.session_state[messages_key] = [{"role": "system", "content": build_system_prompt(match, user_me)}]
        st.session_state[init_key] = sig
    ul = user_play_name(st)
    return ul, ai_display_name(match), ai_avatar_emoji(match)


def ai_display_name(match: dict[str, Any] | None) -> str:
    if match and match.get("name"):
        return str(match["name"])
    return "수연"


def ai_avatar_emoji(match: dict[str, Any] | None) -> str:
    if not match:
        return "👩🏼"
    if match.get("gender") == "남자":
        return "👨"
    return "👩🏼"


def user_profile_step_done(me: Any) -> bool:
    """① 완료: AI 프로필에 이름·성별(남/여)이 확정된 상태."""
    if not isinstance(me, dict):
        return False
    if not str(me.get("display_name") or "").strip():
        return False
    return me.get("gender") in ("남자", "여자")


def match_step_done() -> bool:
    """② 완료: 매칭에서 상대 프로필을 하나 선택한 상태."""
    m = st.session_state.get(MATCHED_PROFILE_KEY)
    return isinstance(m, dict) and bool(str(m.get("name") or "").strip())


def greeting_step_done() -> bool:
    """③ 완료: 인사말 후보를 한 번 이상 생성한 상태."""
    lines = st.session_state.get("_last_intro_lines")
    return isinstance(lines, list) and len(lines) > 0


def journey_can_access(target: str) -> tuple[bool, str]:
    """
    단계 잠금: profile / match / greeting / coach 순.
    반환: (허용 여부, 차단 시 안내 문구).
    """
    me = st.session_state.get(USER_AI_PROFILE_KEY)
    if target == "profile":
        return True, ""

    if not user_profile_step_done(me):
        return (
            False,
            "① **AI 프로필**에서 프로필을 생성하고, 성별을 **남자** 또는 **여자**로 확정해 주세요.",
        )

    if target == "match":
        return True, ""

    if not match_step_done():
        return False, "② **매칭**에서 검색 후 **상대 한 명을 선택**해 주세요."

    if target == "greeting":
        return True, ""

    if not greeting_step_done():
        return (
            False,
            "③ **인사말**에서 **첫 인사 후보 생성** 버튼으로 멘트를 한 번 만들어 주세요.",
        )

    if target == "coach":
        return True, ""

    return True, ""


def opposite_gender_for_match(user_gender: str | None) -> str | None:
    """① 프로필 성별 기준 ② 매칭에서 쓸 이성 필터 값 ('남자' | '여자')."""
    g = (user_gender or "").strip()
    if g == "남자":
        return "여자"
    if g == "여자":
        return "남자"
    return None
