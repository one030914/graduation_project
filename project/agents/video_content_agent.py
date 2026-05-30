from __future__ import annotations

import json

from agents.base import BaseAgent


class VideoContentAgent(BaseAgent):
    name = "video_content_agent"

    role = """
    你擅長根據 YouTube 影片逐字稿整理影片內容，產出簡要文章摘要與精選章節時間軸。
    逐字稿可能來自 YouTube 字幕或 Whisper 語音辨識，內容可能有誤聽、漏字、重複詞、標點錯誤或斷句不自然。
    你需要在逐字稿明確支持的範圍內整理內容；可以修正常見轉錄雜訊，但不能捏造影片沒有提到的事實。
    """

    output_schema = """
    {
      "language": "zh",
      "summary_text": "繁體中文單段文章摘要",
      "final_conclusion": "繁體中文影片最終結論",
      "recommended_audience": "繁體中文適合觀看對象",
      "action_suggestions": ["繁體中文看完後可以採取的行動"],
      "chapter_timeline": [
        {
          "start_seconds": 0,
          "end_seconds": 120,
          "title": "繁體中文重點片段標題",
          "summary": "繁體中文片段重點說明",
          "keywords": ["繁體中文短關鍵字"],
          "importance": "high 或 medium 或 low"
        }
      ]
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
        請分析以下 YouTube 影片逐字稿，輸出影片內容摘要與精選章節時間軸。

        輸出要求：
        1. 只能根據逐字稿內容分析，不要引用外部資料，不要捏造逐字稿沒有支持的資訊。
        2. 逐字稿每行可能包含 [開始時間 - 結束時間]，chapter_timeline 必須使用秒數輸出 start_seconds 與 end_seconds。
        3. language 固定輸出 "zh"。
        4. summary_text、章節 title、章節 summary、章節 keywords 都必須使用繁體中文；外文專有名詞、品牌、人名、產品型號保留原文。
        5. summary_text 請寫成一段自然的簡要文章摘要，不要用條列，約 120 到 220 字。
        6. final_conclusion 請用 1 句話整理影片最終結論。
        7. recommended_audience 請用 1 句話說明這支影片適合誰看。
        8. action_suggestions 請列出 2 到 4 個看完後可以採取的具體行動。
        9. chapter_timeline 只放真正重要的片段，預設 3 到 8 段；不需要連續覆蓋整支影片，可以跳過低資訊量區間。
        10. 重要片段包含：核心論點、關鍵示範、重要結論、明顯轉折、爭議說明、實用步驟或高資訊密度段落。
        11. 每個章節 title 要短而具體，summary 用 1 到 2 句說明該片段重點。
        12. 每個章節可包含 keywords，請提供 0 到 5 個繁體中文短詞；沒有明確關鍵字時可輸出空陣列，不要硬補。
        13. 每個章節必須包含 importance，值只能是 "high"、"medium"、"low"。
        14. 不要輸出全影片層級 keywords、highlights、代表片段或 Markdown。
        15. 請輸出單一 JSON object。

        影片標題：
        {title}

        影片網址：
        {url}

        偵測到的逐字稿語言：
        {language}

        逐字稿：
        {transcript_text}
        """

        return self.run(
            user_prompt,
            temperature=0.1,
            num_predict=1500,
            num_ctx=8000,
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
        請分析這一段 YouTube 影片逐字稿，整理候選重點片段。

        輸出要求：
        1. 只能根據此 chunk 內容分析，不要補充外部資訊。
        2. language 固定輸出 "zh"。
        3. summary_text 請用 1 段繁體中文概括此 chunk 的高可信重點。
        4. final_conclusion、recommended_audience、action_suggestions 可針對此 chunk 暫時整理，最終會再整合。
        5. chapter_timeline 請列出此 chunk 中最值得保留的 0 到 3 個重點片段；若此 chunk 沒有明確重點，可輸出空陣列。
        6. 每個章節必須使用逐字稿時間換算 start_seconds 與 end_seconds，且 end_seconds 必須大於 start_seconds。
        7. 每個章節 title、summary、keywords 都必須使用繁體中文；外文專有名詞、品牌、人名、產品型號保留原文。
        8. 每個章節可包含 keywords，請提供 0 到 5 個短詞；沒有明確關鍵字時可輸出空陣列，不要硬補。
        9. 每個章節必須包含 importance，值只能是 "high"、"medium"、"low"。
        10. 不要輸出全影片層級 keywords、highlights、代表片段或 Markdown。
        11. 請輸出單一 JSON object。

        影片標題：
        {title}

        chunk：
        {chunk_index}/{total_chunks}

        偵測到的逐字稿語言：
        {language}

        逐字稿 chunk：
        {chunk_text}
        """

        return self.run(
            user_prompt,
            temperature=0.1,
            num_predict=1000,
            num_ctx=6000,
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
        請將多個逐字稿 chunk 的分析結果整合成整支 YouTube 影片的內容摘要與精選章節時間軸。

        輸出要求：
        1. language 固定輸出 "zh"。
        2. summary_text 請寫成一段自然的繁體中文簡要文章摘要，不要用條列，約 120 到 220 字。
        3. final_conclusion 請用 1 句話整理影片最終結論。
        4. recommended_audience 請用 1 句話說明這支影片適合誰看。
        5. action_suggestions 請列出 2 到 4 個看完後可以採取的具體行動。
        6. chapter_timeline 請從各 chunk 候選片段中選出全片最重要的 3 到 8 段。
        7. 章節時間軸不需要連續覆蓋影片，可以跳過低資訊量區間；請依 start_seconds 由小到大排序。
        8. 合併高度重複或內容相近的片段，保留資訊量最高、最能代表影片重點者。
        9. 每個章節 title、summary、keywords 都必須使用繁體中文；外文專有名詞、品牌、人名、產品型號保留原文。
        10. 每個章節可包含 keywords，請提供 0 到 5 個短詞；沒有明確關鍵字時可輸出空陣列，不要硬補。
        11. 每個章節必須包含 importance，值只能是 "high"、"medium"、"low"。
        12. 不要輸出全影片層級 keywords、highlights、代表片段或 Markdown。
        13. 請輸出單一 JSON object。

        影片標題：
        {title}

        影片網址：
        {url}

        偵測到的逐字稿語言：
        {language}

        chunk 分析結果：
        {json.dumps(chunk_results, ensure_ascii=False, indent=2)}
        """

        return self.run(
            user_prompt,
            temperature=0.1,
            num_predict=1500,
            num_ctx=8000,
        )
