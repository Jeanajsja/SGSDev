FROM python:3.11-slim
WORKDIR /app
COPY services/roles/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY services/roles/ .
COPY services/common/ ./common/
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app
EXPOSE 5004
CMD ["gunicorn", "-k", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:5004", "app:app"]
