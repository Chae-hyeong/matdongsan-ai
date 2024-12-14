FROM python:3.10-slim
WORKDIR /app
COPY . /app

# 필수 패키지 설치
RUN apt-get update && apt-get install -y \
    build-essential libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

# pip 업그레이드 및 설치
RUN pip install --upgrade pip && pip install -e .

# 유니딕 다운로드
RUN python -m unidic download

# NLTK 리소스 다운로드 (영어, 한국어 관련 리소스 포함)
RUN python -c "import nltk; nltk.download('averaged_perceptron_tagger_eng')"
RUN python -c "import nltk; nltk.download('punkt')"
RUN python -c "import nltk; nltk.download('stopwords')"

# 필요한 NLTK 리소스가 없다면 추가 다운로드 가능
RUN python melo/init_downloads.py

# 포트 노출
EXPOSE 8000

# FastAPI 서버 실행
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]