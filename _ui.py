"""
앱 전반 UI/UX — 로즈·하트 테마, 타이포그래피, 내비게이션, 위젯·채팅 스타일.

실서비스에 가깝게: 가독성(행간·자간·대비), 일관된 컴포넌트 톤, 포커스·호버 피드백.
"""
from __future__ import annotations

import html as html_module
import os
import re

import streamlit as st
from streamlit.errors import StreamlitSecretNotFoundError

JOURNEY_HOME = "home"
JOURNEY_PROFILE = "profile"
JOURNEY_MATCH = "match"
JOURNEY_GREETING = "greeting"
JOURNEY_COACH = "coach"
JOURNEY_KEYWORDS = JOURNEY_PROFILE

_JOURNEY_ORDER = [JOURNEY_HOME, JOURNEY_PROFILE, JOURNEY_MATCH, JOURNEY_GREETING, JOURNEY_COACH]

_JOURNEY_META = [
    (JOURNEY_HOME, "시작", "app.py"),
    (JOURNEY_PROFILE, "내 프로필", "pages/01_AI_프로필_생성.py"),
    (JOURNEY_MATCH, "매칭", "pages/02_프로필_매칭_검색.py"),
    (JOURNEY_GREETING, "인사말", "pages/03_인사말_생성.py"),
    (JOURNEY_COACH, "대화", "pages/04_대화_도우미.py"),
]


def _subtitle_md_to_html(text: str) -> str:
    """부제에 쓰인 **굵게**만 HTML로 변환 (한 줄 기준)."""
    if not text:
        return ""
    s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    return s.replace("\n", "<br />")


def openai_key_configured() -> bool:
    try:
        from _env import load_optional_dotenv

        load_optional_dotenv()
    except ImportError:
        pass
    if os.environ.get("OPENAI_API_KEY", "").strip():
        return True
    try:
        return bool(str(st.secrets.get("OPENAI_API_KEY", "") or "").strip())
    except StreamlitSecretNotFoundError:
        return False


def inject_app_styles() -> None:
    st.markdown(
        """
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=DM+Sans:ital,wght@0,400;0,600;0,700;1,400&family=Noto+Sans+KR:wght@400;500;600;700&display=swap" rel="stylesheet">
""",
        unsafe_allow_html=True,
    )
    st.markdown(
        """
<style>
    :root {
        --rose-50: #fff1f2;
        --rose-100: #ffe4e6;
        --rose-200: #fecdd3;
        --rose-400: #fb7185;
        --rose-500: #f43f5e;
        --rose-600: #e11d48;
        --pink-500: #ec4899;
        --pink-600: #db2777;
        --ink: #3f0d1f;
        --ink-soft: #5c2740;
        --muted: #7a4a5e;
        --surface: #ffffff;
        --surface-glass: rgba(255, 255, 255, 0.82);
        --surface-muted: rgba(255, 255, 255, 0.55);
        --radius-lg: 18px;
        --radius-md: 14px;
        --radius-sm: 10px;
        --radius-pill: 9999px;
        --shadow-sm: 0 2px 12px rgba(120, 20, 60, 0.06);
        --shadow-md: 0 10px 40px rgba(120, 20, 60, 0.1);
        --shadow-nav: 0 1px 0 rgba(244, 114, 182, 0.2);
        --focus: 0 0 0 3px rgba(244, 114, 182, 0.42);
        --line: rgba(244, 114, 182, 0.28);
    }

    html { scroll-behavior: smooth; }
    @media (prefers-reduced-motion: reduce) {
        html { scroll-behavior: auto; }
        * { transition: none !important; }
    }

    html, body, .stApp {
        font-family: "Noto Sans KR", "DM Sans", system-ui, sans-serif !important;
        -webkit-font-smoothing: antialiased;
        -moz-osx-font-smoothing: grayscale;
    }

    [data-testid="stMarkdownContainer"] p,
    [data-testid="stWidgetLabel"] label,
    .stCaption {
        font-family: "Noto Sans KR", "DM Sans", system-ui, sans-serif !important;
    }

    /* 본문 가독성 */
    [data-testid="stAppViewContainer"] [data-testid="stMarkdownContainer"] p {
        font-size: 1rem;
        line-height: 1.68;
        color: var(--ink-soft);
        letter-spacing: -0.01em;
    }
    [data-testid="stAppViewContainer"] [data-testid="stMarkdownContainer"] li {
        line-height: 1.65;
        margin: 0.35rem 0;
        color: var(--ink-soft);
    }
    [data-testid="stAppViewContainer"] [data-testid="stMarkdownContainer"] strong {
        color: var(--ink);
        font-weight: 600;
    }
    [data-testid="stAppViewContainer"] [data-testid="stMarkdownContainer"] code {
        font-size: 0.88em;
        padding: 0.12em 0.4em;
        border-radius: 6px;
        background: rgba(244, 114, 182, 0.12);
        color: var(--pink-600);
        font-weight: 500;
    }

    [data-testid="stAppViewContainer"] {
        background:
            radial-gradient(1100px 520px at 8% -8%, rgba(251, 207, 232, 0.5) 0%, transparent 58%),
            radial-gradient(800px 480px at 96% 12%, rgba(254, 205, 211, 0.42) 0%, transparent 52%),
            linear-gradient(180deg, #fff8fb 0%, #fff0f5 42%, #fffafd 100%) !important;
    }

    [data-testid="stHeader"], [data-testid="stToolbar"], [data-testid="stDecoration"] {
        display: none !important;
    }
    section[data-testid="stMain"] > div { padding-top: 0 !important; }
    div.block-container {
        padding-top: 0.65rem;
        padding-bottom: 3rem;
        padding-left: 1.5rem !important;
        padding-right: 1.5rem !important;
        max-width: 1080px;
    }

    /* 사이드바 */
    [data-testid="stSidebar"] {
        background: linear-gradient(185deg, #ffe8f0 0%, #fff8fb 48%, #fff5f8 100%) !important;
        border-right: 1px solid var(--line) !important;
        box-shadow: 4px 0 28px rgba(90, 20, 50, 0.05);
    }
    [data-testid="stSidebar"] .stMarkdown a { color: var(--pink-600) !important; font-weight: 500 !important; }
    [data-testid="stSidebarNav"] a {
        border-radius: var(--radius-sm) !important;
        padding: 0.4rem 0.55rem !important;
        transition: background 0.16s ease !important;
        font-weight: 500 !important;
    }
    [data-testid="stSidebarNav"] a:hover { background: rgba(255, 255, 255, 0.72) !important; }
    [data-testid="stSidebarNav"] { padding: 0.4rem 0.15rem 1rem !important; }
    [data-testid="stSidebarNav"] ul { padding-left: 0.2rem !important; margin: 0 !important; }
    [data-testid="stSidebarNav"] li { margin: 0.2rem 0 !important; }
    [data-testid="stSidebarNav"] a {
        display: flex !important;
        align-items: center !important;
        min-height: 2.15rem !important;
    }
    [data-testid="stSidebar"] [data-testid="stCaption"] {
        color: var(--muted) !important;
        font-size: 0.78rem !important;
        line-height: 1.45 !important;
    }

    /* 상단 내비 셸 */
    .ux-topnav-shell {
        background: var(--surface-glass);
        border: 1px solid var(--line);
        border-radius: var(--radius-md);
        padding: 0.65rem 0.85rem 0.75rem;
        margin-bottom: 0.65rem;
        box-shadow: var(--shadow-sm);
    }
    .ux-topnav-wrap { margin-bottom: 0.35rem; }
    .ux-topnav-brand {
        font-weight: 700;
        font-size: 1.05rem;
        color: var(--ink);
        letter-spacing: -0.025em;
        line-height: 1.35;
    }
    .ux-topnav-meta { color: var(--pink-600); font-weight: 600; margin-left: 0.3rem; }
    .ux-topnav-hint {
        font-size: 0.8rem;
        color: var(--muted);
        margin-top: 0.35rem;
        line-height: 1.45;
    }

    /* 서비스 배지 */
    .ux-service-badge {
        display: inline-flex;
        align-items: center;
        gap: 0.35rem;
        font-size: 0.72rem;
        font-weight: 600;
        letter-spacing: 0.04em;
        text-transform: uppercase;
        color: var(--pink-600);
        background: rgba(255, 255, 255, 0.75);
        border: 1px solid var(--line);
        padding: 0.25rem 0.55rem;
        border-radius: var(--radius-pill);
        margin-bottom: 0.5rem;
    }

    /* 페이지 헤더 */
    .ux-page-head { margin-bottom: 1.35rem; }
    .ux-page-kicker {
        color: var(--pink-600);
        font-weight: 600;
        margin: 0 0 0.35rem 0;
        font-size: 0.82rem;
        letter-spacing: 0.02em;
        text-transform: uppercase;
    }
    .ux-page-title {
        margin: 0;
        font-size: clamp(1.45rem, 2.8vw, 1.85rem);
        font-weight: 800;
        color: var(--ink);
        letter-spacing: -0.035em;
        line-height: 1.22;
    }
    .ux-page-sub {
        margin: 0.65rem 0 0 0;
        font-size: 1.04rem;
        line-height: 1.65;
        color: var(--ink-soft);
        font-weight: 400;
    }
    .ux-page-sub strong { color: var(--ink); font-weight: 600; }

    .ux-section-title {
        font-size: 1.05rem;
        font-weight: 700;
        color: var(--ink);
        margin: 1.6rem 0 0.5rem;
        letter-spacing: -0.02em;
    }
    .ux-section-lead {
        font-size: 0.92rem;
        color: var(--muted);
        margin: -0.15rem 0 0.85rem 0;
        line-height: 1.55;
    }

    /* 홈 히어로 */
    .home-hero {
        padding: 1.5rem 1.65rem;
        border-radius: var(--radius-lg);
        background: linear-gradient(135deg, rgba(255,255,255,0.95) 0%, rgba(255,245,250,0.92) 100%);
        border: 1px solid var(--line);
        box-shadow: var(--shadow-md);
        margin-bottom: 1rem;
    }
    .home-hero h1 {
        color: var(--ink) !important;
        font-weight: 800 !important;
        letter-spacing: -0.035em !important;
        font-size: clamp(1.5rem, 3vw, 1.95rem) !important;
        line-height: 1.2 !important;
        margin: 0 0 0.5rem 0 !important;
    }
    .home-hero .ux-hero-lead {
        font-size: 1.05rem;
        color: var(--ink-soft);
        line-height: 1.68;
        margin: 0;
    }

    /* 플로우 레일 */
    .ux-flow-rail {
        display: flex; flex-wrap: wrap; align-items: center; gap: 0.4rem 0.65rem;
        padding: 0.85rem 1.05rem;
        border-radius: var(--radius-md);
        background: rgba(255, 255, 255, 0.78);
        border: 1px solid var(--line);
        margin: 0.35rem 0 1.15rem;
        box-shadow: var(--shadow-sm);
    }
    .ux-flow-item { font-size: 0.92rem; color: var(--ink); font-weight: 500; }
    .ux-flow-arrow { color: var(--rose-500); font-weight: 800; opacity: 0.85; }

    /* 시연 흐름 */
    .ux-sidebar-journey-title {
        font-weight: 700;
        color: var(--ink);
        margin-bottom: 0.55rem;
        font-size: 0.88rem;
        letter-spacing: -0.01em;
    }
    .ux-sidebar-step-active {
        padding: 0.55rem 0.65rem;
        border-radius: var(--radius-sm);
        margin: 0.22rem 0;
        border: 1px solid rgba(244, 114, 182, 0.48);
        background: rgba(255, 255, 255, 0.95);
        box-shadow: var(--shadow-sm);
        display: flex;
        align-items: center;
        gap: 0.5rem;
        font-size: 0.88rem;
        font-weight: 600;
        color: var(--pink-600);
    }
    .ux-sidebar-step-num {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        min-width: 1.6rem;
        height: 1.6rem;
        border-radius: 8px;
        background: linear-gradient(145deg, var(--rose-400), var(--pink-600));
        color: white;
        font-size: 0.78rem;
        font-weight: 800;
    }

    .ux-step-card {
        padding: 0.9rem 1.05rem;
        border-radius: var(--radius-md);
        border: 1px solid var(--line);
        background: rgba(255, 255, 255, 0.78);
        margin-bottom: 0.55rem;
        box-shadow: var(--shadow-sm);
        font-size: 0.95rem;
        line-height: 1.55;
        color: var(--ink-soft);
    }
    .ux-step-card strong { color: var(--ink); }

    /* 폼·입력 */
    [data-testid="stTextInputRoot"] label,
    [data-testid="stTextAreaRoot"] label,
    [data-testid="stNumberInputContainer"] label,
    [data-testid="stSelectbox"] label,
    [data-testid="stSlider"] label {
        font-weight: 600 !important;
        color: var(--ink) !important;
        font-size: 0.92rem !important;
    }
    [data-testid="stTextInputRoot"] input,
    [data-testid="stTextAreaRoot"] textarea {
        border-radius: 11px !important;
        border: 1px solid var(--line) !important;
        font-size: 0.95rem !important;
    }
    [data-testid="stTextInputRoot"] input:focus,
    [data-testid="stTextAreaRoot"] textarea:focus {
        border-color: rgba(219, 39, 119, 0.55) !important;
        box-shadow: var(--focus) !important;
    }

    /* 알림 */
    [data-testid="stAlert"] {
        border-radius: var(--radius-md) !important;
        border: 1px solid var(--line) !important;
        padding: 0.85rem 1rem !important;
        font-size: 0.95rem !important;
        line-height: 1.55 !important;
    }
    [data-testid="stAlert"][data-baseweb="notification"] {
        background: rgba(255, 255, 255, 0.88) !important;
    }

    /* Expander */
    [data-testid="stExpander"] details {
        border-radius: var(--radius-md) !important;
        border: 1px solid var(--line) !important;
        background: rgba(255, 255, 255, 0.62) !important;
    }
    [data-testid="stExpander"] summary {
        font-weight: 600 !important;
        color: var(--ink) !important;
        font-size: 0.92rem !important;
    }

    div[data-testid="stVerticalBlockBorderWrapper"] {
        border-radius: var(--radius-md) !important;
        border-color: var(--line) !important;
        background: rgba(255, 255, 255, 0.55) !important;
    }

    .stButton > button {
        border-radius: 11px !important;
        font-weight: 600 !important;
        font-size: 0.92rem !important;
        letter-spacing: -0.01em;
        transition: transform 0.14s ease, box-shadow 0.14s ease !important;
    }
    .stButton > button:active { transform: scale(0.985); }
    .stButton > button[kind="primary"] {
        background: linear-gradient(145deg, var(--rose-500), var(--pink-600)) !important;
        border: none !important;
        color: white !important;
        box-shadow: 0 4px 16px rgba(219, 39, 119, 0.32);
    }
    .stButton > button[kind="primary"]:hover {
        box-shadow: 0 6px 22px rgba(219, 39, 119, 0.42);
    }
    .stButton > button[kind="secondary"] {
        background: rgba(255, 255, 255, 0.9) !important;
        border: 1px solid var(--line) !important;
        color: var(--ink) !important;
    }
    .stButton > button:focus-visible { box-shadow: var(--focus) !important; }

    /* 메트릭 */
    [data-testid="stMetricContainer"] {
        background: rgba(255, 255, 255, 0.72);
        border: 1px solid var(--line);
        border-radius: var(--radius-md);
        padding: 0.65rem 0.75rem !important;
        box-shadow: var(--shadow-sm);
    }
    [data-testid="stMetricValue"] {
        color: var(--ink) !important;
        font-weight: 800 !important;
        font-size: 1.35rem !important;
        letter-spacing: -0.02em !important;
    }
    [data-testid="stMetricLabel"] {
        color: var(--muted) !important;
        font-size: 0.78rem !important;
        font-weight: 600 !important;
        text-transform: uppercase;
        letter-spacing: 0.04em;
    }

    /* 캡션 */
    [data-testid="stCaption"] {
        color: var(--muted) !important;
        font-size: 0.82rem !important;
        line-height: 1.5 !important;
    }

    /* 라디오·슬라이더 */
    [data-testid="stRadio"] label { font-size: 0.9rem !important; }
    [data-baseweb="slider"] [role="slider"] { background: var(--pink-600) !important; }

    /* 채팅 */
    .stChatMessage {
        background: rgba(255, 255, 255, 0.92) !important;
        border-radius: var(--radius-md) !important;
        border: 1px solid rgba(244, 114, 182, 0.15) !important;
    }
    [data-testid="stChatInput"] textarea {
        border-radius: 11px !important;
        border: 1px solid var(--line) !important;
        font-size: 0.95rem !important;
    }

    /* 페이지 링크 버튼 느낌 */
    [data-testid="stPageLink-NavButton"] a {
        border-radius: 11px !important;
        font-weight: 600 !important;
    }

    /* 임시저장 스트립 */
    .ux-save-strip {
        background: rgba(255, 255, 255, 0.88);
        border: 1px solid var(--line);
        border-radius: var(--radius-md);
        padding: 0.55rem 0.85rem;
        margin-bottom: 0.85rem;
        box-shadow: var(--shadow-sm);
    }
    .ux-save-strip .ux-save-caption {
        font-size: 0.8rem;
        color: var(--muted);
        line-height: 1.45;
    }

    /* 푸터 */
    .ux-trust-foot {
        margin-top: 2.25rem;
        padding: 1rem 1.15rem;
        border-radius: var(--radius-md);
        background: rgba(255, 255, 255, 0.78);
        border: 1px solid var(--line);
        font-size: 0.88rem;
        color: var(--muted);
        line-height: 1.6;
    }
    .ux-trust-foot code {
        font-size: 0.82em;
        background: rgba(244, 114, 182, 0.1);
        padding: 0.1em 0.35em;
        border-radius: 5px;
    }

    /* 서브헤딩 (Streamlit markdown h2/h3) */
    [data-testid="stMarkdownContainer"] h2 {
        font-size: 1.2rem !important;
        font-weight: 700 !important;
        color: var(--ink) !important;
        margin-top: 1.5rem !important;
        letter-spacing: -0.02em !important;
    }
    [data-testid="stMarkdownContainer"] h3 {
        font-size: 1.05rem !important;
        font-weight: 700 !important;
        color: var(--ink) !important;
    }
</style>
""",
        unsafe_allow_html=True,
    )


def render_service_badge() -> None:
    """상단에 제품 톤 안내 (데모 경계)."""
    st.markdown(
        '<div class="ux-service-badge">✨ Prototype UI · 로컬 데모</div>',
        unsafe_allow_html=True,
    )


def render_top_nav(page_label: str) -> None:
    label_html = f'<span class="ux-topnav-meta">{page_label}</span>' if page_label else ""
    st.markdown(
        f"""
<div class="ux-topnav-shell">
  <div class="ux-topnav-wrap">
    <div class="ux-topnav">
      <div class="ux-topnav-brand">통합 데이팅 AI {label_html}</div>
    </div>
  </div>
  <div class="ux-topnav-hint">아래 단계를 따라가면 <strong>프로필 → 매칭 → 인사 → 대화</strong>까지 한 흐름으로 이어집니다.</div>
</div>
""",
        unsafe_allow_html=True,
    )
    r1 = st.columns(5)
    links = [
        ("app.py", "홈", "앱 시작 · 키워드 미리 적기"),
        ("pages/01_AI_프로필_생성.py", "① 프로필", "키워드 기반 AI 프로필"),
        ("pages/02_프로필_매칭_검색.py", "② 매칭", "조건 검색 · 상대 선택"),
        ("pages/03_인사말_생성.py", "③ 인사말", "첫 메시지 초안"),
        ("pages/04_대화_도우미.py", "④ 대화", "멘트·RAG·코칭"),
    ]
    for col, (path, label, tip) in zip(r1, links):
        with col:
            st.page_link(path, label=label, use_container_width=True, help=tip)


def render_journey_sidebar(active: str) -> None:
    try:
        idx_active = _JOURNEY_ORDER.index(active)
    except ValueError:
        idx_active = -1
    with st.sidebar:
        st.markdown(
            '<div class="ux-sidebar-journey"><div class="ux-sidebar-journey-title">진행 단계</div></div>',
            unsafe_allow_html=True,
        )
        for i, (key, label, path) in enumerate(_JOURNEY_META):
            is_active = key == active
            is_done = idx_active >= 0 and i < idx_active
            label_txt = f"{'✓ ' if is_done and not is_active else ''}{i + 1}. {label}"
            if is_active:
                st.markdown(
                    f'<div class="ux-sidebar-step-active">'
                    f'<span class="ux-sidebar-step-num">{i + 1}</span>'
                    f'<span>{label} · 현재</span></div>',
                    unsafe_allow_html=True,
                )
            else:
                st.page_link(path, label=label_txt, use_container_width=True, help=f"{i + 1}단계: {label}")


def render_page_header(*, kicker: str, title: str, subtitle: str | None = None) -> None:
    sub_html = ""
    if subtitle:
        sub_html = f'<p class="ux-page-sub">{_subtitle_md_to_html(subtitle)}</p>'
    st.markdown(
        f'<div class="ux-page-head">'
        f'<p class="ux-page-kicker">{html_module.escape(kicker)}</p>'
        f'<h1 class="ux-page-title">{html_module.escape(title)}</h1>'
        f"{sub_html}</div>",
        unsafe_allow_html=True,
    )


def render_trust_footer() -> None:
    try:
        from _persistence import save_session_to_disk

        save_session_to_disk()
    except Exception:
        pass
    st.markdown(
        '<div class="ux-trust-foot">'
        "<strong>개인정보·보안 안내</strong><br>"
        "입력·생성 내용은 이 브라우저 세션과 <code>data/app_session_state.json</code>에 저장될 수 있습니다. "
        "실서비스에서는 약관·동의·암호화·접근 통제가 필요합니다. "
        "API 키는 <code>secrets.toml</code> 또는 <code>.env</code>에만 보관하세요."
        "</div>",
        unsafe_allow_html=True,
    )


def render_page_shell(page_label: str, *, journey_step: str | None = None) -> None:
    try:
        from _persistence import restore_session_from_disk

        restore_session_from_disk()
    except Exception:
        pass
    inject_app_styles()
    render_service_badge()
    render_top_nav(page_label)
    try:
        from _persistence import render_persistence_topbar

        render_persistence_topbar()
    except ImportError as e:
        st.error(f"저장 모듈을 불러올 수 없습니다: `{e}`")
    if journey_step is not None:
        render_journey_sidebar(journey_step)
    try:
        from _persistence import render_persistence_sidebar

        render_persistence_sidebar()
    except ImportError:
        pass


def render_match_page_styles() -> None:
    render_page_shell("프로필 매칭", journey_step=JOURNEY_MATCH)


def render_home_flow_rail() -> None:
    st.markdown(
        """
<div class="ux-flow-rail" aria-label="추천 이용 순서">
  <div class="ux-flow-item"><strong>①</strong> 프로필</div>
  <span class="ux-flow-arrow">→</span>
  <div class="ux-flow-item"><strong>②</strong> 매칭</div>
  <span class="ux-flow-arrow">→</span>
  <div class="ux-flow-item"><strong>③</strong> 인사</div>
  <span class="ux-flow-arrow">→</span>
  <div class="ux-flow-item"><strong>④</strong> 대화</div>
</div>
""",
        unsafe_allow_html=True,
    )


def render_home_navigation() -> None:
    st.markdown('<p class="ux-section-title">단계별 안내</p>', unsafe_allow_html=True)
    st.markdown(
        '<p class="ux-section-lead">왼쪽 <strong>진행 단계</strong>와 같은 순서입니다. ①을 건너뛰려면 ②에서 바로 검색할 수 있어요.</p>',
        unsafe_allow_html=True,
    )
    steps = [
        (
            "①",
            "AI 프로필",
            "pages/01_AI_프로필_생성.py",
            "관심 키워드와 메모를 바탕으로 나만의 프로필 카드를 만듭니다.",
        ),
        (
            "②",
            "프로필 매칭",
            "pages/02_프로필_매칭_검색.py",
            "나이·성별·관심사로 후보를 좁히고 한 명을 선택합니다.",
        ),
        (
            "③",
            "인사말",
            "pages/03_인사말_생성.py",
            "선택한 상대에게 보낼 첫 인사 멘트 초안을 만듭니다.",
        ),
        (
            "④",
            "대화 도우미",
            "pages/04_대화_도우미.py",
            "짧은 멘트, 유사 대화 참고, 투표형 조언으로 대화를 연습합니다.",
        ),
    ]
    for badge, title, path, desc in steps:
        st.markdown(
            f'<div class="ux-step-card"><strong>{badge} {title}</strong> — {desc}</div>',
            unsafe_allow_html=True,
        )
        st.page_link(path, label=f"{badge} 이동", use_container_width=True)

    st.markdown('<p class="ux-section-title">바로가기</p>', unsafe_allow_html=True)
    st.markdown('<p class="ux-section-lead">자주 쓰는 화면으로 바로 점프합니다.</p>', unsafe_allow_html=True)
    g1, g2 = st.columns(2)
    with g1:
        st.page_link("pages/01_AI_프로필_생성.py", label="① AI 프로필", use_container_width=True)
        st.page_link("pages/02_프로필_매칭_검색.py", label="② 매칭 검색", use_container_width=True)
    with g2:
        st.page_link("pages/03_인사말_생성.py", label="③ 인사말", use_container_width=True)
        st.page_link("pages/04_대화_도우미.py", label="④ 대화 도우미", use_container_width=True)
