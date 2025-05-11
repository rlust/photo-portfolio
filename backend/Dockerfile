# Backend Dockerfile for PhotoPortfolio
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py ./
COPY search.py ./

EXPOSE 8080
COPY photo-portfolio-459415-b9617545efb7.json /app/photo-portfolio-459415-b9617545efb7.json
CMD ["python", "app.py"]
