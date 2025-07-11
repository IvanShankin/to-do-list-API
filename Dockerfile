FROM python:3.13.3-slim

WORKDIR /app

# Установка зависимостей для PostgreSQL клиента
RUN apt-get update && apt-get install -y \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Копируем зависимости и устанавливаем их
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем весь проект (исключая ненужное через .dockerignore)
COPY . .

ENV PYTHONPATH=/app

CMD ["python", "app/run.py"]