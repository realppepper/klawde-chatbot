# scripts/test_api.py (기존 파일 덮어쓰기)
import sys
import os
import requests
import tomllib
import voyageai

# 프로젝트 루트 경로 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

with open(".streamlit/api.toml", "rb") as f:
    secrets = tomllib.load(f)

GROQ_API_KEY = secrets.get("GROQ_API_KEY", "")
VOYAGE_API_KEY = secrets.get("VOYAGE_API_KEY", "")

print("=== [1단계] API 통신 및 토큰 한도 진단 ===")

# 1. VoyageAI Reranker 테스트
print("\n[1] VoyageAI Reranker API 테스트 중...")
try:
    vo = voyageai.Client(api_key=VOYAGE_API_KEY)
    res = vo.rerank(query="테스트", documents=["테스트 문서입니다."], model="rerank-2", top_k=1)
    print(f"  ✅ 성공! Reranker 연결 정상 (Score: {res.results[0].relevance_score:.4f})")
except Exception as e:
    print(f"  ❌ 실패: {e}")

# 2. Groq LLM 테스트
print("\n[2] Groq LLM API 테스트 중...")
try:
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": "llama-3.1-8b-instant",
        "messages": [{"role": "user", "content": "안녕, 딱 10글자로 대답해줘."}],
        "max_tokens": 50
    }
    response = requests.post(url, headers=headers, json=payload, timeout=10)
    response.raise_for_status()
    print(f"  ✅ 성공! 응답: {response.json()['choices'][0]['message']['content']}")
except Exception as e:
    print(f"  ❌ 실패: {e}")

print("\n진단 완료.")