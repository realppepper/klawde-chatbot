# src/app.py
import streamlit as st
import style
import time
import threading
import uuid
import os
import json
import logging

app_logger = logging.getLogger("KlawdeLogger")

import database as db
import rag_worker as rw

st.set_page_config(page_title="KlaWde", layout="wide", initial_sidebar_state="expanded")
db.init_db()
st.markdown(style.CUSTOM_CSS, unsafe_allow_html=True)

# 세션 초기화
for key, val in {
    "logged_in": False,
    "user": None,
    "current_rag_conv_id": None,
    "show_register": False,
    "model_type": "Flash", # 원래의 Flash 표기로 롤백
    "rag_ready": True,
    "rag_messages": [],
    "rag_job_id": None,
    "rag_processing": False,
}.items():
    if key not in st.session_state:
        st.session_state[key] = val

# ───────────────────────────────────────────
# 인증 뷰 레이어 (로그인/회원가입)
# ───────────────────────────────────────────
if not st.session_state.logged_in:
    st.markdown('<div class="login-header"><div class="login-logo">KlaWde</div></div>', unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        if not st.session_state.show_register:
            st.markdown('<div class="form-section-title">로그인</div>', unsafe_allow_html=True)
            username = st.text_input("아이디")
            password = st.text_input("비밀번호", type="password")
            if st.button("로그인", use_container_width=True):
                user = db.login_user(username, password)
                if user:
                    st.session_state.logged_in = True
                    st.session_state.user = {"id": user[0], "username": user[1], "name": user[3], "department": user[4], "gender": user[5], "age": user[6]}
                    app_logger.info(f"[Auth] 로그인 성공: {username}")
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
                    if db.register_user(new_username, new_password, new_name, new_department, new_gender, int(new_age)):
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
# 메인 어플리케이션 인터랙션 레이어
# ───────────────────────────────────────────
user = st.session_state.user
model_name = "gemini-2.5-flash" if st.session_state.model_type == "Flash" else "gemini-2.5-pro"

with st.sidebar:
    st.markdown(f'<div class="sidebar-username">{user["name"]} 님</div>', unsafe_allow_html=True)
    if st.button("＋  새 대화", use_container_width=True):
        st.session_state.current_rag_conv_id = None
        st.session_state.rag_messages = []
        st.rerun()
    st.divider()
    
    # 모델 선택 사양 원래 규격(Flash / Pro)으로 복구
    st.session_state.model_type = st.radio("모델", ["Flash", "Pro"], horizontal=True)
    st.divider()

    conversations = db.get_conversations(user["id"])
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
                    st.session_state.rag_messages = db.get_messages(conv_id)
                    st.rerun()
            with col_b:
                if st.button("×", key=f"del_{conv_id}"):
                    if st.session_state.current_rag_conv_id == conv_id:
                        st.session_state.current_rag_conv_id = None
                        st.session_state.rag_messages = []
                    db.delete_conversation(conv_id)
                    st.rerun()
        st.divider()
        if st.button("전체 삭제", use_container_width=True):
            db.delete_all_conversations(user["id"])
            st.session_state.current_rag_conv_id = None
            st.session_state.rag_messages = []
            st.rerun()

    st.divider()
    if st.button("로그아웃", use_container_width=True):
        st.session_state.update({"logged_in": False, "user": None, "current_rag_conv_id": None, "rag_messages": []})
        st.rerun()

# 기존 메시지 출력
for msg in st.session_state.rag_messages:
    with st.chat_message(msg["role"], avatar="🧑‍💻" if msg["role"] == "user" else "🤖"):
        st.markdown(msg["content"])

# 비동기 폴링 뷰 프래그먼트
if st.session_state.rag_processing:
    @st.fragment(run_every=1)
    def _poll_async_worker():
        job_id = st.session_state.get("rag_job_id", "")
        p = rw.get_job_path(job_id)
        elapsed = time.time() - st.session_state.get("rag_job_start", time.time())
        
        app_logger.debug(f"[UI Polling] 대기 중... 경과시간: {elapsed:.1f}초")

        if os.path.exists(p):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    job = json.load(f)
                os.remove(p)
                
                if "result" in job:
                    st.session_state.rag_messages.append({"role": "assistant", "content": job["result"]})
                    db.save_message(st.session_state.current_rag_conv_id, "assistant", job["result"])
                else:
                    st.session_state.rag_last_error = job.get("error", "시스템 오류")
            except Exception as e:
                st.session_state.rag_last_error = f"오류 발생: {str(e)}"
            
            st.session_state.rag_processing = False
            st.rerun()
            
        elif elapsed > 90:
            st.session_state.rag_last_error = "답변 생성 시간이 초과되었습니다."
            st.session_state.rag_processing = False
            st.rerun()
        else:
            st.markdown('<div class="kl-spinner-wrap" style="height:40px;"><div class="kl-spinner"></div></div>', unsafe_allow_html=True)
            
    with st.chat_message("assistant", avatar="🤖"):
        _poll_async_worker()

if st.session_state.get("rag_last_error"):
    st.error(f"⚠️ {st.session_state.rag_last_error}")
    st.session_state.rag_last_error = None

# 입력창 제어 (질의 전송 핸들러)
if not st.session_state.rag_processing:
    if prompt := st.chat_input("문서에 대해 질문하세요"):
        if st.session_state.current_rag_conv_id is None:
            title = prompt[:20] + "..." if len(prompt) > 20 else prompt
            st.session_state.current_rag_conv_id = db.create_conversation(user["id"], title)

        current_conv_id = st.session_state.current_rag_conv_id
        memory_window = st.session_state.rag_messages[-5:] if st.session_state.rag_messages else []
        
        st.session_state.rag_messages.append({"role": "user", "content": prompt})
        db.save_message(current_conv_id, "user", prompt)

        job_id = str(uuid.uuid4())
        st.session_state.update({
            "rag_job_id": job_id, 
            "rag_processing": True, 
            "rag_job_start": time.time()
        })

        t = threading.Thread(target=rw._rag_worker, args=(job_id, prompt, model_name, memory_window), daemon=True)
        t.start()
        st.rerun()