# graduation_project

## startup

cd to project folder and use command: `python -m bot.bot`

## structure

```
project/
 ├─ bot/
 │  ├─ cogs/            # bot feature modules
 │  ├─ core/
 │  │  └─ classes.py    # importing bot cogs
 │  ├─ utils/           # custome discord components
 │  ├─ bot.py           # bot entry main launcher
 │  └─ queue.py         # multi-task queue
 ├─ configs/
 │  └─ settings.py      # define custom constent
 ├─ data/               # data processing utilities
 |  ├─ preprocess/      # preprocess comments
 |  └─ youtube/
 │     └─ api.py        # get youtube comments
 ├─ model/              # models
 |  ├─ keyword/         # processing keyword
 |  └─ summary/         # processing summary
 ├─ pipeline/
 |  ├─ analyze.py       # workflow
 |  └─ schema.py        # custom dataclasses
 ├─ scripts/            # external extension
 ├─ .env
 └─ data.json           # persistent storage
```

# Todo

## rebuild project
-   [x] bot and cogs
-   [x] youtube api
-   [x] preprocess
-   [x] models
-   [x] pipeline
-   [x] multi-task
-   [ ] models train again?

## add-ons
-   [ ] 標題分析分類
-   [ ] 留言情緒分析
-   [ ] 縮圖分析分類