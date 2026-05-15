import streamlit as st
import sqlite3
import hashlib
import tomllib
import os
import shutil
import time
import threading
import uuid
from datetime import datetime

import json
import tempfile

def _job_path(job_id: str) -> str:
    return os.path.join(tempfile.gettempdir(), f"klawde_{job_id}.json")

# ───────────────────────────────────────────
# 설정
# ───────────────────────────────────────────
with open(".streamlit/api.toml", "rb") as f:
    _secrets = tomllib.load(f)
API_KEY = _secrets["GEMINI_API_KEY"]
VOYAGE_API_KEY = _secrets["VOYAGE_API_KEY"]
DB_PATH = "chatbot.db"
CHROMA_DIR = "./chroma_db_html"
HTML_BASE = "./html_data"

# LangChain / ChromaDB (선택적 임포트)
try:
    from langchain_voyageai import VoyageAIEmbeddings
    from langchain_text_splitters import RecursiveCharacterTextSplitter
    from langchain_chroma import Chroma
    from langchain_community.document_loaders import BSHTMLLoader
    from langchain_core.prompts import ChatPromptTemplate
    from langchain_core.output_parsers import StrOutputParser
    LANGCHAIN_OK = True
except ImportError:
    LANGCHAIN_OK = False

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

# ───────────────────────────────────────────
# DB 초기화
# ───────────────────────────────────────────
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            name TEXT,
            department TEXT,
            gender TEXT,
            age INTEGER
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            title TEXT,
            created_at TEXT,
            conv_type TEXT DEFAULT 'rag'
        )
    """)
    try:
        c.execute("ALTER TABLE conversations ADD COLUMN conv_type TEXT DEFAULT 'rag'")
    except Exception:
        pass
    c.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id INTEGER,
            role TEXT,
            content TEXT,
            created_at TEXT
        )
    """)
    # 기존 일반 채팅 기록 삭제
    c.execute("""DELETE FROM messages WHERE conversation_id IN
                 (SELECT id FROM conversations WHERE conv_type='chat')""")
    c.execute("DELETE FROM conversations WHERE conv_type='chat'")
    conn.commit()
    conn.close()

# ───────────────────────────────────────────
# 유틸 함수
# ───────────────────────────────────────────
def hash_password(pw):
    return hashlib.sha256(pw.encode()).hexdigest()

def get_conn():
    return sqlite3.connect(DB_PATH)

def register_user(username, password, name, department, gender, age):
    try:
        conn = get_conn()
        conn.execute(
            "INSERT INTO users (username, password, name, department, gender, age) VALUES (?,?,?,?,?,?)",
            (username, hash_password(password), name, department, gender, age)
        )
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        conn.close()
        return False

def login_user(username, password):
    conn = get_conn()
    c = conn.execute("SELECT * FROM users WHERE username=? AND password=?",
                     (username, hash_password(password)))
    row = c.fetchone()
    conn.close()
    return row

def get_conversations(user_id):
    conn = get_conn()
    c = conn.cursor()
    c.execute("""SELECT id, title, created_at FROM conversations
                 WHERE user_id=? AND conv_type='rag'
                 ORDER BY created_at DESC""", (user_id,))
    rows = c.fetchall()
    conn.close()
    return rows

def create_conversation(user_id, title):
    conn = get_conn()
    c = conn.cursor()
    c.execute("INSERT INTO conversations (user_id, title, created_at, conv_type) VALUES (?,?,?,?)",
              (user_id, title, datetime.now().strftime("%Y-%m-%d %H:%M"), "rag"))
    conv_id = c.lastrowid
    conn.commit()
    conn.close()
    return conv_id

def get_messages(conv_id):
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT role, content FROM messages WHERE conversation_id=? ORDER BY id", (conv_id,))
    rows = c.fetchall()
    conn.close()
    return [{"role": r[0], "content": r[1]} for r in rows]

def save_message(conv_id, role, content):
    conn = get_conn()
    c = conn.cursor()
    c.execute("INSERT INTO messages (conversation_id, role, content, created_at) VALUES (?,?,?,?)",
              (conv_id, role, content, datetime.now().strftime("%Y-%m-%d %H:%M")))
    conn.commit()
    conn.close()

def delete_conversation(conv_id):
    conn = get_conn()
    c = conn.cursor()
    c.execute("DELETE FROM messages WHERE conversation_id=?", (conv_id,))
    c.execute("DELETE FROM conversations WHERE id=?", (conv_id,))
    conn.commit()
    conn.close()

def delete_all_conversations(user_id):
    conn = get_conn()
    c = conn.cursor()
    c.execute("""DELETE FROM messages WHERE conversation_id IN
                 (SELECT id FROM conversations WHERE user_id=? AND conv_type='rag')""", (user_id,))
    c.execute("DELETE FROM conversations WHERE user_id=? AND conv_type='rag'", (user_id,))
    conn.commit()
    conn.close()

def update_user_info(user_id, name, department, gender, age):
    conn = get_conn()
    conn.execute(
        "UPDATE users SET name=?, department=?, gender=?, age=? WHERE id=?",
        (name, department, gender, age, user_id)
    )
    conn.commit()
    conn.close()

def update_password(user_id, new_password):
    conn = get_conn()
    conn.execute(
        "UPDATE users SET password=? WHERE id=?",
        (hash_password(new_password), user_id)
    )
    conn.commit()
    conn.close()

# ───────────────────────────────────────────
# html_data 폴더 목록
# ───────────────────────────────────────────
def get_html_folders():
    if not os.path.exists(HTML_BASE):
        return []
    return sorted(
        [f for f in os.listdir(HTML_BASE) if os.path.isdir(os.path.join(HTML_BASE, f))],
        reverse=True
    )

# ───────────────────────────────────────────
# RAG 함수
# ───────────────────────────────────────────
@st.cache_resource(show_spinner=False)
def load_vector_db(folder_path: str, rebuild: bool = False):
    embeddings = VoyageAIEmbeddings(
        voyage_api_key=VOYAGE_API_KEY,
        model="voyage-3-lite"
    )

    if not rebuild and os.path.exists(CHROMA_DIR) and os.listdir(CHROMA_DIR):
        try:
            return Chroma(persist_directory=CHROMA_DIR, embedding_function=embeddings), None
        except Exception as e:
            return None, str(e)

    if not folder_path or not os.path.exists(folder_path):
        return None, "HTML 폴더 경로를 확인해 주세요."

    files = [f for f in os.listdir(folder_path) if f.endswith(".html")]
    if not files:
        return None, "폴더에 HTML 파일이 없습니다."

    splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
    all_chunks = []
    for fn in files:
        try:
            loader = BSHTMLLoader(
                os.path.join(folder_path, fn),
                open_encoding="utf-8",
                bs_kwargs={"features": "html.parser"}
            )
            all_chunks.extend(splitter.split_documents(loader.load()))
        except Exception:
            pass

    if not all_chunks:
        return None, "청크 생성에 실패했습니다."

    db = None
    batch_size = 30
    for i in range(0, len(all_chunks), batch_size):
        batch = all_chunks[i: i + batch_size]
        if db is None:
            db = Chroma.from_documents(batch, embeddings, persist_directory=CHROMA_DIR)
        else:
            db.add_documents(batch)
    return db, None

def _rag_worker(job_id: str, question: str, model_name: str):
    """백그라운드 스레드 — SDK 우회, 순수 requests + chromadb 직접 사용"""
    import requests
    import chromadb
    import voyageai

    GEMINI_BASE = "https://generativelanguage.googleapis.com/v1beta/models"
    HEADERS = {"x-goog-api-key": API_KEY, "Content-Type": "application/json"}

    try:
        # 1. 임베딩 (Voyage API)
        vo = voyageai.Client(api_key=VOYAGE_API_KEY)
        query_vec = vo.embed([question], model="voyage-3-lite", input_type="query").embeddings[0]

        # 2. ChromaDB 검색 (새 연결 — 스레드 안전)
        chroma = chromadb.PersistentClient(path=CHROMA_DIR)
        col = chroma.get_collection("langchain")
        results = col.query(
            query_embeddings=[query_vec],
            n_results=5,
            include=["documents", "metadatas", "distances"]
        )
        docs_texts = results["documents"][0]
        metadatas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0]
        context = "\n\n".join(docs_texts)

        # 3. 답변 생성 (REST API 직접 호출)
        full_prompt = (
            "다음 문서 내용을 참고해서 질문에 답하세요.\n\n"
            f"문서:\n{context}\n\n질문: {question}"
        )
        r2 = requests.post(
            f"{GEMINI_BASE}/{model_name}:generateContent",
            headers=HEADERS,
            json={
                "contents": [{"role": "user", "parts": [{"text": full_prompt}]}],
                "generationConfig": {"temperature": 0.3}
            },
            timeout=120
        )
        r2.raise_for_status()
        answer = r2.json()["candidates"][0]["content"]["parts"][0]["text"]

        # 거리 기준 0.5 이하인 문서만 참고 문서로 표시
        seen = set()
        sources = []
        for m, d in zip(metadatas, distances):
            if m and m.get("source") and d < 0.5:
                name = os.path.basename(m["source"])
                if name not in seen:
                    seen.add(name)
                    sources.append(name)
        if sources:
            answer += "\n\n📎 **참고 문서**\n" + "\n".join(f"- {s}" for s in sources)

        with open(_job_path(job_id), "w", encoding="utf-8") as f:
            json.dump({"done": True, "result": answer}, f, ensure_ascii=False)
    except Exception as e:
        with open(_job_path(job_id), "w", encoding="utf-8") as f:
            json.dump({"done": True, "error": str(e)}, f, ensure_ascii=False)

# ───────────────────────────────────────────
# 페이지 설정
# ───────────────────────────────────────────
st.set_page_config(page_title="KlaWde", layout="wide", initial_sidebar_state="expanded")
init_db()
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# ───────────────────────────────────────────
# 세션 초기화
# ───────────────────────────────────────────
for key, val in {
    "logged_in": False,
    "user": None,
    "current_rag_conv_id": None,
    "show_register": False,
    "model_type": "Flash",
    "vector_db": None,
    "rag_ready": False,
    "rag_error": None,
    "rag_messages": [],
    "rag_job_id": None,
    "rag_processing": False,
}.items():
    if key not in st.session_state:
        st.session_state[key] = val

# ChromaDB 자동 로드 (앱 시작 시 1회)
if LANGCHAIN_OK and not st.session_state.rag_ready and st.session_state.vector_db is None:
    _loading_slot = st.empty()
    _loading_slot.markdown(
        '<div class="kl-spinner-wrap">'
        '<div class="kl-spinner"></div>'
        '<span class="kl-spinner-label">데이터베이스 로드 중...</span>'
        '</div>',
        unsafe_allow_html=True
    )
    try:
        db, err = load_vector_db("")
        if err:
            st.session_state.rag_error = err
        else:
            st.session_state.vector_db = db
            st.session_state.rag_ready = True
    except Exception as e:
        st.session_state.rag_error = str(e)
    finally:
        _loading_slot.empty()

# ───────────────────────────────────────────
# 로그인 / 회원가입 화면
# ───────────────────────────────────────────


if not st.session_state.logged_in:
    st.markdown("""
    <div class="login-header">
        <div class="login-logo">KlaWde</div>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        if not st.session_state.show_register:
            st.markdown('<div class="form-section-title">로그인</div>', unsafe_allow_html=True)
            username = st.text_input("아이디")
            password = st.text_input("비밀번호", type="password")
            if st.button("로그인", use_container_width=True):
                user = login_user(username, password)
                if user:
                    st.session_state.logged_in = True
                    st.session_state.user = {
                        "id": user[0], "username": user[1],
                        "name": user[3], "department": user[4],
                        "gender": user[5], "age": user[6]
                    }
                    st.rerun()
                else:
                    st.error("아이디 또는 비밀번호가 틀렸습니다.")
            st.markdown("---")
            if st.button("회원가입", use_container_width=True):
                st.session_state.show_register = True
                st.rerun()
        else:
            st.markdown('<div class="form-section-title">회원가입</div>', unsafe_allow_html=True)
            new_username = st.text_input("아이디")
            new_password = st.text_input("비밀번호", type="password")
            new_name = st.text_input("이름")
            new_department = st.text_input("학과")
            new_gender = st.selectbox("성별", ["선택 안 함", "남성", "여성", "기타"])
            new_age = st.number_input("나이", min_value=1, max_value=100, value=20)
            if st.button("가입하기", use_container_width=True):
                if not new_username or not new_password or not new_name:
                    st.error("아이디, 비밀번호, 이름은 필수입니다.")
                else:
                    success = register_user(new_username, new_password, new_name,
                                            new_department, new_gender, int(new_age))
                    if success:
                        st.success("가입 완료! 로그인 해주세요.")
                        st.session_state.show_register = False
                        st.rerun()
                    else:
                        st.error("이미 사용 중인 아이디입니다.")
            if st.button("← 로그인으로", use_container_width=True):
                st.session_state.show_register = False
                st.rerun()
    st.stop()

# ───────────────────────────────────────────
# 메인 화면 (로그인 후)
# ───────────────────────────────────────────
user = st.session_state.user

model_name = "gemini-2.5-flash" if st.session_state.model_type == "Flash" else "gemini-2.5-pro"

# ── 사이드바 ────────────────────────────────
with st.sidebar:
    st.markdown(f'<div class="sidebar-username">{user["name"]} 님</div>', unsafe_allow_html=True)

    if st.button("＋  새 대화", use_container_width=True):
        st.session_state.current_rag_conv_id = None
        st.session_state.rag_messages = []
        st.rerun()

    st.divider()

    st.session_state.model_type = st.radio("모델", ["Flash", "Pro"], horizontal=True)

    st.divider()

    # 대화 목록
    conversations = get_conversations(user["id"])
    if conversations:
        st.markdown('<p style="font-size:0.875rem;font-weight:600;color:var(--text2);font-family:Pretendard,sans-serif;margin:0 0 0.25rem 0;">대화 기록</p>', unsafe_allow_html=True)
        for conv in conversations:
            conv_id, title, created_at = conv
            is_active = st.session_state.current_rag_conv_id == conv_id
            col_a, col_b = st.columns([8, 1])
            with col_a:
                label = f"· {title}" if is_active else title
                if st.button(label, key=f"conv_{conv_id}", use_container_width=True):
                    st.session_state.current_rag_conv_id = conv_id
                    st.session_state.rag_messages = get_messages(conv_id)
                    st.rerun()
            with col_b:
                if st.button("×", key=f"del_{conv_id}"):
                    if st.session_state.current_rag_conv_id == conv_id:
                        st.session_state.current_rag_conv_id = None
                        st.session_state.rag_messages = []
                    delete_conversation(conv_id)
                    st.rerun()

        st.divider()
        if st.button("전체 삭제", use_container_width=True):
            delete_all_conversations(user["id"])
            st.session_state.current_rag_conv_id = None
            st.session_state.rag_messages = []
            st.rerun()

    st.divider()
    with st.expander("회원정보 수정"):
        with st.form("profile_form"):
            f_name = st.text_input("이름", value=user["name"])
            f_dept = st.text_input("학과", value=user["department"])
            f_gender = st.selectbox("성별", ["선택 안 함", "남성", "여성", "기타"],
                                    index=["선택 안 함", "남성", "여성", "기타"].index(user["gender"])
                                    if user["gender"] in ["선택 안 함", "남성", "여성", "기타"] else 0)
            f_age = st.number_input("나이", min_value=1, max_value=100, value=user["age"] or 20)
            if st.form_submit_button("저장", use_container_width=True):
                if not f_name:
                    st.error("이름은 필수입니다.")
                else:
                    update_user_info(user["id"], f_name, f_dept, f_gender, int(f_age))
                    st.session_state.user.update({"name": f_name, "department": f_dept,
                                                   "gender": f_gender, "age": int(f_age)})
                    st.success("저장됐어요.")

        st.markdown("---")
        with st.form("pw_form"):
            cur_pw = st.text_input("현재 비밀번호", type="password")
            new_pw = st.text_input("새 비밀번호", type="password")
            new_pw2 = st.text_input("새 비밀번호 확인", type="password")
            if st.form_submit_button("비밀번호 변경", use_container_width=True):
                if not login_user(user["username"], cur_pw):
                    st.error("현재 비밀번호가 틀렸습니다.")
                elif new_pw != new_pw2:
                    st.error("새 비밀번호가 일치하지 않습니다.")
                elif len(new_pw) < 4:
                    st.error("비밀번호는 4자 이상이어야 합니다.")
                else:
                    update_password(user["id"], new_pw)
                    st.success("변경됐어요.")

    if st.button("로그아웃", use_container_width=True):
        st.session_state.logged_in = False
        st.session_state.user = None
        st.session_state.show_register = False
        st.session_state.current_rag_conv_id = None
        st.session_state.rag_messages = []
        st.session_state.rag_ready = False
        st.session_state.vector_db = None
        st.session_state.rag_error = None
        st.rerun()

# ───────────────────────────────────────────
# RAG 채팅 화면
# ───────────────────────────────────────────
if not LANGCHAIN_OK:
    st.warning("langchain 관련 패키지를 설치하면 RAG 기능을 사용할 수 있습니다.")
elif not st.session_state.rag_ready:
    if st.session_state.rag_error:
        st.error(f"데이터베이스 로드 실패: {st.session_state.rag_error}")
    else:
        st.markdown(
            '<div class="kl-spinner-wrap">'
            '<div class="kl-spinner"></div>'
            '<span class="kl-spinner-label">준비 중...</span>'
            '</div>',
            unsafe_allow_html=True
        )
else:
    # 기존 메시지 표시
    for msg in st.session_state.rag_messages:
        with st.chat_message(msg["role"], avatar="🧑‍💻" if msg["role"] == "user" else "🤖"):
            st.markdown(msg["content"])

    # 처리 중 상태 확인
    if st.session_state.rag_processing:
        @st.fragment(run_every=1)
        def _poll():
            job_id = st.session_state.get("rag_job_id", "")
            p = _job_path(job_id)
            elapsed = time.time() - st.session_state.get("rag_job_start", time.time())

            if os.path.exists(p):
                with open(p, "r", encoding="utf-8") as f:
                    job = json.load(f)
                os.remove(p)
                if "result" in job:
                    st.session_state.rag_messages.append({"role": "assistant", "content": job["result"]})
                    save_message(st.session_state.current_rag_conv_id, "assistant", job["result"])
                else:
                    st.session_state.rag_last_error = job.get("error", "알 수 없는 오류")
                st.session_state.rag_processing = False
                st.rerun()
            elif elapsed > 90:
                st.session_state.rag_last_error = "요청 시간이 초과됐어요. 다시 시도해주세요."
                st.session_state.rag_processing = False
                st.rerun()
            else:
                st.markdown(
                    '<div class="kl-spinner-wrap" style="height:80px;">'
                    '<div class="kl-spinner"></div>'
                    '</div>',
                    unsafe_allow_html=True
                )
        with st.chat_message("assistant", avatar="🤖"):
            _poll()

    if st.session_state.get("rag_last_error"):
        st.error(f"⚠️ {st.session_state.rag_last_error}")
        st.session_state.rag_last_error = None

    # 입력창 (처리 중일 때는 숨김)
    if not st.session_state.rag_processing:
        if prompt := st.chat_input("문서에 대해 질문하세요"):
            if st.session_state.current_rag_conv_id is None:
                title = prompt[:20] + ("..." if len(prompt) > 20 else "")
                rag_conv_id = create_conversation(user["id"], title)
                st.session_state.current_rag_conv_id = rag_conv_id

            rag_conv_id = st.session_state.current_rag_conv_id
            st.session_state.rag_messages.append({"role": "user", "content": prompt})
            save_message(rag_conv_id, "user", prompt)

            # 백그라운드 스레드 시작
            job_id = str(uuid.uuid4())
            st.session_state.rag_job_id = job_id
            st.session_state.rag_processing = True
            st.session_state.rag_job_start = time.time()

            t = threading.Thread(
                target=_rag_worker,
                args=(job_id, prompt, model_name),
                daemon=True
            )
            t.start()
            st.rerun()
