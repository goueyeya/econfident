FROM python:3.9-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    ffmpeg libsm6 libxext6 \
    software-properties-common \
    git supervisor \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/
RUN pip3 install -r requirements.txt

RUN python -m spacy download fr_core_news_sm

COPY dashboard.py /app/
COPY bot.py /app/
COPY supervisord.conf /app/
COPY data/ /app/data/
COPY src/ /app/src/

EXPOSE 8080

HEALTHCHECK CMD curl --fail http://localhos:8080/_stcore/health

STOPSIGNAL SIGTERM
ENTRYPOINT ["/usr/bin/supervisord", "-c", "supervisord.conf"]
