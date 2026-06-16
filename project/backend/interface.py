from contextlib import asynccontextmanager
import hmac
import os

from dotenv import load_dotenv

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from configs.analysis_modes import SUPPORTED_JOB_MODES
from configs.schema import Req
from pipeline.queue import AnalysisQueue, AnalysisQueueFull

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
        max_job_results_size=100,
    )
    await wq.start()
    app.state.web_queue = wq
    yield
    await wq.stop()

app = FastAPI(title="YouTube Comment Analyzer API", lifespan=lifespan)
inference_api_secret = os.getenv("INFERENCE_API_SECRET", "")
PROTECTED_PATHS = {"/jobs", "/status"}


class InvalidJobMode(ValueError):
    pass


def _is_protected_path(path: str) -> bool:
    return path in PROTECTED_PATHS or path.startswith("/jobs/")


def _validate_job_mode(mode: str) -> str:
    if mode not in SUPPORTED_JOB_MODES:
        available = ", ".join(sorted(SUPPORTED_JOB_MODES))
        raise InvalidJobMode(f"無效的 job_mode: {mode}. 可用值: {available}")

    return mode

@app.middleware("http")
async def verify_inference_api_secret(request: Request, call_next):
    if inference_api_secret and _is_protected_path(request.url.path):
        authorization = request.headers.get("Authorization", "")
        scheme, _, token = authorization.partition(" ")
        if scheme.lower() != "bearer" or not hmac.compare_digest(token, inference_api_secret):
            return JSONResponse(
                {"error": "Unauthorized inference request."},
                status_code=401,
            )

    return await call_next(request)


@app.exception_handler(InvalidJobMode)
async def invalid_job_mode_handler(request: Request, exc: InvalidJobMode):
    return JSONResponse({"error": str(exc)}, status_code=400)

@app.get("/")
def root():
    return {"message": "Topic API running"}

@app.get("/status")
def status(request: Request):
    wq = request.app.state.web_queue
    return {
        "status": "ok",
        "queue_size": wq.queue_size(),
        "cache_size": wq.cache_size(),
        "cache_sizes_by_mode": wq.cache_sizes_by_mode(),
        "max_cache_size": wq.max_cache_size,
        "stored_result_size": wq.stored_result_size(),
        "max_job_results_size": wq.max_job_results_size,
        "workers": wq.workers,
    }

@app.post("/jobs")
async def create_job(req: Req, request: Request):
    """建立 queue job，回傳 job_id 供前端輪詢。"""
    wq = request.app.state.web_queue
    mode = _validate_job_mode(req.job_mode)
    try:
        job_id = await wq.submit(req.video_url, mode=mode)
        status = wq.get_status(job_id) or {}
        return {
            "job_id": job_id,
            "status": status.get("status", "queued"),
            "mode": status.get("mode", mode),
            "from_cache": status.get("from_cache"),
        }
    except AnalysisQueueFull as e:
        return JSONResponse({"error": str(e)}, status_code=429)
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
