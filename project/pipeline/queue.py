from __future__ import annotations

import asyncio
import uuid
from collections import OrderedDict
from collections.abc import Mapping
from dataclasses import asdict, is_dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from cachetools import FIFOCache

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
from pipeline.dependencies import check_analysis_dependencies

_yt_api = API()

DEFAULT_CACHE_LIMITS_BY_MODE = {
    "analyze": 10,
    "topics": 20,
    "video_content": 20,
    "summary": 50,
    "keyword": 50,
    "emotion": 50,
    "criticism": 50,
    "timeline": 50,
    "default": 50,
}


class AnalysisQueueFull(RuntimeError):
    """Raised when a new job cannot be accepted because the queue is full."""

def _to_jsonable(obj: Any) -> Any:
    # 讓 FastAPI 之類的 JSON response 可以直接用
    if is_dataclass(obj):
        return {k: _to_jsonable(v) for k, v in asdict(obj).items()}
    if isinstance(obj, dict):
        return {k: _to_jsonable(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_to_jsonable(x) for x in obj]
    if isinstance(obj, tuple):
        return [_to_jsonable(x) for x in obj]
    return obj


def _result_error(result: Any) -> Optional[str]:
    if result is None:
        return "result is empty"

    if isinstance(result, dict):
        error = result.get("error")
        status = str(result.get("status") or "").lower()
    else:
        error = getattr(result, "error", None)
        status = str(getattr(result, "status", "") or "").lower()

    if error:
        return str(error)
    if status in {"error", "failed"}:
        return f"result status is {status}"
    return None

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
        max_cache_size: Optional[int | Mapping[str, int]] = None,
        max_job_results_size: int = 100,
        job_ttl_minutes: int = 60,
    ):
        self.queue: asyncio.Queue[Job] = asyncio.Queue(maxsize=max_queue_size)
        self.workers = workers
        self.cache_ttl = timedelta(minutes=cache_ttl_minutes)
        if max_cache_size is None:
            self.max_cache_size = dict(DEFAULT_CACHE_LIMITS_BY_MODE)
        elif isinstance(max_cache_size, Mapping):
            self.max_cache_size = dict(max_cache_size)
        else:
            self.max_cache_size = {"default": max_cache_size}
        self.max_job_results_size = max_job_results_size
        self.job_ttl = timedelta(minutes=job_ttl_minutes)

        self._worker_tasks: list[asyncio.Task] = []
        self._stop_event = asyncio.Event()

        # mode -> FIFOCache。value 仍保存 expires_at，容量與 FIFO 淘汰交給 cachetools。
        self._caches: Dict[str, FIFOCache] = {}

        # video_id:mode -> job_id，目前 queued/running 的工作，避免重複排隊
        self._active_jobs_by_key: Dict[str, str] = {}

        # video_id -> asyncio.Lock (同影片只跑一次)
        self._locks: Dict[str, asyncio.Lock] = {}

        # job_id -> JobStatus / Future / running event
        self._job_status: Dict[str, JobStatus] = {}
        self._job_futures: Dict[str, asyncio.Future] = {}
        self._running_events: Dict[str, asyncio.Event] = {}
        self._running_executor_futures: Dict[str, asyncio.Future] = {}
        self._job_result_order: OrderedDict[str, None] = OrderedDict()
        
    def _key(self, video_id: str, mode: str) -> str:
        return f"{video_id}:{mode}"

    def _mode_from_key(self, key: str) -> str:
        return key.rsplit(":", 1)[-1]

    def _cache_limit_for_mode(self, mode: str) -> int:
        return self.max_cache_size.get(mode, self.max_cache_size.get("default", 0))

    def _cache_for_mode(self, mode: str) -> Optional[FIFOCache]:
        cache = self._caches.get(mode)
        if cache is not None:
            return cache

        limit = self._cache_limit_for_mode(mode)
        if limit <= 0:
            return None

        cache = FIFOCache(maxsize=limit)
        self._caches[mode] = cache
        return cache

    def _cache_sizes_by_mode(self) -> Dict[str, int]:
        self._purge_expired_cache()
        return {mode: len(cache) for mode, cache in self._caches.items()}

    def _get_lock(self, key: str) -> asyncio.Lock:
        lock = self._locks.get(key)
        if lock is None:
            lock = asyncio.Lock()
            self._locks[key] = lock
        return lock

    def _get_cached(self, key: str) -> Optional[object]:
        mode = self._mode_from_key(key)
        cache = self._cache_for_mode(mode)
        if cache is None:
            return None

        item = cache.get(key)
        if not item:
            return None
        result, exp = item
        if datetime.utcnow() > exp:
            cache.pop(key, None)
            return None
        return result

    def _set_cache(self, key: str, result: object) -> None:
        mode = self._mode_from_key(key)
        cache = self._cache_for_mode(mode)
        if cache is None:
            return

        self._purge_expired_cache()
        cache[key] = (result, datetime.utcnow() + self.cache_ttl)

    def _purge_expired_cache(self) -> None:
        now = datetime.utcnow()
        for cache in self._caches.values():
            expired_keys = [key for key, (_, exp) in cache.items() if now > exp]
            for key in expired_keys:
                cache.pop(key, None)

    def _drop_job(self, job_id: str) -> None:
        st = self._job_status.pop(job_id, None)
        if st is not None:
            key = self._key(st.video_id, st.mode)
            if self._active_jobs_by_key.get(key) == job_id:
                self._active_jobs_by_key.pop(key, None)
        self._job_futures.pop(job_id, None)
        self._running_events.pop(job_id, None)
        self._running_executor_futures.pop(job_id, None)
        self._job_result_order.pop(job_id, None)

    def _active_job_id(self, key: str) -> Optional[str]:
        job_id = self._active_jobs_by_key.get(key)
        if job_id is None:
            return None

        st = self._job_status.get(job_id)
        if st is None or st.status not in ("queued", "running"):
            self._active_jobs_by_key.pop(key, None)
            return None

        if datetime.utcnow() > st.expires_at:
            self._drop_job(job_id)
            return None

        return job_id

    def _remember_job_result(self, job_id: str, result: object) -> None:
        st = self._job_status.get(job_id)
        if st is None:
            return

        if self.max_job_results_size <= 0:
            st.result = None
            return

        st.result = result
        self._job_result_order.pop(job_id, None)
        self._job_result_order[job_id] = None

        while len(self._job_result_order) > self.max_job_results_size:
            old_job_id, _ = self._job_result_order.popitem(last=False)
            old_status = self._job_status.get(old_job_id)
            if old_status is not None:
                old_status.result = None
            self._job_futures.pop(old_job_id, None)

    def _complete_job_with_result(
        self,
        job_id: str,
        result: object,
        *,
        from_cache: bool,
    ) -> None:
        st = self._job_status.get(job_id)
        if st:
            st.status = "completed"
            st.updated_at = datetime.utcnow()
            st.from_cache = from_cache
            st.error = None
        self._remember_job_result(job_id, result)

        future = self._job_futures.get(job_id)
        if future and not future.done():
            future.set_result(result)

    def _create_completed_job(self, video_id: str, mode: str, result: object, *, from_cache: bool) -> str:
        job_id = uuid.uuid4().hex
        created_at = datetime.utcnow()
        future: asyncio.Future = asyncio.get_running_loop().create_future()
        running_event = asyncio.Event()
        running_event.set()

        self._job_futures[job_id] = future
        self._running_events[job_id] = running_event
        self._job_status[job_id] = JobStatus(
            status="completed",
            video_id=video_id,
            mode=mode,
            created_at=created_at,
            updated_at=created_at,
            expires_at=created_at + self.job_ttl,
            from_cache=from_cache,
            error=None,
            result=None,
        )
        self._remember_job_result(job_id, result)
        future.set_result(result)
        return job_id

    async def start(self) -> None:
        if self._worker_tasks:
            return
        self._stop_event.clear()
        for i in range(self.workers):
            self._worker_tasks.append(asyncio.create_task(self._worker_loop(i)))

    async def stop(self) -> None:
        self._stop_event.set()
        for t in self._worker_tasks:
            t.cancel()
        await asyncio.gather(*self._worker_tasks, return_exceptions=True)
        self._worker_tasks.clear()

    def queue_size(self) -> int:
        return self.queue.qsize()

    def cache_size(self) -> int:
        self._purge_expired_cache()
        return sum(len(cache) for cache in self._caches.values())

    def cache_sizes_by_mode(self) -> Dict[str, int]:
        return self._cache_sizes_by_mode()

    def stored_result_size(self) -> int:
        return len(self._job_result_order)

    async def submit(self, url: str, mode: str = "analyze") -> str:
        """
        新增一個分析工作並回傳 job_id（web/discord 都用同一套）。
        """
        video_id = _yt_api.extract_video_id(url) or "unknown"
        cache_key = self._key(video_id, mode)

        cached = self._get_cached(cache_key)
        if cached is not None:
            return self._create_completed_job(video_id, mode, cached, from_cache=True)

        active_job_id = self._active_job_id(cache_key)
        if active_job_id is not None:
            return active_job_id

        if self.queue.full():
            raise AnalysisQueueFull("Analysis queue is full. Please retry later.")

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
        try:
            self.queue.put_nowait(job)
        except asyncio.QueueFull as exc:
            self._drop_job(job_id)
            raise AnalysisQueueFull("Analysis queue is full. Please retry later.") from exc

        self._active_jobs_by_key[cache_key] = job_id
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

    def get_status(self, job_id: str) -> Optional[dict]:
        st = self._job_status.get(job_id)
        if st is None:
            return None
        if datetime.utcnow() > st.expires_at:
            self._drop_job(job_id)
            return None
        payload = {
            "job_id": job_id,
            "status": st.status,
            "video_id": st.video_id,
            "mode": st.mode,
            "from_cache": st.from_cache,
            "error": st.error,
            "created_at": st.created_at.isoformat(),
            "updated_at": st.updated_at.isoformat(),
        }
        if st.status == "running" and st.result is not None:
            payload["partial_result"] = _to_jsonable(st.result)
        return payload

    def get_result_payload(self, job_id: str) -> Optional[dict]:
        st = self._job_status.get(job_id)
        if st is None or st.status not in ("completed", "failed"):
            return None
        if datetime.utcnow() > st.expires_at:
            self._drop_job(job_id)
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

                cached = self._get_cached(cached_key)
                if cached is not None:
                    self._complete_job_with_result(job.job_id, cached, from_cache=True)
                    continue

                # 2) 同影片去重：同一 video_id 同時只允許一個 worker 做
                lock = self._get_lock(cached_key)
                async with lock:
                    # double-check cache（可能另一個 worker 已算完）
                    cached2 = self._get_cached(cached_key)
                    if cached2 is not None:
                        self._complete_job_with_result(job.job_id, cached2, from_cache=True)
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
                        check_analysis_dependencies(job.mode)

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
                            def _on_partial(partial_result):
                                partial_status = self._job_status.get(job.job_id)
                                if partial_status and partial_status.status == "running":
                                    partial_status.updated_at = datetime.utcnow()
                                    partial_status.result = partial_result

                            return build_analyze(job.url, on_partial=_on_partial)
                        
                        return build_analyze(job.url)

                    executor_future = loop.run_in_executor(None, _run)
                    self._running_executor_futures[job.job_id] = executor_future
                    result = await executor_future

                    result_error = _result_error(result)
                    if result_error:
                        st = self._job_status.get(job.job_id)
                        if st:
                            st.status = "failed"
                            st.updated_at = datetime.utcnow()
                            st.from_cache = False
                            st.error = result_error
                            st.result = None
                        future = self._job_futures.get(job.job_id)
                        if future and not future.done():
                            future.set_exception(RuntimeError(result_error))
                        continue

                    # 4) 存快取 + 回傳
                    self._set_cache(cached_key, result)
                    self._complete_job_with_result(job.job_id, result, from_cache=False)

            except Exception as e:
                st = self._job_status.get(job.job_id)
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
                active_key = self._key(job.video_id, job.mode)
                if self._active_jobs_by_key.get(active_key) == job.job_id:
                    self._active_jobs_by_key.pop(active_key, None)
                self.queue.task_done()
