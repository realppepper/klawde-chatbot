import json
import re
import logging

logger = logging.getLogger("KlawdeLogger")

def build_hyde_hyqe_prompt(question: str, chat_history: list) -> str:
    """사용자의 질문과 대화 맥락을 기반으로 HyQE와 HyDE를 동시에 생성하도록 지시하는 시스템 프롬프트 조립"""
    history_str = ""
    if chat_history:
        history_str = "\n".join([f"{msg['role'].upper()}: {msg['content']}" for msg in chat_history])
    else:
        history_str = "이전 대화 기록 없음."
    
    # AI 출력 시 코드블럭 예외가 마크다운 파서를 깨뜨리지 않도록 백틱 동적 결합 처리
    backticks = "`" * 3
    prompt = (
        "당신은 광운대학교 학사 정보 검색 시스템의 효율을 극대화하기 위한 검색 엔진 최적화(HyDE & HyQE) 전문 AI입니다.\n"
        "사용자의 [현재 질문]과 [이전 대화 기록]을 종합적으로 분석한 뒤, 다음 두 가지 요소를 반드시 지정된 'JSON 형식'으로만 생성하여 출력하세요.\n\n"
        "1. \"hyqe_query\": 키워드 매칭 검색기(BM25)가 고유 명사와 핵심 학사 단어를 칼같이 필터링할 수 있도록, 대명사를 제거하고 주어와 목적어를 명확하게 복원한 키워드 중심의 질문 문장.\n"
        "2. \"hyde_document\": 벡터 검색기(ChromaDB)가 의미론적 유사성을 정밀하게 계산할 수 있도록, 해당 질문에 대해 광운대학교 학사 규정 내규나 공지사항 본문이 담고 있을 법한 완성된 형태의 '가상의 예상 답변 문서' (약 200자 내외).\n\n"
        "주의사항:\n"
        f"- 마크다운 코드 블록({backticks}json ... {backticks})이나 불필요한 설명, 인사는 절대로 출력하지 마십시오.\n"
        "- 오직 파이썬 내부에서 json.loads()로 즉시 파싱할 수 있는 순수한 JSON 객체 딱 하나만 반환해야 합니다.\n\n"
        f"[이전 대화 기록]\n{history_str}\n\n"
        f"[현재 질문]: {question}"
    )
    return prompt

def parse_hyde_hyqe_response(response_text: str, original_question: str) -> dict:
    """Gemini가 반환한 원시 텍스트에서 불필요한 기호를 전처리하고 안정적으로 JSON 객체를 분리 및 파싱"""
    try:
        clean_text = response_text.strip()
        
        # 시스템 마크다운이 깨지는 현상을 방지하기 위해 정규식 패턴 대신 백틱을 동적으로 계산하여 트리밍
        triple_backtick = "`" * 3
        if clean_text.startswith(triple_backtick):
            lines = clean_text.splitlines()
            if lines[0].startswith(triple_backtick):
                lines = lines[1:]
            if lines and lines[-1].startswith(triple_backtick):
                lines = lines[:-1]
            clean_text = "\n".join(lines).strip()
            
        parsed = json.loads(clean_text)
        return {
            "hyqe_query": parsed.get("hyqe_query", original_question),
            "hyde_document": parsed.get("hyde_document", original_question)
        }
    except Exception as e:
        logger.error(f"[Query Optimizer Error] JSON 파싱 실패, 원본 질문으로 폴백. 에러: {str(e)}\n원본 응답: {response_text}")
        # 예외 발생 시 서비스 중단을 막기 위한 Fallback 보장
        return {
            "hyqe_query": original_question,
            "hyde_document": original_question
        }