import streamlit as st

from _ui import (
    JOURNEY_HOME,
    openai_key_configured,
    render_home_feature_grid,
    render_home_flow_rail,
    render_home_hero,
    render_home_start_cta,
    render_page_shell,
    render_trust_footer,
)

st.set_page_config(
    page_title="통합 데이팅 AI",
    page_icon="💘",
    layout="wide",
    initial_sidebar_state="expanded",
)

render_page_shell(journey_step=JOURNEY_HOME)

_key_ok = openai_key_configured()

render_home_hero()

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

render_home_flow_rail()

render_home_feature_grid()

render_home_start_cta()

render_trust_footer()
