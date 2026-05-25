FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*

RUN git config --global user.name "TWK Demo" \
    && git config --global user.email "twk-demo@example.com" \
    && git config --global --add safe.directory /flipt-state-repo

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py twk.py ./
COPY templates/ templates/

EXPOSE 5000 5001

CMD ["python", "app.py"]
