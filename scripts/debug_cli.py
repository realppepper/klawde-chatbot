# scripts/debug_cli.py
import os
import sys
import json
import time
import uuid

# src 폴더의 모듈을 임포트하기 위한 경로 설정
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'src'))

from advanced_rag import AdvancedRAGEngine
import rag_worker as rw

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def save_txt_log(filepath, title, content):
    """디버깅 내역을 물리 텍스트 파일에 영속화 아카이브하는 헬퍼 함수"""
    timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
    with open(filepath, "a", encoding="utf-8") as f:
        f.write(f"\n{'='*30}\n[{timestamp}] {title}\n{'='*30}\n")
        f.write(content)
        f.write("\n")

def main():
    clear_screen()
    print("================================================================")
    print("🤖 KlaWde HyDE/HyQE + 하이브리드 지식 파이프라인 심층 디버거")
    print("================================================================")
    print("  [안내] 터미널에는 요약 메타데이터만 심플하게 노출되며,")
    print("  상세 문서 원문 및 랭킹 로그는 아래 3개 파일에 실시간 누적 저장됩니다:")
    print("   1) debug_hyde_hyqe_generation.txt")
    print("   2) debug_raw_retrieval_docs.txt")
    print("   3) debug_reranking_results.txt")
    print("================================================================\n")
    
    # RAG 코어 엔진 강제 로딩
    print("⏳ [System] Advanced RAG 지식 매칭 엔진을 메모리에 적재하고 있습니다...")
    start = time.time()
    try:
        engine = AdvancedRAGEngine(rebuild_mode=False)
        print(f"✅ [System] 검색 엔진 인스턴스 준비 완료 (소요시간: {time.time() - start:.2f}초)\n")
    except Exception as e:
        print(f"❌ [System Error] RAG 코어 로딩 치명적 실패: {e}")
        return

    chat_history = []
    
    while True:
        print("-" * 70)
        query = input("🧑‍💻 분석할 학사 질문을 입력하세요 (종료하려면 'q' 입력): ").strip()
        
        if not query:
            continue
            
        if query.lower() == 'q':
            print("통합 디버깅 도구를 종료합니다.")
            break
            
        print("\n⏳ [1단계: Generation] Gemini 최적화 창구 가동 -> HyDE / HyQE 연산 중...")
        GEMINI_BASE = "https://generativelanguage.googleapis.com/v1beta/models"
        HEADERS = {"x-goog-api-key": rw.API_KEY, "Content-Type": "application/json"}
        
        # HyDE, HyQE 동시 구조 추출
        optimized_data = rw.generate_hyde_hyqe(query, chat_history, GEMINI_BASE, HEADERS)
        hyqe_query = optimized_data["hyqe_query"]
        hyde_doc = optimized_data["hyde_document"]
        
        # 1단계 결과 파일 로그 저장
        hyde_hyqe_log = f"사용자 원본 질문: {query}\n[HyQE 최적화 쿼리]: {hyqe_query}\n[HyDE 가상 예측 답변 문서]:\n{hyde_doc}"
        save_txt_log("debug_hyde_hyqe_generation.txt", f"질문 ID: {query[:15]}...", hyde_hyqe_log)
        
        print("✅ [1단계 완료] HyDE 및 HyQE 소스 생성 완료. (텍스트 파일 백업 완료)")
        print(f"   👉 [HyQE 쿼리]: {hyqe_query}")
        print(f"   👉 [HyDE 문서 요약]: {hyde_doc[:60]}...")
        
        print("\n⏳ [2단계: Raw Retrieval] 듀얼 채널(Chroma & BM25) 원시 지식 수집 엔진 구동 중...")
        
        # 디버깅 정밀 분석을 위해 advanced_rag 내부의 로직을 세부 추적
        engine.bm25_retriever.k = 20
        vector_results = engine.vector_db.similarity_search(hyde_doc, k=20)
        bm25_results = engine.bm25_retriever.invoke(hyqe_query)
        
        # 중복 제거 및 원시 매칭 풀 조립
        unique_chunks_dict = {}
        
        raw_docs_log = []
        raw_docs_log.append(f"--- [Track 1: Dense ChromaDB Results (Target: HyDE)] 총 {len(vector_results)}개 수집 ---")
        for i, c in enumerate(vector_results, 1):
            p_id = c.metadata.get("parent_id", "none")
            src = c.metadata.get("source", "Unknown")
            unique_chunks_dict[p_id + "_" + c.page_content] = c
            raw_docs_log.append(f"[{i}] Parent_ID: {p_id} | Source: {src}\nChunk_Content: {c.page_content}\n")
            
        raw_docs_log.append(f"--- [Track 2: Sparse BM25 Results (Target: HyQE)] 총 {len(bm25_results)}개 수집 ---")
        for i, c in enumerate(bm25_results, 1):
            p_id = c.metadata.get("parent_id", "none")
            src = c.metadata.get("source", "Unknown")
            unique_chunks_dict[p_id + "_" + c.page_content] = c
            raw_docs_log.append(f"[{i}] Parent_ID: {p_id} | Source: {src}\nChunk_Content: {c.page_content}\n")
            
        unique_chunks = list(unique_chunks_dict.values())
        documents_texts = [c.page_content for c in unique_chunks]
        
        # 2단계 결과 파일 로그 저장 (원문 전체 드랍)
        save_txt_log("debug_raw_retrieval_docs.txt", f"원본 질문: {query}", "\n".join(raw_docs_log))
        print(f"✅ [2단계 완료] 중복 제거 전 총 {len(vector_results) + len(bm25_results)}개 단락 수집 -> 중복 제거 후 {len(unique_chunks)}개 후보 확정. (원문 대피 저장 완료)")
        
        print("\n⏳ [3단계: Reranking] Voyage 크로스 인코더 계층 구동 -> 순위 적합도 재정렬 중...")
        
        rerank_summary = []
        rerank_txt_log = []
        
        try:
            # 최종 스코어링 대조군은 오리지널 발화 활용
            rerank_results = engine.voyage_client.rerank(
                query=query, 
                documents=documents_texts, 
                model="rerank-2", 
                top_k=len(documents_texts)
            )
            
            rerank_txt_log.append(f"교차 어텐션 타겟 매칭 풀 크기: {len(rerank_results.results)}개")
            
            for idx, result in enumerate(rerank_results.results, 1):
                target_chunk = unique_chunks[result.index]
                p_id = target_chunk.metadata.get("parent_id", "none")
                src = target_chunk.metadata.get("source", "Unknown")
                score = result.relevance_score
                
                # 1차 채널에서의 원시 소스 출처 가독 필터링
                in_vector = target_chunk in vector_results
                in_bm25 = target_chunk in bm25_results
                channel_info = "Chroma+BM25" if (in_vector and in_bm25) else ("Chroma(Dense)" if in_vector else "BM25(Sparse)")
                
                # 터미널용 초간결 메타데이터 요약본 적재
                if idx <= 5:  # 상위 5개만 요약 가시화
                    rerank_summary.append(f"   🏆 순위 {idx:02d} | Score: {score:.4f} | 출처 채널: {channel_info:14s} | 파일명: {src}")
                
                # 물리 텍스트 로그 파일용 정밀 내역 생성
                rerank_txt_log.append(
                    f"순위: {idx:02d} | 점수: {score:.4f} | 매칭채널: {channel_info}\n"
                    f"부모ID: {p_id} | 원본출처문서: {src}\n"
                    f"자식 청크 원문: {target_chunk.page_content}\n"
                    f"부모 문맥 원문:\n{target_chunk.metadata.get('parent_text')}\n"
                    f"{'-'*40}"
                )
                
            # 3단계 결과 파일 로그 저장
            save_txt_log("debug_reranking_results.txt", f"원본 질문: {query}", "\n".join(rerank_txt_log))
            print("✅ [3단계 완료] Voyage Cross-Attention 정렬 명세 기록 완료.")
            print("\n📊 [터미널 가시화: 최상위 적합도 지식 Top 5 요약 리포트]")
            print("\n".join(rerank_summary))
            
        except Exception as rerank_err:
            print(f"❌ [Rerank Error] 리랭킹 연산 오류 발생: {rerank_err}")
            
        # 4단계: 최종 LLM 생성 워커 가동을 통한 답변 상태 검증
        print("\n⏳ [4단계: Core Generation] 최종 컨텍스트 결합 생성 프로세스를 가동합니다...")
        p_time_final = time.time()
        try:
            rw._RAG_SYSTEM_INSTANCE = engine 
            rw._rag_worker(job_id, query, "gemini-3.1-flash-lite", chat_history)
            
            if os.path.exists(job_path):
                with open(job_path, "r", encoding="utf-8") as f:
                    result_data = json.load(f)
                os.remove(job_path)
                
                if "error" in result_data:
                    print(f"❌ [Pipeline Error] {result_data['error']}")
                else:
                    print(f"✅ [4단계 완료] 전체 프로세스 최종 응답 획득 성공! (생성 소요: {time.time() - p_time_final:.2f}초)")
                    print("\n🤖 [KlaWde RAG 하이브리드 최종 답변]:")
                    print(result_data.get("result", ""))
                    
                    chat_history.append({"role": "user", "content": query})
                    chat_history.append({"role": "assistant", "content": result_data.get("result", "")})
            else:
                print("❌ [Error] 덤프 세션 파일 탐색 실패.")
        except Exception as gen_err:
            print(f"❌ [Critical Generation Error] 최종 생성 실패: {gen_err}")

if __name__ == "__main__":
    main()