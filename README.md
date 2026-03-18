# graduation_project

## Startup

### Docker build

`docker compose up -d` to bulid up docker container in background, `docker compose down -v` to close the container with volume.

### Run the bot

cd to project folder and use command: `python -m bot.bot`.

## Project Structure

```
project/
 ├─ bot/
 │  ├─ cogs/            # bot feature modules
 │  ├─ core/
 │  │  └─ classes.py    # importing bot cogs
 │  ├─ utils/           # components
 │  ├─ bot.py           # bot entry main launcher
 │  └─ queue.py         # multi-task queue
 ├─ configs/
 │  └─ settings.py      # define custom constent
 ├─ data/               # data processing utilities
 |  ├─ preprocess/      # preprocess comments
 |  └─ youtube/
 │     └─ api.py        # get youtube comments
 ├─ model/
 |  ├─ keyword/         # processing keyword
 |  └─ summary/         # processing summary
 ├─ pipeline/           # workflow
 ├─ scripts/            # additional scripts
 ├─ .env                # enviroment variable
 └─ data.json           # persistent storage
docker-compose.yml      # docker services configuration
Dockerfile              # docker image build instrcutions
requirements.txt        # dependencies
```

# Todos

## Rebuilding project
-   [x] bot and cogs
-   [x] youtube api
-   [x] preprocess
-   [x] models
-   [x] pipeline
-   [x] multi-task
-   [ ] retrain models
-   [ ] rebuild enviroment (consider a lower GPU capable of supporting)

## Add-ons
-   [x] top comments
-   [x] topics
-   [x] emotion
-   [ ] trend comments
-   [ ] spam comments dectection
