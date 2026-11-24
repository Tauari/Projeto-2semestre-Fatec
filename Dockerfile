# Imagem do servidor do Aurora (API + site). O banco NÃO fica na imagem: vem de AURORA_BANCO_URL (Postgres na nuvem).
FROM python:3.12-slim

WORKDIR /app
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1

COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

COPY backend backend
COPY frontend frontend
COPY vendor vendor
COPY dados dados

EXPOSE 8000
# a hospedagem define PORT; sem ele, 8000. --no-access-log: o servidor não grava o IP de quem acessa
CMD ["sh", "-c", "uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8000} --no-access-log"]
