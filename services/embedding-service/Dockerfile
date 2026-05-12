FROM python:3.11-slim

WORKDIR /app

COPY services/embedding-service/requirements.txt ./requirements.txt
RUN python -m pip install --upgrade pip

RUN pip install --no-cache-dir --index-url https://pypi.org/simple -r requirements.txt

COPY shared/ ./shared/
COPY services/embedding-service/src/ ./src/

CMD ["python", "src/main.py"]

