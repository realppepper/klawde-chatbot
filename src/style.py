# ───────────────────────────────────────────
# CSS
# ───────────────────────────────────────────
CUSTOM_CSS = """
<style>
@import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.css');

:root {
    --bg:       #fefcfd;
    --bg-side:  #f7f3f5;
    --bg-input: #f0e8ec;
    --bg-msg-user: #f0e8ec;
    --bg-msg-bot:  #fefcfd;
    --primary:  #3a051f;
    --primary-h:#5c0a30;
    --text2:    #b08090;
    --border:   #ddd0d5;
    --radius:   8px;
}

html, body, .stApp {
    font-family: 'Pretendard', -apple-system, BlinkMacSystemFont, sans-serif !important;
    background: var(--bg) !important;
    color: var(--primary) !important;
}

[data-testid="stDecoration"] { display: none !important; }
[data-testid="stToolbar"]   { visibility: hidden !important; }
#MainMenu { visibility: hidden; }
footer    { visibility: hidden; }

/* 사이드바 항상 열린 상태 고정 */
section[data-testid="stSidebar"] {
    transform: none !important;
    -webkit-transform: none !important;
    min-width: 244px !important;
    width: 244px !important;
    display: flex !important;
    visibility: visible !important;
}
[data-testid="collapsedControl"] { display: none !important; }

/* ── 로딩 스피너 ── */
.kl-spinner-wrap {
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    height: 220px;
    gap: 1rem;
}
.kl-spinner {
    width: 38px;
    height: 38px;
    border: 3px solid var(--border);
    border-top-color: var(--primary);
    border-radius: 50%;
    animation: kl-spin 0.75s linear infinite;
}
.kl-spinner-label {
    font-size: 0.83rem;
    color: var(--text2);
    font-family: 'Pretendard', sans-serif;
    letter-spacing: 0.02em;
}
@keyframes kl-spin { to { transform: rotate(360deg); } }

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background: var(--bg-side) !important;
    border-right: 0.5px solid var(--border) !important;
}

/* ── 모든 버튼 기본 ── */
.stButton > button,
button[kind="secondary"],
button[kind="primary"] {
    font-family: 'Pretendard', sans-serif !important;
    font-size: 0.875rem !important;
    font-weight: 500 !important;
    border-radius: var(--radius) !important;
    transition: all 0.15s ease !important;
    letter-spacing: -0.01em !important;
    cursor: pointer !important;
    background: transparent !important;
    background-color: transparent !important;
    border: 0.5px solid var(--border) !important;
    color: var(--primary) !important;
}
.stButton > button:hover,
button[kind="secondary"]:hover,
button[kind="primary"]:hover {
    background: var(--primary) !important;
    background-color: var(--primary) !important;
    border-color: var(--primary) !important;
    color: #ffffff !important;
}

/* ── 사이드바 버튼 기본 ── */
[data-testid="stSidebar"] .stButton > button {
    background: transparent !important;
    border: 0.5px solid transparent !important;
    color: var(--primary) !important;
    text-align: left !important;
    justify-content: flex-start !important;
    padding: 0.45rem 0.65rem !important;
    width: 100% !important;
    font-size: 0.84rem !important;
}
[data-testid="stSidebar"] .stButton > button:hover {
    background: rgba(58,5,31,0.06) !important;
    border-color: var(--border) !important;
    color: var(--primary) !important;
}

/* ── 새 대화 버튼 (primary filled) ── */
[data-testid="stSidebar"] [data-testid="baseButton-primary"] {
    background: var(--primary) !important;
    background-color: var(--primary) !important;
    border: 0.5px solid var(--primary) !important;
    color: #ffffff !important;
    justify-content: center !important;
}
[data-testid="stSidebar"] [data-testid="baseButton-primary"]:hover {
    background: var(--primary-h) !important;
    background-color: var(--primary-h) !important;
    border-color: var(--primary-h) !important;
    color: #ffffff !important;
}

/* ── 활성 대화 연두 포인트 ── */
.conv-active .stButton > button {
    color: #6a9e5e !important;
    font-weight: 600 !important;
}
.conv-active .stButton > button:hover {
    color: #ffffff !important;
}

/* ── 대화 목록 아이템 버튼 (연한 색) ── */
[data-testid="stSidebar"] [data-testid="stHorizontalBlock"] > div:first-child .stButton > button {
    color: var(--text2) !important;
    font-size: 0.83rem !important;
}
[data-testid="stSidebar"] [data-testid="stHorizontalBlock"] > div:first-child .stButton > button:hover {
    color: var(--primary) !important;
}


/* ── 삭제(×) 버튼 ── */
[data-testid="stSidebar"] [data-testid="stHorizontalBlock"] > div:last-child .stButton > button {
    justify-content: center !important;
    text-align: center !important;
    padding: 0.45rem 0 !important;
    background: transparent !important;
    border: 0.5px solid transparent !important;
    color: var(--text2) !important;
}
[data-testid="stSidebar"] [data-testid="stHorizontalBlock"] > div:last-child .stButton > button:hover {
    color: var(--primary) !important;
    background: transparent !important;
}

/* ── 로그아웃 텍스트 링크 스타일 ── */
.logout-wrap .stButton > button {
    background: transparent !important;
    border: none !important;
    color: var(--text2) !important;
    font-size: 0.78rem !important;
    padding: 0.2rem 0.4rem !important;
    justify-content: flex-start !important;
}
.logout-wrap .stButton > button:hover {
    background: transparent !important;
    color: var(--primary) !important;
    text-decoration: underline !important;
}

/* ── 입력창 컨테이너 ── */
[data-testid="stTextInput"] > div,
[data-testid="stTextInput"] > div > div {
    background: var(--bg-input) !important;
    background-color: var(--bg-input) !important;
}

/* 비밀번호 눈 아이콘 버튼 */
[data-testid="stTextInput"] button,
[data-testid="stTextInput"] button:hover {
    background: transparent !important;
    background-color: transparent !important;
    border: none !important;
    color: var(--text2) !important;
    box-shadow: none !important;
}

/* ── 입력창 ── */
[data-testid="stTextInput"] input,
[data-testid="stNumberInput"] input {
    background: var(--bg-input) !important;
    border: 0.5px solid var(--border) !important;
    color: var(--primary) !important;
    border-radius: var(--radius) !important;
    font-family: 'Pretendard', sans-serif !important;
    font-size: 0.9rem !important;
}
[data-testid="stTextInput"] input:focus,
[data-testid="stNumberInput"] input:focus {
    border-color: var(--primary) !important;
    box-shadow: 0 0 0 2px rgba(58,5,31,0.1) !important;
    outline: none !important;
}
[data-testid="stTextInput"] label,
[data-testid="stNumberInput"] label,
[data-testid="stSelectbox"] label {
    color: var(--text2) !important;
    font-size: 0.76rem !important;
    font-weight: 600 !important;
    letter-spacing: 0.05em !important;
    text-transform: uppercase !important;
    font-family: 'Pretendard', sans-serif !important;
}

/* ── 셀렉트박스 ── */
[data-testid="stSelectbox"] > div > div {
    background: var(--bg-input) !important;
    border: 0.5px solid var(--border) !important;
    border-radius: var(--radius) !important;
    color: var(--primary) !important;
    font-family: 'Pretendard', sans-serif !important;
}

/* ── 빈 화면 상태 ── */
.empty-state {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 5rem 1rem 2rem;
    text-align: center;
}
.empty-state-logo {
    font-size: 3rem;
    font-weight: 700;
    letter-spacing: -0.05em;
    color: var(--primary);
    font-family: 'Pretendard', sans-serif;
}
.empty-state-sub {
    font-size: 1rem;
    color: var(--text2);
    margin-top: 0.75rem;
    font-family: 'Pretendard', sans-serif;
}
.empty-state-chips {
    display: flex;
    gap: 8px;
    margin-top: 1.5rem;
    flex-wrap: wrap;
    justify-content: center;
}
.empty-state-chip {
    background: var(--bg-input);
    border: 0.5px solid var(--border);
    border-radius: 999px;
    padding: 6px 14px;
    font-size: 0.8rem;
    color: var(--primary);
    font-family: 'Pretendard', sans-serif;
    cursor: default;
}


/* ── 발신자 레이블 ── */
.msg-label {
    font-size: 0.72rem;
    font-weight: 600;
    color: var(--text2);
    letter-spacing: 0.04em;
    font-family: 'Pretendard', sans-serif;
    margin: 0.6rem 0 0.2rem 0.25rem;
}
.msg-label-right {
    text-align: right;
    margin: 0.6rem 0.25rem 0.2rem 0;
}

/* ── 사용자 메시지 (오른쪽 정렬) ── */
.user-msg {
    background: #ecdde3;
    border: none;
    border-radius: 20px;
    padding: 0.875rem 1.25rem;
    margin: 0.3rem 0;
    text-align: right;
    color: var(--primary);
    font-family: 'Pretendard', sans-serif;
    font-size: 1rem;
    line-height: 1.75;
}

/* ── 어시스턴트 메시지 ── */
[data-testid="stChatMessage"] {
    background: #f7f3f5 !important;
    border: none !important;
    border-radius: 20px !important;
    margin: 0.3rem 0 !important;
    padding: 0.875rem 1.25rem !important;
    font-size: 1rem !important;
}
[data-testid="stChatMessage"] img,
[data-testid="stChatMessage"] [data-testid*="Avatar"],
[data-testid="stChatMessage"] > div:first-child {
    display: none !important;
}

/* ── 채팅 입력창 ── */
[data-testid="stChatInput"] {
    background: var(--bg) !important;
    border-top: none !important;
    padding: 0.75rem 1rem !important;
}
[data-testid="stChatInput"] > div {
    background: var(--bg-side) !important;
    border: 0.5px solid var(--border) !important;
    border-radius: 16px !important;
    padding: 14px 8px 14px 16px !important;
    min-height: 64px !important;
    align-items: center !important;
}
[data-testid="stChatInput"] textarea {
    background: transparent !important;
    border: none !important;
    color: var(--primary) !important;
    border-radius: 0 !important;
    font-family: 'Pretendard', sans-serif !important;
    font-size: 0.9rem !important;
    box-shadow: none !important;
}
[data-testid="stChatInput"] textarea:focus {
    border: none !important;
    box-shadow: none !important;
    outline: none !important;
}
[data-testid="stChatInput"] button {
    background: var(--primary) !important;
    background-color: var(--primary) !important;
    border: none !important;
    border-radius: 50% !important;
    color: #ffffff !important;
    width: 34px !important;
    height: 34px !important;
}
[data-testid="stChatInput"] button:hover {
    background: var(--primary-h) !important;
    background-color: var(--primary-h) !important;
    color: #ffffff !important;
}

/* ── 구분선 ── */
hr {
    border-color: var(--border) !important;
    margin: 0.6rem 0 !important;
}

/* ── 보조 텍스트 ── */
[data-testid="stCaptionContainer"] p,
.stCaption {
    color: var(--text2) !important;
    font-size: 0.78rem !important;
    font-family: 'Pretendard', sans-serif !important;
}

/* ── 알림 ── */
[data-testid="stAlert"] {
    border-radius: var(--radius) !important;
    font-size: 0.875rem !important;
    font-family: 'Pretendard', sans-serif !important;
}

/* ── 스크롤바 ── */
::-webkit-scrollbar { width: 4px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: var(--border); border-radius: 2px; }
::-webkit-scrollbar-thumb:hover { background: var(--text2); }

/* ── 메인 컨테이너 ── */
.main .block-container {
    padding-top: 1.5rem !important;
    max-width: 900px !important;
}

/* ── 로그인 ── */
.login-header {
    text-align: center;
    padding: 3.5rem 0 2rem;
}
.login-logo {
    font-size: 2.4rem;
    font-weight: 700;
    letter-spacing: -0.05em;
    color: var(--primary);
    font-family: 'Pretendard', sans-serif;
}
.login-tagline {
    font-size: 0.83rem;
    color: var(--text2);
    margin-top: 0.45rem;
    letter-spacing: 0.02em;
    font-family: 'Pretendard', sans-serif;
}
.form-section-title {
    font-size: 1.05rem;
    font-weight: 600;
    color: var(--primary);
    margin-bottom: 1.25rem;
    letter-spacing: -0.02em;
    font-family: 'Pretendard', sans-serif;
}

/* ── 사이드바 사용자 이름 + 서브텍스트 ── */
.sidebar-username {
    font-size: 0.95rem;
    font-weight: 600;
    color: var(--primary);
    letter-spacing: -0.02em;
    padding: 0.2rem 0 0.1rem;
    font-family: 'Pretendard', sans-serif;
}
.sidebar-subtext {
    font-size: 0.72rem;
    color: #7a9e6e;
    letter-spacing: 0.04em;
    text-transform: uppercase;
    padding: 0 0 0.5rem;
    font-family: 'Pretendard', sans-serif;
}

/* ── 대화 목록 아이템 ── */
.conv-row {
    display: flex;
    align-items: center;
    gap: 4px;
    margin-bottom: 2px;
}
</style>
"""