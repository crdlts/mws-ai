# src/moderator/Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Копируем common модуль
COPY src/common ./common

# Копируем зависимости moderator
COPY src/moderator/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Копируем код moderator
COPY src/moderator/app ./app

ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

EXPOSE 8001

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]