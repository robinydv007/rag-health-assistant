FROM python:3.11-slim

WORKDIR /app

COPY services/embedding-service/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY shared/ ./shared/
COPY services/embedding-service/src/ ./src/

CMD ["python", "src/main.py"]
