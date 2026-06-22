# src/rag_worker.py
import os
import json
import tempfile
import requests
import tomllib
import logging
import traceback
import time
from datetime import datetime
from advanced_rag import AdvancedRAGEngine

# ───────────────────────────────────────────
# 로그 시스템 세팅
# ───────────────────────────────────────────
logger = logging.getLogger("KlawdeLogger")
if not logger.handlers:
    logger.setLevel(logging.DEBUG)
    file_handler = logging.FileHandler("klawde_debug.log", encoding="utf-8")
    file_formatter = logging.Formatter('[%(asctime)s] [%(levelname)s] %(message)s', '%Y-%m-%d %H:%M:%S')
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(file_formatter)
    logger.addHandler(stream_handler)

_RAG_SYSTEM_INSTANCE = None

def get_rag_system():
    """RAG 엔진 인스턴스를 필요한 시점에 지연 로딩(Lazy Loading) 방식으로 생성합니다."""
    global _RAG_SYSTEM_INSTANCE
    if _RAG_SYSTEM_INSTANCE is None:
        logger.info("[Lazy Loading] RAG 엔진 최초 인스턴스 생성을 시작합니다...")
        _RAG_SYSTEM_INSTANCE = AdvancedRAGEngine(rebuild_mode=False)
        logger.info("[Lazy Loading] RAG 엔진 인스턴스 생성 완료 및 메모리 적재 성공.")
    return _RAG_SYSTEM_INSTANCE

# api.toml 파일로부터 보안 요건에 맞춰 GEMINI_API_KEY 안전 로드
try:
    with open(".streamlit/api.toml", "rb") as f:
        _secrets = tomllib.load(f)
    API_KEY = _secrets["GEMINI_API_KEY"]
    logger.info("api.toml로부터 Gemini API 키를 정상적으로 로드했습니다.")
except Exception as e:
    logger.critical(f"api.toml 파일에서 GEMINI_API_KEY 로드 실패: {str(e)}")
    API_KEY = ""

def get_job_path(job_id: str) -> str:
    return os.path.join(tempfile.gettempdir(), f"klawde_{job_id}.json")

def robust_request_post(url, headers, json_data, timeout=60, max_retries=3, initial_delay=2):
    """
    Gemini 무료 티어 호출 횟수(5 RPM) 제어 장벽 및 순간 지연을 방어하는 지수 백오프 레이어
    """
    delay = initial_delay
    for attempt in range(1, max_retries + 1):
        try:
            response = requests.post(url, headers=headers, json=json_data, timeout=timeout)
            
            # 429(Rate Limit 초과) 발생 시 백오프 대기 후 재시도 방어선 가동
            if response.status_code in [429, 503]:
                logger.warning(f"[Gemini 속도 제한 감지] HTTP {response.status_code} 발생. {attempt}/{max_retries} 백오프 재시도 진입...")
                logger.warning(f"[Gemini 속도 제한 감지] {delay}초 대기 후 안전하게 재요청을 송신합니다.")
                time.sleep(delay)
                delay *= 2
                continue
                
            return response
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
            logger.warning(f"[네트워크 지연] 연결 오류: {str(e)}. {attempt}/{max_retries} 재시도 준비중...")
            time.sleep(delay)
            delay *= 2
            
    return requests.post(url, headers=headers, json=json_data, timeout=timeout)

def rewrite_query(question: str, chat_history: list, gemini_base: str, headers: dict) -> str:
    """대화 기록을 바탕으로 사용자의 질문을 검색에 최적화된 독립적인 쿼리로 재작성합니다."""
    if not chat_history:
        return question
        
    history_str = "\n".join([f"{msg['role'].upper()}: {msg['content']}" for msg in chat_history])
    
    rewrite_prompt = (
        "당신은 검색 쿼리 최적화 AI입니다. 아래 제공된 [이전 대화 기록]을 바탕으로 "
        "[현재 질문]에 포함된 대명사('이것', '그거', '저 사람' 등)나 생략된 주어를 명확한 명사로 치환하여, "
        "단독으로 검색 시스템에 입력해도 맥락을 완벽히 이해할 수 있는 '하나의 명확한 검색 질문'으로 다시 작성해주세요.\n\n"
        "주의: 질문에 대한 답을 절대 하지 말고, 오직 '재작성된 질문 문장' 딱 하나만 출력하세요.\n\n"
        f"[이전 대화 기록]\n{history_str}\n\n"
        f"[현재 질문]: {question}"
    )
    
    # 250K TPM 한도를 가진 안전한 대형 창구인 gemini-2.5-flash 모델로 고정 우회
    url = f"{gemini_base}/gemini-3.1-flash-lite:generateContent"
    payload = {
        "contents": [{"role": "user", "parts": [{"text": rewrite_prompt}]}],
        "generationConfig": {"temperature": 0.0}
    }
    
    try:
        response = robust_request_post(url, headers=headers, json_data=payload, timeout=15)
        response.raise_for_status()
        rewritten = response.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
        rewritten = rewritten.replace('"', '').replace("'", "")
        return rewritten if rewritten else question
    except Exception as e:
        logger.error(f"[Query Rewriting Error] {str(e)}")
        return question

def _rag_worker(job_id: str, question: str, model_name: str, chat_history: list):
    """
    백그라운드 비동기 RAG 워커 함수 (구글 Gemini API 공식 복구 연동 버젼)
    """
    # Google Generative Language API 표준 베이스 엔드포인트 규격 선언
    GEMINI_BASE = "https://generativelanguage.googleapis.com/v1beta/models"
    HEADERS = {
        "x-goog-api-key": API_KEY, 
        "Content-Type": "application/json"
    }
    job_path = get_job_path(job_id)
    
    logger.info(f"=== [Gemini API Worker Start] Job ID: {job_id} ===")

    try:
        # 1. 쿼리 최적화 수행 (Gemini 2.5 Flash 기반 안전 구동)
        optimized_query = rewrite_query(question, chat_history, GEMINI_BASE, HEADERS)
        logger.info(f"[Query Rewrite 완료] 결과 변환 쿼리: '{optimized_query}'")

        # 2. RAG 지식 검색 가동 (VoyageAI + BM25)
        rag_engine = get_rag_system()
        
        logger.info(f"[Hybrid Search] 탐색 시작 -> '{optimized_query}'")
        start_time = datetime.now()
        
        # Gemini의 250,000 TPM 한도 마진 회복에 맞춰 상위 Parent 복원 단락 개수를 다시 4개로 원상 복귀! (RAG 답변 가버리지 전면 복원)
        context, sources = rag_engine.hybrid_search(optimized_query, top_n=4)
        logger.info(f"[Hybrid Search] 탐색 완료. 소요 시간: {datetime.now() - start_time}")

        # 3. 대화 이력 포장
        history_str = ""
        if chat_history:
            history_str = "\n".join([f"- {msg['role'].upper()}: {msg['content']}" for msg in chat_history])
        else:
            history_str = "이전 대화 기록이 없음."

        # 4. 메모리와 지식이 융합된 프롬프트 조립
        full_prompt = (
            "당신은 광운대학교 학사안내 전문 AI 비서 KlaWde입니다.\n"
            "제공된 [참조 컨텍스트 지식 스토어]의 내용과 이전에 나눈 [이전 대화 메모리 기록]을 함께 참고하여 대화의 맥락에 맞는 답변을 완성하세요.\n"
            "컨텍스트 지식으로 유추할 수 없거나 확답이 불가능한 질문은 억지로 답변하지 마세요.\n\n"
            f"[이전 대화 메모리 기록]:\n{history_str}\n\n"
            f"[참조 컨텍스트 지식 스토어]:\n{context}\n\n"
            f"[사용자 질의 요구사항]: {question}"
        )
        
        # app.py 단 라디오 버튼 선택에 대응하는 공식 구글 모델 식별자 맵핑
        target_model = "gemini-3.1-flash-lite"
        url = f"{GEMINI_BASE}/{target_model}:generateContent"
        
        payload = {
            "contents": [{"role": "user", "parts": [{"text": full_prompt}]}],
            "generationConfig": {"temperature": 0.2}
        }
        
        # 5. 메인 Gemini API 생성 요청 송신
        logger.info(f"[Gemini LLM] 메인 생성 요청 송신 중 -> 타겟 모델: {target_model}")
        response = robust_request_post(url, headers=HEADERS, json_data=payload, timeout=60)
        response.raise_for_status()
        answer = response.json()["candidates"][0]["content"]["parts"][0]["text"]

        if sources:
            answer += "\n\n📎 **KlaWde RAG 분석 기반 시스템 참조 출처**\n" + "\n".join(f"- {s}" for s in sources)

        # 6. 임시 결과 영속화 디스크 드랍
        with open(job_path, "w", encoding="utf-8") as f:
            json.dump({"done": True, "result": answer}, f, ensure_ascii=False)
        logger.info(f"[File I/O] 결과 파일 드랍 완료.")
            
    except Exception as e:
        logger.error(f"[Worker Error] {str(e)}\n{traceback.format_exc()}")
        try:
            with open(job_path, "w", encoding="utf-8") as f:
                json.dump({"done": True, "error": f"백엔드 에러: {str(e)}"}, f, ensure_ascii=False)
        except Exception:
            pass

    logger.info(f"=== [Gemini API Worker End] Job ID: {job_id} ===")