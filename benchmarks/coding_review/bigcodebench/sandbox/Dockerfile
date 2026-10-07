# Imagem de avaliação do benchmark BigCodeBench (split complete).
#
# Contém as bibliotecas de terceiros exigidas pelas tarefas, para que o código
# gerado pelo Coder seja executado isolado do ambiente do dev. Construída e
# reutilizada por `run.py` (ver `sandbox_image.py`); build manual:
#
#   docker build -t ai4se-bigcodebench-sandbox:v0.1.4 benchmarks/coding_review/bigcodebench/sandbox
FROM python:3.10-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    MPLBACKEND=Agg \
    TF_CPP_MIN_LOG_LEVEL=3 \
    NLTK_DATA=/usr/share/nltk_data

RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential tesseract-ocr libgl1 libglib2.0-0 libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /tmp/requirements.txt
RUN pip install --upgrade pip && pip install -r /tmp/requirements.txt

# Dados do NLTK baixados no build: em runtime o container roda sem rede.
RUN python -m nltk.downloader -d /usr/share/nltk_data \
        punkt stopwords wordnet omw-1.4 averaged_perceptron_tagger vader_lexicon brown

WORKDIR /app
