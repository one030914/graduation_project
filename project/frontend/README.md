# Website Interface

## Startup

### Frontend

From `project/frontend`, start the Next.js development server with Bun:

```bash
bun install
bun run dev # for local enviroment
bun run dev:docker # for docker container
```

### Backend Interface

Open a new terminal from the project root and start the FastAPI interface:

***for local enviroment***

```bash
uvicorn backend.interface:app --reload
```

***for docker container***

```bash
./scripts/dev-backend.sh
```

## Backend Interface Usage

The frontend communicates with `project/backend/interface.py`, which exposes a queue-based API for comment analysis.

### Available job modes

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

### Main endpoints

#### `POST /queue`

Runs a job through the queue and waits for the result before returning.

Example request body:

```json
{
  "video_url": "https://www.youtube.com/watch?v=example",
  "job_mode": "analyze"
}
```

#### `POST /jobs`

Creates a queue job and returns a `job_id` for polling.

Example request body:

```json
{
  "video_url": "https://www.youtube.com/watch?v=example",
  "job_mode": "topics"
}
```

Example response:

```json
{
  "job_id": "your-job-id",
  "status": "queued",
  "mode": "topics"
}
```

#### `GET /jobs/{job_id}`

Returns the current job status.

Possible states:

```text
queued
running
completed
failed
```

#### `GET /jobs/{job_id}/result`

Returns the completed result payload.

- `202` if the job is still running
- `500` if the job failed
- `200` with `result` if the job completed successfully

### Current frontend flow

The current frontend uses the async queue flow:

1. Submit a job with `POST /jobs`
2. Poll the job status with `GET /jobs/{job_id}`
3. Fetch the final result from `GET /jobs/{job_id}/result`

## Frontend Structure

```text
frontend/
├─ prisma/                 # Prisma schema and database configuration
├─ public/                 # Static assets
├─ src/
│  ├─ app/                 # Next.js App Router pages and API routes
│  │  ├─ api/
│  │  │  └─ history/       # History record API route
│  │  ├─ history/          # History page
│  │  ├─ globals.css       # Global styles and animated background
│  │  ├─ layout.jsx        # Root layout
│  │  └─ page.jsx          # Home page
│  ├─ components/          # Shared UI components
│  │  └─ results/          # Analysis result view components
│  └─ lib/                 # Shared helpers and configuration
├─ .env.template           # Environment variable template
├─ jsconfig.json           # Path alias configuration
├─ next.config.mjs         # Next.js configuration
├─ package.json            # Scripts and dependencies
├─ postcss.config.mjs      # PostCSS configuration
├─ prisma.config.ts        # Prisma configuration
└─ bun.lock                # Bun lockfile
```
