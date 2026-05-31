# 🤖 KlaWde: 광운대학교 학사안내 전문 지능형 Hybrid RAG 챗봇 시스템

KlaWde는 광운대학교 학사 지침, 공지사항 및 복잡한 시간표 정보를 정밀하게 탐색하여 학생들에게 신뢰할 수 있는 답변을 제공하는 고성능 지능형 챗봇 시스템입니다.

대규모 지식 데이터베이스 환경에서 발생하는 런타임 CPU 병목을 최소화하고, 프론트엔드와 백엔드 간의 교착 상태(Deadlock)를 방지하기 위해 **사전 인덱싱 캐싱(Pre-indexing Baking)**, **지연 로딩(Lazy Loading)** 및 **비동기 스레드 상태 폴링 구조**를 채택하였습니다.

---

## 🏗️ 1. 시스템 아키텍처 (Architecture)

본 시스템은 유연한 UI 인터랙션과 무거운 RAG 연산 간의 간섭을 원천 차단하기 위해 디스크 에포크(Temp File Session) 기반의 비동기 차단막 구조를 가집니다.

```
[ User Browser ]
│  ▲
│  │ (1s 주기 무부하 @st.fragment 폴링)
▼  │
┌────────────────────────────────────────────────────────┐
│  Streamlit UI (Main Frontend Thread)                   │
│  - 세션 및 인증(Auth) 관리                             │
│  - 대화 내역 영속화 (SQLite DB 동기화)                 │
└──────────────────────────┬─────────────────────────────┘
                           │
                           │ (threading.Thread 비동기 스레드 분기 및 GIL 격리)
                           ▼
┌────────────────────────────────────────────────────────┐
│  Background RAG Worker (Sub Daemon Thread)             │
│                                                        │
│  1. Query Rewriting (Gemini 3.1 Flash Lite)            │
│     - 단발성 질의를 과거 대화 맥락 반영형 쿼리로 최적화  │
│                                                        │
│  2. Hybrid Retrieval Pipeline (AdvancedRAGEngine)      │
│     - Sparse: Kiwi 형태소 분석 기반 사전 빌드 BM25     │
│     - Dense: Voyage-3-Lite 고성능 임베딩 Vector DB     │
│                                                        │
│  3. Cross-Attention Reranking (Voyage Reranker)        │
│     - 통합 40개 후보군 대상 상위 top_n=4 정밀 필터링   │
│                                                        │
│  4. Context Reconstruction                             │
│     - 정밀 Child 청크에서 1,500자 Parent 윈도우 문맥 복원│
│                                                        │
│  5. Core Generation (Gemini 3.5 Flash / 3.1 Pro)       │
│     - 대용량 문맥 융합 최종 학사 답변 생성             │
└──────────────────────────┬─────────────────────────────┘
                           │
                           ▼ (임시 세션 파일 드랍)
                   [ /tmp/klawde_*.json ]
```

---

## 📂 2. 프로젝트 디렉토리 구조 (Directory Structure)

본 프로젝트는 프론트엔드 인터페이스, 백엔드 RAG 비즈니스 로직, 오프라인 테스트 스크립트가 기능별로 완벽히 격리된 구조를 유지합니다.

```
klawde-project/
├── .streamlit/
│   └── api.toml              # API 보안 키 (Gemini, Voyage) 관리 및 설정 파일
├── data/
│   ├── html_data/            # 원본 학사 지침, 공지사항 및 시간표 데이터 소스 (HTML/JSON)
│   └── chroma_db_html/       # Chroma Vector DB 스토리지 및 사전 빌드된 BM25 피클 객체 보관 디렉토리
├── scripts/
│   ├── test_api.py           # [1단계] API 게이트웨이 통신 상태 독립 검증 스크립트
│   └── debug_cli.py          # [2, 3단계] 터미널 기반 Headless RAG 파이프라인 통합 디버거
├── src/
│   ├── app.py                # Streamlit UI 메인 프론트엔드 구동 파일
│   ├── rag_worker.py         # 비동기 백그라운드 데몬 스레드 워커 (폴백 재시도 내장)
│   ├── advanced_rag.py       # 하이브리드 검색 인덱싱 및 Voyage Reranker 추론 엔진 코어
│   ├── database.py           # Local SQLite 사용자 인증 및 대화 히스토리 관리 모듈
│   └── style.py              # 챗봇 UI 렌더링용 커스텀 CSS 스타일 명세
├── klawde_debug.log          # 전체 파이프라인 정밀 진단 시스템 타임스탬프 로그 파일
└── README.md                 # 본 프로젝트 마스터 명세서
```

---

## 🛠️ 3. 사용 기술 및 스택 (Tech Stack)

### Frontend & Orchestration

- **Streamlit (v1.x):** 단일 프로세스 기반 고속 UI 웹 서비스 프레임워크 및 프래그먼트(`@st.fragment`) 제어
- **SQLite3:** 로컬 사용자 계정 보안 인증 및 대화 세트 히스토리 영속화

### NLP & Vector Search Engine

- **Kiwipiepy:** 한국어 언어학 특성에 맞춘 고속 C++ 기반 형태소 분석 엔진 (명사 토크나이저 바인딩)
- **ChromaDB:** 임베딩 벡터 동적 색인 및 코사인 유사도 1차 탐색용 초경량 로컬 벡터 스토어
- **LangChain Community & Core:** 구조화된 문서 가공용 텍스트 스플리터 및 로더 허브

### Advanced Core AI Cloud API

- **Google Gemini API:** `gemini-3.1-flash-lite` 코어 생성 엔진
- **VoyageAI:** 최신 다국어 지원 덴스 임베딩 모델(`voyage-3-lite`) 및 정밀 교차 크로스 인코더 Reranker(`rerank-2`)

---

## 📈 4. 시스템 트래픽 및 토큰 프로파일링 (Token Profile)

한글 RAG 데이터셋의 언어학적 특성(한글 토큰 가중치 패널티) 및 Parent-Child 컨텍스트 윈도우 설계에 따른 단일 요청당 실질적인 입출력 토큰 부하 수치 프로파일링입니다.

| 파이프라인 단계 | 사용 모델 ID | 평균 입력 토큰 수 (Prompt) | 평균 출력 토큰 수 (Completion) | 특이사항 / 방어 기전 |
| :--- | :--- | :--- | :--- | :--- |
| **1단계: Query Rewrite** | `gemini-3.1-flash-lite` | **~500 Tokens** (대화 이력 포함) | **~100 Tokens** (최적화 검색어) | 250K TPM 예산 내 고속 처리 |
| **2단계: Core RAG Generation** | `gemini-3.1-flash-lite` | **~6,500 - 7,500 Tokens** (1,500자 Parent 문맥 × 4개) | **~500 - 800 Tokens** (최종 자연어 답변) | 대용량 컨텍스트 윈도우 수용 및 500 RPD 무료 한도 대응 |

---

## 💡 5. 구체적인 핵심 구현 (Implementation & Optimization)

### ① 빌드 타임 사전 인덱싱 캐싱 (Pre-indexing Baking)

런타임에 수만 개의 텍스트 조각을 한국어 형태소 분석기(`Kiwi`)로 쪼개는 방식은 심각한 CPU 병목을 유발합니다. 이를 해결하기 위해 **오프라인 빌드 타임에 BM25Retriever 객체 자체를 통째로 연산 및 가공하여 Pickle 파일로 디스크에 드랍**합니다. 런타임 진입 시점에는 단 0.1초 만에 인덱싱이 로드됩니다.


### ④ 검색 성능 고도화의 핵심: Cross-Attention Reranker 도입

본 RAG 시스템의 검색 정확도를 비약적으로 상승시킨 핵심 장치는 VoyageAI의 Cross-Attention 기반 리랭킹(Reranker) 레이어입니다.

- **기존의 한계:** Sparse 검색(BM25)과 Dense 검색(Vector DB)을 단순히 결합하는 하이브리드 방식은 키워드 매칭과 유사도 점수가 파편화되어, LLM에 노이즈 정보가 섞여 들어가거나 순위가 밀린 핵심 학사 정보가 누락되는 고질적인 문제가 있었습니다.
- **해결 및 최적화:** 1차 검색 허브를 통해 추출된 총 40개의 청크 후보군(BM25 20개 + Vector DB 20개)을 VoyageAI의 고성능 크로스 인코더 모델인 `rerank-2`에 통과시켰습니다. 문맥과 질문 간의 고차원 인과관계를 재정렬하여 실제 정답에 가까운 최상위 단락들만 유실 없이 `top_n=4` 범위 내로 압도적으로 압축·필터링해 냅니다.
- **장점:** 복잡한 다중 조건(예: 특정 학년 전공 필수/선택 과목명과 담당 교수명이 한꺼번에 뒤섞인 질문) 질의가 들어와도, 리랭킹 레이어가 관련 학사 테이블과 텍스트 정보를 칼같이 최상단으로 정렬해 주기 때문에 LLM의 환각(Hallucination) 현상을 원천 차단하고 최고 품질의 정밀한 답변 생성을 보장합니다.


---

## 🔍 6. Headless CLI 디버깅 파이프라인

웹 브라우저를 띄우거나 로그인하는 번거로운 UI 조작 없이 백엔드 파이프라인만 고속으로 추적·검증할 수 있는 디버깅 전용 도구 체계를 포함하고 있습니다.

### [1단계] API & 네트워크 상태 1초 진단

API 키의 유효성, 네트워크 도달성 및 토큰 만료 여부를 독립적으로 즉시 체크합니다.

```bash
python scripts/test_api.py
```

### [2단계 & 3단계] 통합 CLI RAG 엔진 디버거

터미널 환경에서 백엔드 코어 파이프라인만 격리 구동하여, 변환 쿼리 원문 및 Reranker를 거친 검색 문맥(Context)의 실시간 정렬 상태를 추적합니다.

```bash
python scripts/debug_cli.py
```

- `q` 입력 시 디버거 종료
- `s` 입력 시 LLM 호출을 생략하고, 순수 검색 엔진(Retrieval) 매칭 결과 및 출처만 빠르게 확인 가능한 검색 전용 모드 전환

---

## 🚀 7. 시작하기 (Quick Start)

### 1) 환경 변수 설정

`.streamlit/api.toml` 파일을 생성하고 아래 규격에 맞게 키를 설정합니다.

```toml
GEMINI_API_KEY = "AIzaSy..."
VOYAGE_API_KEY = "pa-..."
```

### 2) Sparse BM25 인덱스 캐싱 고속 빌드 (최초 1회 필수)

```bash
python src/advanced_rag.py build_bm25
```

### 3) Streamlit 서비스 구동

```bash
streamlit run src/app.py
```