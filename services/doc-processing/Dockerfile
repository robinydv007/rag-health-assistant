FROM python:3.11-slim

WORKDIR /app

COPY services/doc-processing/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt && \
    python -m spacy download en_core_web_lg

COPY shared/ ./shared/
COPY services/doc-processing/src/ ./src/

ENV PYTHONPATH=/app
CMD ["python", "-m", "src.main"]
