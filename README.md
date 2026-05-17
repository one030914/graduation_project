# graduation_project

## Startup

### Docker build

Use these commands depending on your situation:

- Build or rebuild the image, then start the container:

```bash
docker compose --env-file ./docker/cu128.env -f ./docker/compose.yml up -d --build
```

- Start the container directly when the image already exists and nothing in the build config has changed:

```bash
docker compose --env-file ./docker/cu128.env -f ./docker/compose.yml up -d
```

- Stop the container and remove volumes:

```bash
docker compose --env-file ./docker/cu128.env -f ./docker/compose.yml down -v
```

CUDA variants:

- Default uses image tag `cu128`, `pt2.7-cu128.txt`, and `pytorch/pytorch:2.7.0-cuda12.8-cudnn9-runtime`
- To switch variant in both `CMD` and `PowerShell`, use `--env-file`
- `cu118` example:

```bash
docker compose --env-file ./docker/cu118.env -f ./docker/compose.yml up -d --build
```

- `cu128` example:

```bash
docker compose --env-file ./docker/cu128.env -f ./docker/compose.yml up -d --build
```

### Run the bot

cd to project folder and use command: `python -m bot.bot`.

### Run the website
[This README](https://github.com/one030914/graduation_project/tree/work/project/frontend#readme) explains how to set up the website.

## Project Structure

```
graduation_project/
├─ docker/                  # docker build and compose configuration
├─ project/
│  ├─ backend/              # the frontend bridge
│  ├─ bot/
│  │  ├─ cogs/              # bot feature modules
│  │  ├─ core/
│  │  │  └─ classes.py      # importing bot cogs
│  │  ├─ utils/             # components
│  │  └─ bot.py             # bot entry point
│  ├─ configs/
│  │  ├─ schema.py          # defining custom constants
│  │  └─ settings.py        # constants and settings
│  ├─ data/
│  │  ├─ preprocess/        # comment preprocessing
│  │  └─ youtube/
│  │     └─ api.py          # youtube comment retrieval
│  ├─ frontend/             # website interface
│  ├─ model/
│  │  ├─ models/            # model list
│  │  └─ process/           # model processing
│  ├─ pipeline/             # workflow pipeline
│  ├─ scripts/              # helper scripts
│  ├─ .env                  # environment variables
│  └─ data.json             # persistent storage
├─ .gitignore
└─ README.md
```

# Todos

## Rebuilding project
-   [x] bot and cogs
-   [x] youtube api
-   [x] preprocess
-   [x] models
-   [x] pipeline
-   [x] multi-task
-   [x] rebuild enviroment (consider a lower GPU capable of supporting)
-   [ ] get datasets
-   [ ] retrain models

## Add-ons
-   [x] frontend interface
-   [x] top
-   [x] topics
-   [x] emotion
-   [x] video analysis
-   [x] criticism
-   [x] timeline
-   [x] intent
-   [x] insight