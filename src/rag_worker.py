# rag_worker.py
import os
import json
import tempfile
import requests
import chromadb
import voyageai
import tomllib
from advanced_rag import AdvancedRAGEngine

# 토큰 보안 로드
with open(".streamlit/api.toml", "rb") as f:
    _secrets = tomllib.load(f)
API_KEY = _secrets["GEMINI_API_KEY"]
VOYAGE_API_KEY = _secrets["VOYAGE_API_KEY"]

# RAG 백엔드 싱글톤 인스턴스
RAG_SYSTEM = AdvancedRAGEngine(rebuild_mode=False)

def get_job_path(job_id: str) -> str:
    return os.path.join(tempfile.gettempdir(), f"klawde_{job_id}.json")

def _rag_worker(job_id: str, question: str, model_name: str, chat_history: list):
    """
    백그라운드 비동기 RAG 워커 함수
    chat_history 예시: [{'role': 'user', 'content': '안녕'}, {'role': 'assistant', 'content': '안녕하세요!'}]
    """
    GEMINI_BASE = "https://generativelanguage.googleapis.com/v1beta/models"
    HEADERS = {"x-goog-api-key": API_KEY, "Content-Type": "application/json"}

    try:
        # 1. 고도화 하이브리드 지식 검색 가동
        context, sources = RAG_SYSTEM.hybrid_search(question, top_n=4)

        # 2. [기능 추가]: 이전 대화 내역(메모리)을 히스토리 텍스트 포맷으로 포장
        history_str = ""
        if chat_history:
            history_str = "\n".join([f"- {msg['role'].upper()}: {msg['content']}" for msg in chat_history])
        else:
            history_str = "이전 대화 기록이 없음."

        # 3. 메모리와 검색 지식이 통합된 컨텍스트 프롬프트 빌드
        full_prompt = (
            "당신은 광운대학교 학사안내 전문 AI 비서 KlaWde입니다.\n"
            "제공된 [참조 컨텍스트 지식 스토어]의 내용과 이전에 나눈 [이전 대화 메모리 기록]을 함께 참고하여 대화의 맥락에 맞는 답변을 완성하세요.\n"
            "컨텍스트 지식으로 유추할 수 없거나 확답이 불가능한 질문은 억지로 답변하지 마세요.\n\n"
            f"[이전 대화 메모리 기록]:\n{history_str}\n\n"
            f"[참조 컨텍스트 지식 스토어]:\n{context}\n\n"
            f"[사용자 질의 요구사항]: {question}"
        )
        
        # 4. REST API 직접 호출
        response = requests.post(
            f"{GEMINI_BASE}/{model_name}:generateContent",
            headers=HEADERS,
            json={
                "contents": [{"role": "user", "parts": [{"text": full_prompt}]}],
                "generationConfig": {"temperature": 0.2}
            },
            timeout=120
        )
        response.raise_for_status()
        answer = response.json()["candidates"][0]["content"]["parts"][0]["text"]

        # 출처 리포팅 바인딩
        if sources:
            answer += "\n\n📎 **KlaWde RAG 분석 기반 시스템 참조 출처**\n" + "\n".join(f"- {s}" for s in sources)

        with open(get_job_path(job_id), "w", encoding="utf-8") as f:
            json.dump({"done": True, "result": answer}, f, ensure_ascii=False)
            
    except Exception as e:
        with open(get_job_path(job_id), "w", encoding="utf-8") as f:
            json.dump({"done": True, "error": str(e)}, f, ensure_ascii=False)