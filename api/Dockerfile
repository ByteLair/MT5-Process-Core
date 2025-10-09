FROM python:3.11-slim

WORKDIR /app

# (opcional) dependências nativas caso precise compilar algo
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# ⬅️ o requirements.txt está na RAIZ de /api (não em app/)
COPY requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# código da aplicação
COPY app ./app

EXPOSE 8001
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]
