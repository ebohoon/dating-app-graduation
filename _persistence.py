"""
세션·저장 동작 요약
------------------
- **브라우저 탭이 열려 있는 동안**: Streamlit이 `st.session_state`에 상태를 유지합니다.
  (일반 웹의 "쿠키"가 아니라, 서버·세션 연결 단위 저장입니다.)
- **새로고침(F5) / 브라우저 재실행 후**: 세션이 비워질 수 있어, 같은 PC에서는
  `data/app_session_state.json`에 주기적으로 백업합니다.
- **자동 저장 시점**: 각 페이지 맨 아래 `render_trust_footer()`가 스크립트 한 번
  실행이 끝날 때 `save_session_to_disk()`를 호출합니다.
- **자동 복원 시점**: `render_page_shell()` 시작 시 `restore_session_from_disk()`
  한 번(중복 복원 방지 플래그 사용).
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
    USER_AI_PROFILE_KEY,
    USER_KEYWORDS_SEED_KEY,
    USER_SELF_INTRO_KEY,
)
from _paths import data_path

MESSAGES_COACH_KEY = "messages_coach"
INIT_SIG_SUFFIX = "_init_sig"

SESSION_FILE = data_path("app_session_state.json")

PERSIST_KEYS: tuple[str, ...] = (
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
    "_greeting_scores",
    "_profile_score",
    "_coach_side_out_practice",
    "_coach_side_out_reference_paste",
    "_coach_side_out_reference_vision",
    "_danger_report_practice",
    "_danger_report_reference_paste",
    "_danger_report_reference_vision",
    "coach_external_paste",
    "coach_vision_transcript",
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

    if not SESSION_FILE.exists():
        st.session_state[_hydrated_key()] = True
        return

    try:
        raw = SESSION_FILE.read_text(encoding="utf-8")
        data = json.loads(raw)
        for k, v in data.items():
            if k == _hydrated_key():
                continue
            out = _from_stored(v)
            if k == MATCH_FILTER_META_KEY:
                out = _fix_match_meta(out)
            if k in ("liked_profiles", "disliked_profiles") and isinstance(out, list):
                out = set(out)
            st.session_state[k] = out
    except (OSError, json.JSONDecodeError, ValueError, TypeError):
        pass
    finally:
        st.session_state[_hydrated_key()] = True


def save_session_to_disk() -> bool:
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
    st.session_state.pop(_hydrated_key(), None)
