# YouTube 留言多模組分析與視覺化系統之設計與實作

[English](README.md)

本專案整合 YouTube 資料擷取、自然語言處理、LLM 推論、非同步工作佇列、Discord Bot 與網頁介面。使用者可提交 YouTube 影片網址，取得主題、情緒、批評意見、影片內容脈絡及綜合分析結果。

## 系統架構

```text
本機開發
Browser
  -> Next.js /api/inference/*
  -> http://127.0.0.1:8000
  -> FastAPI
  -> AnalysisQueue
  -> 推論流程

Vercel 部署
Browser
  -> Vercel Next.js /api/inference/*
  -> Tailscale Funnel HTTPS
  -> 本機 Docker :8000
  -> FastAPI
  -> AnalysisQueue
  -> 推論流程
```

瀏覽器不會直接呼叫 FastAPI。所有推理請求一律先進入 Next.js Proxy，因此本機與 Vercel 使用相同的前端程式碼，只需切換伺服器端的 `INFERENCE_API_BASE`。

完成的分析結果會由 Next.js 寫入 PostgreSQL，供歷史紀錄頁面查詢與刪除。

## 主要技術

- Backend：Python、FastAPI、Uvicorn
- Inference：PyTorch、Ollama、Whisper
- Frontend：Next.js、React、Tailwind CSS、Recharts
- Database：PostgreSQL、Prisma
- Runtime：Docker、NVIDIA CUDA
- Public ingress：Tailscale Funnel
- Deployment：Vercel

## 專案結構

```text
graduation_project/
├─ docker/
│  ├─ compose.yml              # GPU backend service
│  ├─ Dockerfile
│  ├─ cu118.env                # CUDA 11.8 build parameters
│  ├─ cu128.env                # CUDA 12.8 build parameters
│  └─ pt2.7-cu*.txt            # Python dependencies
├─ project/
│  ├─ agents/                  # LLM agents and Ollama integration
│  ├─ backend/interface.py     # FastAPI HTTP interface
│  ├─ bot/                     # Discord Bot
│  ├─ configs/                 # Shared schemas and settings
│  ├─ data/                    # YouTube access and preprocessing
│  ├─ frontend/                # Next.js application
│  ├─ model/                   # Model loading and processing
│  ├─ pipeline/                # Analysis workflows and job queue
│  ├─ scripts/                 # Development launch scripts
│  └─ .env                     # Local backend secrets, not committed
└─ README.md
```

## 環境需求

- Python 與虛擬環境，或 Docker
- NVIDIA GPU 與驅動程式
- Ollama running on the host when an analysis mode requires an LLM
- Bun for local frontend development
- PostgreSQL database for analysis history
- Tailscale with Funnel enabled when Vercel must reach the local backend

使用 Docker GPU 執行時，還需要 Docker Compose 與 NVIDIA Container Toolkit。使用原生 Python 執行時，則需要安裝與 GPU、CUDA 驅動相容的 PyTorch。

## 後端設定

Copy `project/.env.template` to `project/.env`, then replace all required values:

```env
INFERENCE_API_SECRET=generate-a-long-random-secret

TOKEN=YOUR_DISCORD_BOT_TOKEN
API_KEY=YOUR_YOUTUBE_API_KEY

OLLAMA_HOST=http://host.docker.internal:11434
# 不使用 Docker 時改為：
# OLLAMA_HOST=http://127.0.0.1:11434
OLLAMA_MODEL=gemma3:12b

WHISPER_MODEL_SIZE=small
WHISPER_BEAM_SIZE=8
WHISPER_BEST_OF=5
WHISPER_PATIENCE=1.2
WHISPER_CONDITION_ON_PREVIOUS_TEXT=True
```

`INFERENCE_API_SECRET` 是自行產生的共享密鑰，不是 Tailscale token。FastAPI 會驗證 Next.js Proxy 傳入的 Bearer token。

可使用 PowerShell 產生密鑰：

```powershell
$bytes = New-Object byte[] 32
$rng = New-Object System.Security.Cryptography.RNGCryptoServiceProvider
$rng.GetBytes($bytes)
$rng.Dispose()
[Convert]::ToBase64String($bytes)
```

## 啟動後端

### CUDA 12.8

```powershell
docker compose --env-file ./docker/cu128.env -f ./docker/compose.yml up -d --build
```

### CUDA 11.8

```powershell
docker compose --env-file ./docker/cu118.env -f ./docker/compose.yml up -d --build
```

後端啟動後可從主機存取：

```text
http://127.0.0.1:8000
```

查看狀態：

```powershell
curl.exe -H "Authorization: Bearer YOUR_SECRET" http://127.0.0.1:8000/status
```

停止服務：

```powershell
docker compose --env-file ./docker/cu128.env -f ./docker/compose.yml down
```

如需同時移除 Compose volumes：

```powershell
docker compose --env-file ./docker/cu128.env -f ./docker/compose.yml down -v
```

## 不使用 Docker 啟動後端

以下指令都從 repository 根目錄開始執行。

### Windows PowerShell

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r docker/pt2.7-cu128.txt
Set-Location project
python -m uvicorn backend.interface:app --reload --host 0.0.0.0 --port 8000
```

CUDA 11.8 環境請改用：

```powershell
python -m pip install -r docker/pt2.7-cu118.txt
```

### Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r docker/pt2.7-cu128.txt
cd project
python -m uvicorn backend.interface:app --reload --host 0.0.0.0 --port 8000
```

原生執行時，請在 `project/.env` 設定：

```env
OLLAMA_HOST=http://127.0.0.1:11434
```

若依賴檔提供的 PyTorch 版本與本機 GPU 或 CUDA 驅動不相容，請先依 PyTorch 官方安裝方式選擇合適版本，再啟動 FastAPI。

## 本機前端

前端的完整安裝、資料庫與 API 說明請參考 [前端中文說明](project/frontend/README.zh-TW.md)。

本機串聯的核心設定如下：

```env
INFERENCE_API_BASE=http://127.0.0.1:8000
INFERENCE_API_SECRET=與 project/.env 相同的值
```

請求路徑：

```text
Browser -> localhost:3000/api/inference/* -> localhost:8000
```

## Vercel 與 Tailscale Funnel

Tailscale Funnel 將 Docker 發佈到主機的 `8000` port 轉成公開 HTTPS 網址。先在 Tailscale 管理介面啟用 MagicDNS、HTTPS 與 Funnel，再以系統管理員 PowerShell 執行：

```powershell
tailscale funnel --bg 8000
tailscale funnel status
```

狀態輸出會提供類似以下網址：

```text
https://your-machine.your-tailnet.ts.net
```

在 Vercel Project Settings 的 Environment Variables 設定：

```env
INFERENCE_API_BASE=https://your-machine.your-tailnet.ts.net
INFERENCE_API_SECRET=與 project/.env 相同的值
DATABASE_URL=YOUR_POSTGRES_RUNTIME_URL
DIRECT_URL=YOUR_POSTGRES_DIRECT_URL
```

所有變數皆為伺服器端設定，不可加上 `NEXT_PUBLIC_`。修改 Vercel 環境變數後需重新部署。

Vercel 的請求流程：

```text
Browser
  -> Vercel /api/inference/*
  -> Authorization: Bearer INFERENCE_API_SECRET
  -> Tailscale Funnel
  -> FastAPI :8000
```

停止公開 Funnel：

```powershell
tailscale funnel reset
```

Tailscale Funnel 指令與限制請參考 [Tailscale 官方文件](https://tailscale.com/docs/reference/tailscale-cli/funnel)。

## 後端 API

| Method | Path | Description |
|---|---|---|
| `GET` | `/` | 基本服務資訊 |
| `GET` | `/status` | 服務、worker 與 queue 狀態 |
| `POST` | `/jobs` | 建立非同步分析工作 |
| `GET` | `/jobs/{job_id}` | 查詢工作狀態與部分結果 |
| `GET` | `/jobs/{job_id}/result` | 取得完成結果 |
| `POST` | `/queue` | 建立工作並等待結果，保留相容用途 |

當 `INFERENCE_API_SECRET` 有設定時，`/status`、`/jobs*` 與 `/queue` 都需要：

```http
Authorization: Bearer <INFERENCE_API_SECRET>
```

支援的 job mode：

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

## Discord Bot

在 `project` 目錄執行：

```powershell
python -m bot.bot
```

需先在 `project/.env` 設定 Discord `TOKEN`、YouTube `API_KEY` 及相關模型參數。

## 疑難排解

### Vercel 顯示推理服務未啟動

依序確認：

1. Docker backend 或原生 FastAPI process 正在執行。
2. `http://127.0.0.1:8000/status` 可從主機存取。
3. `tailscale funnel status` 顯示 port `8000` 正在公開。
4. Vercel 的 `INFERENCE_API_BASE` 使用正確 Funnel HTTPS URL。
5. Vercel 與 `project/.env` 的 `INFERENCE_API_SECRET` 完全相同。

### FastAPI 回傳 401

代表 Bearer token 缺失或不一致。修改環境變數後需重啟 Docker backend 或原生 FastAPI process，Vercel 端則需重新部署。

### Tailscale CLI 顯示 Access denied

在 Windows 上請使用系統管理員 PowerShell 執行 Funnel 指令。

### Ollama 無法連線

確認主機的 Ollama 正在執行。Docker backend 使用：

```env
OLLAMA_HOST=http://host.docker.internal:11434
```

原生 backend 使用：

```env
OLLAMA_HOST=http://127.0.0.1:11434
```
