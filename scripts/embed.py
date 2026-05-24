import os
import sys
import json
import time
import shutil
import tomllib

# ───────────────────────────────────────────
# 설정
# ───────────────────────────────────────────
with open(".streamlit/api.toml", "rb") as f:
    _secrets = tomllib.load(f)
VOYAGE_API_KEY = _secrets["VOYAGE_API_KEY"]

HTML_BASE = "./html_data"
CHROMA_DIR  = "./chroma_db_html"
CHUNK_SIZE  = 1000
CHUNK_OVERLAP = 100
BATCH_SIZE  = 30

# ───────────────────────────────────────────
# 임포트
# ───────────────────────────────────────────
try:
    from langchain_voyageai import VoyageAIEmbeddings
    from langchain_text_splitters import RecursiveCharacterTextSplitter
    from langchain_chroma import Chroma
    from langchain_community.document_loaders import BSHTMLLoader
    from langchain_core.documents import Document
except ImportError as e:
    print(f"패키지 설치 필요: {e}")
    print("pip install langchain-voyageai langchain-community langchain-text-splitters chromadb beautifulsoup4")
    sys.exit(1)

# ───────────────────────────────────────────
# 벡터 DB 구축
# ───────────────────────────────────────────
def build_vectordb(html_folder: str):
    print(f"폴더: {html_folder}")

    html_files = []
    json_files = []
    for root, dirs, filenames in os.walk(html_folder):
        for fn in filenames:
            if fn.endswith(".html"):
                html_files.append(os.path.join(root, fn))
            elif fn.endswith(".json"):
                json_files.append(os.path.join(root, fn))

    if not html_files and not json_files:
        print("처리할 파일이 없습니다.")
        sys.exit(1)
    print(f"HTML 파일 {len(html_files)}개, JSON 파일 {len(json_files)}개 발견")

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP
    )
    all_chunks = []

    # HTML 파일 처리
    for filepath in html_files:
        try:
            loader = BSHTMLLoader(
                filepath,
                open_encoding="utf-8",
                bs_kwargs={"features": "html.parser"}
            )
            chunks = splitter.split_documents(loader.load())
            all_chunks.extend(chunks)
            print(f"  청킹 완료: {os.path.basename(filepath)} ({len(chunks)}개 청크)")
        except Exception as e:
            print(f"  건너뜀: {os.path.basename(filepath)} ({e})")

    # JSON 파일 처리 ({"filename":..., "text":..., "metadata":...} 리스트 형식)
    for filepath in json_files:
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                items = json.load(f)
            count = 0
            for item in items:
                text = item.get("text", "").strip()
                if not text:
                    continue
                doc = Document(
                    page_content=text,
                    metadata={"source": item.get("filename", os.path.basename(filepath))}
                )
                chunks = splitter.split_documents([doc])
                all_chunks.extend(chunks)
                count += len(chunks)
            print(f"  청킹 완료: {os.path.basename(filepath)} ({len(items)}개 항목 → {count}개 청크)")
        except Exception as e:
            print(f"  건너뜀: {os.path.basename(filepath)} ({e})")

    if not all_chunks:
        print("청킹 실패: 유효한 내용이 없습니다.")
        sys.exit(1)
    print(f"\n총 {len(all_chunks)}개 청크 생성")

    # 기존 DB 삭제 후 재구축
    if os.path.exists(CHROMA_DIR):
        shutil.rmtree(CHROMA_DIR)
        print("기존 ChromaDB 삭제")

    embeddings = VoyageAIEmbeddings(
        voyage_api_key=VOYAGE_API_KEY,
        model="voyage-3-lite"
    )

    print(f"\n임베딩 시작 (배치 {BATCH_SIZE}개씩)...")
    db = None
    for i in range(0, len(all_chunks), BATCH_SIZE):
        batch = all_chunks[i: i + BATCH_SIZE]
        if db is None:
            db = Chroma.from_documents(batch, embeddings, persist_directory=CHROMA_DIR)
        else:
            db.add_documents(batch)
        print(f"  [{i + len(batch)}/{len(all_chunks)}] 완료")

    print(f"\nChromaDB 저장 완료: {CHROMA_DIR}")

# ───────────────────────────────────────────
# 실행
# ───────────────────────────────────────────
if __name__ == "__main__":
    folder = sys.argv[1] if len(sys.argv) > 1 else HTML_BASE

    if not os.path.exists(folder):
        print(f"폴더를 찾을 수 없습니다: {folder}")
        print(f"사용법: python embed.py [폴더경로]  ← 생략 시 html_data/ 직접 사용")
        sys.exit(1)

    build_vectordb(folder)
