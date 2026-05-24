import streamlit as st
import google.generativeai as genai
import sqlite3
import hashlib
import tomllib
from datetime import datetime

# ───────────────────────────────────────────
# 설정
# ───────────────────────────────────────────
with open(".streamlit/api.toml", "rb") as f:
    _secrets = tomllib.load(f)
API_KEY = _secrets["GEMINI_API_KEY"]
DB_PATH = "chatbot.db"

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
            created_at TEXT
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id INTEGER,
            role TEXT,
            content TEXT,
            created_at TEXT
        )
    """)
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
        with get_conn() as conn:
            conn.execute(
                "INSERT INTO users (username, password, name, department, gender, age) VALUES (?,?,?,?,?,?)",
                (username, hash_password(password), name, department, gender, age)
            )
        return True
    except sqlite3.IntegrityError:
        return False

def login_user(username, password):
    with get_conn() as conn:
        c = conn.execute("SELECT * FROM users WHERE username=? AND password=?",
                         (username, hash_password(password)))
        return c.fetchone()

def get_conversations(user_id):
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT id, title, created_at FROM conversations WHERE user_id=? ORDER BY created_at DESC", (user_id,))
    rows = c.fetchall()
    conn.close()
    return rows

def create_conversation(user_id, title):
    conn = get_conn()
    c = conn.cursor()
    c.execute("INSERT INTO conversations (user_id, title, created_at) VALUES (?,?,?)",
              (user_id, title, datetime.now().strftime("%Y-%m-%d %H:%M")))
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
                 (SELECT id FROM conversations WHERE user_id=?)""", (user_id,))
    c.execute("DELETE FROM conversations WHERE user_id=?", (user_id,))
    conn.commit()
    conn.close()

# ───────────────────────────────────────────
# 페이지 설정
# ───────────────────────────────────────────
st.set_page_config(page_title="AI 챗봇", layout="wide")
init_db()

# ───────────────────────────────────────────
# 세션 초기화
# ───────────────────────────────────────────
for key, val in {
    "logged_in": False,
    "user": None,
    "current_conv_id": None,
    "messages": [],
    "show_register": False,
    "model_type": "Flash"
}.items():
    if key not in st.session_state:
        st.session_state[key] = val

# ───────────────────────────────────────────
# 로그인 / 회원가입 화면
# ───────────────────────────────────────────
if not st.session_state.logged_in:
    st.markdown("<h2 style='text-align:center; margin-top:3rem;'>AI 챗봇</h2>", unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        if not st.session_state.show_register:
            st.subheader("로그인")
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
            st.subheader("회원가입")
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
                    success = register_user(new_username, new_password, new_name, new_department, new_gender, int(new_age))
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
genai.configure(api_key=API_KEY)

# 사이드바
with st.sidebar:
    st.markdown(f"**{user['name']}** 님")
    st.caption(f"{user['department']} · {user['age']}세 · {user['gender']}")
    st.divider()

    # 모델 선택
    st.session_state.model_type = st.radio("모델", ["Flash", "Pro"], horizontal=True)
    st.divider()

    # 새 대화
    if st.button("+ 새 대화", use_container_width=True):
        st.session_state.current_conv_id = None
        st.session_state.messages = []
        st.rerun()

    # 대화 목록
    st.caption("최근 대화")
    conversations = get_conversations(user["id"])
    for conv in conversations:
        conv_id, title, created_at = conv
        col_a, col_b = st.columns([5, 1])
        with col_a:
            if st.button(f"💬 {title}", key=f"conv_{conv_id}", use_container_width=True):
                st.session_state.current_conv_id = conv_id
                st.session_state.messages = get_messages(conv_id)
                st.rerun()
        with col_b:
            if st.button("🗑", key=f"del_{conv_id}"):
                if st.session_state.current_conv_id == conv_id:
                    st.session_state.current_conv_id = None
                    st.session_state.messages = []
                delete_conversation(conv_id)
                st.rerun()

    if conversations:
        st.divider()
        if st.button("🗑 전체 대화 삭제", use_container_width=True):
            delete_all_conversations(user["id"])
            st.session_state.current_conv_id = None
            st.session_state.messages = []
            st.rerun()

    st.divider()
    if st.button("로그아웃", use_container_width=True):
        st.session_state.logged_in = False
        st.session_state.user = None
        st.session_state.current_conv_id = None
        st.session_state.messages = []
        st.rerun()

# 채팅 화면
model_name = "gemini-2.5-flash" if st.session_state.model_type == "Flash" else "gemini-2.0-pro-exp"
st.caption(f"Gemini {st.session_state.model_type} 모드")

# 이전 메시지 출력
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

# 입력창
if prompt := st.chat_input("메시지를 입력하세요"):
    # 새 대화면 conv 생성
    if st.session_state.current_conv_id is None:
        title = prompt[:20] + ("..." if len(prompt) > 20 else "")
        conv_id = create_conversation(user["id"], title)
        st.session_state.current_conv_id = conv_id

    conv_id = st.session_state.current_conv_id

    # 사용자 메시지
    st.session_state.messages.append({"role": "user", "content": prompt})
    save_message(conv_id, "user", prompt)
    with st.chat_message("user"):
        st.write(prompt)

    # 시스템 프롬프트 (사용자 정보 반영)
    system_prompt = f"""당신은 친절한 AI 어시스턴트입니다.
현재 대화 중인 사용자 정보:
- 이름: {user['name']}
- 학과: {user['department']}
- 성별: {user['gender']}
- 나이: {user['age']}세
이 정보를 참고해서 적절한 답변을 제공하세요."""

    # Gemini 호출
    model = genai.GenerativeModel(
        model_name,
        system_instruction=system_prompt
    )
    history = [
        {"role": m["role"] if m["role"] != "assistant" else "model", "parts": [m["content"]]}
        for m in st.session_state.messages[:-1]
    ]
    chat = model.start_chat(history=history)

    with st.chat_message("assistant"):
        with st.spinner("답변 생성 중..."):
            response = chat.send_message(prompt)
            answer = response.text
            st.write(answer)

    st.session_state.messages.append({"role": "assistant", "content": answer})
    save_message(conv_id, "assistant", answer)