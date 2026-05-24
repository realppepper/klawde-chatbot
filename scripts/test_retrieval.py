import sys
import tomllib

with open(".streamlit/api.toml", "rb") as f:
    secrets = tomllib.load(f)
API_KEY = secrets["GEMINI_API_KEY"]

print("[1] GoogleGenerativeAIEmbeddings 생성 중...", flush=True)
from langchain_google_genai import GoogleGenerativeAIEmbeddings
embeddings = GoogleGenerativeAIEmbeddings(
    model="models/gemini-embedding-001",
    google_api_key=API_KEY
)
print("    완료", flush=True)

print("[2] Chroma 객체 생성 중...", flush=True)
from langchain_chroma import Chroma
db = Chroma(persist_directory="./chroma_db_html", embedding_function=embeddings)
print("    완료", flush=True)

print("[3] 문서 수 확인 중...", flush=True)
count = db._collection.count()
print(f"    문서 수: {count}", flush=True)

print("[4] embed_query 호출 중...", flush=True)
vec = embeddings.embed_query("테스트 질문입니다")
print(f"    벡터 길이: {len(vec)}", flush=True)

print("[5] ChromaDB 검색 중...", flush=True)
results = db._collection.query(query_embeddings=[vec], n_results=2)
print(f"    결과 수: {len(results['documents'][0])}", flush=True)

print("\n전체 완료")
