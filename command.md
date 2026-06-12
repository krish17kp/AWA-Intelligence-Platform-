Before making any changes, read `command.md` fully.

Fix Railway Playwright/Chromium deployment using Dockerfile.

Current problem:
Railway APHIS ingestion fails with:

`BrowserType.launch: Executable doesn't exist at /root/.cache/ms-playwright/.../chrome-headless-shell`
`Please run: playwright install`

Railway build logs currently show:

- `using build driver railpack-v0.27.0`
- `Found web command in Procfile`
- `pip install -r requirements.txt`
- Chromium browser binaries are not installed.

This means the Python `playwright` package is installed, but the actual Chromium browser is missing.

Goal:
Use a Dockerfile-based Railway deployment so Chromium and browser system dependencies are available in production.

Important project path:
Railway Root Directory is `backend`, so Dockerfile must be created at:

`backend/Dockerfile`

Do not put Dockerfile in project root.

Tasks:

1. Create this exact file:

`backend/Dockerfile`

Use this exact content:

```dockerfile
FROM mcr.microsoft.com/playwright/python:v1.60.0-noble

WORKDIR /app

ENV PYTHONUNBUFFERED=1
ENV PORT=8080
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}"]
```

2. Update `backend/requirements.txt`.

Make sure these dependencies exist:

```txt
fastapi
uvicorn[standard]
sqlalchemy
alembic
pydantic-settings
python-dotenv
requests
psycopg2-binary
boto3
botocore
playwright==1.60.0
```

If `playwright` exists without version pinning, change it to:

```txt
playwright==1.60.0
```

Reason:
The Docker base image is `mcr.microsoft.com/playwright/python:v1.60.0-noble`, so the Python package version should match the browser image version.

3. Remove deployment conflicts.

Check if this file exists:

`backend/Procfile`

If it exists, delete it.

Reason:
Railway previously used Procfile/Railpack instead of Dockerfile. We want Dockerfile to be the single source of deployment truth.

4. Remove or ignore `backend/nixpacks.toml`.

If `backend/nixpacks.toml` exists, either delete it or leave a clear note in README that Dockerfile is now the real deployment method. Prefer deleting it to avoid confusion.

5. Make sure the app still starts through Docker CMD.

Do not add a new Railway build command.
Do not make Railway build command and start command the same.
Dockerfile CMD already runs:

`alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}`

6. Update `backend/README.md`.

Add a section:

```md
## Railway Docker Deployment

Railway uses `backend/Dockerfile` because the service Root Directory is `backend`.

The Dockerfile uses the official Playwright Python image:

`mcr.microsoft.com/playwright/python:v1.60.0-noble`

This is required because APHIS scraping uses Playwright/Chromium. A normal Python/Railpack build installs the Playwright Python package but does not install Chromium browser binaries, causing APHIS ingestion to fail.

Railway variables still required:

- DATABASE_URL
- INGESTION_API_KEY
- RAW_STORAGE_MODE=railway_bucket
- S3_ENDPOINT_URL
- S3_BUCKET_NAME
- AWS_ACCESS_KEY_ID
- AWS_SECRET_ACCESS_KEY
- AWS_DEFAULT_REGION
```

7. Run local checks:

```powershell
cd backend
python -m compileall app scripts
```

8. Commit and push.

Use commit message:

```text
Add Dockerfile for Railway Playwright deployment
```

9. Append/update `AGENT_HANDOFF.md`.

Add:

- Dockerfile created
- Procfile removed or status noted
- nixpacks.toml removed or status noted
- requirements updated
- compile command run
- output
- next Railway verification steps
- remaining blockers if any

Do not build frontend.
Do not add AI.
Do not add Neo4j.
Do not add Dagster.
Do not add Celery.
Do not change ingestion logic unless required for Docker compatibility.
Focus only on making Railway use Dockerfile with Playwright/Chromium correctly.
