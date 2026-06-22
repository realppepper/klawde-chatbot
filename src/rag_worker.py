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
from query_optimizer import build_hyde_hyqe_prompt, parse_hyde_hyqe_response

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
    """Gemini 호출 횟수 제한(Rate Limit) 및 일시적인 네트워크 지연을 방어하는 지수 백오프 레이어"""
    delay = initial_delay
    for attempt in range(1, max_retries + 1):
        try:
            response = requests.post(url, headers=headers, json=json_data, timeout=timeout)
            if response.status_code in [429, 503]:
                logger.warning(f"[Gemini 속도 제한 감지] HTTP {response.status_code} 발생. {attempt}/{max_retries} 백오프 대기 진입...")
                time.sleep(delay)
                delay *= 2
                continue
            return response
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
            logger.warning(f"[네트워크 지연] 연결 오류: {str(e)}. {attempt}/{max_retries} 재시도 준비중...")
            time.sleep(delay)
            delay *= 2
            
    return requests.post(url, headers=headers, json=json_data, timeout=timeout)

def generate_hyde_hyqe(question: str, chat_history: list, gemini_base: str, headers: dict) -> dict:
    """Gemini 최적화 창구를 가동하여 가상 문서(HyDE)와 최적 키워드(HyQE) 딕셔너리를 빌드"""
    prompt = build_hyde_hyqe_prompt(question, chat_history)
    url = f"{gemini_base}/gemini-3.1-flash-lite:generateContent"
    payload = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.3}
    }
    try:
        response = robust_request_post(url, headers=headers, json_data=payload, timeout=25)
        response.raise_for_status()
        response_text = response.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
        return parse_hyde_hyqe_response(response_text, question)
    except Exception as e:
        logger.error(f"[HyDE/HyQE Generation Error] 생성 API 연산 중 예외 발생: {str(e)}")
        return {"hyqe_query": question, "hyde_document": question}

def _rag_worker(job_id: str, question: str, model_name: str, chat_history: list):
    """백그라운드 비동기 RAG 워커 메인 프로세스 (HyDE / HyQE 하이브리드 파이프라인 구동)"""
    GEMINI_BASE = "https://generativelanguage.googleapis.com/v1beta/models"
    HEADERS = {"x-goog-api-key": API_KEY, "Content-Type": "application/json"}
    job_path = get_job_path(job_id)
    logger.info(f"=== [Gemini HyDE/HyQE RAG Worker Start] Job ID: {job_id} ===")

    try:
        optimized_data = generate_hyde_hyqe(question, chat_history, GEMINI_BASE, HEADERS)
        hyqe_query = optimized_data["hyqe_query"]
        hyde_doc = optimized_data["hyde_document"]
        
        logger.info(f"[HyQE Keyword Query]: '{hyqe_query}'")
        logger.info(f"[HyDE Hypothetical Doc]: '{hyde_doc[:80]}...'")

        rag_engine = get_rag_system()
        logger.info(f"[Hybrid Search] 멀티 트랙 탐색 알고리즘 가동")
        start_time = datetime.now()
        
        context, sources = rag_engine.hybrid_search(
            original_query=question,
            hyde_doc=hyde_doc,
            hyqe_query=hyqe_query,
            top_n=4
        )
        logger.info(f"[Hybrid Search] 검색 완료. 소요 시간: {datetime.now() - start_time}")

        history_str = ""
        if chat_history:
            history_str = "\n".join([f"- {msg['role'].upper()}: {msg['content']}" for msg in chat_history])
        else:
            history_str = "이전 대화 기록이 없음."

        full_prompt = (
            "당신은 광운대학교 학사안내 전문 AI 비서 KlaWde입니다.\n"
            "제공된 [참조 컨텍스트 지식 스토어]의 내용과 이전에 나눈 [이전 대화 메모리 기록]을 함께 참고하여 대화의 맥락에 맞는 답변을 완성하세요.\n"
            "컨텍스트 지식으로 유추할 수 없거나 확답이 불가능한 질문은 억지로 답변하지 마세요.\n\n"
            f"[이전 대화 메모리 기록]:\n{history_str}\n\n"
            f"[참조 컨텍스트 지식 스토어]:\n{context}\n\n"
            f"[사용자 질의 요구사항]: {question}"
        )
        
        target_model = "gemini-3.1-flash-lite"
        url = f"{GEMINI_BASE}/{target_model}:generateContent"
        payload = {
            "contents": [{"role": "user", "parts": [{"text": full_prompt}]}],
            "generationConfig": {"temperature": 0.2}
        }
        
        logger.info(f"[Gemini LLM] 답변 생성 요청 전송 -> 모델: {target_model}")
        response = robust_request_post(url, headers=HEADERS, json_data=payload, timeout=60)
        response.raise_for_status()
        answer = response.json()["candidates"][0]["content"]["parts"][0]["text"]

        if sources:
            answer += "\n\n📎 **KlaWde RAG 분석 기반 시스템 참조 출처**\n" + "\n".join(f"- {s}" for s in sources)

        with open(job_path, "w", encoding="utf-8") as f:
            json.dump({"done": True, "result": answer}, f, ensure_ascii=False)
        logger.info(f"[File I/O] 결과 세션 덤프 완료.")
            
    except Exception as e:
        logger.error(f"[Worker Error] 내부 치명적 에러: {str(e)}\n{traceback.format_exc()}")
        try:
            with open(job_path, "w", encoding="utf-8") as f:
                json.dump({"done": True, "error": f"백엔드 런타임 에러 발생: {str(e)}"}, f, ensure_ascii=False)
        except Exception:
            pass

    logger.info(f"=== [Gemini API Worker End] Job ID: {job_id} ===")