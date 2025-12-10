# src/audit/Dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY src/audit/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY src/audit/app ./app

ENV PYTHONUNBUFFERED=1

EXPOSE 8003

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8003"]