FROM python:3.11-slim
WORKDIR /app
COPY ml/requirements.txt .
RUN pip install -r requirements.txt
COPY ml/ ml/
COPY sql/ sql/
ENV PYTHONUNBUFFERED=1
