# 🤖 KlaWde (광운대학교 학사안내 RAG 챗봇)

KlaWde는 광운대학교의 학사 공지, 장학, 입시 등 다양한 학사 정보를 실시간으로 탐색하고 사용자 맞춤형으로 답변하는 지능형 AI 챗봇 서비스입니다. Gemini 2.5 flash와 VoyageAI를 결합하여 높은 정확도와 속도를 동시에 보장합니다.

---

## 🛠️ 주요 기술 스택 및 아키텍처

| 구분 | 기술 스택 | 설명 |
| :--- | :--- | :--- |
| **Frontend** | Streamlit | 비동기 UI 제어 및 `@st.fragment`를 활용한 렌더링 최적화 |
| **Embedding** | VoyageAI (`voyage-3-lite`) | 한국어 시맨틱 검색 성능 최적화 |
| **LLM** | Google Gemini 2.5 flash | 고속 답변 생성 및 메모리 기반 컨텍스트 반영 |
| **Vector DB** | ChromaDB | 고밀도 벡터 인덱싱 스토리지 |
| **Search** | Tavily, BM25 | 웹 탐색 및 키워드 기반 하이브리드 검색 |
| **Deployment** | GCP Cloud Run | 컨테이너 기반 자동 확장 배포 |

---

## 📂 프로젝트 디렉토리 구조 (Refactored)

서비스 확장성과 코드 가독성을 위해 **관심사 분리(SoC)** 원칙에 따라 리팩토링된 구조입니다.

```plaintext
klawde-chatbot/
├── .streamlit/
│   ├── api.toml            # [보안] API 키 관리 (Git 업로드 절대 금지)
│   └── config.toml         # Streamlit 서버 호스트 및 브라우저 UI 테마 설정
│
├── src/                    # 💡 핵심 프로덕션 코드
│   ├── app.py              # 서비스 엔트리포인트 (UI 전담)
│   ├── database.py         # SQLite3 연동 사용자 관리 및 대화 이력 저장
│   ├── rag_worker.py       # 비동기 RAG 워커 및 LLM 프롬프트 가공
│   ├── advanced_rag.py     # 하이브리드 Parent-Child 검색 엔진 로직
│   └── style.py            # 프론트엔드 UI/UX CSS 스타일링 격리
│
├── data/                   # 💡 데이터 및 벡터 스토리지 통합
│   ├── html_data/          # 수집 및 정제된 클린 HTML 데이터셋
│   └── chroma_db_html/     # 벡터 DB 인덱스 파일
│
├── scripts/                # 💡 보조 스크립트 격리
│   ├── crawler.py          # 광운대 학사공지 크롤러
│   ├── embed.py            # 벡터 DB 빌드 파이프라인
│   ├── analyze_json.py     # 수집 데이터 통계 검증
│   ├── analyze_length.py   # 글자 수 분포 분석
│   ├── test_api.py         # API 연결 벤치마크
│   ├── test_models.py      # GCP 모델 목록 조회
│   └── test_retrieval.py   # 하이브리드 검색 정확도 테스트
│
├── analytics_result/       # 데이터 분석 시각화 결과물
├── .gitignore              # 버전 관리 제외 설정
├── Dockerfile              # 컨테이너 빌드 명세서
├── chatbot.db              # 로컬 데이터베이스
└── 서버재업로드.txt        # 배포 자동화 커맨드
```

# 🛠️ 주요 기술 스택 및 고도화 아키텍처 상세
1. Frontend & UI/UX 제어 (Streamlit)
    화면 뿌여짐(Blur/Shadowing) 차단: 기존 구조에서는 백그라운드 연산 감시를 위해 전체 화면을 주기적으로 리런(Rerun)하여 UI가 얼어붙거나 뿌옇게 흐려지는 현상이 있었습니다. 이를 해결하기 위해 비동기 상태 폴링 파트를 @st.fragment 데코레이터를 통해 메인 돔(DOM) 트리와 분리하여 로딩 중에도 입력창이 쾌적하게 유지되도록 최적화했습니다.

2. 단기 대화 메모리 (Context Window Memory)
    대화 연속성 확보: 단발성 검색의 한계를 극복하기 위해, 사용자가 질의를 던질 때마다 데이터베이스에서 직전 대화 내역 최대 5개 턴(memory_window)을 실시간 추출합니다. 이를 LLM 프롬프트에 동적으로 결합하여 지시어나 대명사가 포함된 후속 질문도 문맥에 맞게 완벽히 이해합니다.

3. 하이브리드 Parent-Child 윈도우 청킹 검색 엔진 (advanced_rag)
    계층형 청킹전략: 수만 자에 달하는 대형 학사 지침 문서 대응을 위해 문맥 파악용 대형 Parent 청크(1500자)와 정밀 시맨틱 탐색용 작은 Child 청크(300자)로 2차 계층 분할을 취합니다. 

    복합 인덱싱 및 RRF 앙상블: 의미 구조를 짚어내는 밀집 벡터 검색(ChromaDB + Voyage-3-lite)과 고유 학사 키워드 매칭을 담당하는 희소 검색(BM25) 결과를 RRF(Reciprocal Rank Fusion) 알고리즘으로 수학적 가중치 융합을 수행합니다. 최종 검색 시 Child 조각이 매칭되면 메타데이터에 각인된 원본 Parent 문맥을 온전히 복원하여 LLM에 전달합니다.

4. LLM & Search Infra
    LLM: Google Gemini 2.5 flash 모델을 적용하여 고속 응답 속도를 확보하고 정밀한 인스트럭션 제어를 수행합니다.

    웹 탐색: 웹 보조 서치가 필요할 경우 툴 아키텍처 내에 Tavily Search API를 결합하여 지식 스토어 외부의 최신 정보를 유연하게 보완합니다.

5. 배포 인프라 (GCP Cloud Run)
    서비스 전체를 경량화된 리눅스 컨테이너 이미지(Dockerfile)로 패키징하여 무상태(Stateless) 아키텍처 기반의 자동 스케일링 환경으로 안정적으로 구동됩니다.

# 🚀 개발 및 배포 가이드
1. 레포 클론 (최초 1회)
```bash
git clone [https://github.com/realppepper/klawde-chatbot.git](https://github.com/realppepper/klawde-chatbot.git)
cd klawde-chatbot
```

2. 코드 수정 후 GitHub 업로드
```bash
git add .
git commit -m "변경 내용 메모"
git push
```

3. GCP 재배포 방법
    GCP Cloud Shell 터미널에서 아래 명령어를 차례대로 실행합니다.
```bash
git clone [https://github.com/realppepper/klawde-chatbot.git](https://github.com/realppepper/klawde-chatbot.git)
cd klawde-chatbot

# .streamlit 보안 폴더 및 키파일 생성
mkdir -p .streamlit
cat > .streamlit/api.toml << 'EOF'
GEMINI_API_KEY = "본인의_GEMINI_API_KEY"
VOYAGE_API_KEY = "본인의_VOYAGE_API_KEY"
TAVILY_API_KEY = "본인의_TAVILY_API_KEY"
EOF

# 빌드 및 클라우드 배포 자동화 스크립트 실행
cat 서버재업로드.txt | bash
```

4. 로컬 환경 테스트 및 가동
    필수 의존성 패키지 설치:
```bash
pip install streamlit langchain-voyageai langchain-google-genai langchain-chroma langchain-community langchain-text-splitters voyageai chromadb tavily-python beautifulsoup4 requests pysqlite3-binary
```

    벡터 DB 구축 및 인덱싱 파이프라인 구동:
```bash
python scripts/embed.py

Streamlit 프로덕션 앱 실행:
```

```bash
streamlit run src/app.py
```



KlaWde 프로젝트 소스 코드 및 배포 설정에 관한 변경 문의 사항이 있을 경우 이슈 트래커나 메인 커밋 코멘트를 남겨주시기 바랍니다.