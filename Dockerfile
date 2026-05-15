# 1. 베이스 이미지: 파이썬 3.11 버전이 깔린 가벼운 리눅스를 가져와
FROM python:3.11-slim

# 2. 작업 디렉토리 설정: 컨테이너 내부의 /app 폴더에서 작업할 거야
WORKDIR /app

# 3. 필수 도구 설치: 리눅스 업데이트 및 빌드 도구 설치 (ChromaDB 등을 위해 필요)
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# 4. 소스 코드 복사: 내 컴퓨터의 파일들을 컨테이너 안으로 옮겨
COPY . .

# 5. 라이브러리 설치: 라이브러리들을 설치해
RUN pip install --no-cache-dir \
    streamlit \
    langchain-voyageai \
    langchain-google-genai \
    langchain-chroma \
    langchain-community \
    langchain-text-splitters \
    voyageai \
    chromadb \
    tavily-python \
    beautifulsoup4 \
    requests \
    pysqlite3-binary

# 6. 실행 명령: 컨테이너가 켜지면 스트림릿을 실행해!
CMD ["streamlit", "run", "2.py", "--server.port=8080", "--server.enableCORS=false", "--server.enableXsrfProtection=false"]