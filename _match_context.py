"""
프로필 매칭 → 대화 보조 페이지 연동용 공통 유틸.
"""
from __future__ import annotations

from typing import Any

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
        f"- 이름(닉네임): {me.get('display_name', '')}\n"
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
