FROM python:3.11-slim

WORKDIR /app

COPY requirments.txt .

RUN pip install --no-cache-dir -r requirments.txt

COPY . .

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

RUN mkdir -p /logs

RUN chmod -R 755 /logs

CMD ["python", "download_liked_coubs.py"]