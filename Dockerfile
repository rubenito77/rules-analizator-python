FROM python:3.11-slim

LABEL maintainer="tu_nombre <tu_email@dominio.com>"

ENV LOG_DIR=/logs
ENV PORT=8081
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
COPY app.py .
COPY config.py .
COPY modules/ ./modules/
COPY templates/ ./templates/

RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt
RUN mkdir -p ${LOG_DIR}

CMD ["python", "app.py"]

