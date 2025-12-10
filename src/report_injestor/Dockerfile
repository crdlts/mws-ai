# src/report_injestor/Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Копируем common модуль
COPY src/common ./common

# Копируем зависимости report_injector
COPY src/report_injestor/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Копируем код report_injector
COPY src/report_injestor/app ./app

ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

EXPOSE 8002

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8002"]