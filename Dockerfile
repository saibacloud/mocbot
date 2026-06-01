FROM python:3.12-slim AS base
WORKDIR /app

ARG OLLAMA_HOST
ARG OLLAMA_MODEL
ENV OLLAMA_HOST=$OLLAMA_HOST \
    OLLAMA_MODEL=$OLLAMA_MODEL

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py index.html ./

EXPOSE 8000
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
