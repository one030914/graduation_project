# Web Frontend

Frontend for **Design and Implementation of a Multi-Module YouTube Comment Analysis and Visualization System**.

[繁體中文說明](README.zh-TW.md)

This directory contains the Next.js web application. It:

- provides the YouTube analysis interface;
- proxies inference requests to FastAPI;
- polls asynchronous jobs and renders results;
- stores completed analyses in PostgreSQL;
- lists and deletes analysis history.

## Architecture

```text
Browser
  -> Next.js pages
  -> /api/inference/*        -> FastAPI
  -> /api/analysis-records   -> PostgreSQL
  -> /api/history            -> PostgreSQL
```

The browser only calls same-origin Next.js APIs. The FastAPI address and `INFERENCE_API_SECRET` remain in the Next.js server runtime and are never included in the browser bundle.

## Requirements

- Bun
- A running FastAPI backend, with or without Docker
- PostgreSQL

Backend installation options are documented in the [root README](../../README.md).

## Environment Variables

Copy `.env.template` to `.env`. The `.env` file is ignored by Git.

Local development:

```env
DATABASE_URL=YOUR_POSTGRES_RUNTIME_URL
DIRECT_URL=YOUR_POSTGRES_DIRECT_URL

INFERENCE_API_BASE=http://127.0.0.1:8000
INFERENCE_API_SECRET=the-same-value-as-project/.env
```

Vercel:

```env
DATABASE_URL=YOUR_POSTGRES_RUNTIME_URL
DIRECT_URL=YOUR_POSTGRES_DIRECT_URL

INFERENCE_API_BASE=https://your-machine.your-tailnet.ts.net
INFERENCE_API_SECRET=the-same-value-as-project/.env
```

| Variable | Purpose |
|---|---|
| `DATABASE_URL` | PostgreSQL connection used by the Next.js runtime |
| `DIRECT_URL` | Direct PostgreSQL connection used by Prisma CLI |
| `INFERENCE_API_BASE` | FastAPI base URL used by the Next.js proxy |
| `INFERENCE_API_SECRET` | Bearer secret shared by the proxy and FastAPI |

These are server-side variables. Do not use the `NEXT_PUBLIC_` prefix.

## Install and Run

```powershell
cd project/frontend
bun install
bun run dev
```

Open `http://127.0.0.1:3000`.

Other commands:

```powershell
bun run lint
bun run build
bun run start
```

For a bind-mounted development environment that needs polling:

```powershell
bun run dev:docker
```

The frontend does not require Docker. It only requires a reachable FastAPI backend at `INFERENCE_API_BASE`.

## Database Setup

The Prisma schema is located at `prisma/schema.prisma`.

```powershell
bunx prisma generate
bunx prisma db push
```

The `analysis` table stores:

| Field | Description |
|---|---|
| `job_id` | FastAPI queue job ID |
| `mode` | Analysis mode |
| `title` | Video title or fallback name |
| `url` | YouTube URL |
| `payload` | Complete result JSON |
| `createdAt` | Creation timestamp |

## Request Flow

1. The browser sends `POST /api/inference/jobs`.
2. Next.js forwards it to FastAPI `POST /jobs`.
3. The browser polls `GET /api/inference/jobs/{job_id}`.
4. It reads `GET /api/inference/jobs/{job_id}/result` after completion.
5. It sends successful results to `POST /api/analysis-records`.
6. Next.js stores the record through Prisma.

Local and Vercel execution use the same code. Only `INFERENCE_API_BASE` changes:

```text
Local:  http://127.0.0.1:8000
Vercel: https://your-machine.your-tailnet.ts.net
```

## Next.js API Routes

### Inference Proxy

| Method | Next.js Path | FastAPI Path |
|---|---|---|
| `GET` | `/api/inference/status` | `/status` |
| `POST` | `/api/inference/jobs` | `/jobs` |
| `GET` | `/api/inference/jobs/{job_id}` | `/jobs/{job_id}` |
| `GET` | `/api/inference/jobs/{job_id}/result` | `/jobs/{job_id}/result` |

The proxy:

- builds the upstream URL from `INFERENCE_API_BASE`;
- adds `Authorization: Bearer <INFERENCE_API_SECRET>`;
- allows only known inference routes;
- disables response caching;
- converts connection failures to `503 INFERENCE_OFFLINE`.

### Analysis Records

```text
POST /api/analysis-records
```

This route only stores completed, non-cached analysis results. It does not run inference.

### History

```text
GET    /api/history
DELETE /api/history?id={record_id}
```

`GET` supports repeated `category` filters and a `q` search parameter. It returns at most the latest 100 records.

## Analysis Modes

The backend supports:

```text
analyze
summary
keyword
topics
emotion
video_content
criticism
timeline
```

The current home page exposes combined analysis, topics, sentiment, criticism, and video context.

## Project Layout

```text
frontend/
├─ prisma/
│  └─ schema.prisma
├─ public/
├─ src/
│  ├─ app/
│  │  ├─ api/
│  │  │  ├─ analysis-records/
│  │  │  ├─ history/
│  │  │  └─ inference/
│  │  ├─ history/
│  │  ├─ layout.jsx
│  │  └─ page.jsx
│  ├─ components/
│  ├─ generated/prisma/
│  └─ lib/
├─ .env.template
├─ next.config.mjs
├─ package.json
└─ prisma.config.ts
```

## Verification

With the frontend and backend running:

```powershell
curl.exe http://127.0.0.1:3000/api/inference/status
```

Run project checks:

```powershell
bun run lint
bun run build
```

## Troubleshooting

### `INFERENCE_CONFIG_ERROR`

`INFERENCE_API_BASE` is missing or invalid. Restart the development server after editing `.env`; redeploy Vercel after changing project variables.

### `INFERENCE_AUTH_FAILED`

The backend rejected the Bearer token. Ensure the frontend and `project/.env` use the same `INFERENCE_API_SECRET`.

### `INFERENCE_OFFLINE`

Next.js could not reach FastAPI before the timeout. Check the native or Docker backend, port `8000`, and Tailscale Funnel when applicable.

### Database errors

Verify that `DATABASE_URL` is reachable from the Next.js runtime, `DIRECT_URL` is valid for Prisma CLI, and the schema has been applied.
