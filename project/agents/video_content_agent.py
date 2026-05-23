from __future__ import annotations
import json
from agents.base import BaseAgent

class VideoContentAgent(BaseAgent):
    name = "video_content_agent"

    role = """
    你是一位 YouTube 影片內容分析師。
    你擅長根據影片逐字稿整理影片摘要、重點關鍵字與代表性亮點。
    逐字稿可能來自字幕或 Whisper，因此可能有錯字、斷句錯誤、漏字或辨識錯誤。
    你必須根據上下文修正常見轉錄雜訊，但不能捏造逐字稿中沒有的內容。
    """

    output_schema = """
    {
    "language": "zh 或 en",
    "summary": ["影片內容摘要"],
    "keywords": ["關鍵字"],
    "highlights": ["影片亮點或代表性內容"]
    }
    """

    def analyze_full_transcript(
        self,
        *,
        title: str,
        url: str,
        transcript_text: str,
        language: str,
    ) -> dict:
        user_prompt = f"""
        請根據以下 YouTube 影片逐字稿產生內容分析。

        重要規則：
        1. 只根據逐字稿與影片標題分析，不要捏造內容。
        2. 逐字稿可能有 ASR 錯字，只有在上下文清楚時才修正。
        3. 人名、頻道名、品牌名、作品名不要亂翻譯。
        4. 如果專有名詞不確定，請用保守描述，不要硬猜。
        5. summary 最多 5 點。
        6. keywords 最多 10 個，使用短詞或短語。
        7. highlights 最多 5 點，要是觀眾能快速理解影片重點的內容。
        8. 輸出語言請優先使用逐字稿主要語言；中文請使用繁體中文。
        9. 輸出必須是 JSON object。

        影片標題：
        {title}

        影片網址：
        {url}

        偵測語言：
        {language}

        逐字稿：
        {transcript_text}
        """

        return self.run(
            user_prompt,
            temperature=0.1,
            num_predict=1400,
            num_ctx=12000,
        )

    def analyze_chunk(
        self,
        *,
        title: str,
        chunk_text: str,
        language: str,
        chunk_index: int,
        total_chunks: int,
    ) -> dict:
        user_prompt = f"""
        請分析以下 YouTube 影片逐字稿片段。

        重要規則：
        1. 只根據此片段分析，不要補其他片段沒有的內容。
        2. summary 最多 3 點。
        3. keywords 最多 8 個。
        4. highlights 最多 3 點。
        5. 逐字稿可能有錯字或斷句問題，請只在上下文清楚時修正。
        6. 輸出必須是 JSON object。

        影片標題：
        {title}

        片段：
        {chunk_index}/{total_chunks}

        偵測語言：
        {language}

        逐字稿片段：
        {chunk_text}
        """

        return self.run(
            user_prompt,
            temperature=0.1,
            num_predict=900,
            num_ctx=10000,
        )

    def synthesize_chunks(
        self,
        *,
        title: str,
        url: str,
        language: str,
        chunk_results: list[dict],
    ) -> dict:
        user_prompt = f"""
        以下是同一支 YouTube 影片不同逐字稿片段的分析結果。
        請整合成完整影片內容分析。

        重要規則：
        1. 只保留多個片段中高可信度、明確支持的內容。
        2. 不要把片段中的不確定內容寫成事實。
        3. summary 最多 5 點。
        4. keywords 最多 10 個。
        5. highlights 最多 5 點。
        6. 輸出必須是 JSON object。

        影片標題：
        {title}

        影片網址：
        {url}

        偵測語言：
        {language}

        片段分析結果：
        {json.dumps(chunk_results, ensure_ascii=False, indent=2)}
        """

        return self.run(
            user_prompt,
            temperature=0.1,
            num_predict=1400,
            num_ctx=12000,
        )