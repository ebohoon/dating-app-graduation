"""
세션·저장 동작 요약
------------------
- **브라우저 탭이 열려 있는 동안**: Streamlit이 `st.session_state`에 상태를 유지합니다.
- **새로고침(F5)**: 새 세션이 시작되며, 아래 플래그가 꺼져 있으면 **디스크에서 복원하지 않아**
  입력·프로필·매칭 등이 초기화된 것처럼 시작합니다.
- **디스크 지속화**: `ENABLE_SESSION_DISK_PERSIST` 가 True일 때만
  `data/app_session_state.json` 에 저장·복원합니다.
- **기본값 False**: 브라우저 **새로고침(F5)** 시 Streamlit 세션이 비워지므로 **입력·프로필 등도 함께 초기화**됩니다.
  (탭을 닫지 않고 단계만 옮길 때는 메모리 세션으로 유지됩니다.)
- **홈 경유** `_session_from_home` 은 디스크에 저장하지 않아, F5 후 ①~④는 **홈을 거치도록** `_ui.render_page_shell` 에서 보냅니다.
"""
from __future__ import annotations

import json
from io import StringIO
from typing import Any

import streamlit as st

from _match_context import (
    MATCHED_PROFILE_KEY,
    MATCH_FILTER_META_KEY,
    MATCH_RESULTS_DF_KEY,
    PF_INPUT_AGE,
    PF_INPUT_BIO_DRAFT,
    PF_INPUT_DATING_GOAL,
    PF_INPUT_DISPLAY_NAME,
    PF_INPUT_GENDER,
    PF_INPUT_IDEAL,
    PF_INPUT_JOB,
    PF_INPUT_LIFESTYLE,
    PF_INPUT_LOCATION,
    SELECTED_OPENING_MATCH_SIG_KEY,
    SELECTED_OPENING_MESSAGE_KEY,
    STEP1_FORM_PROFILE_SIG_KEY,
    USER_AI_PROFILE_KEY,
    USER_KEYWORDS_SEED_KEY,
    USER_SELF_INTRO_KEY,
)
from _paths import data_path

# True로 두면 새로고침(F5) 후에도 app_session_state.json 에서 상태를 복원합니다.
ENABLE_SESSION_DISK_PERSIST: bool = False

MESSAGES_COACH_KEY = "messages_coach"
INIT_SIG_SUFFIX = "_init_sig"

SESSION_FILE = data_path("app_session_state.json")

PERSIST_KEYS: tuple[str, ...] = (
    STEP1_FORM_PROFILE_SIG_KEY,
    USER_AI_PROFILE_KEY,
    USER_KEYWORDS_SEED_KEY,
    USER_SELF_INTRO_KEY,
    PF_INPUT_DISPLAY_NAME,
    PF_INPUT_AGE,
    PF_INPUT_GENDER,
    PF_INPUT_LOCATION,
    PF_INPUT_JOB,
    PF_INPUT_BIO_DRAFT,
    PF_INPUT_DATING_GOAL,
    PF_INPUT_IDEAL,
    PF_INPUT_LIFESTYLE,
    MATCHED_PROFILE_KEY,
    "interest_draft",
    MATCH_RESULTS_DF_KEY,
    "_kw_only_results",
    MATCH_FILTER_META_KEY,
    "liked_profiles",
    "disliked_profiles",
    MESSAGES_COACH_KEY,
    f"{MESSAGES_COACH_KEY}{INIT_SIG_SUFFIX}",
    "_last_intro_lines",
    "_intro_lines_match_sig",
    SELECTED_OPENING_MESSAGE_KEY,
    SELECTED_OPENING_MATCH_SIG_KEY,
    "selected_intro_idx_radio",
    "_profile_score",
    "_coach_side_out_practice",
    "_coach_side_out_reference_paste",
    "_coach_side_out_reference_vision",
    "_danger_report_practice",
    "_danger_report_reference_paste",
    "_danger_report_reference_vision",
    "coach_external_paste",
    "coach_vision_transcript",
    "coach_scenario_context_practice",
    "coach_scenario_context_reference",
    "coach_conversation_domain_practice",
    "coach_conversation_domain_reference",
    "coach_domain_other_hint_practice",
    "coach_domain_other_hint_reference",
)


def _hydrated_key() -> str:
    return "_persist_hydrated"


def _to_storable(val: Any) -> Any:
    if isinstance(val, set):
        return {"__kind__": "set", "items": list(val)}
    try:
        import pandas as pd

        if isinstance(val, pd.DataFrame):
            return {
                "__kind__": "dataframe",
                "json": val.to_json(orient="records", force_ascii=False, date_format="iso"),
            }
    except ImportError:
        pass
    return val


def _from_stored(val: Any) -> Any:
    if isinstance(val, dict) and val.get("__kind__") == "dataframe":
        import pandas as pd

        return pd.read_json(StringIO(val["json"]), orient="records")
    if isinstance(val, dict) and val.get("__kind__") == "set":
        return set(val.get("items") or [])
    return val


def _fix_match_meta(meta: Any) -> Any:
    if not isinstance(meta, dict):
        return meta
    meta = dict(meta)
    ar = meta.get("age_range")
    if isinstance(ar, list) and len(ar) == 2:
        meta["age_range"] = (int(ar[0]), int(ar[1]))
    return meta


def restore_session_from_disk() -> None:
    if st.session_state.get(_hydrated_key()):
        return

    st.session_state[_hydrated_key()] = True

    if not ENABLE_SESSION_DISK_PERSIST:
        return

    if not SESSION_FILE.exists():
        return

    try:
        raw = SESSION_FILE.read_text(encoding="utf-8")
        data = json.loads(raw)
        for k, v in data.items():
            if k == _hydrated_key():
                continue
            # 예전 파일에 있어도 복원하지 않음 → F5 후 journey 페이지가 홈으로 보내짐
            if k == "_session_from_home":
                continue
            out = _from_stored(v)
            if k == MATCH_FILTER_META_KEY:
                out = _fix_match_meta(out)
            if k in ("liked_profiles", "disliked_profiles") and isinstance(out, list):
                out = set(out)
            st.session_state[k] = out
    except (OSError, json.JSONDecodeError, ValueError, TypeError):
        pass


def save_session_to_disk() -> bool:
    if not ENABLE_SESSION_DISK_PERSIST:
        return False

    payload: dict[str, Any] = {}
    for k in PERSIST_KEYS:
        if k not in st.session_state:
            continue
        try:
            val = st.session_state[k]
            payload[k] = _to_storable(val)
        except (TypeError, ValueError, OverflowError):
            continue

    try:
        SESSION_FILE.parent.mkdir(parents=True, exist_ok=True)
        SESSION_FILE.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )
        return True
    except OSError:
        return False


def clear_saved_session() -> None:
    try:
        if SESSION_FILE.exists():
            SESSION_FILE.unlink()
    except OSError:
        pass
    for k in PERSIST_KEYS:
        st.session_state.pop(k, None)
    st.session_state.pop("_session_from_home", None)
    st.session_state.pop(_hydrated_key(), None)
