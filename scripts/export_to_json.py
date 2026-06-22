import chromadb
import pickle
import json
import os

# 환경 경로 설정
CHROMA_DB_PATH = "/app/data/chroma_db_html"
BM25_PKL_PATH = "/app/data/chroma_db_html/bm25_docs.pkl"
OUTPUT_JSON_PATH = "/app/exported_rag_data.json"

def export_rag_data_to_json():
    print("==================================================")
    print("📦 KlaWde RAG 시스템 데이터 JSON 추출 시작")
    print("==================================================")
    
    exported_data = {
        "metadata": {
            "description": "KlaWde ChromaDB 및 BM25 인덱스 데이터 익스포트",
            "extracted_at": os.popen("date").read().strip()
        },
        "chroma_collections": {},
        "bm25_index": []
    }
    
    # --------------------------------------------------
    # 1. ChromaDB 컬렉션 데이터 추출 (Batch 처리 반영)
    # --------------------------------------------------
    if os.path.exists(CHROMA_DB_PATH):
        try:
            client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
            collections = client.list_collections()
            
            for col in collections:
                print(f"▶ [ChromaDB] '{col.name}' 컬렉션 데이터 추출 중...")
                col_data_list = []
                offset = 0
                batch_size = 500
                
                while True:
                    data = col.get(limit=batch_size, offset=offset, include=["documents", "metadatas"])
                    if not data['ids']:
                        break
                    
                    for doc_id, doc_text, meta in zip(data['ids'], data['documents'], data['metadatas']):
                        col_data_list.append({
                            "chunk_id": doc_id,
                            "source_file": meta.get("source", "Unknown"),
                            "parent_id": meta.get("parent_id", "Unknown"),
                            "child_content": doc_text,
                            "parent_content": meta.get("parent_text", "")
                        })
                    offset += batch_size
                
                exported_data["chroma_collections"][col.name] = col_data_list
                print(f"   └ 완료: {len(col_data_list)}개 자식 청크 확보")
        except Exception as e:
            print(f"❌ [ChromaDB 에러] 데이터를 추출하지 못했습니다: {e}")
    else:
        print("⚠️ [ChromaDB] 지정된 경로에 데이터베이스 폴더가 존재하지 않습니다.")

    # --------------------------------------------------
    # 2. BM25 피클 파일 데이터 추출
    # --------------------------------------------------
    if os.path.exists(BM25_PKL_PATH):
        print(f"▶ [BM25] '{BM25_PKL_PATH}' 역직렬화 및 데이터 파싱 중...")
        try:
            with open(BM25_PKL_PATH, "rb") as f:
                bm25_retriever = pickle.load(f)
            
            # BM25Retriever가 들고 있는 LangChain Document 객체 풀 순회
            # 런타임에 빌드된 문서 조각 리스트(docs)에 접근합니다.
            bm25_docs = getattr(bm25_retriever, "docs", [])
            
            for idx, doc in enumerate(bm25_docs):
                meta = doc.metadata if hasattr(doc, "metadata") else {}
                content = doc.page_content if hasattr(doc, "page_content") else str(doc)
                
                # 가독성을 위해 BM25 청크 구조 정리
                exported_data["bm25_index"].append({
                    "index": idx,
                    "source_file": meta.get("source", "Unknown"),
                    "parent_id": meta.get("parent_id", "Unknown"),
                    "chunk_content": content,
                    "parent_content": meta.get("parent_text", "")
                })
            print(f"   └ 완료: {len(exported_data['bm25_index'])}개 BM25 매칭 데이터 확보")
        except Exception as e:
            print(f"❌ [BM25 에러] 피클 파일을 로드하지 못했습니다: {e}")
    else:
        print("⚠️ [BM25] 지정된 경로에 bm25_docs.pkl 파일이 존재하지 않습니다.")

    # --------------------------------------------------
    # 3. JSON 파일로 저장 수행
    # --------------------------------------------------
    print("\n💾 통합 데이터 JSON 쓰기 작업 중...")
    try:
        with open(OUTPUT_JSON_PATH, "w", encoding="utf-8") as json_file:
            json.dump(exported_data, json_file, ensure_ascii=False, indent=4)
        print("==================================================")
        print(f"🎉 성공! RAG 통합 데이터가 JSON으로 저장되었습니다.")
        print(f"📂 저장 경로: {OUTPUT_JSON_PATH}")
        print("==================================================")
    except Exception as e:
        print(f"❌ [JSON 저장 에러] 파일 작성에 실패했습니다: {e}")

if __name__ == "__main__":
    export_rag_data_to_json()