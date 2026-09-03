FROM python:3.13-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY src ./src
COPY tests ./tests
COPY docs ./docs
ENV PYTHONUNBUFFERED=1
CMD ["python", "-m", "src.pipeline"]
