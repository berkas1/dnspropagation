FROM python:3.13-alpine

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt pytest

COPY src/ ./src/
COPY tests/ ./tests/
COPY custom-list.yaml .

CMD ["python", "-m", "pytest", "tests/functional.py", "-v"]
