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
# 홈(app.py)을 거친 세션만 True. 새로고침 시 세션이 비워지면 하위 페이지에서 홈으로 보냄.
SESSION_FROM_HOME_KEY = "_session_from_home"

JOURNEY_PROFILE = "profile"
JOURNEY_MATCH = "match"
JOURNEY_GREETING = "greeting"
JOURNEY_COACH = "coach"
JOURNEY_KEYWORDS = JOURNEY_PROFILE

_JOURNEY_ORDER = [JOURNEY_HOME, JOURNEY_PROFILE, JOURNEY_MATCH, JOURNEY_GREETING, JOURNEY_COACH]

# 사이드바·네비 단계 잠금용 (journey_can_access 인자)
_JOURNEY_GATE_STEP: dict[str, str] = {
    JOURNEY_PROFILE: "profile",
    JOURNEY_MATCH: "match",
    JOURNEY_GREETING: "greeting",
    JOURNEY_COACH: "coach",
}

# 홈은 ‘단계’가 아니라 진입 화면 — 사이드바에는 ①~④만 노출해 인지 부하를 줄임
_STEP_MARKERS = ["①", "②", "③", "④"]
_FLOW_STEPS: list[tuple[str, str, str]] = [
    (JOURNEY_PROFILE, "프로필", "pages/01_AI_프로필_생성.py"),
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
<link rel="preconnect" href="https://cdn.jsdelivr.net" crossorigin>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.min.css" crossorigin>
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
        --violet-500: #8b5cf6;
        --ink: #2d0a18;
        --ink-soft: #5c2740;
        --muted: #7a4a5e;
        --surface: #ffffff;
        --surface-glass: rgba(255, 255, 255, 0.78);
        --surface-muted: rgba(255, 255, 255, 0.55);
        --radius-lg: 22px;
        --radius-md: 16px;
        --radius-sm: 11px;
        --radius-pill: 9999px;
        --shadow-sm: 0 2px 14px rgba(120, 20, 60, 0.07);
        --shadow-md: 0 16px 48px rgba(120, 20, 60, 0.12);
        --shadow-lg: 0 24px 64px rgba(90, 15, 45, 0.14);
        --shadow-glow: 0 0 80px rgba(244, 114, 182, 0.22);
        --shadow-nav: 0 1px 0 rgba(244, 114, 182, 0.2);
        --focus: 0 0 0 3px rgba(244, 114, 182, 0.45);
        --line: rgba(244, 114, 182, 0.32);
        --line-strong: rgba(219, 39, 119, 0.45);
        --font: "Pretendard", -apple-system, BlinkMacSystemFont, system-ui, sans-serif;
    }

    html { scroll-behavior: smooth; }
    @media (prefers-reduced-motion: reduce) {
        html { scroll-behavior: auto; }
        * { transition: none !important; }
        [data-testid="stMain"] [data-testid="stVerticalBlockBorderWrapper"] [data-testid="stPageLink-NavButton"] a:hover,
        .element-container:has(.ux-mark-home-start) + .element-container [data-testid="stPageLink-NavButton"] a:hover {
            transform: none !important;
        }
        .ux-feature-card:hover { transform: none !important; }
    }

    html, body, .stApp {
        font-family: var(--font) !important;
        -webkit-font-smoothing: antialiased;
        -moz-osx-font-smoothing: grayscale;
    }

    [data-testid="stMarkdownContainer"] p,
    [data-testid="stWidgetLabel"] label,
    .stCaption {
        font-family: var(--font) !important;
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
        position: relative;
        background:
            radial-gradient(ellipse 900px 420px at 12% -6%, rgba(251, 207, 232, 0.55) 0%, transparent 55%),
            radial-gradient(ellipse 700px 380px at 92% 8%, rgba(233, 213, 255, 0.35) 0%, transparent 50%),
            radial-gradient(ellipse 600px 360px at 50% 100%, rgba(254, 205, 211, 0.4) 0%, transparent 45%),
            linear-gradient(165deg, #fff9fc 0%, #fff0f6 38%, #faf5ff 72%, #fffafd 100%) !important;
    }
    [data-testid="stAppViewContainer"]::before {
        content: "";
        position: fixed;
        inset: 0;
        pointer-events: none;
        z-index: 0;
        opacity: 0.4;
        background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)' opacity='0.05'/%3E%3C/svg%3E");
        background-size: 180px 180px;
    }
    section[data-testid="stMain"], [data-testid="stSidebar"] {
        position: relative;
        z-index: 1;
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
        max-width: 1180px;
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
    .ux-sidebar-step-locked {
        padding: 0.45rem 0.55rem;
        border-radius: var(--radius-sm);
        color: var(--muted);
        font-size: 0.88rem;
        font-weight: 500;
        opacity: 0.72;
    }
    .ux-topnav-locked {
        display: flex;
        align-items: center;
        justify-content: center;
        min-height: 2.35rem;
        padding: 0.35rem 0.4rem;
        border-radius: var(--radius-sm);
        background: rgba(255,255,255,0.35);
        color: var(--muted);
        font-size: 0.82rem;
        font-weight: 500;
        opacity: 0.75;
    }
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

    /* 페이지 헤더 */
    .ux-page-head { margin-bottom: 1.35rem; }
    .ux-page-kicker {
        display: inline-block;
        color: var(--pink-600);
        font-weight: 700;
        margin: 0 0 0.45rem 0;
        font-size: 0.78rem;
        letter-spacing: 0.06em;
        text-transform: uppercase;
        padding: 0.28rem 0.65rem;
        border-radius: var(--radius-pill);
        background: linear-gradient(135deg, rgba(255, 255, 255, 0.95), rgba(255, 240, 248, 0.9));
        border: 1px solid rgba(244, 114, 182, 0.35);
        box-shadow: var(--shadow-sm);
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
        display: flex;
        align-items: center;
        gap: 0.5rem;
        font-size: 1.08rem;
        font-weight: 800;
        color: var(--ink);
        margin: 1.75rem 0 0.5rem;
        letter-spacing: -0.03em;
    }
    .ux-section-title::before {
        content: "";
        width: 4px;
        height: 1.15em;
        border-radius: 4px;
        background: linear-gradient(180deg, var(--rose-400), var(--pink-600));
        flex-shrink: 0;
    }
    .ux-section-lead {
        font-size: 0.92rem;
        color: var(--muted);
        margin: -0.15rem 0 0.85rem 0;
        line-height: 1.55;
    }

    /* 홈 히어로 — 프리미엄 글래스 */
    .ux-hero-shell {
        position: relative;
        margin-bottom: 1.15rem;
        border-radius: var(--radius-lg);
        padding: 2px;
        background: linear-gradient(
            135deg,
            rgba(251, 113, 133, 0.55),
            rgba(236, 72, 153, 0.45),
            rgba(167, 139, 250, 0.4)
        );
        box-shadow: var(--shadow-md), var(--shadow-glow);
    }
    .ux-hero-shell-inner {
        position: relative;
        border-radius: calc(var(--radius-lg) - 2px);
        overflow: hidden;
        background: linear-gradient(155deg, rgba(255, 255, 255, 0.97) 0%, rgba(255, 250, 252, 0.94) 55%, rgba(253, 244, 255, 0.92) 100%);
        backdrop-filter: blur(12px);
        -webkit-backdrop-filter: blur(12px);
    }
    .ux-hero-blob {
        position: absolute;
        border-radius: 50%;
        filter: blur(48px);
        opacity: 0.55;
        pointer-events: none;
    }
    .ux-hero-blob--a {
        width: 220px;
        height: 220px;
        top: -80px;
        right: -40px;
        background: radial-gradient(circle, rgba(251, 113, 133, 0.5) 0%, transparent 70%);
        animation: ux-float 14s ease-in-out infinite;
    }
    .ux-hero-blob--b {
        width: 180px;
        height: 180px;
        bottom: -60px;
        left: -30px;
        background: radial-gradient(circle, rgba(167, 139, 250, 0.45) 0%, transparent 70%);
        animation: ux-float 18s ease-in-out infinite reverse;
    }
    @keyframes ux-float {
        0%, 100% { transform: translate(0, 0) scale(1); }
        50% { transform: translate(8px, -12px) scale(1.05); }
    }
    @media (prefers-reduced-motion: reduce) {
        .ux-hero-blob--a, .ux-hero-blob--b { animation: none; }
    }
    .home-hero {
        position: relative;
        z-index: 1;
        padding: 1.85rem 2rem 1.9rem;
        margin: 0;
        border: none;
        box-shadow: none;
        background: transparent;
    }
    .ux-hero-eyebrow {
        display: inline-flex;
        align-items: center;
        gap: 0.45rem;
        font-size: 0.84rem;
        font-weight: 600;
        letter-spacing: -0.02em;
        text-transform: none;
        color: var(--ink-soft);
        margin-bottom: 0.75rem;
        padding: 0.38rem 0.9rem 0.38rem 0.75rem;
        border-radius: var(--radius-pill);
        background: rgba(255, 255, 255, 0.65);
        border: 1px solid rgba(244, 114, 182, 0.22);
        box-shadow: 0 1px 8px rgba(120, 20, 60, 0.06);
    }
    .ux-hero-eyebrow::before {
        content: "";
        width: 7px;
        height: 7px;
        border-radius: 50%;
        flex-shrink: 0;
        background: linear-gradient(145deg, var(--rose-400), var(--pink-600));
        box-shadow: 0 0 0 3px rgba(244, 114, 182, 0.18);
    }
    .home-hero h1 {
        color: var(--ink) !important;
        font-weight: 800 !important;
        letter-spacing: -0.045em !important;
        font-size: clamp(1.55rem, 3.2vw, 2.15rem) !important;
        line-height: 1.18 !important;
        margin: 0 0 0.55rem 0 !important;
    }
    .ux-hero-rule {
        width: min(100%, 12rem);
        height: 3px;
        margin: 0 0 1rem 0;
        border-radius: 3px;
        background: linear-gradient(90deg, var(--rose-400), var(--pink-600) 55%, rgba(167, 139, 250, 0.65));
        opacity: 0.9;
    }
    .ux-hero-accent {
        background: linear-gradient(105deg, var(--rose-500) 0%, var(--pink-600) 45%, var(--violet-500) 100%);
        -webkit-background-clip: text;
        background-clip: text;
        color: transparent !important;
        -webkit-text-fill-color: transparent;
    }
    .home-hero .ux-hero-lead {
        font-size: 1.05rem;
        color: var(--ink-soft);
        line-height: 1.74;
        margin: 0;
        max-width: 42rem;
        font-weight: 450;
    }
    .home-hero .ux-hero-lead strong {
        color: var(--ink);
        font-weight: 700;
    }

    /* 플로우 트랙 — 칩 + 연결선 */
    .ux-flow-rail {
        display: flex;
        flex-wrap: wrap;
        align-items: stretch;
        gap: 0;
        padding: 1rem 1.1rem;
        border-radius: var(--radius-md);
        background: rgba(255, 255, 255, 0.55);
        backdrop-filter: blur(14px);
        -webkit-backdrop-filter: blur(14px);
        border: 1px solid rgba(255, 255, 255, 0.85);
        box-shadow: var(--shadow-sm), inset 0 1px 0 rgba(255, 255, 255, 0.9);
        margin: 0 0 1.25rem;
    }
    .ux-flow-step {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        flex: 1 1 auto;
        min-width: 5.5rem;
        padding: 0.45rem 0.35rem;
    }
    .ux-flow-num {
        display: flex;
        align-items: center;
        justify-content: center;
        width: 2rem;
        height: 2rem;
        border-radius: 12px;
        font-size: 0.82rem;
        font-weight: 800;
        color: #fff;
        background: linear-gradient(145deg, var(--rose-400), var(--pink-600));
        box-shadow: 0 4px 14px rgba(219, 39, 119, 0.35);
        flex-shrink: 0;
    }
    .ux-flow-label {
        font-size: 0.88rem;
        font-weight: 700;
        color: var(--ink);
        letter-spacing: -0.02em;
    }
    .ux-flow-sub {
        display: block;
        font-size: 0.72rem;
        font-weight: 500;
        color: var(--muted);
        margin-top: 0.12rem;
    }
    .ux-flow-bridge {
        display: flex;
        align-items: center;
        justify-content: center;
        width: 1.25rem;
        flex-shrink: 0;
        color: var(--rose-400);
        font-weight: 800;
        font-size: 1rem;
        opacity: 0.85;
    }
    @media (max-width: 640px) {
        .ux-flow-bridge { width: 100%; height: 0.5rem; transform: rotate(90deg); }
    }

    /* 홈 — 기능 카드·신뢰 스트립·시작 CTA */
    .ux-home-section-after-flow {
        margin-top: 1.85rem !important;
    }
    .ux-home-lead-tight {
        margin: -0.25rem 0 1rem 0 !important;
        font-size: 0.9rem !important;
        color: var(--muted) !important;
        line-height: 1.55 !important;
    }
    .ux-feature-card {
        height: 100%;
        min-height: 9.5rem;
        padding: 1rem 1rem 0.85rem;
        border-radius: var(--radius-md);
        background: linear-gradient(165deg, rgba(255, 255, 255, 0.92) 0%, rgba(255, 248, 252, 0.88) 100%);
        border: 1px solid rgba(255, 255, 255, 0.95);
        box-shadow: var(--shadow-sm), inset 0 1px 0 rgba(255, 255, 255, 0.9);
        margin-bottom: 0.45rem;
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    @media (hover: hover) {
        .ux-feature-card:hover {
            transform: translateY(-3px);
            box-shadow: var(--shadow-md), inset 0 1px 0 rgba(255, 255, 255, 0.95);
        }
    }
    .ux-feature-card-icon {
        font-size: 1.65rem;
        line-height: 1;
        margin-bottom: 0.55rem;
        filter: drop-shadow(0 2px 8px rgba(219, 39, 119, 0.15));
    }
    .ux-feature-card-title {
        font-size: 0.95rem;
        font-weight: 800;
        color: var(--ink);
        letter-spacing: -0.03em;
        margin: 0 0 0.35rem 0;
        line-height: 1.25;
    }
    .ux-feature-card-desc {
        font-size: 0.82rem;
        font-weight: 500;
        color: var(--muted);
        line-height: 1.5;
        margin: 0;
    }
    .ux-mark-home-start { height: 0; margin: 0; padding: 0; overflow: hidden; visibility: hidden; }
    .element-container:has(.ux-mark-home-start) + .element-container [data-testid="stPageLink-NavButton"] a {
        justify-content: center !important;
        min-height: 2.85rem !important;
        font-size: 0.98rem !important;
        font-weight: 700 !important;
        letter-spacing: -0.02em !important;
        border: none !important;
        color: #fff !important;
        background: linear-gradient(135deg, var(--rose-500) 0%, var(--pink-600) 48%, #c026d3 100%) !important;
        box-shadow: 0 8px 28px rgba(219, 39, 119, 0.35), 0 2px 8px rgba(90, 15, 45, 0.1) !important;
        transition: transform 0.18s ease, box-shadow 0.18s ease !important;
    }
    .element-container:has(.ux-mark-home-start) + .element-container [data-testid="stPageLink-NavButton"] a:hover {
        transform: translateY(-2px);
        box-shadow: 0 12px 36px rgba(219, 39, 119, 0.42), 0 4px 12px rgba(90, 15, 45, 0.12) !important;
    }
    .element-container:has(.ux-mark-home-start) + .element-container [data-testid="stPageLink-NavButton"] a:focus-visible {
        box-shadow: var(--focus), 0 8px 28px rgba(219, 39, 119, 0.35) !important;
    }

    /* 시연 흐름 */
    .ux-sidebar-brand-wrap {
        display: flex;
        align-items: center;
        gap: 0.45rem;
        margin-bottom: 0.7rem;
    }
    .ux-sidebar-brand-icon {
        font-size: 1.15rem;
        line-height: 1;
        filter: drop-shadow(0 2px 6px rgba(219, 39, 119, 0.25));
    }
    .ux-sidebar-brand {
        font-size: 1rem;
        font-weight: 800;
        background: linear-gradient(105deg, var(--ink) 0%, var(--pink-600) 100%);
        -webkit-background-clip: text;
        background-clip: text;
        color: transparent;
        -webkit-text-fill-color: transparent;
        letter-spacing: -0.03em;
        line-height: 1.25;
        margin: 0;
    }
    .ux-sidebar-here {
        font-size: 0.84rem;
        font-weight: 600;
        color: var(--pink-600);
        padding: 0.48rem 0.6rem;
        border-radius: var(--radius-sm);
        background: rgba(255, 255, 255, 0.92);
        border: 1px solid rgba(244, 114, 182, 0.38);
        margin-bottom: 0.55rem;
        box-shadow: var(--shadow-sm);
    }
    .ux-sidebar-divider {
        height: 1px;
        background: var(--line);
        margin: 0.55rem 0 0.65rem;
        opacity: 0.9;
    }
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
        transition: background 0.15s ease, box-shadow 0.15s ease !important;
    }
    [data-testid="stPageLink-NavButton"] a:hover {
        background: rgba(255, 255, 255, 0.75) !important;
    }
    [data-testid="stPageLink-NavButton"] a:focus-visible {
        box-shadow: var(--focus) !important;
    }

    .ux-nav-rule {
        height: 2px;
        margin: 0.55rem 0 1.15rem;
        border-radius: 2px;
        background: linear-gradient(90deg, transparent 0%, rgba(251, 113, 133, 0.45) 20%, rgba(236, 72, 153, 0.5) 50%, rgba(167, 139, 250, 0.4) 80%, transparent 100%);
        opacity: 0.95;
    }

    .ux-topnav-kicker {
        font-size: 0.72rem;
        font-weight: 700;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        color: var(--muted);
        margin: 0 0 0.4rem 0;
    }
    [data-testid="stMain"] [data-testid="stVerticalBlockBorderWrapper"] {
        border-radius: var(--radius-md) !important;
        border: 1px solid rgba(255, 255, 255, 0.9) !important;
        background: linear-gradient(165deg, rgba(255, 255, 255, 0.72) 0%, rgba(255, 245, 250, 0.55) 100%) !important;
        box-shadow: var(--shadow-sm), inset 0 1px 0 rgba(255, 255, 255, 0.95) !important;
        backdrop-filter: blur(12px) !important;
        -webkit-backdrop-filter: blur(12px) !important;
        padding: 0.55rem 0.65rem 0.65rem !important;
    }
    [data-testid="stMain"] [data-testid="stVerticalBlockBorderWrapper"] [data-testid="stPageLink-NavButton"] a {
        background: rgba(255, 255, 255, 0.88) !important;
        border: 1px solid rgba(244, 114, 182, 0.22) !important;
        box-shadow: 0 2px 8px rgba(120, 20, 60, 0.05) !important;
    }
    [data-testid="stMain"] [data-testid="stVerticalBlockBorderWrapper"] [data-testid="stPageLink-NavButton"] a:hover {
        background: rgba(255, 255, 255, 1) !important;
        border-color: rgba(236, 72, 153, 0.45) !important;
        box-shadow: 0 4px 16px rgba(219, 39, 119, 0.12) !important;
        transform: translateY(-1px);
    }
    [data-testid="stMain"] [data-testid="stVerticalBlockBorderWrapper"] .ux-section-title {
        margin-top: 0.25rem !important;
    }

    [data-testid="stTextAreaRoot"] textarea {
        background: rgba(255, 255, 255, 0.92) !important;
        box-shadow: inset 0 1px 3px rgba(120, 20, 60, 0.06) !important;
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


def render_top_nav() -> None:
    """글래스 패널 안 상단 빠른 이동."""
    from _match_context import journey_can_access

    with st.container(border=True):
        st.markdown('<p class="ux-topnav-kicker">빠른 이동</p>', unsafe_allow_html=True)
        r1 = st.columns(5)
        links: list[tuple[str, str, str, str | None]] = [
            ("app.py", "홈", "키워드 입력 · 추천 순서 안내", None),
            ("pages/01_AI_프로필_생성.py", "① 프로필", "키워드 기반 AI 프로필", "profile"),
            ("pages/02_프로필_매칭_검색.py", "② 매칭", "조건 검색 · 상대 선택", "match"),
            ("pages/03_인사말_생성.py", "③ 인사말", "첫 메시지 초안", "greeting"),
            ("pages/04_대화_도우미.py", "④ 대화", "한마디·예시 코칭·조언 비교", "coach"),
        ]
        for col, (path, label, tip, gate) in zip(r1, links):
            with col:
                if gate is None:
                    st.page_link(path, label=label, use_container_width=True, help=tip)
                else:
                    ok, _ = journey_can_access(gate)
                    if ok:
                        st.page_link(path, label=label, use_container_width=True, help=tip)
                    else:
                        st.markdown(
                            f'<div class="ux-topnav-locked" title="이전 단계를 먼저 완료하세요">'
                            f"{html_module.escape(label)} 🔒</div>",
                            unsafe_allow_html=True,
                        )
    st.markdown('<div class="ux-nav-rule" aria-hidden="true"></div>', unsafe_allow_html=True)


def render_journey_sidebar(active: str) -> None:
    from _match_context import journey_can_access

    try:
        idx_active = _JOURNEY_ORDER.index(active)
    except ValueError:
        idx_active = -1
    with st.sidebar:
        st.markdown(
            '<div class="ux-sidebar-brand-wrap">'
            '<span class="ux-sidebar-brand-icon" aria-hidden="true">💘</span>'
            '<div class="ux-sidebar-brand">통합 데이팅 AI</div>'
            "</div>",
            unsafe_allow_html=True,
        )
        if active == JOURNEY_HOME:
            st.markdown('<div class="ux-sidebar-here">현재 · 홈</div>', unsafe_allow_html=True)
        else:
            st.page_link("app.py", label="← 홈", use_container_width=True, help="키워드·메모 입력 화면")
        st.markdown('<div class="ux-sidebar-divider"></div>', unsafe_allow_html=True)
        st.markdown('<div class="ux-sidebar-journey-title">진행 단계 (①~④)</div>', unsafe_allow_html=True)

        for i, (key, label, path) in enumerate(_FLOW_STEPS):
            sym = _STEP_MARKERS[i]
            try:
                order_idx = _JOURNEY_ORDER.index(key)
            except ValueError:
                order_idx = i + 1
            is_active = key == active
            is_done = idx_active >= 0 and idx_active > order_idx
            label_txt = f"{'✓ ' if is_done and not is_active else ''}{sym} {label}"
            gate_target = _JOURNEY_GATE_STEP.get(key, "profile")
            step_ok, _ = journey_can_access(gate_target)
            if is_active:
                st.markdown(
                    f'<div class="ux-sidebar-step-active">'
                    f'<span class="ux-sidebar-step-num">{sym}</span>'
                    f"<span>{html_module.escape(label)} · 현재</span></div>",
                    unsafe_allow_html=True,
                )
            elif not step_ok:
                st.markdown(
                    f'<div class="ux-sidebar-step-locked">{html_module.escape(label_txt)} 🔒</div>',
                    unsafe_allow_html=True,
                )
                st.caption("이전 단계 완료 후 이동")
            else:
                st.page_link(
                    path,
                    label=label_txt,
                    use_container_width=True,
                    help=f"{sym} {label}: 다음 화면으로 이동",
                )


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
    """페이지 끝에서 진행 내용만 조용히 디스크에 저장(시연용 UI 없음)."""
    try:
        from _persistence import save_session_to_disk

        save_session_to_disk()
    except Exception:
        pass


def render_page_shell(*, journey_step: str | None = None) -> None:
    try:
        from _persistence import restore_session_from_disk

        restore_session_from_disk()
    except Exception:
        pass

    # 새로고침(F5) → 새 Streamlit 세션 → 표식 없음 → 홈으로 이동
    if journey_step is not None and journey_step != JOURNEY_HOME:
        if not st.session_state.get(SESSION_FROM_HOME_KEY):
            st.switch_page("app.py")
    if journey_step == JOURNEY_HOME:
        st.session_state[SESSION_FROM_HOME_KEY] = True

    inject_app_styles()
    render_top_nav()
    if journey_step is not None:
        render_journey_sidebar(journey_step)


def render_match_page_styles() -> None:
    render_page_shell(journey_step=JOURNEY_MATCH)


def render_home_hero() -> None:
    st.markdown(
        """
<div class="ux-hero-shell">
  <div class="ux-hero-shell-inner">
    <div class="ux-hero-blob ux-hero-blob--a" aria-hidden="true"></div>
    <div class="ux-hero-blob ux-hero-blob--b" aria-hidden="true"></div>
    <div class="home-hero">
      <span class="ux-hero-eyebrow">통합 데이팅 AI</span>
      <h1>나에게 맞는 만남까지, <span class="ux-hero-accent">한 흐름으로</span></h1>
      <div class="ux-hero-rule" aria-hidden="true"></div>
      <p class="ux-hero-lead">
        <strong>프로필</strong>로 나를 소개하고, <strong>매칭</strong>에서 상대를 고른 뒤
        <strong>첫 인사</strong>와 <strong>대화 연습</strong>까지 자연스럽게 이어집니다.
      </p>
    </div>
  </div>
</div>
""",
        unsafe_allow_html=True,
    )


def render_home_flow_rail() -> None:
    st.markdown(
        """
<div class="ux-flow-rail" aria-label="추천 이용 순서">
  <div class="ux-flow-step">
    <span class="ux-flow-num">1</span>
    <div><span class="ux-flow-label">프로필</span><span class="ux-flow-sub">AI 카드</span></div>
  </div>
  <span class="ux-flow-bridge" aria-hidden="true">→</span>
  <div class="ux-flow-step">
    <span class="ux-flow-num">2</span>
    <div><span class="ux-flow-label">매칭</span><span class="ux-flow-sub">검색·선택</span></div>
  </div>
  <span class="ux-flow-bridge" aria-hidden="true">→</span>
  <div class="ux-flow-step">
    <span class="ux-flow-num">3</span>
    <div><span class="ux-flow-label">인사</span><span class="ux-flow-sub">첫 멘트</span></div>
  </div>
  <span class="ux-flow-bridge" aria-hidden="true">→</span>
  <div class="ux-flow-step">
    <span class="ux-flow-num">4</span>
    <div><span class="ux-flow-label">대화</span><span class="ux-flow-sub">코칭·RAG</span></div>
  </div>
</div>
""",
        unsafe_allow_html=True,
    )


def render_home_feature_grid() -> None:
    """홈 본문 채움: 단계별 요약 카드(이동 버튼 없음 — 사이드바·상단 네비 사용)."""
    st.markdown(
        '<p class="ux-section-title ux-home-section-after-flow">단계별로 이렇게 써요</p>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<p class="ux-home-lead-tight">순서는 상단 <strong>빠른 이동</strong>·왼쪽 <strong>진행 단계</strong>와 같아요.</p>',
        unsafe_allow_html=True,
    )
    cols = st.columns(4, gap="medium")
    items: list[tuple[str, str, str]] = [
        ("🪪", "① AI 프로필", "키워드·톤에 맞는 소개 카드 문구를 만듭니다."),
        ("🔍", "② 매칭", "나이·관심사로 후보를 좁히고 한 명을 고릅니다."),
        ("💌", "③ 인사말", "선택한 상대에게 보낼 첫 멘트 초안을 뽑습니다."),
        ("💬", "④ 대화 도우미", "한마디 추천·예시 코칭·조언 비교·대화 점검으로 연습합니다."),
    ]
    for col, (icon, title, desc) in zip(cols, items):
        with col:
            st.markdown(
                f'<div class="ux-feature-card" role="article">'
                f'<div class="ux-feature-card-icon" aria-hidden="true">{html_module.escape(icon)}</div>'
                f"<div class=\"ux-feature-card-title\">{html_module.escape(title)}</div>"
                f"<p class=\"ux-feature-card-desc\">{html_module.escape(desc)}</p>"
                f"</div>",
                unsafe_allow_html=True,
            )


def render_home_start_cta() -> None:
    """홈 하단 단일 시작 동선."""
    st.markdown('<p class="ux-section-title">바로 시작하기</p>', unsafe_allow_html=True)
    st.markdown(
        '<p class="ux-home-lead-tight">프로필을 먼저 채우면 매칭·인사·대화 단계가 더 자연스럽게 이어집니다.</p>',
        unsafe_allow_html=True,
    )
    st.markdown('<div class="ux-mark-home-start" aria-hidden="true"></div>', unsafe_allow_html=True)
    st.page_link(
        "pages/01_AI_프로필_생성.py",
        label="① 프로필 만들기로 시작",
        use_container_width=True,
        help="AI 프로필 생성 화면으로 이동",
    )


def render_home_navigation() -> None:
    from _match_context import journey_can_access

    st.markdown('<p class="ux-section-title">단계별 안내</p>', unsafe_allow_html=True)
    st.markdown(
        '<p class="ux-section-lead">사이드바 <strong>진행 단계 (①~④)</strong>와 같은 순서입니다. '
        "앞 단계를 완료해야 다음 화면으로 이동할 수 있습니다.</p>",
        unsafe_allow_html=True,
    )
    steps: list[tuple[str, str, str, str, str]] = [
        (
            "①",
            "AI 프로필",
            "pages/01_AI_프로필_생성.py",
            "profile",
            "관심 키워드와 메모를 바탕으로 나만의 프로필 카드를 만듭니다.",
        ),
        (
            "②",
            "프로필 매칭",
            "pages/02_프로필_매칭_검색.py",
            "match",
            "① 성별 기준 **이성** 후보만 보이도록 검색합니다.",
        ),
        (
            "③",
            "인사말",
            "pages/03_인사말_생성.py",
            "greeting",
            "선택한 상대에게 보낼 첫 인사 멘트 초안을 만듭니다.",
        ),
        (
            "④",
            "대화 도우미",
            "pages/04_대화_도우미.py",
            "coach",
            "한마디 추천·예시 코칭·조언 비교·대화 점검으로 연습합니다.",
        ),
    ]
    for badge, title, path, gate, desc in steps:
        st.markdown(
            f'<div class="ux-step-card"><strong>{badge} {title}</strong> — {desc}</div>',
            unsafe_allow_html=True,
        )
        ok, _ = journey_can_access(gate)
        if ok:
            st.page_link(path, label=f"{badge} 이동", use_container_width=True)
        else:
            st.caption(f"{badge} 잠금 · 이전 단계를 먼저 완료하세요")

    st.markdown('<p class="ux-section-title">바로가기</p>', unsafe_allow_html=True)
    st.markdown('<p class="ux-section-lead">자주 쓰는 화면으로 바로 점프합니다. (잠긴 단계는 사이드바에서 안내를 확인하세요.)</p>', unsafe_allow_html=True)
    g1, g2 = st.columns(2)
    quick = [
        ("pages/01_AI_프로필_생성.py", "① AI 프로필", "profile"),
        ("pages/02_프로필_매칭_검색.py", "② 매칭 검색", "match"),
        ("pages/03_인사말_생성.py", "③ 인사말", "greeting"),
        ("pages/04_대화_도우미.py", "④ 대화 도우미", "coach"),
    ]
    with g1:
        for path, label, gate in quick[:2]:
            if journey_can_access(gate)[0]:
                st.page_link(path, label=label, use_container_width=True)
            else:
                st.caption(f"{label} 🔒")
    with g2:
        for path, label, gate in quick[2:]:
            if journey_can_access(gate)[0]:
                st.page_link(path, label=label, use_container_width=True)
            else:
                st.caption(f"{label} 🔒")
