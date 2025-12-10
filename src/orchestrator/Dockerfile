# src/orchestrator/Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Копируем common модуль
COPY src/common ./common

# Копируем зависимости orchestrator
COPY src/orchestrator/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Копируем код orchestrator
COPY src/orchestrator/app ./app

ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]