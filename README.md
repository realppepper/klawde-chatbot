# klawde-chatbot

광운대학교 정보 기반 AI 챗봇 서비스입니다.  

---

## 기술 스택

- **Frontend**: Streamlit
- **Embedding**: VoyageAI (`voyage-3-lite`)
- **LLM**: Google Gemini 2.5 flash
- **Vector DB**: ChromaDB
- **Search**: Tavily
- **배포**: GCP Cloud Run

---

## 1. 레포 클론 (최초 1회)

```bash
git clone https://github.com/realppepper/klawde-chatbot.git
cd klawde-chatbot
```

---

## 2. 코드 수정 후 GitHub 업로드

```bash
git add .
git commit -m "변경 내용 메모"
git push
```

---

## 3. GCP 재배포 방법

GCP Cloud Shell에서 실행:

```bash
git clone https://github.com/realppepper/klawde-chatbot.git
cd klawde-chatbot

mkdir -p .streamlit
cat > .streamlit/api.toml << 'EOF'
GEMINI_API_KEY = "키입력"
VOYAGE_API_KEY = "키입력"
TAVILY_API_KEY = "키입력"
EOF

cat 서버재업로드.txt | bash
```

---

## 4. 벡터 DB 구축
```bash
python embed.py
```

---

## 5. 앱 실행
```bash
streamlit run 2.py
```