# Forex Data Updater Container
# Atualiza automaticamente dados históricos do banco
FROM python:3.11-slim

LABEL maintainer="MT5-Process-Core"
LABEL description="Automated Forex data updater using Yahoo Finance API"

# Configurar timezone
ENV TZ=America/Sao_Paulo
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# Instalar dependências do sistema
RUN apt-get update && apt-get install -y \
    cron \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Criar diretório de trabalho
WORKDIR /app

# Copiar requirements
COPY ./requirements-updater.txt .

# Instalar dependências Python
RUN pip install --no-cache-dir -r requirements-updater.txt

# Criar diretório de scripts
RUN mkdir -p /app/scripts

# Copiar scripts
COPY ./scripts/updater/ /app/scripts/

# Criar diretório de logs
RUN mkdir -p /var/log/forex-updater

# Copiar configuração do cron
COPY ./docker/updater/crontab /etc/cron.d/forex-updater
RUN chmod 0644 /etc/cron.d/forex-updater && \
    crontab /etc/cron.d/forex-updater

# Script de entrada
COPY docker/updater/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Healthcheck
HEALTHCHECK --interval=1h --timeout=30s --start-period=10s --retries=3 \
    CMD python /app/scripts/healthcheck.py || exit 1

# Expor logs via volume
VOLUME ["/var/log/forex-updater"]

ENTRYPOINT ["/entrypoint.sh"]
CMD ["cron", "-f"]
