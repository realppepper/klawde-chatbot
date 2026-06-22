# scripts/debug_cli.py (새 파일 생성)
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

def main():
    clear_screen()
    print("==================================================")
    print("🤖 KlaWde Headless CLI Debugger (Streamlit 우회)")
    print("==================================================\n")
    
    # 1. 엔진 직접 초기화 (에러 발생 시 여기서 바로 트레이스백이 뜸)
    print("⏳ [System] RAG 엔진을 로딩하고 있습니다...")
    start = time.time()
    try:
        engine = AdvancedRAGEngine(rebuild_mode=False)
        print(f"✅ [System] 엔진 로딩 완료 (소요시간: {time.time() - start:.2f}초)\n")
    except Exception as e:
        print(f"❌ [System Error] 엔진 로딩 실패: {e}")
        return

    chat_history = []
    
    while True:
        print("-" * 50)
        query = input("🧑‍💻 질문을 입력하세요 (종료: 'q', 검색전용모드: 's'): ").strip()
        
        if query.lower() == 'q':
            print("디버거를 종료합니다.")
            break
            
        # [2단계 테스트] LLM 없이 검색(Retrieval) 결과만 빠르게 확인하고 싶을 때
        if query.lower() == 's':
            test_query = input("🔍 검색할 키워드/문장을 입력하세요: ").strip()
            print("\n⏳ [Search] 문서를 검색하고 있습니다...")
            s_time = time.time()
            context, sources = engine.hybrid_search(test_query, top_n=3)
            print(f"✅ [Search] 검색 완료 (소요시간: {time.time() - s_time:.2f}초)")
            print("\n[추출된 문맥(Context)]")
            print(context[:1000] + "\n... (중략) ...\n" if len(context) > 1000 else context)
            print(f"\n[출처(Sources)]\n{sources}\n")
            continue
            
        # [3단계 테스트] 전체 워커 파이프라인 (Query Rewrite -> Search -> LLM)
        job_id = str(uuid.uuid4())
        job_path = rw.get_job_path(job_id)
        
        print("\n⏳ [Pipeline] 전체 RAG 워커 파이프라인을 가동합니다...")
        p_time = time.time()
        
        # 워커를 스레드가 아닌 메인 스레드에서 직접 동기 실행 (에러가 나면 터미널에 즉시 출력됨)
        try:
            # 강제로 엔진 인스턴스 주입 (싱글톤 우회)
            rw._RAG_SYSTEM_INSTANCE = engine 
            rw._rag_worker(job_id, query, "llama-3.1-8b-instant", chat_history)
            
            # 결과 파일 즉시 확인
            if os.path.exists(job_path):
                with open(job_path, "r", encoding="utf-8") as f:
                    result_data = json.load(f)
                os.remove(job_path)
                
                if "error" in result_data:
                    print(f"\n❌ [Worker Error] 워커 내부 에러 발생:\n{result_data['error']}")
                else:
                    answer = result_data.get("result", "")
                    print(f"✅ [Pipeline] 생성 완료 (소요시간: {time.time() - p_time:.2f}초)\n")
                    print("🤖 [답변]")
                    print(answer)
                    
                    # 대화 기록 누적 (실제 서비스와 동일한 환경 구성)
                    chat_history.append({"role": "user", "content": query})
                    chat_history.append({"role": "assistant", "content": answer})
                    if len(chat_history) > 10:
                        chat_history = chat_history[-10:]
            else:
                print("\n❌ [System Error] 결과 파일이 생성되지 않았습니다. 워커가 비정상 종료되었습니다.")
                
        except Exception as e:
            print(f"\n❌ [Critical Error] 예외 발생: {e}")

if __name__ == "__main__":
    main()