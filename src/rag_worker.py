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
# 로그 시스템 및 디렉토리 세팅
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

# 수집 문서 무생략 저장을 위한 logs 폴더 보장
os.makedirs("logs", exist_ok=True)

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

def save_ui_retrieved_documents(raw_question, optimized_query, bm25_docs, vector_docs):
    """
    [요구사항 반영]: UI에서 사용자가 입력한 질문과 하이브리드 검색엔진이 수집한 
    모든 문서의 원문 본문 전체를 생략 없이 고유 텍스트 파일로 안전하게 백업합니다.
    """
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        # 파일명 안정성 검크 및 슬라이싱
        clean_q = "".join([c for c in raw_question if c.isalnum() or c in (' ', '_', '-')]).strip()[:25]
        clean_q = clean_q.replace(' ', '_')
        if not clean_q:
            clean_q = "ui_query"
            
        filename = f"logs/ui_retrieved_docs_{timestamp}_{clean_q}.txt"
        
        with open(filename, "w", encoding="utf-8") as f:
            f.write("==================================================================\n")
            f.write("📱 KlaWde Web UI 실시간 수집 문서 원문 백업 로그\n")
            f.write(f"📅 일시: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"🧑‍💻 사용자 원본 질문: {raw_question}\n")
            f.write(f"🔄 최적화 정제 쿼리: {optimized_query}\n")
            f.write("==================================================================\n\n")
            
            f.write(f"■ [1] BM25 (Sparse) 검색엔진 수집 단락 (총 {len(bm25_docs)}개)\n")
            f.write("-" * 70 + "\n")
            for idx, doc in enumerate(bm25_docs, 1):
                src = doc.metadata.get("source", "Unknown")
                p_id = doc.metadata.get("parent_id", "Unknown")
                f.write(f"[{idx:02d}] 출처: {src} | Parent ID: {p_id}\n")
                f.write(f"[메타데이터]: {json.dumps(doc.metadata, ensure_ascii=False)}\n")
                f.write("-" * 40 + "\n")
                f.write("[원문 본문 내용]\n")
                f.write(doc.page_content)
                f.write("\n" + "=" * 50 + "\n\n")
                
            f.write(f"■ [2] Vector DB (Dense) 검색엔진 수집 단락 (총 {len(vector_docs)}개)\n")
            f.write("-" * 70 + "\n")
            for idx, doc in enumerate(vector_docs, 1):
                src = doc.metadata.get("source", "Unknown")
                p_id = doc.metadata.get("parent_id", "Unknown")
                f.write(f"[{idx:02d}] 출처: {src} | Parent ID: {p_id}\n")
                f.write(f"[메타데이터]: {json.dumps(doc.metadata, ensure_ascii=False)}\n")
                f.write("-" * 40 + "\n")
                f.write("[원문 본문 내용]\n")
                f.write(doc.page_content)
                f.write("\n" + "=" * 50 + "\n\n")
                
        logger.info(f"[UI Document Backup Success] 원문 백업 파일이 저장되었습니다 -> {filename}")
    except Exception as backup_err:
        logger.error(f"[UI Document Backup Failed] 백업 도중 오류 발생: {str(backup_err)}")

def robust_request_post(url, headers, json_data, timeout=60, max_retries=3, initial_delay=2):
    """Gemini 무료 티어 호출 횟수(5 RPM) 제어 장벽 및 순간 지연을 방어하는 지수 백오프 레이어"""
    delay = initial_delay
    for attempt in range(1, max_retries + 1):
        try:
            response = requests.post(url, headers=headers, json=json_data, timeout=timeout)
            if response.status_code in [429, 503]:
                logger.warning(f"[Gemini 속도 제한 감지] HTTP {response.status_code} 발생. {attempt}/{max_retries} 백오프 재시도 진입...")
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
        
    history_str = ""
    for msg in chat_history[-4:]:
        history_str += f"{msg['role'].upper()}: {msg['content']}\n"
    
    rewrite_prompt = (
        "당신은 정보 검색 시스템(RAG)의 성능을 극대화하기 위해 사용자의 질의를 최적화하는 검색 쿼리 정제 전문가입니다.\n"
        "제공된 [이전 대화 기록]을 분석하여 사용자가 생략한 주어나 목적어가 있다면 이를 보완하되, "
        "절대로 문장형 서술어('~에 대해 알려줘', '찾아줘', '구체적인 안내')나 불필요한 조사, 안내성 수식어를 붙이지 마십시오.\n"
        "검색엔진의 키워드 매칭 신뢰도를 높이기 위해, 반드시 고유명사와 핵심 명사 위주의 콤팩트한 단어 조합 형태로만 결과를 딱 하나 출력하세요.\n\n"
        "❌ 나쁜 출력 예시: 박수원 교수님의 연구실 위치와 연락처 정보를 찾아줘\n"
        "⭕ 좋은 출력 예시: 박수원 교수 연구실 위치 연락처\n\n"
        "◆ [Few-Shot Examples]\n"
        "이전 대화 기록:\n"
        "USER: 컴퓨터공학과 학과사무실 전화번호가 뭐야?\n"
        "ASSISTANT: 컴퓨터공학과 사무실 번호는 02-940-XXXX 입니다.\n"
        "현재 질문: 박수원 교수님은?\n"
        "출력: 박수원 교수\n\n"
        f"[이전 대화 기록]\n{history_str}\n"
        f"[현재 질문]: {question}\n\n"
        "출력:"
    )
    
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
    """백그라운드 비동기 RAG 워커 함수 (UI 실시간 원문 파일 저장 연동 버전)"""
    GEMINI_BASE = "https://generativelanguage.googleapis.com/v1beta/models"
    HEADERS = {
        "x-goog-api-key": API_KEY, 
        "Content-Type": "application/json"
    }
    job_path = get_job_path(job_id)
    
    logger.info(f"=== [Gemini API Worker Start] Job ID: {job_id} ===")

    try:
        # 1. 쿼리 최적화 수행
        optimized_query = rewrite_query(question, chat_history, GEMINI_BASE, HEADERS)
        logger.info(f"[Query Rewrite 완료] 결과 변환 쿼리: '{optimized_query}'")

        # 2. RAG 지식 검색 인스턴스 지연 생성 후 개별 수집 가동
        rag_engine = get_rag_system()
        
        # [원문 분리 백업을 위해 지연 호출 전 1차 매칭 단계 로깅 연동]
        bm25_query = rag_engine.extract_keywords_for_bm25(optimized_query)
        rag_engine.bm25_retriever.k = 20
        bm25_results = rag_engine.bm25_retriever.invoke(bm25_query)
        vector_results = rag_engine.vector_db.similarity_search(optimized_query, k=20)
        
        # 📌 [핵심 요구사항 반영]: 사용자가 UI에서 할 질문과 수집 문서를 원문 통째로 백업 실행
        save_ui_retrieved_documents(question, optimized_query, bm25_results, vector_results)

        # 3. 기존의 하이브리드 통합 융합 파이프라인 수행 (Rerank -> Parent Context 복원)
        logger.info(f"[Hybrid Search] 탐색 시작 -> '{optimized_query}'")
        start_time = datetime.now()
        context, sources = rag_engine.hybrid_search(optimized_query, top_n=4)
        logger.info(f"[Hybrid Search] 탐색 완료. 소요 시간: {datetime.now() - start_time}")

        # 4. 대화 이력 포장
        history_str = ""
        if chat_history:
            history_str = "\n".join([f"- {msg['role'].upper()}: {msg['content']}" for msg in chat_history])
        else:
            history_str = "이전 대화 기록이 없음."

        # 5. 메모리와 지식이 융합된 최종 프롬프트 조립
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
        
        # 6. 메인 Gemini API 생성 요청 송신
        logger.info(f" can[Gemini LLM] 메인 생성 요청 송신 중 -> 타겟 모델: {target_model}")
        response = robust_request_post(url, headers=HEADERS, json_data=payload, timeout=60)
        response.raise_for_status()
        answer = response.json()["candidates"][0]["content"]["parts"][0]["text"]

        if sources:
            answer += "\n\n📎 **KlaWde RAG 분석 기반 시스템 참조 출처**\n" + "\n".join(f"- {s}" for s in sources)

        # 7. 임시 결과 영속화 디스크 드랍 (Streamlit 프론트엔드가 감지하는 규격 엔드포인트)
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