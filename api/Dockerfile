FROM python:3.11-slim

WORKDIR /app

# (opcional) dependências nativas caso precise compilar algo
# adiciona wget/curl e certificados para o healthcheck e possíveis downloads
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    wget \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# ⬅️ o requirements.txt está na RAIZ de /api (não em app/)
COPY requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# código da aplicação
COPY . /app

EXPOSE 8001
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]
