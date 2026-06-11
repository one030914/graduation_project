# Web Frontend（繁體中文）

**YouTube 留言多模組分析與視覺化系統之設計與實作**之前端應用。

[English](README.md)

本目錄是專案的 Next.js 網頁應用，負責：

- 提供 YouTube 分析操作介面
- 透過 Next.js Proxy 呼叫 FastAPI
- 輪詢非同步推理工作並顯示結果
- 將完成的分析寫入 PostgreSQL
- 查詢與刪除歷史分析紀錄

## 架構

```text
Browser
  -> Next.js pages
  -> /api/inference/*        -> FastAPI
  -> /api/analysis-records   -> PostgreSQL
  -> /api/history            -> PostgreSQL
```

瀏覽器只呼叫同網域的 Next.js API。FastAPI 網址與 `INFERENCE_API_SECRET` 僅存在於 Next.js server runtime，不會包含在瀏覽器 bundle。

## 環境需求

- Bun
- 已啟動的 FastAPI backend，可使用 Docker 或原生 Python
- PostgreSQL database
- Node-compatible environment variables

後端的 Docker 與原生安裝方式請參考 [根目錄中文說明](../../README.zh-TW.md)。

## 環境變數

將 `.env.template` 複製為本目錄下的 `.env`。`.env` 已被 Git 忽略，不應提交任何真實憑證。

### 本機開發

```env
DATABASE_URL=YOUR_POSTGRES_RUNTIME_URL
DIRECT_URL=YOUR_POSTGRES_DIRECT_URL

INFERENCE_API_BASE=http://127.0.0.1:8000
INFERENCE_API_SECRET=與 project/.env 相同的值
```

### Vercel

在 Vercel Project Settings 設定：

```env
DATABASE_URL=YOUR_POSTGRES_RUNTIME_URL
DIRECT_URL=YOUR_POSTGRES_DIRECT_URL

INFERENCE_API_BASE=https://your-machine.your-tailnet.ts.net
INFERENCE_API_SECRET=與 project/.env 相同的值
```

變數用途：

| Variable | Purpose |
|---|---|
| `DATABASE_URL` | Next.js runtime 使用的 PostgreSQL connection string |
| `DIRECT_URL` | Prisma CLI schema 操作使用的 direct connection string |
| `INFERENCE_API_BASE` | Next.js Proxy 要呼叫的 FastAPI base URL |
| `INFERENCE_API_SECRET` | Proxy 與 FastAPI 共用的 Bearer secret |

以上變數均為伺服器端設定，不可使用 `NEXT_PUBLIC_` 前綴。

## 安裝與啟動

```powershell
cd project/frontend
bun install
bun run dev
```

開啟：

```text
http://127.0.0.1:3000
```

其他指令：

```powershell
bun run lint
bun run build
bun run start
```

當前端在 Docker bind mount 環境開發且需要 polling watcher 時，可使用：

```powershell
bun run dev:docker
```

前端本身不依賴 Docker，只要 `INFERENCE_API_BASE` 指向可連線的 FastAPI backend 即可。

## 資料庫設定

Prisma schema 位於 `prisma/schema.prisma`，目前使用 PostgreSQL 並儲存分析結果。

產生 Prisma Client：

```powershell
bunx prisma generate
```

將目前 schema 同步至開發資料庫：

```powershell
bunx prisma db push
```

資料表 `analysis` 主要欄位：

| Field | Description |
|---|---|
| `job_id` | FastAPI queue job ID |
| `mode` | 分析模式 |
| `title` | 影片標題或替代名稱 |
| `url` | YouTube URL |
| `payload` | 完整分析結果 JSON |
| `createdAt` | 建立時間 |

## 請求流程

1. Browser 呼叫 `POST /api/inference/jobs`。
2. Next.js Proxy 將請求轉送至 FastAPI `POST /jobs`。
3. Browser 輪詢 `GET /api/inference/jobs/{job_id}`。
4. 工作完成後取得 `GET /api/inference/jobs/{job_id}/result`。
5. Browser 將成功結果送至 `POST /api/analysis-records`。
6. Next.js 使用 Prisma 將紀錄寫入 PostgreSQL。

本機與 Vercel 的程式流程完全相同，只有 `INFERENCE_API_BASE` 不同：

```text
Local:  http://127.0.0.1:8000
Vercel: https://your-machine.your-tailnet.ts.net
```

## Next.js API 路由

### 推理代理

Base path：

```text
/api/inference
```

允許的路徑：

| Method | Next.js Path | FastAPI Path |
|---|---|---|
| `GET` | `/api/inference/status` | `/status` |
| `POST` | `/api/inference/jobs` | `/jobs` |
| `GET` | `/api/inference/jobs/{job_id}` | `/jobs/{job_id}` |
| `GET` | `/api/inference/jobs/{job_id}/result` | `/jobs/{job_id}/result` |

Proxy 會：

- 從 `INFERENCE_API_BASE` 建立上游 URL
- 加入 `Authorization: Bearer <INFERENCE_API_SECRET>`
- 限制可代理的路徑
- 停用 response cache
- 將無法連線統一轉換為 `503 INFERENCE_OFFLINE`

### 分析紀錄

```text
POST /api/analysis-records
```

只負責保存已完成且非 cache 命中的分析結果。它不會執行推理。

### 歷史紀錄

```text
GET    /api/history
DELETE /api/history?id={record_id}
```

`GET` 支援：

- `category`：可重複提供的分類篩選
- `q`：影片標題或 URL 搜尋

最多回傳最近 100 筆紀錄。

## 分析模式

Backend 支援：

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

目前首頁顯示的操作：

- 綜合分析
- 熱門主題
- 情緒風向
- 批評回饋
- 影片內容脈絡

其餘模式仍保留於資料流程與結果元件，可視需求重新開放。

## 目錄結構

```text
frontend/
├─ prisma/
│  └─ schema.prisma
├─ public/
├─ src/
│  ├─ app/
│  │  ├─ api/
│  │  │  ├─ analysis-records/ # Save completed results
│  │  │  ├─ history/          # Query and delete records
│  │  │  └─ inference/        # FastAPI proxy
│  │  ├─ history/             # History page
│  │  ├─ layout.jsx
│  │  └─ page.jsx             # Main analysis page
│  ├─ components/
│  │  ├─ charts/
│  │  └─ results/
│  ├─ generated/prisma/       # Generated Prisma Client
│  └─ lib/
├─ .env.template
├─ next.config.mjs
├─ package.json
└─ prisma.config.ts
```

## 驗證

確認 FastAPI proxy：

```powershell
curl.exe http://127.0.0.1:3000/api/inference/status
```

確認 lint 與 production build：

```powershell
bun run lint
bun run build
```

## 疑難排解

### `INFERENCE_CONFIG_ERROR`

Next.js 沒有讀到有效的 `INFERENCE_API_BASE`。確認 `.env` 後重新啟動開發伺服器；Vercel 修改後需重新部署。

### `INFERENCE_AUTH_FAILED`

FastAPI 拒絕 Bearer token。確認 frontend 與 `project/.env` 的 `INFERENCE_API_SECRET` 完全一致。

### `INFERENCE_OFFLINE`

Next.js 無法在時限內連到 FastAPI。檢查 Docker 或原生 backend、port `8000` 及需要時使用的 Tailscale Funnel。

### Database error

確認 `DATABASE_URL` 可由 Next.js runtime 連線，`DIRECT_URL` 可供 Prisma CLI 使用，並確認 schema 已同步至資料庫。
