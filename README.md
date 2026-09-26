# Polyvox

Multilingual text-to-speech platform, built on [Supertonic 3](https://huggingface.co/Supertone/supertonic-3)
(31 languages including English and Hindi, CPU inference via ONNX Runtime — no GPU required).

- **JSON API** for other applications (e.g. a video pipeline) to submit text and get back audio, protected by
  admin-issued API keys.
- **Web UI** (mobile-friendly, server-rendered) where any logged-in user can generate audio directly, and admins
  manage user accounts and API keys.
- **Async job queue**: submitting text returns a job id immediately; the caller polls for status and, once
  finished, downloads the resulting audio file. Long narration text is expected to take real synthesis time, so
  nothing blocks on an open HTTP connection.
- Generated audio is stored on disk with a **TTL** (deleted after `AUDIO_TTL_SECONDS`, default 30 minutes) and a
  **total size cap** (`AUDIO_STORAGE_MAX_BYTES`, oldest files evicted first).

## Architecture

```
Browser (session cookie) ──┐
External app (X-API-Key) ──┼──▶ web (FastAPI: UI + JSON API — never loads the TTS model)
                            │        │                  │
                            │    Postgres           Redis (RQ queue) ──▶ worker (loads Supertonic
                            │  (users, api keys,                          once per process, writes
                            │   job history)                              .wav to a shared volume)
                            └────────────────────────────────────────────────▶ web serves /audio/*
```

Scaling out is done by running more `worker` container replicas (each loads its own model instance); the `web`
tier does no CPU-heavy work and stays a single process by default.

Postgres and Redis are **not** part of this compose file — `web`/`worker` connect out to existing instances via
`DATABASE_URL`/`REDIS_URL` (see Configuration below). This was originally a self-contained stack with its own
`postgres`/`redis` services; it now expects to reuse shared instances (e.g. Coolify's shared-postgres/shared-redis
resources) instead, joining their Docker network directly.

## Running locally (Docker required)

```bash
cp .env.example .env
# edit .env: set SECRET_KEY, ADMIN_EMAIL/ADMIN_PASSWORD, and DATABASE_URL/REDIS_URL to point at
# reachable Postgres/Redis instances. Set ENV=development if testing over plain HTTP (session
# cookies default to HTTPS-only).

docker compose up --build
```

Then open `http://localhost:8000/login` and sign in with `ADMIN_EMAIL` / `ADMIN_PASSWORD` (the admin account is
created automatically on first startup). From there:

- **Generate** — any logged-in user can submit text and download the resulting audio.
- **Users** (admin only) — create additional user or admin accounts. There's no public signup.
- **API Keys** (admin only) — issue a key for an external application; the raw key is shown exactly once.

Scale worker capacity with:

```bash
docker compose up --scale worker=3
```

## API

All `/api/v1/*` and `/audio/*` routes accept either the browser session cookie or an `X-API-Key: pvx_...` header.

| Method & path | Purpose |
|---|---|
| `GET /health` | Liveness/readiness check (Postgres + Redis) |
| `GET /api/v1/languages` | Supported language codes/names |
| `GET /api/v1/voices` | Available voice ids (`M1`-`M5`, `F1`-`F5`) |
| `POST /api/v1/jobs` | `{"text": "...", "lang": "hi", "voice": "F1", "speed": 1.0, "steps": 8}` → `202 {"job_id": "..."}` |
| `GET /api/v1/jobs/{job_id}` | Job status; includes `audio_url` once `status` is `finished` |
| `GET /api/v1/jobs` | Caller's own job history |
| `GET /audio/{job_id}.wav` | The synthesized audio (requires the same auth as above, `410` once expired) |

Example:

```bash
curl -X POST http://localhost:8000/api/v1/jobs \
  -H "X-API-Key: pvx_..." -H "Content-Type: application/json" \
  -d '{"text": "नमस्ते, यह एक परीक्षण है।", "lang": "hi", "voice": "F1"}'
# => {"job_id": "...", "status": "queued", ...}

curl http://localhost:8000/api/v1/jobs/<job_id> -H "X-API-Key: pvx_..."
# => {"status": "finished", "audio_url": "/audio/<job_id>.wav", ...}

curl http://localhost:8000/audio/<job_id>.wav -H "X-API-Key: pvx_..." --output out.wav
```

## Configuration

See `.env.example` for the full list. Notable ones:

- `MAX_TEXT_CHARS` — rejects a job before it's even queued if the text is longer than this (default 20000).
- `AUDIO_TTL_SECONDS` / `AUDIO_STORAGE_MAX_BYTES` — cleanup policy for generated audio, enforced by a background
  task in the `web` process every `AUDIO_CLEANUP_INTERVAL_SECONDS`.
- `ONNX_THREADS` — ONNX Runtime's intra-op thread count for the `worker` process. The library's default can
  oversubscribe hybrid CPUs; 4 is a reasonable starting point, tune per host.

## Deploying on Coolify

1. Point a Coolify "Docker Compose" application at this repo (branch `master`, compose file
   `docker-compose.yaml`).
2. Set the environment variables from `.env.example` in Coolify's UI — in particular `SECRET_KEY`,
   `ADMIN_EMAIL`/`ADMIN_PASSWORD`, and `DATABASE_URL`/`REDIS_URL` pointed at your actual shared Postgres/Redis
   instances. Use the **container name** (or resource UUID) as the hostname, not a human-readable display name —
   `docker inspect <container>` is the reliable way to confirm it resolves on the shared Docker network.
3. Create a dedicated database for Polyvox on the shared Postgres first (`CREATE DATABASE polyvox;`) rather than
   reusing another app's database.
4. Only the `web` service publishes a port (`8000`); point Coolify's domain/HTTPS proxy at it. Leave `ENV=production`
   so session cookies are marked `Secure` (requires HTTPS, which Coolify's proxy provides).
5. `worker` can be scaled to multiple replicas from Coolify once you need more synthesis throughput; it has its
   own model-cache volume so replicas don't re-download weights on restart.

## Notes

- The `web` process never loads the Supertonic model — only `worker` does. Voice ids are a static list; the
  language list is read from `supertonic.config` at import time (cheap, no model weights involved).
- RQ workers use `SimpleWorker` (no forking): onnxruntime's internal thread pools make fork()-after-model-load a
  known deadlock hazard, and `SimpleWorker` also lets each worker process load the model exactly once and reuse
  it for every job.
- Database tables are created on startup via `Base.metadata.create_all()` — there's no migration framework yet;
  add one (e.g. Alembic) before making breaking schema changes in production.
