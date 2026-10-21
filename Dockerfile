FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt psycopg2-binary==2.9.11

COPY . .

EXPOSE 8000

CMD ["python", "run.py"]
