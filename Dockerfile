FROM python:3.11-slim
WORKDIR /app
RUN apt-get update && apt-get install -y build-essential && rm -rf /var/lib/apt/lists/*
COPY . .
RUN pip install --no-cache-dir streamlit langchain-voyageai langchain-google-genai langchain-chroma langchain-community langchain-text-splitters voyageai chromadb tavily-python beautifulsoup4 requests pysqlite3-binary

# 실행 경로를 src/app.py로 명시적 수정
CMD ["streamlit", "run", "src/app.py", "--server.port=8080", "--server.enableCORS=false", "--server.enableXsrfProtection=false"]