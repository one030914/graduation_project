from __future__ import annotations

import asyncio
import uuid
from dataclasses import asdict, is_dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Tuple

from configs.schema import Job, JobStatus
from data.youtube.api import API
from pipeline.analyze import build_analyze
from pipeline.summary import build_summary
from pipeline.keyword import build_keyword
from pipeline.topic import build_topics
from pipeline.emotion import build_emotion
from pipeline.video_content import build_video_content
from pipeline.criticism import analyze_comment_criticism
from pipeline.timeline import build_timeline

_yt_api = API()

def _to_jsonable(obj: Any) -> Any:
    # 讓 FastAPI 之類的 JSON response 可以直接用
    if obj is None:
        return None
    if is_dataclass(obj):
        return {k: _to_jsonable(v) for k, v in asdict(obj).items()}
    if isinstance(obj, dict):
        return {k: _to_jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_to_jsonable(x) for x in obj]
    if isinstance(obj, datetime):
        return obj.isoformat()
    # numpy / pandas 純量
    type_name = type(obj).__name__
    if type_name in ("float32", "float64", "int32", "int64", "bool_"):
        return obj.item()
    if hasattr(obj, "item") and callable(obj.item):
        try:
            return obj.item()
        except Exception:
            pass
    if type_name == "ndarray":
        return [_to_jsonable(x) for x in obj.tolist()]
    return obj

class AnalysisQueue:
    """
    - asyncio.Queue 當任務隊列
    - 固定 N 個 worker 消費任務（控制併發）
    - 同影片去重：同一 video_id 只跑一次
    - TTL cache：短時間重複請求直接回結果
    """

    def __init__(
        self,
        *,
        workers: int = 2,
        cache_ttl_minutes: int = 10,
        max_queue_size: int = 50,
        job_ttl_minutes: int = 60,
    ):
        self.queue: asyncio.Queue[Job] = asyncio.Queue(maxsize=max_queue_size)
        self.workers = workers
        self.cache_ttl = timedelta(minutes=cache_ttl_minutes)
        self.job_ttl = timedelta(minutes=job_ttl_minutes)

        self._worker_tasks: list[asyncio.Task] = []
        self._stop_event = asyncio.Event()

        # video_id -> (result, expires_at)
        self._cache: Dict[str, Tuple[object, datetime]] = {}

        # video_id -> asyncio.Lock (同影片只跑一次)
        self._locks: Dict[str, asyncio.Lock] = {}

        # job_id -> JobStatus / Future / running event
        self._job_status: Dict[str, JobStatus] = {}
        self._job_futures: Dict[str, asyncio.Future] = {}
        self._running_events: Dict[str, asyncio.Event] = {}
        self._cancelled_jobs: set[str] = set()
        self._running_executor_futures: Dict[str, asyncio.Future] = {}
        
    def _key(self, video_id: str, mode: str) -> str:
        return f"{video_id}:{mode}"


    def _get_lock(self, key: str) -> asyncio.Lock:
        lock = self._locks.get(key)
        if lock is None:
            lock = asyncio.Lock()
            self._locks[key] = lock
        return lock

    def _get_cached(self, key: str) -> Optional[object]:
        item = self._cache.get(key)
        if not item:
            return None
        result, exp = item
        if datetime.utcnow() > exp:
            self._cache.pop(key, None)
            return None
        return result

    def _set_cache(self, key: str, result: object) -> None:
        self._cache[key] = (result, datetime.utcnow() + self.cache_ttl)

    async def start(self) -> None:
        if self._worker_tasks:
            return
        self._stop_event.clear()
        for i in range(self.workers):
            self._worker_tasks.append(asyncio.create_task(self._worker_loop(i)))

    async def stop(self) -> None:
        self._stop_event.set()
        # 送停止訊號：放入 None 類似的方式也可，這裡用 cancel
        for t in self._worker_tasks:
            t.cancel()
        await asyncio.gather(*self._worker_tasks, return_exceptions=True)
        self._worker_tasks.clear()

    def queue_size(self) -> int:
        return self.queue.qsize()

    async def submit(self, url: str, mode: str = "analyze") -> str:
        """
        新增一個分析工作並回傳 job_id（web/discord 都用同一套）。
        """
        video_id = _yt_api.extract_video_id(url) or "unknown"
        job_id = uuid.uuid4().hex
        created_at = datetime.utcnow()

        loop = asyncio.get_running_loop()
        future: asyncio.Future = loop.create_future()
        running_event = asyncio.Event()

        self._job_futures[job_id] = future
        self._running_events[job_id] = running_event
        expires_at = created_at + self.job_ttl
        self._job_status[job_id] = JobStatus(
            status="queued",
            video_id=video_id,
            mode=mode,
            created_at=created_at,
            updated_at=created_at,
            expires_at=expires_at,
            from_cache=None,
            error=None,
            result=None,
        )

        job = Job(job_id=job_id, video_id=video_id, url=url, created_at=created_at, mode=mode)
        await self.queue.put(job)
        return job_id

    async def wait_until_running(self, job_id: str, *, timeout: Optional[float] = None) -> bool:
        event = self._running_events.get(job_id)
        if event is None:
            return False
        try:
            if timeout is None:
                await event.wait()
            else:
                await asyncio.wait_for(event.wait(), timeout=timeout)
            return event.is_set()
        except asyncio.TimeoutError:
            return False

    async def wait_for_result(self, job_id: str, *, timeout: Optional[float] = None) -> Any:
        future = self._job_futures.get(job_id)
        if future is None:
            raise KeyError(f"job_id not found: {job_id}")
        if timeout is None:
            return await future
        return await asyncio.wait_for(future, timeout=timeout)

    def cancel_job(self, job_id: str) -> bool:
        st = self._job_status.get(job_id)
        if st is None or st.status in ("completed", "failed", "cancelled"):
            return False

        self._cancelled_jobs.add(job_id)
        st.status = "cancelled"
        st.updated_at = datetime.utcnow()
        st.from_cache = False
        st.error = "Job cancelled by user."
        st.result = None

        future = self._job_futures.get(job_id)
        if future and not future.done():
            future.cancel()

        running_event = self._running_events.get(job_id)
        if running_event:
            running_event.set()

        return True

    def get_status(self, job_id: str) -> Optional[dict]:
        st = self._job_status.get(job_id)
        if st is None:
            return None
        if datetime.utcnow() > st.expires_at:
            self._job_status.pop(job_id, None)
            self._job_futures.pop(job_id, None)
            self._running_events.pop(job_id, None)
            self._cancelled_jobs.discard(job_id)
            self._running_executor_futures.pop(job_id, None)
            return None
        return {
            "job_id": job_id,
            "status": st.status,
            "video_id": st.video_id,
            "mode": st.mode,
            "stage": st.stage,
            "stage_progress": st.stage_progress,
            "partial_result": _to_jsonable(st.partial_result) if st.partial_result else None,
            "from_cache": st.from_cache,
            "error": st.error,
            "created_at": st.created_at.isoformat(),
            "updated_at": st.updated_at.isoformat(),
        }

    def get_result_payload(self, job_id: str) -> Optional[dict]:
        st = self._job_status.get(job_id)
        if st is None or st.status not in ("completed", "failed"):
            return None
        if datetime.utcnow() > st.expires_at:
            self._job_status.pop(job_id, None)
            self._job_futures.pop(job_id, None)
            self._running_events.pop(job_id, None)
            self._cancelled_jobs.discard(job_id)
            self._running_executor_futures.pop(job_id, None)
            return None
        if st.status == "failed" or st.result is None:
            return None
        return _to_jsonable(st.result)

    async def _worker_loop(self, worker_id: int) -> None:
        loop = asyncio.get_running_loop()

        while not self._stop_event.is_set():
            job = await self.queue.get()
            try:
                # 1) cache 命中就直接回
                cached_key = self._key(job.video_id, job.mode)
                if job.job_id in self._cancelled_jobs:
                    st = self._job_status.get(job.job_id)
                    if st:
                        st.status = "cancelled"
                        st.updated_at = datetime.utcnow()
                    continue

                cached = self._get_cached(cached_key)
                if cached is not None:
                    st = self._job_status.get(job.job_id)
                    if st:
                        st.status = "completed"
                        st.updated_at = datetime.utcnow()
                        st.from_cache = True
                        st.error = None
                        st.result = cached
                    future = self._job_futures.get(job.job_id)
                    if future and not future.done():
                        future.set_result(cached)
                    continue

                # 2) 同影片去重：同一 video_id 同時只允許一個 worker 做
                lock = self._get_lock(cached_key)
                async with lock:
                    if job.job_id in self._cancelled_jobs:
                        st = self._job_status.get(job.job_id)
                        if st:
                            st.status = "cancelled"
                            st.updated_at = datetime.utcnow()
                        continue

                    # double-check cache（可能另一個 worker 已算完）
                    cached2 = self._get_cached(cached_key)
                    if cached2 is not None:
                        st = self._job_status.get(job.job_id)
                        if st:
                            st.status = "completed"
                            st.updated_at = datetime.utcnow()
                            st.from_cache = True
                            st.error = None
                            st.result = cached2
                        future = self._job_futures.get(job.job_id)
                        if future and not future.done():
                            future.set_result(cached2)
                        continue

                    # 3) 真的跑 analyze（CPU/IO heavy），丟 executor
                    st = self._job_status.get(job.job_id)
                    if st:
                        st.status = "running"
                        st.updated_at = datetime.utcnow()
                        st.from_cache = False
                        st.error = None
                        st.result = None
                    running_event = self._running_events.get(job.job_id)
                    if running_event:
                        running_event.set()

                    def _run():
                        def _on_progress(stage, progress, partial):
                            st = self._job_status.get(job.job_id)
                            if not st:
                                return
                            try:
                                st.stage = stage
                                st.stage_progress = progress
                                st.partial_result = _to_jsonable(partial)
                                st.updated_at = datetime.utcnow()
                            except Exception as exc:
                                print(
                                    f"[progress] job={job.job_id} stage={stage} "
                                    f"serialize failed: {exc}"
                                )

                        if job.mode == "summary":
                            return build_summary(job.url)
                        elif job.mode == "keyword":
                            return build_keyword(job.url)
                        elif job.mode == "topics":
                            return build_topics(job.url)
                        elif job.mode == "emotion":
                            return build_emotion(job.url)
                        elif job.mode == "video_content":
                            return build_video_content(job.url)
                        elif job.mode == "criticism":
                            return analyze_comment_criticism(job.url)
                        elif job.mode == "timeline":
                            return build_timeline(job.url)
                        elif job.mode == "analyze":
                            return build_analyze(job.url, on_progress=_on_progress)

                        return build_analyze(job.url, on_progress=_on_progress)

                    executor_future = loop.run_in_executor(None, _run)
                    self._running_executor_futures[job.job_id] = executor_future
                    result = await executor_future

                    if job.job_id in self._cancelled_jobs:
                        st = self._job_status.get(job.job_id)
                        if st:
                            st.status = "cancelled"
                            st.updated_at = datetime.utcnow()
                            st.result = None
                        continue

                    # 4) 存快取 + 回傳
                    self._set_cache(cached_key, result)
                    st = self._job_status.get(job.job_id)
                    if st:
                        st.status = "completed"
                        st.updated_at = datetime.utcnow()
                        st.from_cache = False
                        st.error = None
                        st.result = result
                    future = self._job_futures.get(job.job_id)
                    if future and not future.done():
                        future.set_result(result)

            except asyncio.CancelledError:
                st = self._job_status.get(job.job_id)
                if st:
                    st.status = "cancelled"
                    st.updated_at = datetime.utcnow()
                    st.from_cache = False
                    st.error = "Job cancelled by user."
                    st.result = None
            except Exception as e:
                st = self._job_status.get(job.job_id)
                if job.job_id in self._cancelled_jobs:
                    if st:
                        st.status = "cancelled"
                        st.updated_at = datetime.utcnow()
                        st.from_cache = False
                        st.error = "Job cancelled by user."
                        st.result = None
                    continue

                if st:
                    st.status = "failed"
                    st.updated_at = datetime.utcnow()
                    st.from_cache = False
                    st.error = f"{type(e).__name__}: {e}"
                    st.result = None
                future = self._job_futures.get(job.job_id)
                if future and not future.done():
                    future.set_exception(e)
            finally:
                self._running_executor_futures.pop(job.job_id, None)
                self.queue.task_done()