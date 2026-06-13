FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app/scan-resources
COPY scan-resources/ /app/scan-resources/
RUN pip install --no-cache-dir boto3

WORKDIR /app/scan-resources/route53

# Batch mode: run once and exit.
ENTRYPOINT ["python", "scan_route53.py"]
