# Setup Checklist

## A. Prerequisites

1. Install Docker Desktop.
   - Windows/macOS: download Docker Desktop from `https://www.docker.com/products/docker-desktop/`, run the installer, then start Docker.
   - Ubuntu: `sudo apt-get update && sudo apt-get install -y docker.io docker-compose-plugin`.
2. Install Node 20 or newer.
   - Windows: `winget install OpenJS.NodeJS.LTS`.
   - macOS: `brew install node`.
   - Ubuntu: `curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash - && sudo apt-get install -y nodejs`.
3. Install Python 3.11 or newer.
   - Windows: `winget install Python.Python.3.11`.
   - macOS: `brew install python@3.11`.
   - Ubuntu: `sudo apt-get install -y python3.11 python3.11-venv`.

## B. Gemini API Key

1. Open `https://aistudio.google.com/`.
2. Sign in with a Google account.
3. Click `Get API key`.
4. Click `Create API key`.
5. Copy the key.
6. In this repo, copy `.env.example` to `.env`.
7. Paste the key into `GEMINI_API_KEY=`.
8. To avoid API spend, leave it blank and run ingestion with `--mock-llm`.

Optional Mapbox token:

1. Open `https://account.mapbox.com/`.
2. Create or copy a public token.
3. Paste it into `MAPBOX_TOKEN=`.
4. You can skip this; MapLibre works with free CARTO/OSM tiles.

## C. Local Run

1. Clone the repo.
2. Run `cp .env.example .env`.
3. Confirm these local values:
   - `DATABASE_URL=postgresql+asyncpg://travel:travel@localhost:5432/travel`
   - `REDIS_URL=redis://localhost:6379/0`
   - `NEXT_PUBLIC_API_URL=http://localhost:8000`
4. Start the stack: `docker-compose up --build`.
5. In another terminal, install backend dependencies if running ingest outside Docker: `cd backend && python -m venv .venv && .venv\Scripts\activate && pip install -e .` on Windows, or `cd backend && python3.11 -m venv .venv && source .venv/bin/activate && pip install -e .` on macOS/Linux.
6. Run sample ingest: `python -m pipeline.ingest --mock-llm --sample`.
7. For a larger deterministic seed, run: `python -m pipeline.ingest --mock-llm`.
8. For real URL discovery plus seed loading, omit `--seed-only`: `python -m pipeline.ingest --mock-llm --sample`.
9. Confirm success by seeing a JSON summary with `properties`, `reviews`, and `calendar` counts.
10. Open `http://localhost:3000`.

Troubleshooting:

1. Port conflict on `3000`, `8000`, `5432`, or `6379`: stop the other service or change the mapped port in `docker-compose.yml`.
2. Missing pgvector/PostGIS: run `CREATE EXTENSION IF NOT EXISTS vector; CREATE EXTENSION IF NOT EXISTS postgis;` in the target database.
3. Gemini 429s: rerun with `--mock-llm`, or wait for free-tier quota reset.
4. Low memory during real ingest: use `--sample`, keep Docker Desktop memory at 6 GB or higher, and ingest reviews/calendar in chunks.

## D. Live Deploy

### Supabase Postgres

1. Open `https://supabase.com/dashboard`.
2. Click `New project`.
3. Name it `ai-native-travel`.
4. Choose the nearest region to the backend Render region.
5. Set and save the database password.
6. Open `Project Settings` → `Database`.
7. Copy the connection string and replace the password placeholder.
8. Open `SQL Editor`.
9. Run:

```sql
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS postgis;
```

10. From your machine, run migrations against Supabase using the copied URL converted to SQLAlchemy async form in `.env` as `DATABASE_URL=postgresql+asyncpg://...`.

### Upstash Redis

1. Open `https://console.upstash.com/`.
2. Click `Create Database`.
3. Name it `ai-native-travel-cache`.
4. Pick the same region family as Render.
5. Click the database.
6. Copy the TLS Redis URL beginning with `rediss://`.
7. Save it as `REDIS_URL` in Render.

### Render Backend

1. Open `https://dashboard.render.com/`.
2. Click `New` → `Web Service`.
3. Connect the GitHub repo.
4. Name the service `ai-native-travel-api`.
5. Set root directory to `backend`.
6. Build command: `pip install -e .`.
7. Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`.
8. Add environment variables:
   - `DATABASE_URL`
   - `REDIS_URL`
   - `GEMINI_API_KEY`
   - `CORS_ORIGINS=https://YOUR-VERCEL-URL.vercel.app`
   - `APP_ENV=production`
9. Set health check path to `/health`.
10. Deploy.
11. Open Render Shell and run `python -m pipeline.ingest --mock-llm --sample` for a free-tier sample database, or remove `--mock-llm` when ready to spend Gemini quota.

### Vercel Frontend

1. Open `https://vercel.com/dashboard`.
2. Click `Add New` → `Project`.
3. Import the GitHub repo.
4. Set root directory to `frontend`.
5. Add `NEXT_PUBLIC_API_URL=https://YOUR-RENDER-SERVICE.onrender.com`.
6. Click `Deploy`.
7. Copy the Vercel public URL.
8. Return to Render and update `CORS_ORIGINS` to that Vercel URL.

Post-deploy verification:

1. Open the Vercel URL and run a London search with `near transit`.
2. Type `a quiet 1-bed in Lisbon under €130 with a balcony for late June` and confirm filter chips update.
3. Open the concierge and run the London itinerary query; confirm streamed Intent, Retrieval, and Itinerary steps.

## E. Cost And Limits

The sample path stays inside free-tier database limits. Real full ingest can incur charges from Gemini embeddings and larger managed Postgres storage. Use `--mock-llm --sample` for demos, then run full enrichment only when you are ready to pay for embeddings and extra database space.
