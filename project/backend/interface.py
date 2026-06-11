from contextlib import asynccontextmanager
import hmac
import os

from dotenv import load_dotenv

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from configs.schema import Req
from pipeline.queue import AnalysisQueue

load_dotenv(verbose=True)

# ----------------------
# FastAPI App 初始化
# ----------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    wq = AnalysisQueue(
        workers=2,
        cache_ttl_minutes=10,
        max_queue_size=50,
    )
    await wq.start()
    app.state.web_queue = wq
    yield
    await wq.stop()

app = FastAPI(title="YouTube Comment Analyzer API", lifespan=lifespan)
ALLOWED_JOB_MODES = {
    "analyze",
    "summary",
    "keyword",
    "topics",
    "emotion",
    "video_content",
    "criticism",
    "timeline",
}

inference_api_secret = os.getenv("INFERENCE_API_SECRET", "")

@app.middleware("http")
async def verify_inference_api_secret(request: Request, call_next):
    protected_path = request.url.path in {"/queue", "/jobs", "/status"}
    protected_path = protected_path or request.url.path.startswith("/jobs/")

    if inference_api_secret and protected_path:
        authorization = request.headers.get("Authorization", "")
        scheme, _, token = authorization.partition(" ")
        if scheme.lower() != "bearer" or not hmac.compare_digest(token, inference_api_secret):
            return JSONResponse(
                {"error": "Unauthorized inference request."},
                status_code=401,
            )

    return await call_next(request)

@app.get("/")
def root():
    return {"message": "Topic API running"}

@app.get("/status")
def status(request: Request):
    wq = request.app.state.web_queue
    return {
        "status": "ok",
        "queue_size": wq.queue_size(),
        "workers": wq.workers,
    }

# ----------------------
# POST: 經佇列的分析
# ----------------------
@app.post("/queue")
async def queue(req: Req, request: Request):
    """經 AnalysisQueue 執行；行為對齊 bot/cogs/slash.py 的 mode 呼叫方式。"""
    wq = request.app.state.web_queue
    video_url = req.video_url
    mode = req.job_mode
    if mode not in ALLOWED_JOB_MODES:
        return JSONResponse(
            {"error": f"無效的 job_mode: {mode}. 可用值: {sorted(ALLOWED_JOB_MODES)}"},
            status_code=400,
        )
    try:
        job_id = await wq.submit(video_url, mode=mode)
        # 等待任務完成
        result = await wq.wait_for_result(job_id, timeout=30)
        return {"result": result}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

@app.post("/jobs")
async def create_job(req: Req, request: Request):
    """建立 queue job，回傳 job_id 供前端輪詢。"""
    wq = request.app.state.web_queue
    mode = req.job_mode
    if mode not in ALLOWED_JOB_MODES:
        return JSONResponse(
            {"error": f"無效的 job_mode: {mode}. 可用值: {sorted(ALLOWED_JOB_MODES)}"},
            status_code=400,
        )
    try:
        job_id = await wq.submit(req.video_url, mode=mode)
        return {"job_id": job_id, "status": "queued", "mode": mode}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

@app.get("/jobs/{job_id}")
def get_job_status(job_id: str, request: Request):
    """查詢 queue job 狀態。"""
    wq = request.app.state.web_queue
    status = wq.get_status(job_id)
    if status is None:
        return JSONResponse({"error": "job_id not found or expired"}, status_code=404)
    return status

@app.get("/jobs/{job_id}/result")
def get_job_result(job_id: str, request: Request):
    """取得 queue job 結果；尚未完成會回 202。"""
    wq = request.app.state.web_queue
    status = wq.get_status(job_id)
    if status is None:
        return JSONResponse({"error": "job_id not found or expired"}, status_code=404)

    if status["status"] in ("queued", "running"):
        return JSONResponse(
            {"job_id": job_id, "status": status["status"]},
            status_code=202,
        )

    if status["status"] == "failed":
        return JSONResponse(
            {"job_id": job_id, "status": "failed", "error": status.get("error")},
            status_code=500,
        )

    result = wq.get_result_payload(job_id)
    if result is None:
        return JSONResponse(
            {"job_id": job_id, "status": status["status"], "error": "result not available"},
            status_code=404,
        )

    return {
        "job_id": job_id,
        "status": status["status"],
        "mode": status["mode"],
        "from_cache": status.get("from_cache"),
        "result": result,
    }
