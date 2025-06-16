# Construction
FROM python:3.10-slim

ENV PYTHONUNBUFFERED=1 \
    # empêche psycopg2 de nécessiter les headers PostgreSQL
    PIP_NO_BINARY=":none:" \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# 1. Dépendances Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 2. Code de l’API
COPY . .

# Exposition & démarrage
EXPOSE 8081
# Gunicorn démarre l’instance Flask retournée par create_app()
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:8081", "app:create_app()"]
