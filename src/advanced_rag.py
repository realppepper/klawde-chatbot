import os
import sys
import json
import shutil
import pickle
import tomllib
import voyageai
import logging
import traceback
from langchain_voyageai import VoyageAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_community.document_loaders import BSHTMLLoader
from langchain_community.retrievers import BM25Retriever
from langchain_core.documents import Document
from kiwipiepy import Kiwi

# ───────────────────────────────────────────
# 엔진 전용 로깅 시스템 세팅
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

try:
    with open(".streamlit/api.toml", "rb") as f:
        _secrets = tomllib.load(f)
    VOYAGE_API_KEY = _secrets["VOYAGE_API_KEY"]
except Exception as e:
    logger.critical(f"[Engine System] api.toml 파싱 에러: {str(e)}")
    VOYAGE_API_KEY = ""

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HTML_BASE = os.path.join(BASE_DIR, "data/html_data")
CHROMA_DIR = os.path.join(BASE_DIR, "data/chroma_db_html")
BM25_PKL_PATH = os.path.join(CHROMA_DIR, "bm25_docs.pkl")

MIN_CHAR_LIMIT = 100
PARENT_CHUNK_SIZE = 1500
PARENT_OVERLAP = 200
CHILD_CHUNK_SIZE = 300
CHILD_OVERLAP = 50

logger.info("[Engine System] Kiwi 한국어 형태소 분석기 인스턴스를 초기화합니다...")
kiwi = Kiwi()

def korean_tokenizer(text):
    return [token.form for token in kiwi.tokenize(text) if token.tag.startswith("N")]

class AdvancedRAGEngine:
    def __init__(self, rebuild_mode=False):
        logger.info(f"[Engine Init] AdvancedRAGEngine 초기화 호출 (rebuild_mode={rebuild_mode})")
        try:
            self.embeddings = VoyageAIEmbeddings(
                voyage_api_key=VOYAGE_API_KEY,
                model="voyage-3-lite"
            )
            self.voyage_client = voyageai.Client(api_key=VOYAGE_API_KEY)
            self.vector_db = None
            self.bm25_retriever = None

            if not rebuild_mode:
                if os.path.exists(CHROMA_DIR) and os.path.exists(BM25_PKL_PATH):
                    logger.info("[Engine Init] [구간 확인 1] Chroma 데이터베이스 연결 시도...")
                    self.vector_db = Chroma(persist_directory=CHROMA_DIR, embedding_function=self.embeddings)
                    logger.info("[Engine Init] [구간 통과 1] Chroma 데이터베이스 연결 성공.")
                    
                    logger.info("[Engine Init] [구간 확인 2] 사전 빌드된 BM25 인덱스 역직렬화(Pickle Load) 시도...")
                    with open(BM25_PKL_PATH, "rb") as f:
                        self.bm25_retriever = pickle.load(f)
                    
                    self.bm25_retriever.preprocess_func = korean_tokenizer
                    logger.info("[Engine Init] [구간 통과 2] BM25 사전 빌드 인덱스 적재 완료 (CPU 병목 원천 차단).")
                else:
                    logger.warning("[Engine Init] 인덱싱 데이터 파일 세트가 유실되었습니다. 선행 빌드가 요구됩니다.")
                    
        except Exception as e:
            logger.critical(f"[Engine Init 치명적 에러] {str(e)}\n{traceback.format_exc()}")
            raise e

    def build_index(self, folder_path=HTML_BASE, skip_chroma=False):
        logger.info(f"[Engine Build] 인덱스 빌드 가동 (skip_chroma={skip_chroma})")
        try:
            html_files = []
            json_files = []
            for root, _, filenames in os.walk(folder_path):
                for fn in filenames:
                    if fn.endswith(".html"):
                        html_files.append(os.path.join(root, fn))
                    elif fn.endswith(".json"):
                        json_files.append(os.path.join(root, fn))

            raw_documents = []
            for filepath in html_files:
                try:
                    loader = BSHTMLLoader(filepath, open_encoding="utf-8", bs_kwargs={"features": "html.parser"})
                    for d in loader.load():
                        d.metadata["source"] = os.path.basename(filepath)
                        raw_documents.append(d)
                except Exception as e:
                    pass

            for filepath in json_files:
                try:
                    with open(filepath, "r", encoding="utf-8") as f:
                        for item in json.load(f):
                            text = item.get("text", "").strip()
                            if text:
                                raw_documents.append(Document(page_content=text, metadata={"source": item.get("filename", os.path.basename(filepath))}))
                except Exception as e:
                    pass

            valid_documents = [d for d in raw_documents if len(d.page_content.strip()) >= MIN_CHAR_LIMIT]

            parent_splitter = RecursiveCharacterTextSplitter(chunk_size=PARENT_CHUNK_SIZE, chunk_overlap=PARENT_OVERLAP)
            child_splitter = RecursiveCharacterTextSplitter(chunk_size=CHILD_CHUNK_SIZE, chunk_overlap=CHILD_OVERLAP)

            all_child_chunks = []
            for doc_idx, doc in enumerate(valid_documents):
                source_name = doc.metadata.get("source", "Unknown")
                for p_idx, p_doc in enumerate(parent_splitter.split_documents([doc])):
                    parent_id = f"doc_{doc_idx}_p_{p_idx}"
                    for c_doc in child_splitter.split_documents([p_doc]):
                        c_doc.metadata.update({"parent_id": parent_id, "parent_text": p_doc.page_content, "source": source_name})
                        all_child_chunks.append(c_doc)

            if not skip_chroma:
                if os.path.exists(CHROMA_DIR):
                    shutil.rmtree(CHROMA_DIR)
                os.makedirs(CHROMA_DIR, exist_ok=True)
                db = None
                for i in range(0, len(all_child_chunks), 30):
                    batch = all_child_chunks[i: i + 30]
                    if db is None:
                        db = Chroma.from_documents(batch, self.embeddings, persist_directory=CHROMA_DIR)
                    else:
                        db.add_documents(batch)
            
            os.makedirs(CHROMA_DIR, exist_ok=True)
            
            logger.info("[Engine Build] 사전 빌드용 BM25Retriever 형태소 토크나이징 시작 (수 분 소요 예정)...")
            bm25_retriever = BM25Retriever.from_documents(all_child_chunks, preprocess_func=korean_tokenizer)
            
            bm25_retriever.preprocess_func = None 
            
            with open(BM25_PKL_PATH, "wb") as f:
                pickle.dump(bm25_retriever, f)
                
            logger.info(f"[Engine Build] 백업 파일 최종 드랍 성공: {BM25_PKL_PATH}")
        except Exception as e:
            logger.error(f"[Engine Build 에러] {str(e)}\n{traceback.format_exc()}")
            raise e

    def hybrid_search(self, query, top_n=4):
        logger.info(f"[Engine Search] 런타임 하이브리드 서치 기동 -> 쿼리: '{query}'")
        if not self.vector_db or not self.bm25_retriever:
            return "엔진 상태가 비정상입니다.", []

        try:
            self.bm25_retriever.k = 20
            vector_results = self.vector_db.similarity_search(query, k=20)
            bm25_results = self.bm25_retriever.invoke(query)

            unique_chunks_dict = {c.metadata.get("parent_id", "none") + "_" + c.page_content: c for c in (vector_results + bm25_results)}
            unique_chunks = list(unique_chunks_dict.values())
            documents_texts = [c.page_content for c in unique_chunks]

            # [핵심 교정] 지원되지 않는 'voyage-rerank-2' 모델명을 공식 규격인 'rerank-2'로 변경
            try:
                rerank_results = self.voyage_client.rerank(
                    query=query, 
                    documents=documents_texts, 
                    model="rerank-2", 
                    top_k=min(top_n * 3, len(documents_texts))
                )
                
                # 정상 정렬된 인덱스 바인딩 순회
                fused_parent_contexts = []
                retrieved_sources = set()
                seen_parent_ids = set()

                for result in rerank_results.results:
                    target_chunk = unique_chunks[result.index]
                    if (p_id := target_chunk.metadata.get("parent_id")) not in seen_parent_ids:
                        seen_parent_ids.add(p_id)
                        fused_parent_contexts.append(target_chunk.metadata.get("parent_text"))
                        if src := target_chunk.metadata.get("source"): retrieved_sources.add(src)
                    if len(fused_parent_contexts) >= top_n: break
                    
            except Exception as rerank_err:
                # [안전 장치] Voyage API 호출간 한도 초과나 기타 네트워크 에러 발생 시, 검색이 통째로 폭파되지 않고 1차 검색 랭킹순으로 안정적으로 폴백되도록 보호
                logger.error(f"[Rerank API Warning] 리랭킹 연산 실패 (1차 매칭 순으로 폴백 수행): {str(rerank_err)}")
                fused_parent_contexts = []
                retrieved_sources = set()
                seen_parent_ids = set()
                
                for target_chunk in unique_chunks:
                    if (p_id := target_chunk.metadata.get("parent_id")) not in seen_parent_ids:
                        seen_parent_ids.add(p_id)
                        fused_parent_contexts.append(target_chunk.metadata.get("parent_text"))
                        if src := target_chunk.metadata.get("source"): retrieved_sources.add(src)
                    if len(fused_parent_contexts) >= top_n: break

            return "\n\n[참조 섹션 단락]\n" + "\n\n".join(fused_parent_contexts), list(retrieved_sources)
        except Exception as e:
            logger.error(f"[Engine Search 에러 발생] {str(e)}\n{traceback.format_exc()}")
            return "지식 매칭 연산 도중 에러가 발생했습니다.", []

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "build":
        AdvancedRAGEngine(rebuild_mode=True).build_index(skip_chroma=False)
    elif len(sys.argv) > 1 and sys.argv[1] == "build_bm25":
        AdvancedRAGEngine(rebuild_mode=True).build_index(skip_chroma=True)