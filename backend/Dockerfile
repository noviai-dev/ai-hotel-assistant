FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
WORKDIR /app

COPY requirements.txt ./
RUN python -m pip install --no-cache-dir -r requirements.txt

COPY competitors.py competitor_db.py competitors.example.json ./
COPY sql/ ./sql/

ENTRYPOINT ["python", "competitors.py"]
CMD ["--execute", "--limit-runs", "1"]
