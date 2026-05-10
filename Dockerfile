FROM python:3.12-slim AS base
WORKDIR /app

ARG ALEX_TOKEN
ARG JASON_TOKEN
ARG OLLAMA_HOST
ARG MOC_MODEL
ARG SERIOUS_MODEL
ENV ALEX_TOKEN=$ALEX_TOKEN \
    JASON_TOKEN=$JASON_TOKEN \
    OLLAMA_HOST=$OLLAMA_HOST \
    MOC_MODEL=$MOC_MODEL \
    SERIOUS_MODEL=$SERIOUS_MODEL

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py db.py ./
COPY static ./static

EXPOSE 8000
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
