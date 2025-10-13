FROM python:3.10.3-slim

WORKDIR /app

RUN apt update && apt-get install -y ffmpeg gettext-base

RUN pip install --upgrade pip wheel
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install debugpy

COPY app.py .
COPY configs.py .
COPY startup.py .
COPY consumer.py .
COPY credentials/ /app/credentials
COPY src/ /app/src
COPY tests/ /app/tests

