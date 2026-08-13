FROM python:3.12-slim

WORKDIR /app

# Runtime dependencies only (test deps stay out of the image).
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

# Runtime config defaults. Swallow a copy of infracheck.db / reports dirs so a
# stateless run still works; mount volumes override these in compose.
RUN mkdir -p /app/data /app/reports_out
ENV DATABASE_URL=sqlite:////app/data/infracheck.db \
    REPORTS_OUT_DIR=/app/reports_out \
    RUNNER_TRANSPORT=dryrun \
    AUTH_MODE=mock \
    SCHEDULER_ENABLED=true

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
