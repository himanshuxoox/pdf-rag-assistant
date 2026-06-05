import os
import streamlit as st
import requests
import time

# API_URL = "http://127.0.0.1:8000"

# To this:
API_URL = os.getenv("BACKEND_API_URL", "http://127.0.0.1:8000")

# Must be the first Streamlit command
st.set_page_config(
    page_title="Claude — Document Assistant",
    page_icon="✦",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==========================================
# CUSTOM CSS — Claude-inspired design system
# ==========================================
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Source+Serif+4:opsz,wght@8..60,400;8..60,500;8..60,600;8..60,700&display=swap');

    /* ---------- Base palette (Claude warm cream) ---------- */
    :root {
        --bg: #faf9f5;
        --bg-elev: #ffffff;
        --sidebar-bg: #f5f3ec;
        --text: #1f1e1d;
        --text-muted: #7a7873;
        --text-faint: #a8a6a0;
        --border: #ebe8de;
        --border-soft: #f0ede4;
        --accent: #c96342;
        --accent-2: #d97757;
        --accent-hover: #b5563a;
        --accent-soft: #f7ece5;
        --user-bubble: #f2efe6;
        --shadow-sm: 0 1px 2px rgba(40, 30, 20, 0.04);
        --shadow-md: 0 4px 16px rgba(40, 30, 20, 0.06);
        --shadow-lg: 0 12px 40px rgba(40, 30, 20, 0.08);
    }

    /* ---------- Global ---------- */
    html, body, [class*="css"], .stApp {
        background-color: var(--bg) !important;
        background-image:
            radial-gradient(ellipse 80% 50% at 50% -10%, rgba(217, 119, 87, 0.06), transparent 60%),
            radial-gradient(ellipse 60% 40% at 100% 100%, rgba(201, 99, 66, 0.04), transparent 60%);
        color: var(--text) !important;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif !important;
        -webkit-font-smoothing: antialiased;
        -moz-osx-font-smoothing: grayscale;
    }

    /* Smooth custom scrollbar */
    ::-webkit-scrollbar { width: 10px; height: 10px; }
    ::-webkit-scrollbar-track { background: transparent; }
    ::-webkit-scrollbar-thumb { background: rgba(0,0,0,0.08); border-radius: 10px; border: 2px solid transparent; background-clip: content-box; }
    ::-webkit-scrollbar-thumb:hover { background: rgba(0,0,0,0.18); background-clip: content-box; }

    /* ---------- Layout ---------- */
    .block-container {
        padding-top: 2.5rem;
        padding-bottom: 8rem;
        max-width: 780px;
    }
    footer {visibility: hidden;}
    #MainMenu {visibility: hidden;}
    header[data-testid="stHeader"] { background: transparent; }

    /* Fade-in animation for everything */
    @keyframes fadeUp {
        from { opacity: 0; transform: translateY(8px); }
        to   { opacity: 1; transform: translateY(0); }
    }
    @keyframes shimmer {
        0%, 100% { opacity: 0.85; transform: scale(1) rotate(0deg); }
        50%      { opacity: 1;    transform: scale(1.08) rotate(180deg); }
    }
    @keyframes pulse {
        0%, 100% { box-shadow: 0 0 0 0 rgba(201, 99, 66, 0.25); }
        50%      { box-shadow: 0 0 0 14px rgba(201, 99, 66, 0); }
    }

    /* ---------- Typography ---------- */
    h1, h2, h3, .stMarkdown h1, .stMarkdown h2, .stMarkdown h3 {
        font-family: 'Source Serif 4', 'Charter', 'Georgia', serif !important;
        font-weight: 500 !important;
        color: var(--text) !important;
        letter-spacing: -0.015em;
    }
    h1 { font-size: 2.6rem !important; }
    h2 { font-size: 1.7rem !important; }
    h3 { font-size: 1.2rem !important; }

    p, .stMarkdown p, label, .stCaption {
        color: var(--text) !important;
    }
    .stCaption, [data-testid="stCaptionContainer"] {
        color: var(--text-muted) !important;
    }

    /* ---------- Sidebar (fixed, non-collapsible, non-resizable) ---------- */
    section[data-testid="stSidebar"] {
        background-color: var(--sidebar-bg) !important;
        border-right: 1px solid var(--border);
        width: 300px !important;
        min-width: 300px !important;
        max-width: 300px !important;
        flex-shrink: 0 !important;
        transform: none !important;
        visibility: visible !important;
    }

    /* Hide the collapse (×) button inside the sidebar header */
    section[data-testid="stSidebar"] button[kind="header"],
    section[data-testid="stSidebar"] [data-testid="stSidebarCollapseButton"],
    section[data-testid="stSidebar"] [data-testid="stBaseButton-headerNoPadding"],
    section[data-testid="stSidebar"] [data-testid="stSidebarHeader"] button {
        display: none !important;
    }

    /* Hide the floating "open sidebar" arrow that appears when collapsed */
    [data-testid="stSidebarCollapsedControl"],
    [data-testid="collapsedControl"] {
        display: none !important;
    }

    /* Disable & hide the right-edge resize handle */
    [data-testid="stSidebarResizeHandle"],
    section[data-testid="stSidebar"] [data-testid*="ResizeHandle"] {
        display: none !important;
        pointer-events: none !important;
    }
    section[data-testid="stSidebar"] > div { padding-top: 1.5rem; }
    section[data-testid="stSidebar"] h1 {
        font-size: 1.4rem !important;
        display: flex; align-items: center; gap: 0.5rem;
    }
    section[data-testid="stSidebar"] h3 {
        font-size: 0.75rem !important;
        font-family: 'Inter', sans-serif !important;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: var(--text-muted) !important;
        font-weight: 600 !important;
        margin-top: 1.5rem !important;
    }

    /* Dividers */
    hr, [data-testid="stDivider"] {
        border-color: var(--border) !important;
        background-color: var(--border) !important;
        opacity: 0.6;
    }

    /* ---------- Buttons ---------- */
    .stButton > button {
        border-radius: 10px;
        font-weight: 500;
        width: 100%;
        border: 1px solid var(--border);
        background: var(--bg-elev);
        color: var(--text);
        padding: 0.55rem 1rem;
        transition: transform 0.12s ease, box-shadow 0.18s ease, border-color 0.18s ease, background 0.18s ease;
        box-shadow: var(--shadow-sm);
    }

    /* Sidebar buttons: shrink to content & center via column wrapper */
    section[data-testid="stSidebar"] .stButton > button,
    section[data-testid="stSidebar"] [data-testid="stBaseButton-primary"],
    section[data-testid="stSidebar"] [data-testid="stBaseButton-secondary"] {
        width: auto !important;
        min-width: 160px !important;
        padding: 0.55rem 1.5rem !important;
        margin: 0 auto !important;
        display: inline-flex !important;
        justify-content: center !important;
    }
    section[data-testid="stSidebar"] .stButton {
        text-align: center !important;
    }
    .stButton > button:hover {
        border-color: var(--text-faint);
        box-shadow: var(--shadow-md);
        transform: translateY(-1px);
    }
    .stButton > button:active { transform: translateY(0); }
    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, var(--accent-2) 0%, var(--accent) 100%);
        color: #fff;
        border-color: transparent;
        box-shadow: 0 4px 14px rgba(201, 99, 66, 0.25);
    }
    .stButton > button[kind="primary"]:hover {
        background: linear-gradient(135deg, var(--accent) 0%, var(--accent-hover) 100%);
        box-shadow: 0 6px 20px rgba(201, 99, 66, 0.35);
        color: #fff;
    }

    /* ---------- Inputs ---------- */
    .stTextInput input, .stTextArea textarea {
        background: var(--bg-elev) !important;
        border: 1px solid var(--border) !important;
        border-radius: 10px !important;
        color: var(--text) !important;
        font-family: 'Inter', sans-serif !important;
        transition: border-color 0.18s, box-shadow 0.18s;
    }
    .stTextInput input:focus, .stTextArea textarea:focus {
        border-color: var(--accent) !important;
        box-shadow:0 0 0 4px var(--accent-soft) !important;
    }

    /* ---------- File uploader (single unified card) ---------- */
    [data-testid="stFileUploader"] section {
        background: var(--bg-elev) !important;
        border: 1px solid var(--border) !important;
        border-radius: 14px !important;
        padding: 1rem !important;
        box-shadow: var(--shadow-sm);
        transition: border-color 0.2s, background 0.2s, box-shadow 0.2s;
    }
    [data-testid="stFileUploader"] section:hover {
        border-color: var(--accent) !important;
        background: #fffaf6 !important;
        box-shadow: var(--shadow-md);
    }

    /* Force the dropzone into a centered column with our header on top */
    [data-testid="stFileUploaderDropzone"] {
        display: flex !important;
        flex-direction: column !important;
        align-items: center !important;
        justify-content: center !important;
        gap: 0.35rem !important;
        background: transparent !important;
        border: none !important;
        padding: 0.25rem !important;
        text-align: center;
    }

    /* Gradient icon block at the top */
    [data-testid="stFileUploaderDropzone"]::before {
        content: "↑";
        display: flex;
        align-items: center;
        justify-content: center;
        width: 40px; height: 40px;
        margin-bottom: 0.35rem;
        border-radius: 11px;
        background: linear-gradient(135deg, var(--accent-2), var(--accent));
        color: #fff;
        font-size: 1.15rem;
        font-weight: 600;
        box-shadow: 0 4px 12px rgba(201, 99, 66, 0.25);
    }

    /* Default Streamlit text styling */
    [data-testid="stFileUploaderDropzone"] [data-testid="stFileUploaderDropzoneInstructions"] {
        display: flex !important;
        flex-direction: column !important;
        align-items: center !important;
        gap: 1px !important;
        color: var(--text) !important;
    }
    [data-testid="stFileUploaderDropzone"] span {
        font-size: 0.92rem !important;
        font-weight: 500 !important;
        color: var(--text) !important;
    }
    [data-testid="stFileUploaderDropzone"] small {
        font-size: 0.76rem !important;
        color: var(--text-muted) !important;
    }

    /* Browse files button */
    [data-testid="stFileUploaderDropzone"] button {
        background: var(--bg-elev) !important;
        color: var(--text) !important;
        border: 1px solid var(--border) !important;
        border-radius: 8px !important;
        padding: 0.35rem 0.85rem !important;
        font-size: 0.8rem !important;
        font-weight: 500 !important;
        margin-top: 0.5rem !important;
        box-shadow: var(--shadow-sm);
        width: auto !important;
    }
    [data-testid="stFileUploaderDropzone"] button:hover {
        border-color: var(--accent) !important;
        color: var(--accent) !important;
    }
    /* ---------- Chat area wrapper — force light bg so messages are never on dark ---------- */
    [data-testid="stVerticalBlock"],
    [data-testid="stMainBlockContainer"],
    .main .block-container {
        background: var(--bg) !important;
    }

    /* ---------- Chat messages ---------- */
    [data-testid="stChatMessage"] {
        background: transparent !important;
        border: none !important;
        padding: 0.85rem 0 !important;
        margin-bottom: 0.25rem;
        animation: fadeUp 0.35s ease;
    }

    /* User bubble — warm cream card */
    [data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]) {
        background: var(--user-bubble) !important;
        border-radius: 18px !important;
        padding: 0.9rem 1.25rem !important;
        margin-bottom: 0.75rem;
        box-shadow: var(--shadow-sm);
    }

    /* ALL text inside any chat message — always dark, always visible */
    [data-testid="stChatMessage"] p,
    [data-testid="stChatMessage"] span,
    [data-testid="stChatMessage"] li,
    [data-testid="stChatMessage"] td,
    [data-testid="stChatMessage"] h1,
    [data-testid="stChatMessage"] h2,
    [data-testid="stChatMessage"] h3,
    [data-testid="stChatMessage"] [data-testid="stMarkdownContainer"],
    [data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] * {
        color: var(--text) !important;
        font-size: 1rem;
        line-height: 1.7;
    }

    /* Avatar styling */
    [data-testid="stChatMessage"] [data-testid^="chatAvatar"] {
        border-radius: 10px;
        background: var(--bg-elev) !important;
        border: 1px solid var(--border);
        box-shadow: var(--shadow-sm);
        color: var(--text) !important;
    }
    [data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-assistant"]) [data-testid^="chatAvatar"] {
        background: linear-gradient(135deg, var(--accent-2) 0%, var(--accent) 100%) !important;
        color: #fff !important;
        border-color: transparent;
    }

    /* ---------- Chat input (sticky / glassy) ---------- */

    /* Bottom container — must be light, not dark */
    [data-testid="stBottomBlockContainer"] {
        background: var(--bg) !important;
        padding-top: 1.5rem !important;
        padding-bottom: 0.5rem !important;
    }

    /* The outer stChatInput wrapper */
    [data-testid="stChatInput"],
    [data-testid="stChatInputContainer"],
    .stChatInputContainer {
        background: #ffffff !important;
        border: 1px solid var(--border) !important;
        border-radius: 18px !important;
        box-shadow: var(--shadow-md) !important;
        padding: 0.3rem !important;
        transition: border-color 0.2s, box-shadow 0.2s, transform 0.2s;
    }
    [data-testid="stChatInput"]:focus-within,
    [data-testid="stChatInputContainer"]:focus-within {
        border-color: var(--accent) !important;
        box-shadow: 0 8px 28px rgba(201, 99, 66, 0.14) !important;
        transform: translateY(-1px);
    }

    /* The actual textarea — explicit white bg + dark text so typing is always visible */
    [data-testid="stChatInput"] textarea,
    [data-testid="stChatInputContainer"] textarea,
    .stChatInputContainer textarea {
        background: #ffffff !important;
        color: #1f1e1d !important;
        caret-color: var(--accent) !important;
        font-size: 1rem !important;
        font-family: 'Inter', sans-serif !important;
        line-height: 1.5 !important;
        border-radius: 14px !important;
        padding: 0.6rem 0.75rem !important;
    }
    [data-testid="stChatInput"] textarea::placeholder,
    [data-testid="stChatInputContainer"] textarea::placeholder {
        color: var(--text-faint) !important;
        opacity: 1 !important;
    }

    /* Send button inside chat input */
    [data-testid="stChatInput"] button,
    [data-testid="stChatInputContainer"] button {
        background: linear-gradient(135deg, var(--accent-2), var(--accent)) !important;
        border-radius: 12px !important;
        color: #fff !important;
        border: none !important;
        box-shadow: 0 2px 8px rgba(201, 99, 66, 0.3) !important;
        transition: opacity 0.15s ease !important;
        width: auto !important;
    }
    [data-testid="stChatInput"] button:hover,
    [data-testid="stChatInputContainer"] button:hover {
        opacity: 0.88 !important;
    }

    /* ---------- Expander ---------- */
    [data-testid="stExpander"] {
        background: var(--bg-elev);
        border: 1px solid var(--border-soft) !important;
        border-radius: 14px !important;
        box-shadow: var(--shadow-sm) !important;
        overflow: hidden;
    }
    /* Expander toggle row */
    [data-testid="stExpander"] summary {
        background: var(--bg-elev) !important;
        color: var(--text) !important;
        font-weight: 600 !important;
        font-size: 0.95rem !important;
        padding: 0.9rem 1.1rem !important;
        letter-spacing: 0.01em;
    }
    /* Only style text nodes, NOT the arrow SVG icon */
    [data-testid="stExpander"] summary span,
    [data-testid="stExpander"] summary p {
        background: transparent !important;
        color: var(--text) !important;
    }
    /* Expander content area */
    [data-testid="stExpander"] > div[data-testid],
    [data-testid="stExpander"] > div {
        background: var(--bg-elev) !important;
        padding: 0.5rem 1rem 1rem !important;
    }
    /* Text inside expander content */
    [data-testid="stExpander"] [data-testid="stMarkdownContainer"] p,
    [data-testid="stExpander"] [data-testid="stMarkdownContainer"] * {
        color: var(--text) !important;
        font-size: 0.95rem !important;
        line-height: 1.7 !important;
    }

    /* ---------- Alerts ---------- */
    [data-testid="stAlert"] {
        background: var(--accent-soft) !important;
        border: 1px solid var(--border) !important;
        border-radius: 14px !important;
        color: var(--text) !important;
        box-shadow: var(--shadow-sm);
    }
    [data-testid="stAlert"] [data-testid="stMarkdownContainer"] p {
        color: var(--text) !important;
    }

    /* ---------- Status widget ---------- */
    [data-testid="stStatusWidget"], [data-testid="stStatus"] {
        background: var(--bg-elev) !important;
        border: 1px solid var(--border) !important;
        border-radius: 14px !important;
        box-shadow: var(--shadow-sm);
        width: 100% !important;
        min-width: 0 !important;
        overflow: hidden !important;
    }
    /* Status label — prevent word-break, single line with ellipsis */
    [data-testid="stStatusWidget"] p,
    [data-testid="stStatusWidget"] span,
    [data-testid="stStatus"] p,
    [data-testid="stStatus"] span,
    [data-testid="stStatus"] > div,
    [data-testid="stStatusWidget"] > div {
        color: var(--text) !important;
        white-space: nowrap !important;
        overflow: hidden !important;
        text-overflow: ellipsis !important;
        font-size: 0.92rem !important;
        max-width: 100% !important;
    }
    /* Status summary toggle row */
    [data-testid="stStatus"] summary,
    [data-testid="stStatusWidget"] summary {
        background: var(--bg-elev) !important;
        color: var(--text) !important;
        white-space: nowrap !important;
        overflow: hidden !important;
        text-overflow: ellipsis !important;
        padding: 0.75rem 1rem !important;
        font-size: 0.92rem !important;
        font-weight: 500 !important;
    }

    /* ---------- Code ---------- */
    /* Inline code */
    code {
        background: #f0ece6 !important;
        color: var(--accent) !important;
        border-radius: 6px;
        padding: 2px 6px;
        font-size: 0.9em;
        font-family: 'JetBrains Mono', 'Fira Code', ui-monospace, monospace !important;
    }

    /* Code & pre blocks (e.g. ASCII diagrams, multi-line code) inside chat */
    [data-testid="stChatMessage"] pre,
    [data-testid="stChatMessage"] .stCode,
    [data-testid="stChatMessage"] [data-testid="stCode"] {
        background: #1e1e2e !important;
        border-radius: 10px !important;
        padding: 1rem !important;
        overflow-x: auto !important;
        border: 1px solid rgba(255,255,255,0.08) !important;
    }
    /* Text INSIDE pre/code blocks should stay white — override the broad * rule */
    [data-testid="stChatMessage"] pre *,
    [data-testid="stChatMessage"] pre code,
    [data-testid="stChatMessage"] .stCode *,
    [data-testid="stChatMessage"] [data-testid="stCode"] * {
        color: #cdd6f4 !important;
        background: transparent !important;
        font-family: 'JetBrains Mono', 'Fira Code', ui-monospace, monospace !important;
        font-size: 0.85rem !important;
        line-height: 1.6 !important;
    }

    /* ===========================================================
       Custom components
       =========================================================== */

    /* Brand mark with gradient + shimmer */
    .brand-mark {
        font-size: 1.4rem;
        background: linear-gradient(135deg, var(--accent-2), var(--accent));
        -webkit-background-clip: text;
        background-clip: text;
        color: transparent;
        display: inline-block;
        animation: shimmer 8s ease-in-out infinite;
    }

    /* Model pill */
    .model-pill {
        display: inline-flex; align-items: center; gap: 0.4rem;
        background: var(--bg-elev);
        border: 1px solid var(--border);
        border-radius: 999px;
        padding: 4px 12px;
        font-size: 0.78rem;
        color: var(--text-muted);
        font-weight: 500;
        box-shadow: var(--shadow-sm);
    }
    .model-pill .dot {
        width: 6px; height: 6px; border-radius: 50%;
        background: #4caf50;
        animation: pulse 2.5s ease-in-out infinite;
    }

    /* Doc header card */
    .doc-header {
        display: flex; align-items: center; justify-content: space-between;
        gap: 1rem;
        margin-bottom: 1.25rem;
        animation: fadeUp 0.4s ease;
    }
    .doc-header .label {
        font-size: 0.78rem;
        color: var(--text-muted);
        text-transform: uppercase;
        letter-spacing: 0.08em;
        font-weight: 600;
    }
    .doc-header h2 {
        margin: 0.15rem 0 0 0 !important;
        font-size: 1.5rem !important;
    }

    /* Empty state hero */
    .claude-hero {
        text-align: center;
        padding-top: 5rem;
        animation: fadeUp 0.5s ease;
    }
    .claude-hero .glyph {
        width: 64px; height: 64px;
        margin: 0 auto 1.5rem;
        border-radius: 18px;
        background: linear-gradient(135deg, var(--accent-2), var(--accent));
        display: flex; align-items: center; justify-content: center;
        color: #fff;
        font-size: 1.8rem;
        box-shadow: 0 10px 30px rgba(201, 99, 66, 0.25);
        animation: shimmer 6s ease-in-out infinite;
    }
    .claude-hero h1 {
        font-family: 'Source Serif 4', 'Charter', 'Georgia', serif;
        font-size: 2.8rem;
        font-weight: 500;
        color: var(--text);
        margin-bottom: 0.5rem;
        letter-spacing: -0.025em;
        line-height: 1.15;
    }
    .claude-hero h1 .grad {
        background: linear-gradient(135deg, var(--accent-2), var(--accent));
        -webkit-background-clip: text;
        background-clip: text;
        color: transparent;
        font-style: italic;
    }
    .claude-hero p {
        color: var(--text-muted);
        font-size: 1.05rem;
        line-height: 1.6;
        max-width: 480px;
        margin: 0 auto 2.5rem auto;
    }

    /* ---------- Sidebar: Claude-style components ---------- */
    .brand-row {
        display: flex;
        align-items: center;
        gap: 0.6rem;
        margin: 0.25rem 0 1.5rem;
    }
    .brand-row .glyph {
        width: 32px; height: 32px;
        display: flex; align-items: center; justify-content: center;
        border-radius: 9px;
        background: linear-gradient(135deg, var(--accent-2), var(--accent));
        color: #fff;
        font-size: 1.05rem;
        box-shadow: 0 4px 12px rgba(201,99,66,0.22);
        flex-shrink: 0;
    }
    .brand-row .name {
        font-family: 'Source Serif 4', serif;
        font-size: 1.25rem;
        font-weight: 500;
        color: var(--text);
        line-height: 1.1;
    }
    .brand-row .sub {
        font-size: 0.72rem;
        color: var(--text-muted);
        margin-top: 1px;
    }

    /* Section eyebrow */
    .side-eyebrow {
        font-size: 0.68rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.1em;
        color: var(--text-muted);
        margin: 1.4rem 0 0.5rem;
        padding-left: 2px;
    }

    /* Recent item card */
    .recent-item {
        display: flex; align-items: center; gap: 0.55rem;
        padding: 0.55rem 0.75rem;
        border-radius: 10px;
        background: var(--bg-elev);
        border: 1px solid var(--border);
        color: var(--text);
        font-size: 0.83rem;
        box-shadow: var(--shadow-sm);
        margin-bottom: 0.3rem;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
        animation: fadeUp 0.3s ease;
    }
    .recent-item.active {
        border-color: var(--accent);
        background: var(--accent-soft);
    }
    .recent-item .dot {
        width: 7px; height: 7px;
        border-radius: 50%;
        background: var(--accent);
        flex-shrink: 0;
        animation: pulse 2.5s ease-in-out infinite;
    }
    .recent-empty {
        font-size: 0.78rem;
        color: var(--text-faint);
        padding: 0.5rem 0.75rem;
        font-style: italic;
    }

    /* User pill (account chip) */
    .user-pill {
        display: flex;
        align-items: center;
        gap: 0.6rem;
        background: var(--bg-elev);
        border: 1px solid var(--border);
        border-radius: 12px;
        padding: 0.55rem 0.7rem;
        margin-top: 2rem;
        box-shadow: var(--shadow-sm);
        transition: all 0.15s ease;
    }
    .user-pill:hover {
        border-color: var(--text-muted);
        box-shadow: var(--shadow-md);
    }
    .user-pill .avatar {
        width: 32px; height: 32px;
        border-radius: 50%;
        background: linear-gradient(135deg, var(--accent-2), var(--accent));
        color: #fff;
        display: flex; align-items: center; justify-content: center;
        font-size: 0.78rem;
        font-weight: 600;
        flex-shrink: 0;
    }
    .user-pill .info { line-height: 1.2; min-width: 0; flex: 1; }
    .user-pill .name {
        font-size: 0.84rem; font-weight: 500; color: var(--text);
        overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
    }
    .user-pill .email {
        font-size: 0.7rem; color: var(--text-muted);
        overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
        margin-top: 1px;
    }

    /* ---------- Footer ---------- */
    .claude-footer {
        position: fixed;
        bottom: 10px;
        left: 50%;
        transform: translateX(-50%);
        display: flex;
        align-items: center;
        gap: 0.6rem;
        padding: 6px 14px;
        background: rgba(255, 255, 255, 0.7);
        backdrop-filter: blur(10px) saturate(140%);
        -webkit-backdrop-filter: blur(10px) saturate(140%);
        border: 1px solid var(--border);
        border-radius: 999px;
        box-shadow: var(--shadow-sm);
        font-size: 0.78rem;
        color: var(--text-muted);
        z-index: 1000;
        animation: fadeUp 0.5s ease;
    }
    .claude-footer .dev {
        color: var(--text);
        font-weight: 500;
    }
    .claude-footer a {
        display: inline-flex;
        align-items: center;
        gap: 4px;
        color: var(--text-muted);
        text-decoration: none;
        transition: color 0.15s ease;
    }
    .claude-footer a:hover { color: var(--accent); }
    .claude-footer .sep {
        width: 4px; height: 4px;
        border-radius: 50%;
        background: var(--border);
    }
    .claude-footer svg { width: 14px; height: 14px; }

    /* Suggestion cards */
    .suggestion-grid {
        display: grid;
        grid-template-columns: repeat(2, 1fr);
        gap: 0.75rem;
        max-width: 580px;
        margin: 0 auto;
    }
    .suggestion-card {
        background: var(--bg-elev);
        border: 1px solid var(--border);
        border-radius: 14px;
        padding: 1rem 1.1rem;
        text-align: left;
        cursor: pointer;
        transition: all 0.2s ease;
        box-shadow: var(--shadow-sm);
    }
    .suggestion-card:hover {
        border-color: var(--accent);
        box-shadow: var(--shadow-md);
        transform: translateY(-2px);
    }
    .suggestion-card .title {
        font-size: 0.92rem;
        font-weight: 500;
        color: var(--text);
        margin-bottom: 0.15rem;
    }
    .suggestion-card .sub {
        font-size: 0.82rem;
        color: var(--text-muted);
    }
</style>
""", unsafe_allow_html=True)
# ==========================================
# SIDEBAR: CONTROLS & UPLOAD
# ==========================================
with st.sidebar:
    # Brand
    st.markdown(
        """
        <div class="brand-row">
            <div class="glyph">✦</div>
            <div>
                <div class="name">Claude</div>
                <div class="sub">Document assistant</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    # New conversation
    # if st.button("＋  New conversation", key="new_conv", use_container_width=True):
    #     for _k in ("current_doc_id", "filename", "summary", "messages"):
    #         st.session_state.pop(_k, None)
    #     st.rerun()

    # ----- Upload section -----
    st.markdown('<div class="side-eyebrow">Upload</div>', unsafe_allow_html=True)
    uploaded_file = st.file_uploader("Choose a PDF file", type="pdf", label_visibility="collapsed")

    _l, _m, _r = st.columns([1, 3, 1])
    with _m:
        _upload_clicked = st.button("Process", type="primary")

    if _upload_clicked and uploaded_file is not None:
        with st.status("Processing document…", expanded=True) as status:
            st.write("Sending to server…")
            files = {"file": (uploaded_file.name, uploaded_file.getvalue(), "application/pdf")}
            response = requests.post(f"{API_URL}/upload", files=files)

            if response.status_code == 200:
                resp_data = response.json()
                doc_id = resp_data["document_id"]
                st.session_state["current_doc_id"] = doc_id
                if resp_data.get("duplicate"):
                    st.info(f"⚡ {resp_data['message']}", icon=None)

                st.write("Analyzing and vectorizing…")
                while True:
                    status_res = requests.get(f"{API_URL}/document/{doc_id}")
                    if status_res.status_code == 200:
                        doc_data = status_res.json()
                        if doc_data["status"] == "completed":
                            st.session_state["summary"] = doc_data["summary"]
                            st.session_state["filename"] = doc_data["filename"]
                            # Clear chat history when new doc is uploaded
                            st.session_state.messages = [] 
                            status.update(label="Ready!", state="complete", expanded=False)
                            break
                        elif "failed" in doc_data["status"]:
                            status.update(label="Error processing", state="error")
                            st.error(doc_data['status'])
                            break
                    time.sleep(1.5)
                time.sleep(1)
                st.rerun()
            else:
                status.update(label="Upload failed", state="error")

    # ----- Recents — fetched live from DB -----
    st.markdown('<div class="side-eyebrow">Recent</div>', unsafe_allow_html=True)
    try:
        _docs_res = requests.get(f"{API_URL}/documents", timeout=3)
        _all_docs = _docs_res.json().get("documents", []) if _docs_res.status_code == 200 else []
    except Exception:
        _all_docs = []

    if _all_docs:
        for _d in _all_docs:
            _is_active = _d["document_id"] == st.session_state.get("current_doc_id")
            _cls = "recent-item active" if _is_active else "recent-item"
            # Clickable label using a button styled to look like a list item
            if st.button(
                f"{'● ' if _is_active else '○ '}{_d['filename']}",
                key=f"recent_{_d['document_id']}",
                use_container_width=True,
            ):
                if not _is_active:
                    load_res = requests.get(f"{API_URL}/load-doc/{_d['document_id']}")
                    if load_res.status_code == 200:
                        data = load_res.json()
                        st.session_state["current_doc_id"] = data["document_id"]
                        st.session_state["filename"] = data["filename"]
                        st.session_state["summary"] = data["summary"]
                        st.session_state["messages"] = []
                        st.rerun()
    else:
        st.markdown('<div class="recent-empty">No documents yet</div>', unsafe_allow_html=True)

    # ----- Search -----
    st.markdown('<div class="side-eyebrow">Search</div>', unsafe_allow_html=True)
    search_query = st.text_input("Find topics across all PDFs:", placeholder="e.g. Revenue growth", label_visibility="collapsed")

    _sl, _sm, _sr = st.columns([1, 3, 1])
    with _sm:
        _search_clicked = st.button("Search")

    # ── When Search is clicked: fetch and STORE results in session_state ──────
    # This is critical — storing in session_state means results persist across
    # reruns (e.g. when the user clicks "Chat with this doc")
    if _search_clicked and search_query:
        with st.spinner("Searching..."):
            res = requests.post(f"{API_URL}/search", json={"query": search_query, "limit": 3})
            if res.status_code == 200:
                st.session_state["search_results"] = res.json().get("results", [])
                st.session_state["search_query_text"] = search_query
            else:
                st.session_state["search_results"] = []
                st.error("Search failed. Is the backend running?")

    # ── Always render whatever results are stored (survives reruns) ───────────
    _results = st.session_state.get("search_results", [])
    if _results:
        st.markdown(
            f'<div style="font-size:0.75rem;color:var(--text-muted);margin:4px 0 8px;">Results for: '
            f'<b>{st.session_state.get("search_query_text","")}</b></div>',
            unsafe_allow_html=True,
        )
        for r in _results:
            doc_id = r["document_id"]
            with st.expander(f"📄 {r['filename']}", expanded=False):
                summary_text = r.get("summary", "No summary available.")
                # Show first 400 chars in sidebar, full summary opens in chat
                preview = summary_text[:400] + ("…" if len(summary_text) > 400 else "")
                st.markdown(preview, unsafe_allow_html=True)

                btn_key = f"chat_btn_{doc_id}"
                if st.button("💬 Chat with this doc", key=btn_key, type="primary", use_container_width=True):
                    # Store intent — handled BELOW the sidebar block to avoid rerun race
                    st.session_state["_pending_load_doc_id"] = doc_id

    # ── Handle pending "load doc" intent (set by button above) ───────────────
    # We handle this OUTSIDE the button callback so session_state is fully
    # committed before st.rerun() is called.
    if st.session_state.get("_pending_load_doc_id"):
        _pending = st.session_state.pop("_pending_load_doc_id")
        load_res = requests.get(f"{API_URL}/load-doc/{_pending}")
        if load_res.status_code == 200:
            data = load_res.json()
            st.session_state["current_doc_id"] = data["document_id"]
            st.session_state["filename"]        = data["filename"]
            st.session_state["summary"]         = data["summary"]
            st.session_state["messages"]        = []
            st.session_state["search_results"]  = []   # clear results after loading
            st.rerun()
        else:
            st.error("Could not load document.")

    # ----- User pill (account chip) -----
    # st.markdown(
    #     """
    #     <div class="user-pill">
    #         <div class="avatar">HS</div>
    #         <div class="info">
    #             <div class="name">Himanshu Singh</div>
    #             <div class="email">himanshu.singh43@infosys.com</div>
    #         </div>
    #     </div>
    #     """,
    #     unsafe_allow_html=True
    # )


# ==========================================
# MAIN SCREEN: CHAT & READING
# ==========================================
if "current_doc_id" in st.session_state:

    filename = st.session_state.get('filename', 'Unknown')
    st.markdown(
        f"""
        <div class="doc-header">
            <div>
                <div class="label">Chatting with</div>
                <h2>{filename}</h2>
            </div>
           <!-- <div class="model-pill"><span class="dot"></span>Claude Sonnet 4.6</div> -->
        </div>
        """,
        unsafe_allow_html=True
    )

    with st.expander("View summary", expanded=False):
        st.markdown(st.session_state.get("summary", "No summary available."))

    st.divider()

    if "messages" not in st.session_state:
        st.session_state.messages = []

    # ── Per-session question rate limit ──────────────────────────────────────
    QUESTION_LIMIT = 10
    if "questions_asked" not in st.session_state:
        st.session_state.questions_asked = 0

    _questions_used = st.session_state.questions_asked
    _questions_left = max(0, QUESTION_LIMIT - _questions_used)

    # Counter bar — shown above chat history
    _bar_color = "#c96342" if _questions_left <= 3 else "#6b9e78"
    _bar_pct   = int((_questions_used / QUESTION_LIMIT) * 100)
    st.markdown(
        f"""
        <div style="display:flex;align-items:center;gap:10px;margin-bottom:0.75rem;">
            <div style="flex:1;height:5px;background:#ebe8de;border-radius:99px;overflow:hidden;">
                <div style="width:{_bar_pct}%;height:100%;background:{_bar_color};
                            border-radius:99px;transition:width 0.4s ease;"></div>
            </div>
            <span style="font-size:0.78rem;color:{_bar_color};font-weight:600;white-space:nowrap;">
                {_questions_left} / 10 questions left
            </span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    for message in st.session_state.messages:
        avatar = "👤" if message["role"] == "user" else "🤖"
        with st.chat_message(message["role"], avatar=avatar):
            st.markdown(message["content"], unsafe_allow_html=True)
            # Re-render citations stored with assistant messages
            if message["role"] == "assistant" and message.get("citations"):
                with st.expander(f"📎 Sources ({len(message['citations'])} chunks used)", expanded=False):
                    for src in message["citations"]:
                        st.markdown(
                            f"""<div style="border-left:3px solid #c96342;
                                padding:0.5rem 0.75rem;margin-bottom:0.6rem;
                                background:#fdf3ef;border-radius:0 8px 8px 0;">
                                <span style="font-size:0.75rem;font-weight:600;
                                    color:#c96342;">[{src['ref']}] {src['chunk']}</span>
                                <p style="font-size:0.82rem;color:#3d3530;
                                    margin:0.25rem 0 0;line-height:1.5;">
                                    {src['preview']}</p>
                            </div>""",
                            unsafe_allow_html=True,
                        )

    # Disable input and show wall when limit is reached
    if _questions_left == 0:
        st.markdown(
            """
            <div style="text-align:center;padding:1.5rem;background:#fdf3ef;
                        border:1px solid #f0d5c8;border-radius:14px;margin-top:1rem;">
                <div style="font-size:1.5rem;margin-bottom:0.5rem;">🔒</div>
                <div style="font-weight:600;color:#c96342;font-size:1rem;">Session limit reached</div>
                <div style="color:#7a7873;font-size:0.88rem;margin-top:0.4rem;">
                    You've used all 10 questions for this session.<br>
                    Refresh the page to start a new session.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        if prompt := st.chat_input(f"Reply to Claude… ({_questions_left} left)"):

            st.session_state.questions_asked += 1
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user", avatar="👤"):
                st.markdown(prompt)

            with st.chat_message("assistant", avatar="🤖"):
                    # Send full history EXCLUDING the current user message
                    history_to_send = st.session_state.messages[:-1][-20:]
                    chat_payload = {
                        "document_id": st.session_state["current_doc_id"],
                        "message": prompt,
                        "history": history_to_send,
                    }

                    CITATION_SENTINEL = "__CITATIONS__:"
                    try:
                        with requests.post(
                            f"{API_URL}/chat",
                            json=chat_payload,
                            stream=True,
                            timeout=60,
                        ) as chat_res:
                            if chat_res.status_code == 200:

                                # ── Custom streaming generator that hides the sentinel ────────
                                # st.write_stream renders EVERYTHING it receives to the screen,
                                # so we must intercept the sentinel BEFORE passing tokens to it.
                                # Strategy: buffer tokens until we see the sentinel, then stop
                                # yielding — the citation JSON never reaches the screen.
                                import json as _json

                                answer_buf = []     # accumulates clean answer tokens
                                citation_buf = []   # accumulates tokens after sentinel
                                sentinel_found = [False]

                                def clean_stream():
                                    """Yields only answer tokens — stops at the sentinel."""
                                    buffer = ""
                                    for raw_token in chat_res.iter_content(
                                        chunk_size=None, decode_unicode=True
                                    ):
                                        if sentinel_found[0]:
                                            # Sentinel already hit — accumulate rest silently
                                            citation_buf.append(raw_token)
                                            continue

                                        buffer += raw_token

                                        if CITATION_SENTINEL in buffer:
                                            # Split: yield only the answer part before sentinel
                                            before, after = buffer.split(CITATION_SENTINEL, 1)
                                            if before:
                                                answer_buf.append(before)
                                                yield before
                                            citation_buf.append(after)
                                            sentinel_found[0] = True
                                        elif len(buffer) > len(CITATION_SENTINEL) * 2:
                                            # Safe to flush — sentinel can't straddle this far back
                                            flush = buffer[:-len(CITATION_SENTINEL)]
                                            answer_buf.append(flush)
                                            yield flush
                                            buffer = buffer[-len(CITATION_SENTINEL):]
                                        # else: keep buffering — sentinel may be mid-arrival

                                    # Flush remaining buffer if no sentinel was found
                                    if buffer and not sentinel_found[0]:
                                        answer_buf.append(buffer)
                                        yield buffer

                                # Stream clean answer tokens to screen
                                st.write_stream(clean_stream())

                                # Assemble final answer and citations
                                ai_response = "".join(answer_buf).strip()
                                citations_raw = "".join(citation_buf).strip()
                                try:
                                    citations = _json.loads(citations_raw) if citations_raw else []
                                except Exception:
                                    citations = []

                                # Store clean answer text (without sentinel) in history
                                st.session_state.messages.append({
                                    "role": "assistant",
                                    "content": ai_response,
                                    "citations": citations,
                                })

                                # ── Render citations as a collapsed expander ──────────────
                                if citations:
                                    with st.expander(f"📎 Sources ({len(citations)} chunks used)", expanded=False):
                                        for src in citations:
                                            st.markdown(
                                                f"""<div style="border-left:3px solid #c96342;
                                                    padding:0.5rem 0.75rem;margin-bottom:0.6rem;
                                                    background:#fdf3ef;border-radius:0 8px 8px 0;">
                                                    <span style="font-size:0.75rem;font-weight:600;
                                                        color:#c96342;">[{src['ref']}] {src['chunk']}</span>
                                                    <p style="font-size:0.82rem;color:#3d3530;
                                                        margin:0.25rem 0 0;line-height:1.5;">
                                                        {src['preview']}</p>
                                                </div>""",
                                                unsafe_allow_html=True,
                                            )

                                # Auto-scroll after streaming completes
                                st.markdown(
                                    """<script>
                                    (function() {
                                        setTimeout(function() {
                                            var mainEl = window.parent.document.querySelector(
                                                '[data-testid="stAppScrollToBottomContainer"]'
                                                ) || window.parent.document.querySelector('section.main');
                                            if (mainEl) mainEl.scrollTop = mainEl.scrollHeight;
                                            window.parent.scrollTo(0, window.parent.document.body.scrollHeight);
                                        }, 120);
                                    })();
                                    </script>""",
                                    unsafe_allow_html=True,
                                )
                            else:
                                st.error(f"Backend error {chat_res.status_code}. Is the server running?")
                    except requests.exceptions.Timeout:
                        st.error("Request timed out. The document may be too large — try a shorter question.")
                    except requests.exceptions.ConnectionError:
                        st.error("Could not reach the backend. Is it running on port 8000?")

else:
    st.markdown(
        """
        <div class="claude-hero">
            <div class="glyph">✦</div>
            <h1>Good to see you <span class="grad">again</span>.</h1>
            <p>Upload a PDF from the sidebar — I'll read it, summarize it, and answer questions about it.</p>
            <div class="suggestion-grid">
                <div class="suggestion-card">
                    <div class="title">Summarize a report</div>
                    <div class="sub">Pull out the key findings in seconds</div>
                </div>
                <div class="suggestion-card">
                    <div class="title">Answer questions</div>
                    <div class="sub">Ask anything about the document</div>
                </div>
                <div class="suggestion-card">
                    <div class="title">Find a topic</div>
                    <div class="sub">Search across every PDF you've uploaded</div>
                </div>
                <div class="suggestion-card">
                    <div class="title">Extract insights</div>
                    <div class="sub">Surface numbers, names, and decisions</div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )


# ==========================================
# FOOTER — injected as position:fixed so it never lands inside the chat bar
# ==========================================
DEVELOPER_NAME = "Himanshu Singh"
GITHUB_URL = "https://github.com/himanshuxoox"
BUSINESS_EMAIL = "himanshu.singh43@infosys.com"

st.markdown(
    f"""
    <style>
        /* Fixed footer sits below everything, never overlaps the chat input */
        .claude-footer-fixed {{
            position: fixed;
            bottom: 0;
            left: 0;
            width: 100%;
            z-index: 999;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 1rem;
            padding: 6px 1rem;
            background: rgba(248, 244, 238, 0.92);
            backdrop-filter: blur(10px);
            border-top: 1px solid rgba(201,99,66,0.12);
            font-size: 0.78rem;
            color: #6b6460;
            font-family: 'Inter', sans-serif;
        }}
        /* Push main content up so footer never covers the chat input */
        [data-testid="stBottomBlockContainer"] {{
            padding-bottom: 2.5rem !important;
        }}
        .claude-footer-fixed .dev {{ font-weight: 600; color: #3d3530; }}
        .claude-footer-fixed a {{
            display: inline-flex; align-items: center; gap: 4px;
            color: #6b6460; text-decoration: none;
            transition: color 0.2s;
        }}
        .claude-footer-fixed a:hover {{ color: #c96342; }}
        .claude-footer-fixed .sep {{
            width: 4px; height: 4px; border-radius: 50%;
            background: #c9b8ac; display: inline-block;
        }}
        .claude-footer-fixed svg {{ width: 13px; height: 13px; }}
    </style>
    <div class="claude-footer-fixed">
        <span>Built by <span class="dev">{DEVELOPER_NAME}</span></span>
        <span class="sep"></span>
        <a href="{GITHUB_URL}" target="_blank" rel="noopener noreferrer">
            <svg viewBox="0 0 24 24" fill="currentColor">
                <path d="M12 .5C5.65.5.5 5.65.5 12c0 5.08 3.29 9.39 7.86 10.91.58.11.79-.25.79-.56 0-.28-.01-1.02-.02-2-3.2.7-3.87-1.54-3.87-1.54-.52-1.33-1.28-1.68-1.28-1.68-1.05-.72.08-.7.08-.7 1.16.08 1.77 1.19 1.77 1.19 1.03 1.76 2.7 1.25 3.36.96.1-.75.4-1.25.73-1.54-2.55-.29-5.24-1.28-5.24-5.71 0-1.26.45-2.29 1.19-3.1-.12-.29-.52-1.47.11-3.06 0 0 .97-.31 3.18 1.18a11.06 11.06 0 0 1 5.79 0c2.21-1.49 3.18-1.18 3.18-1.18.63 1.59.23 2.77.11 3.06.74.81 1.19 1.84 1.19 3.1 0 4.44-2.69 5.42-5.26 5.7.41.36.78 1.06.78 2.14 0 1.55-.01 2.8-.01 3.18 0 .31.21.68.8.56C20.21 21.39 23.5 17.08 23.5 12 23.5 5.65 18.35.5 12 .5Z"/>
            </svg>
            GitHub
        </a>
        <span class="sep"></span>
        <a href="mailto:{BUSINESS_EMAIL}?subject=Business%20inquiry">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"/>
                <polyline points="22,6 12,13 2,6"/>
            </svg>
            Email
        </a>
    </div>
    """,
    unsafe_allow_html=True
)