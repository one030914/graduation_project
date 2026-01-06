from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
from typing import Callable, Dict, Optional, Tuple

import discord

from pipeline.schema import Job

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
        analyze_fn: Callable[[str], object],               # analyze(url) -> AnalysisResult
        build_embed_fn: Callable[[object], discord.Embed], # build_summary_embed(result)
        extract_video_id_fn: Callable[[str], Optional[str]],# extract_video_id(url) -> video_id
        workers: int = 2,
        cache_ttl_minutes: int = 10,
        max_queue_size: int = 50,
    ):
        self.analyze_fn = analyze_fn
        self.build_embed_fn = build_embed_fn
        self.extract_video_id_fn = extract_video_id_fn

        self.queue: asyncio.Queue[Job] = asyncio.Queue(maxsize=max_queue_size)
        self.workers = workers
        self.cache_ttl = timedelta(minutes=cache_ttl_minutes)

        self._worker_tasks: list[asyncio.Task] = []
        self._stop_event = asyncio.Event()

        # video_id -> (result, expires_at)
        self._cache: Dict[str, Tuple[object, datetime]] = {}

        # video_id -> asyncio.Lock (同影片只跑一次)
        self._locks: Dict[str, asyncio.Lock] = {}
        
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

    async def submit(self, url: str, message: discord.Message, mode: str = "full") -> None:
        video_id = self.extract_video_id_fn(url) or "unknown"
        job = Job(video_id=video_id, url=url, message=message, created_at=datetime.utcnow(), mode=mode)
        await self.queue.put(job)

    async def _worker_loop(self, worker_id: int) -> None:
        loop = asyncio.get_running_loop()

        while not self._stop_event.is_set():
            job = await self.queue.get()
            try:
                # 1) cache 命中就直接回
                cached_key = self._key(job.video_id, job.mode)
                cached = self._get_cached(cached_key)
                if cached is not None:
                    embed = self.build_embed_fn(cached)
                    await job.message.edit(content="✅（快取）分析完成", embed=embed)
                    continue

                # 2) 同影片去重：同一 video_id 同時只允許一個 worker 做
                lock = self._get_lock(cached_key)
                async with lock:
                    # double-check cache（可能另一個 worker 已算完）
                    cached2 = self._get_cached(cached_key)
                    if cached2 is not None:
                        embed = self.build_embed_fn(cached2)
                        await job.message.edit(content="✅（快取）分析完成", embed=embed)
                        continue

                    # 3) 真的跑 analyze（CPU/IO heavy），丟 executor
                    mode_text = {"full":"全套分析", "summary":"摘要分析", "keywords":"關鍵字分析"}.get(job.mode, job.mode)
                    await job.message.edit(content=f"🔎 {mode_text}中…（模型推論可能需要一點時間）", embed=None)

                    def _run():
                        if job.mode == "summary":
                            return self.analyze_fn(job.url, run_summary=True, run_keywords=False)
                        if job.mode == "keywords":
                            return self.analyze_fn(job.url, run_summary=False, run_keywords=True)
                        return self.analyze_fn(job.url, run_summary=True, run_keywords=True)

                    result = await loop.run_in_executor(None, _run)

                    # 4) 存快取 + 回傳
                    self._set_cache(cached_key, result)
                    embed = self.build_embed_fn(result, mode=job.mode)
                    await job.message.edit(content="✅ 分析完成", embed=embed)

            except Exception as e:
                # 不讓 worker 死掉：回錯誤訊息即可
                try:
                    await job.message.edit(content=f"⚠️ 分析失敗：{type(e).__name__}: {e}", embed=None)
                except Exception:
                    pass
            finally:
                self.queue.task_done()
