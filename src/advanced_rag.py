import os
import sys
import json
import shutil
import pickle
import tomllib
from langchain_voyageai import VoyageAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_community.document_loaders import BSHTMLLoader
from langchain_community.retrievers import BM25Retriever
from langchain_core.documents import Document

# ───────────────────────────────────────────
# [기본 설정 변수] 통계적 분포 기반 커스텀 세팅
# ───────────────────────────────────────────
with open(".streamlit/api.toml", "rb") as f:
    _secrets = tomllib.load(f)
VOYAGE_API_KEY = _secrets["VOYAGE_API_KEY"]

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

HTML_BASE = os.path.join(BASE_DIR, "data/html_data")
CHROMA_DIR = os.path.join(BASE_DIR, "data/chroma_db_html")
BM25_PKL_PATH = os.path.join(CHROMA_DIR, "bm25_docs.pkl")

# 최적화 임계치 세팅
MIN_CHAR_LIMIT = 100       # ① 아웃라이어 필터링: 100자 이하 노이즈 문서 제거
PARENT_CHUNK_SIZE = 1500   # ③ Parent 윈도우 컨텍스트 크기
PARENT_OVERLAP = 200
CHILD_CHUNK_SIZE = 300     # ③ Child 정밀 검색 청크 크기
CHILD_OVERLAP = 50


class AdvancedRAGEngine:
    def __init__(self, rebuild_mode=False):
        """
        RAG 엔진 초기화
        - 검색 모드일 때 Chroma DB와 로컬 빌드된 BM25 객체를 연동합니다.
        """
        self.embeddings = VoyageAIEmbeddings(
            voyage_api_key=VOYAGE_API_KEY,
            model="voyage-3-lite"
        )
        if not rebuild_mode:
            # 검색 엔진 모드로 로드
            if os.path.exists(CHROMA_DIR) and os.path.exists(BM25_PKL_PATH):
                self.vector_db = Chroma(persist_directory=CHROMA_DIR, embedding_function=self.embeddings)
                with open(BM25_PKL_PATH, "rb") as f:
                    self.child_documents = pickle.load(f)
                self.bm25_retriever = BM25Retriever.from_documents(self.child_documents)
                print("[Engine] 하이브리드 Parent-Child RAG 엔진 로드 완료.")
            else:
                self.vector_db = None
                self.bm25_retriever = None
                print("[Warning] 색인 데이터가 존재하지 않습니다. 먼저 빌드를 수행하세요.")

    def build_index(self, folder_path=HTML_BASE):
        """
        데이터 수집 및 복합 데이터베이스 인덱싱 (기존 embed.py 대체)
        """
        print(f"--- [1단계] 데이터 수집 및 ① 아웃라이어 필터링 검증 시작 ---")
        html_files = []
        json_files = []
        for root, _, filenames in os.walk(folder_path):
            for fn in filenames:
                if fn.endswith(".html"):
                    html_files.append(os.path.join(root, fn))
                elif fn.endswith(".json"):
                    json_files.append(os.path.join(root, fn))

        raw_documents = []

        # HTML 가공
        for filepath in html_files:
            try:
                loader = BSHTMLLoader(filepath, open_encoding="utf-8", bs_kwargs={"features": "html.parser"})
                docs = loader.load()
                for d in docs:
                    d.metadata["source"] = os.path.basename(filepath)
                    raw_documents.append(d)
            except Exception as e:
                print(f"  HTML 로드 건너뜀: {os.path.basename(filepath)} ({e})")

        # 첨부파일 JSON 가공
        for filepath in json_files:
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    items = json.load(f)
                for item in items:
                    text = item.get("text", "").strip()
                    if text:
                        doc = Document(
                            page_content=text,
                            metadata={"source": item.get("filename", os.path.basename(filepath))}
                        )
                        raw_documents.append(doc)
            except Exception as e:
                print(f"  JSON 로드 건너뜀: {os.path.basename(filepath)} ({e})")

        print(f"필터링 전 총 문서 후보군: {len(raw_documents)}개")

        # ① 아웃라이어 필터링 적용
        valid_documents = []
        for d in raw_documents:
            if len(d.page_content.strip()) >= MIN_CHAR_LIMIT:
                valid_documents.append(d)
            else:
                print(f"  [필터 탈락] {len(d.page_content.strip())}자 노이즈 문서 제외 -> 출처: {d.metadata['source']}")

        print(f"① 필터링 통과 유효 지식 문서군: {len(valid_documents)}개")

        print(f"\n--- [2단계] ③ Parent-Child 트리 구조 윈도우 청킹 가공 ---")
        parent_splitter = RecursiveCharacterTextSplitter(chunk_size=PARENT_CHUNK_SIZE, chunk_overlap=PARENT_OVERLAP)
        child_splitter = RecursiveCharacterTextSplitter(chunk_size=CHILD_CHUNK_SIZE, chunk_overlap=CHILD_OVERLAP)

        all_child_chunks = []
        
        for doc_idx, doc in enumerate(valid_documents):
            source_name = doc.metadata.get("source", "Unknown")
            # 가이드라인에 따른 대형 문서 솔루션: 대형 문서를 상위 윈도우(Parent)로 1차 분할
            parents = parent_splitter.split_documents([doc])
            
            for p_idx, p_doc in enumerate(parents):
                parent_id = f"doc_{doc_idx}_p_{p_idx}"
                parent_text = p_doc.page_content
                
                # 상위 윈도우 컨텍스트 내부에서 정밀 검색용 Child 조각 분할
                children = child_splitter.split_documents([p_doc])
                for c_idx, c_doc in enumerate(children):
                    # 상위 텍스트와 ID를 메타데이터에 주입 (Stateless 완전 무결성 확보)
                    c_doc.metadata["parent_id"] = parent_id
                    c_doc.metadata["parent_text"] = parent_text
                    c_doc.metadata["source"] = source_name
                    all_child_chunks.append(c_doc)

        print(f"최종 생성된 정밀 Child 청크 수: {len(all_child_chunks)}개")

        # 기존 DB 초기화
        if os.path.exists(CHROMA_DIR):
            shutil.rmtree(CHROMA_DIR)
        os.makedirs(CHROMA_DIR, exist_ok=True)

        print(f"\n--- [3단계] 복합 인덱스(Vector DB + BM25 Serializer) 스토리지 빌드 ---")
        # 1. Vector DB 구축 (배치단위 인덱싱)
        batch_size = 30
        db = None
        for i in range(0, len(all_child_chunks), batch_size):
            batch = all_child_chunks[i: i + batch_size]
            if db is None:
                db = Chroma.from_documents(batch, self.embeddings, persist_directory=CHROMA_DIR)
            else:
                db.add_documents(batch)
            print(f"  Dense 임베딩 진행률: [{i + len(batch)}/{len(all_child_chunks)}]")

        # 2. ② BM25 직렬화 아티팩트 저장 (GCP Cloud Run 메모리 인스턴스 대응용)
        with open(BM25_PKL_PATH, "wb") as f:
            pickle.dump(all_child_chunks, f)
        print(f"  Sparse 키워드 데이터셋 백업 저장 완료 -> {BM25_PKL_PATH}")
        print("인덱싱 자동화 빌드 파이프라인이 정상 종료되었습니다.")

    def hybrid_search(self, query, top_n=4, rrf_k=60):
        """
        ② 하이브리드 앙상블 검색 기능 (Reciprocal Rank Fusion 알고리즘 가동)
        """
        if not self.vector_db or not self.bm25_retriever:
            return "엔진이 초기화되지 않았거나 색인 파일이 유실되었습니다.", []

        # 후보군 수집 범위 확장 (앙상블 매칭을 위해 각 모델당 20개 노출)
        candidate_pool_size = 20
        self.bm25_retriever.k = candidate_pool_size

        # 1. Dense Vector 검색 결과 도출
        vector_results = self.vector_db.similarity_search(query, k=candidate_pool_size)
        # 2. Sparse Keyword (BM25) 검색 결과 도출
        bm25_results = self.bm25_retriever.invoke(query)

        # 3. Reciprocal Rank Fusion (RRF) 스코어 연산
        rrf_scores = {}
        chunk_registry = {}

        def compute_rrf(search_results):
            for rank, chunk in enumerate(search_results):
                # Child 텍스트 고유 식별자 키 맵핑
                chunk_key = chunk.metadata.get("parent_id", "none") + "_" + chunk.page_content
                if chunk_key not in rrf_scores:
                    rrf_scores[chunk_key] = 0.0
                    chunk_registry[chunk_key] = chunk
                # RRF 수학 공식 대입: 1 / (k + rank)
                rrf_scores[chunk_key] += 1.0 / (rrf_k + (rank + 1))

        compute_rrf(vector_results)
        compute_rrf(bm25_results)

        # RRF 스코어 기준 내림차순 정렬
        sorted_keys = sorted(rrf_scores.keys(), key=lambda x: rrf_scores[x], reverse=True)

        # 4. ③ Parent 컨텍스트 복원 및 중복 제어(Deduplication)
        fused_parent_contexts = []
        retrieved_sources = set()
        seen_parent_ids = set()

        for key in sorted_keys:
            target_chunk = chunk_registry[key]
            p_id = target_chunk.metadata.get("parent_id")
            p_text = target_chunk.metadata.get("parent_text")
            src = target_chunk.metadata.get("source", "Unknown")

            if p_id not in seen_parent_ids:
                seen_parent_ids.add(p_id)
                fused_parent_contexts.append(p_text)
                if src:
                    retrieved_sources.add(src)

            # LLM에게 전달할 최적 상위 컨텍스트 개수에 도달하면 브레이크
            if len(fused_parent_contexts) >= top_n:
                break

        # 완성된 대형 컨텍스트 조인 및 출처 반환
        final_context = "\n\n[참조 섹션 단락]\n" + "\n\n".join(fused_parent_contexts)
        return final_context, list(retrieved_sources)


if __name__ == "__main__":
    # CLI 단축 명령 파싱 (터미널에서 "python advanced_rag.py build" 실행 시 인덱싱 가동)
    if len(sys.argv) > 1 and sys.argv[1] == "build":
        engine = AdvancedRAGEngine(rebuild_mode=True)
        engine.build_index()
    else:
        # 단독 테스트 검증용 내부 코드
        engine = AdvancedRAGEngine(rebuild_mode=False)
        if engine.vector_db:
            ctx, sources = engine.hybrid_search("장학금 신청 기간과 필수 제출 서류는 무엇인가요?")
            print("\n[테스트 검색 결과 컨텍스트 출력]")
            print(ctx[:500] + "...")
            print("탐색된 출처 문서군:", sources)