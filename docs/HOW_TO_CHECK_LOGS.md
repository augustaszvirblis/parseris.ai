# How to check logs

Backend and prompt-service logs go to **stdout** (console) only by default. How you see them depends on how you run the app.

## Log level

- Default level: **INFO** (set by `DEFAULT_LOG_LEVEL` env, e.g. in `.env`).
- To see more detail: set `DEFAULT_LOG_LEVEL=DEBUG` for the backend.

## Where to look

### 1. Running with Django `runserver` (local dev)

Logs appear in the **terminal** where you started the backend:

```bash
cd backend && python manage.py runserver
```

Watch that terminal when you trigger extraction.

### 2. Running with Docker Compose

View logs for the backend service:

```bash
cd docker
docker compose logs -f backend
```

Follow logs for all services:

```bash
docker compose logs -f
```

To only see backend and prompt-service:

```bash
docker compose logs -f backend prompt-service
```

### 3. Running with Gunicorn / systemd / other

- **Gunicorn**: Logs go to the process stdout/stderr. If you start it in a terminal, they appear there; if a process manager (systemd, supervisord) runs it, check that manager’s log configuration (e.g. `journalctl -u your-service` or the file it redirects stdout to).

## Confirm LLM (vision) extraction is used

When PDF extraction uses the **vision LLM** path (no pdfplumber/x2text), the backend logs:

```
EXTRACTION_MODE=LLM_VISION: PDF extraction is performed by the vision LLM (no pdfplumber/x2text). Document pages are sent as images to the LLM.
```

**Search for that line** in your backend logs (e.g. pipe to `grep`):

```bash
# Docker
docker compose logs backend 2>&1 | grep -i "EXTRACTION_MODE=LLM_VISION"

# Or follow and filter
docker compose logs -f backend 2>&1 | grep -E "EXTRACTION_MODE=LLM_VISION|vision table extraction"
```

If you see `EXTRACTION_MODE=LLM_VISION`, that request used the vision LLM for extraction.

## Log format

Backend uses an enriched format similar to:

```
LEVEL : [timestamp] {module:... process:... thread:... request_id:... trace_id:... span_id:...} :- message
```

So log lines include level, time, request id, and the message (e.g. the EXTRACTION_MODE line above).
