# ───────────────────────────────────────────
# CSS
# ───────────────────────────────────────────
CUSTOM_CSS = """
<style>
@import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.css');

:root {
    --bg:       #ffffff;
    --bg-side:  #faf8f9;
    --bg-input: #f5f0f2;
    --primary:  #3a051f;
    --primary-h:#5c0a30;
    --text2:    #9d828f;
    --border:   #e0d0d6;
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
    border-right: 1px solid var(--border) !important;
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
    border: 1px solid var(--border) !important;
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

/* ── 사이드바 버튼 ── */
[data-testid="stSidebar"] .stButton > button {
    background: transparent !important;
    border: 1px solid transparent !important;
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

/* ── 대화 목록 아이템 버튼 (연한 색) ── */
[data-testid="stSidebar"] [data-testid="stHorizontalBlock"] > div:first-child .stButton > button {
    color: var(--text2) !important;
    font-size: 0.83rem !important;
}
[data-testid="stSidebar"] [data-testid="stHorizontalBlock"] > div:first-child .stButton > button:hover {
    color: var(--primary) !important;
}

/* ── 삭제(×) 버튼 중앙 정렬 ── */
[data-testid="stSidebar"] [data-testid="stHorizontalBlock"] > div:last-child .stButton > button {
    justify-content: center !important;
    text-align: center !important;
    padding: 0.45rem 0 !important;
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
    border: 1px solid var(--border) !important;
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
    border: 1px solid var(--border) !important;
    border-radius: var(--radius) !important;
    color: var(--primary) !important;
    font-family: 'Pretendard', sans-serif !important;
}

/* ── 라디오 위젯 레이블 (예: "모델") ── */
.stRadio > label,
.stRadio > label p {
    color: var(--text2) !important;
    font-size: 0.875rem !important;
    font-weight: 600 !important;
    font-family: 'Pretendard', sans-serif !important;
    letter-spacing: 0 !important;
    text-transform: none !important;
}
/* ── 라디오 옵션 레이블 (Flash / Pro) ── */
.stRadio label span {
    color: var(--primary) !important;
    font-family: 'Pretendard', sans-serif !important;
    font-size: 0.875rem !important;
}
/* ── 라디오 버튼 선택 색상 ── */
.stRadio input[type="radio"] {
    accent-color: var(--primary) !important;
}

/* ── 채팅 메시지 ── */
[data-testid="stChatMessage"] {
    background: var(--bg-input) !important;
    border: 1px solid var(--border) !important;
    border-radius: 10px !important;
    margin: 0.25rem 0 !important;
    padding: 0.75rem 1rem !important;
}

/* ── 채팅 입력창 ── */
[data-testid="stChatInput"] {
    background: var(--bg) !important;
    border-top: 1px solid var(--border) !important;
}
[data-testid="stChatInput"] textarea {
    background: var(--bg-input) !important;
    border: 1px solid var(--border) !important;
    color: var(--primary) !important;
    border-radius: var(--radius) !important;
    font-family: 'Pretendard', sans-serif !important;
    font-size: 0.9rem !important;
}
[data-testid="stChatInput"] textarea:focus {
    border-color: var(--primary) !important;
    box-shadow: 0 0 0 2px rgba(58,5,31,0.1) !important;
    outline: none !important;
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

/* ── 사이드바 사용자 이름 ── */
.sidebar-username {
    font-size: 0.95rem;
    font-weight: 600;
    color: var(--primary);
    letter-spacing: -0.02em;
    padding: 0.2rem 0 0.6rem;
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