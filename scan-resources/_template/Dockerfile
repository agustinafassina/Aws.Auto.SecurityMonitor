FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app/scan-resources

COPY scan-resources/requirements.txt .
COPY scan-resources/scanner_core.py .
COPY scan-resources/MODULE ./MODULE

RUN pip install --no-cache-dir -r requirements.txt

# ECS overrides command; default for local docker run.
CMD ["python", "MODULE/scan_MODULE.py", "--source", "aws"]
