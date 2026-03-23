"""
Streamlit 세션은 새로고침(F5) 시 초기화될 수 있어,
주요 사용자 데이터를 data/app_session_state.json 에 저장·복원합니다.
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
    MATCH_FILTER_META_KEY,
    MESSAGES_COACH_KEY,
    f"{MESSAGES_COACH_KEY}{INIT_SIG_SUFFIX}",
    "_last_intro_lines",
)


def _hydrated_key() -> str:
    return "_persist_hydrated"


def _to_storable(val: Any) -> Any:
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


def _feedback_after_temp_save() -> None:
    if save_session_to_disk():
        st.success("저장했어요. 새로고침 후에도 이 기기에서 이어집니다.")
    else:
        st.error("`data/` 폴더에 쓸 수 없습니다. 권한을 확인해 주세요.")


def render_persistence_topbar() -> None:
    """본문 상단: 임시저장 (카드형)."""
    with st.container(border=True):
        c1, c2 = st.columns([1, 4])
        with c1:
            if st.button(
                "임시저장",
                key="_persist_btn_topbar",
                type="primary",
                help="입력·검색 결과·대화 등을 로컬 파일에 저장합니다. 페이지 끝까지 내려가도 자동 저장됩니다.",
            ):
                _feedback_after_temp_save()
        with c2:
            st.caption(
                "이 PC의 data/app_session_state.json 에 저장됩니다. "
                "탭을 닫기 전에 한 번 저장해 두면 안전합니다."
            )


def render_persistence_sidebar() -> None:
    with st.sidebar:
        st.divider()
        st.caption("로컬 저장을 비우면 복원용 데이터가 사라집니다.")
        if st.button(
            "저장 초기화",
            key="_btn_clear_session_file",
            help="저장 파일 삭제 + 이 탭의 복원용 입력 제거",
        ):
            clear_saved_session()
            st.rerun()
