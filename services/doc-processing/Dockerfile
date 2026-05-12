FROM python:3.11-slim

WORKDIR /app

COPY services/doc-processing/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY shared/ ./shared/
COPY services/doc-processing/src/ ./src/

CMD ["python", "src/main.py"]
