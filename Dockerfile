FROM python:3.11-slim

WORKDIR /app

# Desabilita buffer de saída do Python para logs em tempo real
ENV PYTHONUNBUFFERED=1

# Copia o arquivo a partir da pasta backend/
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia todo o código do projeto
COPY . .

EXPOSE 8000

# Executa o servidor backend servindo a API e o Frontend estático
CMD ["python", "-m", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]