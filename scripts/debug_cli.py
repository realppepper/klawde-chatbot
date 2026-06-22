# scripts/debug_cli.py
import os
import sys
import json
import time
import uuid
import logging
from datetime import datetime

# src 폴더의 모듈을 임포트하기 위한 경로 설정
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'src'))

try:
    from advanced_rag import AdvancedRAGEngine, korean_tokenizer
    import rag_worker as rw
except ImportError:
    # 모듈 의존성 결여 상황 대비 폴백 플레이스홀더 구성
    class AdvancedRAGEngine:
        def __init__(self, rebuild_mode=False):
            self.vector_db = self
            self.bm25_retriever = self
            self.voyage_client = self
        def invoke(self, q): return []
        def similarity_search(self, q, k): return []
        def rerank(self, query, documents, model, top_k):
            class Res:
                def __init__(self): self.results = []
            return Res()
    class rw:
        API_KEY = "MOCK_KEY"
        @staticmethod
        def rewrite_query(q, h, b, hd): return q
        @staticmethod
        def robust_request_post(*args, **kwargs):
            class Resp:
                def raise_for_status(self): pass
                def json(self): return {"candidates": [{"content": {"parts": [{"text": "Mock Response"}]}}]}
            return Resp()

# 로그 전용 디렉토리 생성 안정성 확보
os.makedirs("logs", exist_ok=True)

# 1. 파일 통합 분석 로그 설정
logger = logging.getLogger("KlawdeLogger")
logger.setLevel(logging.INFO)
if not logger.handlers:
    fh = logging.FileHandler("logs/klawde_debug.log", encoding="utf-8")
    formatter = logging.Formatter('[%(asctime)s] %(levelname)s: %(message)s')
    fh.setFormatter(formatter)
    logger.addHandler(fh)

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def save_raw_documents_to_file(query_text, mode_name, bm25_docs, vector_docs):
    """
    수집한 모든 문서들의 원문 전체를 생략 없이 별도의 고유 텍스트 파일로 완벽하게 기록 저장합니다.
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    # 파일명으로 사용할 수 있는 안전한 문자열 처리
    safe_query = "".join([c for c in query_text if c.isalnum() or c in (' ', '_', '-')]).strip()[:30]
    safe_query = safe_query.replace(' ', '_')
    if not safe_query:
        safe_query = "empty_query"
        
    filename = f"logs/retrieved_docs_{timestamp}_{safe_query}.txt"
    
    with open(filename, "w", encoding="utf-8") as f:
        f.write("==================================================================\n")
        f.write(f"📄 수집 문서 원문 백업 로그 (Mode: {mode_name})\n")
        f.write(f"📅 일시: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"🔍 입력/검색 질의어: {query_text}\n")
        f.write("==================================================================\n\n")
        
        f.write(f"■ [1] BM25 (Sparse) 검색 수집 문서 (총 {len(bm25_docs)}개)\n")
        f.write("-" * 70 + "\n")
        for idx, doc in enumerate(bm25_docs, 1):
            src = doc.metadata.get("source", "Unknown")
            p_id = doc.metadata.get("parent_id", "Unknown")
            f.write(f"[{idx:02d}] 출처: {src} | Parent ID: {p_id}\n")
            f.write(f"[메타데이터 전체]: {json.dumps(doc.metadata, ensure_ascii=False)}\n")
            f.write("-" * 40 + "\n")
            f.write("[원문 본문 내용]\n")
            f.write(doc.page_content)
            f.write("\n" + "=" * 50 + "\n\n")
            
        f.write(f"■ [2] Vector DB (Dense) 검색 수집 문서 (총 {len(vector_docs)}개)\n")
        f.write("-" * 70 + "\n")
        for idx, doc in enumerate(vector_docs, 1):
            src = doc.metadata.get("source", "Unknown")
            p_id = doc.metadata.get("parent_id", "Unknown")
            f.write(f"[{idx:02d}] 출처: {src} | Parent ID: {p_id}\n")
            f.write(f"[메타데이터 전체]: {json.dumps(doc.metadata, ensure_ascii=False)}\n")
            f.write("-" * 40 + "\n")
            f.write("[원문 본문 내용]\n")
            f.write(doc.page_content)
            f.write("\n" + "=" * 50 + "\n\n")
            
    return filename

def main():
    clear_screen()
    print("==================================================================")
    print("🤖 KlaWde Headless CLI Debugger v2.1 (원문 무생략 완전 저장 모드)")
    print("==================================================================\n")
    
    print("⏳ [System] RAG 엔진 및 의존성 모듈을 로딩하고 있습니다...")
    start = time.time()
    try:
        engine = AdvancedRAGEngine(rebuild_mode=False)
        print(f"✅ [System] 엔진 로딩 완료 (소요시간: {time.time() - start:.2f}초)\n")
    except Exception as e:
        print(f"❌ [System Error] 엔진 로딩 실패: {e}")
        return

    chat_history = []
    
    while True:
        print("-" * 70)
        query = input("🧑‍💻 질문을 입력하세요 (종료: 'q', 검색전용모드: 's'): ").strip()
        
        if not query:
            continue
            
        if query.lower() == 'q':
            print("디버거를 종료합니다.")
            break
            
        # ----------------------------------------------------------------
        # [s] 검색 전용 모드 (LLM 호출 없이 검색 및 리랭킹 파이프라인만 정밀 추적)
        # ----------------------------------------------------------------
        if query.lower() == 's':
            test_query = input("🔍 검색 프로세스를 정밀 추적할 키워드/문장을 입력하세요: ").strip()
            if not test_query:
                continue
                
            print("\n⏳ [Retrieval Pipeline] 하이브리드 검색 및 리랭킹을 수행 중...")
            
            if not engine.vector_db or not engine.bm25_retriever:
                print("❌ [Engine Error] 엔진 상태가 비정상입니다. 사전 빌드를 확인하세요.")
                continue
                
            try:
                # 1) Sparse (BM25) 검색 수행
                engine.bm25_retriever.k = 20
                bm25_results = engine.bm25_retriever.invoke(test_query)
                
                # 2) Dense (Vector DB) 검색 수행
                vector_results = engine.vector_db.similarity_search(test_query, k=20)
                
                # 3) 요구사항: 원문 생략 없이 전체 텍스트 파일로 완벽 저장
                backup_file = save_raw_documents_to_file(test_query, "Search_Only", bm25_results, vector_results)
                print(f"💾 [원문 저장 완료] 수집된 {len(bm25_results) + len(vector_results)}개 문서의 무생략 본문이 다음 파일에 저장되었습니다:\n    👉 {backup_file}")
                
                logger.info(f"[CLI Debug - Search Only] Query: '{test_query}'")
                logger.info(f"[Sparse Match] BM25 수집 청크 수: {len(bm25_results)}")
                logger.info(f"[Dense Match] Vector DB 수집 청크 수: {len(vector_results)}")
                logger.info(f"[Raw Content Backup] File written to {backup_file}")
                
                print(f"\n📊 [1차 검색 결과 요약] BM25: {len(bm25_results)}개 / Vector: {len(vector_results)}개")
                
                print("\n--- 1. BM25 수집 문서 목록 (화면 출력용 요약) ---")
                for idx, doc in enumerate(bm25_results, 1):
                    src = doc.metadata.get("source", "Unknown")
                    p_id = doc.metadata.get("parent_id", "Unknown")
                    snippet = doc.page_content[:60].replace('\n', ' ')
                    print(f" [{idx:02d}] 출처: {src} | ParentID: {p_id} | 요약: {snippet}...")
                    logger.info(f"[Sparse Doc {idx}] Src: {src}, PID: {p_id}, Snippet: {snippet}")
                    
                print("\n--- 2. Vector DB 수집 문서 목록 (화면 출력용 요약) ---")
                for idx, doc in enumerate(vector_results, 1):
                    src = doc.metadata.get("source", "Unknown")
                    p_id = doc.metadata.get("parent_id", "Unknown")
                    snippet = doc.page_content[:60].replace('\n', ' ')
                    print(f" [{idx:02d}] 출처: {src} | ParentID: {p_id} | 요약: {snippet}...")
                    logger.info(f"[Dense Doc {idx}] Src: {src}, PID: {p_id}, Snippet: {snippet}")

                # 중복 제거 및 리랭킹 대상 설정
                unique_chunks_dict = {}
                for c in (vector_results + bm25_results):
                    key = c.metadata.get("parent_id", "none") + "_" + c.page_content
                    unique_chunks_dict[key] = c
                unique_chunks = list(unique_chunks_dict.values())
                documents_texts = [c.page_content for c in unique_chunks]
                
                print(f"\n🔄 [중복 제거 완료] 총 {len(unique_chunks)}개의 고유 청크 대상 VoyageAI 리랭킹 진입...")
                
                # 4) VoyageAI Rerank 수행
                rerank_results = engine.voyage_client.rerank(
                    query=test_query, 
                    documents=documents_texts, 
                    model="rerank-2", 
                    top_k=min(12, len(documents_texts))
                )
                
                print("\n--- 3. VoyageAI 리랭킹 최종 순위 및 메타데이터 ---")
                logger.info(f"[Rerank Stage] 리랭킹 분석 시작 (총 후보 청크: {len(documents_texts)})")
                
                for r_idx, result in enumerate(rerank_results.results, 1):
                    target_chunk = unique_chunks[result.index]
                    src = target_chunk.metadata.get("source", "Unknown")
                    p_id = target_chunk.metadata.get("parent_id", "Unknown")
                    score = result.relevance_score
                    snippet = target_chunk.page_content[:70].replace('\n', ' ')
                    meta_json = json.dumps(target_chunk.metadata, ensure_ascii=False)
                    
                    # 터미널 출력
                    print(f" 🏆 순위 {r_idx:02d} | Score: {score:.4f} | 출처: {src} | PID: {p_id}")
                    print(f"    ├ 청크 요약: {snippet}...")
                    
                    # 로그 파일 기록 (모든 메타데이터 포함)
                    logger.info(f"[Rerank Rank {r_idx}] Score: {score:.4f}, Src: {src}, PID: {p_id}, Meta: {meta_json}")
                    
            except Exception as err:
                print(f"❌ [Search Error] 검색/리랭킹 추적 중 오류 발생: {err}")
                logger.error(f"[Search Error] {str(err)}")
            continue
            
        # ----------------------------------------------------------------
        # 전체 파이프라인 모드 (Query Rewrite -> 정밀 검색 기록 -> LLM 최종 답변)
        # ----------------------------------------------------------------
        print("\n⏳ [Pipeline] 전체 RAG 워커 파이프라인(Query Rewrite 포함) 가동 중...")
        p_time = time.time()
        
        GEMINI_BASE = "https://generativelanguage.googleapis.com/v1beta/models"
        HEADERS = {"x-goog-api-key": rw.API_KEY, "Content-Type": "application/json"}
        
        try:
            # 1) Query Rewrite 단계 수행 및 로그 기록
            print(" 🔄 [Step 1] 대화 히스토리 기반 Query Rewrite 분석 중...")
            logger.info(f"[Pipeline Start] User Raw Input: '{query}'")
            
            if chat_history:
                logger.info(f"[Query Rewrite Context] 현재 저장된 대화방 히스토리 메모리 수: {len(chat_history)}개")
                
            optimized_query = rw.rewrite_query(query, chat_history, GEMINI_BASE, HEADERS)
            
            print(f"    ➡️  정제된 검색 쿼리: '{optimized_query}'")
            logger.info(f"[Query Rewrite Output] '{query}' -> 변환 완료 -> '{optimized_query}'")
            
            # 2) 하이브리드 매칭 및 개별 소스 수집
            print(" 🔍 [Step 2] 하이브리드 검색엔진 가동 (BM25 + Vector DB)...")
            engine.bm25_retriever.k = 20
            bm25_res = engine.bm25_retriever.invoke(optimized_query)
            vector_res = engine.vector_db.similarity_search(optimized_query, k=20)
            
            # 요구사항: 파이프라인 대화 모드에서도 수집한 문서를 생략 없이 별도 텍스트 파일로 완벽 저장
            backup_file = save_raw_documents_to_file(optimized_query, "Pipeline_Full", bm25_res, vector_res)
            logger.info(f"[Pipeline Raw Content Backup] File written to {backup_file}")
            print(f"    💾 [수집 원문 완전 백업 완료] -> {backup_file}")
            
            logger.info(f"[Pipeline Search Log] BM25 수집 문서 수: {len(bm25_res)}")
            logger.info(f"[Pipeline Vector Log] Vector DB 수집 문서 수: {len(vector_res)}")
                
            # 3) 리랭킹 순위 매핑 및 최종 메타데이터 보관
            unique_chunks_dict = {}
            for c in (vector_res + bm25_res):
                key = c.metadata.get("parent_id", "none") + "_" + c.page_content
                unique_chunks_dict[key] = c
            unique_chunks = list(unique_chunks_dict.values())
            documents_texts = [c.page_content for c in unique_chunks]
            
            rerank_results = engine.voyage_client.rerank(
                query=optimized_query, documents=documents_texts, model="rerank-2", top_k=min(4, len(documents_texts))
            )
            
            fused_parent_contexts = []
            retrieved_sources = set()
            seen_parent_ids = set()

            logger.info(f"[Pipeline Rerank Result] 최종 채택된 TOP 청크 랭킹 및 메타데이터:")
            for r_idx, result in enumerate(rerank_results.results, 1):
                target_chunk = unique_chunks[result.index]
                p_id = target_chunk.metadata.get("parent_id")
                src = target_chunk.metadata.get("source", "Unknown")
                meta_json = json.dumps(target_chunk.metadata, ensure_ascii=False)
                
                logger.info(f"  - 순위 {r_idx} | Score: {result.relevance_score:.4f} | Source: {src} | ParentID: {p_id} | Meta: {meta_json}")
                
                if p_id not in seen_parent_ids:
                    seen_parent_ids.add(p_id)
                    fused_parent_contexts.append(target_chunk.metadata.get("parent_text"))
                    if src: 
                        retrieved_sources.add(src)

            context_str = "\n\n[참조 섹션 단락]\n" + "\n\n".join(fused_parent_contexts)
            
            # 4) LLM 생성 요청 송신
            print(" 🧠 [Step 3] Gemini 3.1 Flash Lite 융합 답변 생성 중...")
            history_str = "\n".join([f"- {msg['role'].upper()}: {msg['content']}" for msg in chat_history]) if chat_history else "이전 대화 기록이 없음."
            
            full_prompt = (
                "당신은 광운대학교 학사안내 전문 AI 비서 KlaWde입니다.\n"
                "제공된 [참조 컨텍스트 지식 스토어]의 내용과 이전에 나눈 [이전 대화 메모리 기록]을 함께 참고하여 대화의 맥락에 맞는 답변을 완성하세요.\n\n"
                f"[이전 대화 메모리 기록]:\n{history_str}\n\n"
                f"[참조 컨텍스트 지식 스토어]:\n{context_str}\n\n"
                f"[사용자 질의 요구사항]: {query}"
            )
            
            payload = {
                "contents": [{"role": "user", "parts": [{"text": full_prompt}]}],
                "generationConfig": {"temperature": 0.2}
            }
            
            response = rw.robust_request_post(f"{GEMINI_BASE}/gemini-3.1-flash-lite:generateContent", headers=HEADERS, json_data=payload, timeout=60)
            response.raise_for_status()
            answer = response.json()["candidates"][0]["content"]["parts"][0]["text"]

            if retrieved_sources:
                answer += "\n\n📎 **KlaWde RAG 분석 기반 시스템 참조 출처**\n" + "\n".join(f"- {s}" for s in retrieved_sources)
                
            print(f"✅ [Pipeline] 생성 완료 (소요시간: {time.time() - p_time:.2f}초)\n")
            print("🤖 [KlaWde 답변]")
            print(answer)
            print()
            
            # 기록 누적
            chat_history.append({"role": "user", "content": query})
            chat_history.append({"role": "assistant", "content": answer})
            if len(chat_history) > 10:
                chat_history = chat_history[-10:]
                
        except Exception as e:
            print(f"\n❌ [Critical Error] 예외 발생: {e}")
            logger.error(f"[Critical Pipeline Error] {str(e)}")

if __name__ == "__main__":
    main()