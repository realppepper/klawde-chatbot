import tomllib
from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage

with open(".streamlit/api.toml", "rb") as f:
    secrets = tomllib.load(f)
API_KEY = secrets["GEMINI_API_KEY"]

print(f"API 키 확인: {API_KEY[:8]}...")

# 1. 임베딩 테스트
print("\n[1] 임베딩 API 테스트 중...")
try:
    embeddings = GoogleGenerativeAIEmbeddings(
        model="models/gemini-embedding-001",
        google_api_key=API_KEY
    )
    vec = embeddings.embed_query("테스트 문장입니다")
    print(f"    성공! 벡터 길이: {len(vec)}")
except Exception as e:
    print(f"    실패: {e}")

# 2. 채팅 모델 테스트
print("\n[2] 채팅 API 테스트 중...")
try:
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.0-flash",
        google_api_key=API_KEY,
        temperature=0
    )
    resp = llm.invoke([HumanMessage(content="안녕")])
    print(f"    성공! 응답: {resp.content[:50]}")
except Exception as e:
    print(f"    실패: {e}")

print("\n테스트 완료")
