import os

import pandas as pd
import streamlit as st
from streamlit.errors import StreamlitSecretNotFoundError

from _match_context import USER_KEYWORDS_SEED_KEY, USER_SELF_INTRO_KEY
from _paths import data_path
from _ui import (
    JOURNEY_HOME,
    openai_key_configured,
    render_home_flow_rail,
    render_home_navigation,
    render_page_shell,
    render_trust_footer,
)

st.set_page_config(
    page_title="통합 데이팅 AI",
    page_icon="💘",
    layout="wide",
    initial_sidebar_state="expanded",
)

render_page_shell("홈", journey_step=JOURNEY_HOME)

try:
    _prof_path = data_path("profile_db.jsonl")
    _n_profiles = len(pd.read_json(str(_prof_path), lines=True)) if _prof_path.exists() else 0
except Exception:
    _n_profiles = 0

_key_ok = openai_key_configured()

m1, m2, m3 = st.columns(3)
with m1:
    st.metric(label="매칭 DB 인원", value=f"{_n_profiles}명", help="data/profile_db.jsonl 기준")
with m2:
    st.metric(
        label="AI 연결",
        value="연결됨" if _key_ok else "미설정",
        help="OPENAI_API_KEY — 환경 변수, secrets.toml, .env 순으로 인식",
    )
with m3:
    st.metric(label="권장 단계", value="4단계", help="프로필 → 매칭 → 인사 → 대화")

st.markdown(
    """
<div class="home-hero">
    <h1>나에게 맞는 만남까지, 한 흐름으로</h1>
    <p class="ux-hero-lead">
        관심 <strong>키워드</strong>로 프로필을 채우고, <strong>매칭</strong>으로 상대를 고른 뒤
        <strong>첫 인사</strong>와 <strong>대화 연습</strong>까지 이어지도록 설계했습니다.
        (졸업작품·로컬 데모 — 실제 서비스와 동일한 인프라는 아닙니다.)
    </p>
</div>
""",
    unsafe_allow_html=True,
)

st.info(
    "**이렇게 써 보세요.** 홈에서 키워드를 적고 → **①**에서 프로필 생성 → **②**에서 검색 후 한 명 선택 → "
    "**③**에서 첫 인사 → **④**에서 대화·코칭.",
    icon="💡",
)

render_home_flow_rail()

if USER_KEYWORDS_SEED_KEY not in st.session_state:
    st.session_state[USER_KEYWORDS_SEED_KEY] = ""
if USER_SELF_INTRO_KEY not in st.session_state:
    st.session_state[USER_SELF_INTRO_KEY] = ""

st.markdown('<p class="ux-section-title">시작하기</p>', unsafe_allow_html=True)
st.markdown(
    '<p class="ux-section-lead">① AI 프로필로 넘어갈 때 그대로 반영됩니다. 쉼표로 키워드를 구분해 주세요.</p>',
    unsafe_allow_html=True,
)

c1, c2 = st.columns(2, gap="large")
with c1:
    st.text_area(
        "관심 키워드",
        key=USER_KEYWORDS_SEED_KEY,
        height=120,
        placeholder="예: 커피, 여행, 클래식, 러닝",
        help="매칭 DB의 keywords와 겹치면 검색에 유리합니다.",
    )
with c2:
    st.text_area(
        "추가 메모 (선택)",
        key=USER_SELF_INTRO_KEY,
        height=120,
        placeholder="성향·금지어·대화 스타일 등 AI가 참고할 짧은 메모",
        help="프로필 생성 프롬프트에만 쓰이며, 다른 사용자에게 공개되지 않습니다.",
    )

cta1, cta2, cta3 = st.columns(3)
with cta1:
    st.page_link("pages/01_AI_프로필_생성.py", label="① 프로필 만들기", use_container_width=True)
with cta2:
    st.page_link("pages/02_프로필_매칭_검색.py", label="② 매칭만 열기", use_container_width=True)
with cta3:
    st.page_link("pages/04_대화_도우미.py", label="④ 대화 도우미", use_container_width=True)

render_home_navigation()

if not _key_ok:
    st.warning("**OpenAI API 키가 없습니다.** 아래를 펼쳐 설정 방법을 확인하세요.")
    with st.expander("API 키 설정", expanded=True):
        st.markdown(
            """
1. **`.streamlit/secrets.toml`**  
   `secrets.toml.example` 을 복사해 `secrets.toml` 로 저장한 뒤 `OPENAI_API_KEY` 를 넣습니다.

2. **`.env` (프로젝트 루트)**  
   `OPENAI_API_KEY=sk-...` 한 줄 저장 (`python-dotenv`).

3. **환경 변수**  
   PowerShell: `$env:OPENAI_API_KEY="sk-..."`

저장 후 터미널에서 `streamlit run app.py` **재실행**이 필요합니다.
"""
        )
else:
    st.caption("OpenAI API 키가 감지되었습니다. 모델·과금은 OpenAI 정책을 따릅니다.")

with st.expander("환경·데이터 경로", expanded=False):
    key_ok = bool(os.environ.get("OPENAI_API_KEY"))
    if not key_ok:
        try:
            key_ok = bool(st.secrets.get("OPENAI_API_KEY", ""))
        except StreamlitSecretNotFoundError:
            pass
    st.markdown(
        f"- OpenAI 키: **{'감지됨' if key_ok else '미감지'}**\n"
        f"- 프로필 DB: `{data_path('profile_db.jsonl')}`\n"
        f"- 세션 백업: `{data_path('app_session_state.json')}`"
    )

render_trust_footer()
