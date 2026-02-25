# graduation_project

## Startup

cd to project folder and use command: `python -m bot.bot`

## Project Structure

```
project/
 ├─ bot/
 │  ├─ cogs/            # bot feature modules
 │  ├─ core/
 │  │  └─ classes.py    # importing bot cogs
 │  ├─ utils/           # custom discord components
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
```

# Todos

## Rebuilding project
-   [x] bot and cogs
-   [x] youtube api
-   [x] preprocess
-   [x] models
-   [x] pipeline
-   [x] multi-task
-   [ ] models train again?

## Add-ons
-   [x] top comments
-   [ ] topics
-   [ ] sentiment
-   [ ] trend comments
-   [ ] spam comments dectection
