import json
from ollama import Client
import re
from typing import List, Optional
from data.youtube.api import API
from data.preprocess.pipeline import batch_preprocess_comments
from configs.schema import CommentCriticismResult

def analyze_comment_criticism(
    video_url: str, 
    pages: int = 5, 
    page_size: int = 100, 
    min_likes: int = 0, 
    model_name: str = "llama3.2"
) -> CommentCriticismResult:
    """
    抓取 YouTube 影片留言，經過預處理後，使用 Ollama 模型分析觀眾集體的批評、不滿與改進建議。
    """
    api = API()
    
    # 1. 提取影片 ID 與基本資訊
    video_id = api.extract_video_id(video_url)
    if not video_id:
        return CommentCriticismResult(
            url=video_url, 
            error="Invalid YouTube URL / video_id not found."
        )

    video_info = api.get_video_info(video_id)
    title = (video_info or {}).get("title") or video_id

    # 2. 抓取 YouTube 留言 (對齊專題原本的 API 規格)
    try:
        comments = api.get_comments(
            url=video_url, 
            page_size=page_size, 
            pages=pages, 
            min_likes=min_likes
        )
    except Exception as e:
        return CommentCriticismResult(
            video_id=video_id, 
            title=title, 
            url=video_url, 
            error=f"無法抓取留言: {str(e)}"
        )
    
    if len(comments) < 5:
        return CommentCriticismResult(
            video_id=video_id, 
            title=title, 
            url=video_url, 
            error="留言數量過少，無法進行輿情批評分析。"
        )
    
    # 3. 執行留言預處理 (過濾廣告、機器人訊息與分詞)
    df = batch_preprocess_comments(comments)
    if df.empty:
        return CommentCriticismResult(
            video_id=video_id, 
            title=title, 
            url=video_url, 
            error="留言經預處理清洗後為空。"
        )

    # 4. 準備文本 (選取前 150 條清洗後的留言作為分析樣本)
    cleaned_comments = df["清理後留言"].dropna().tolist()
    sampled_comments = cleaned_comments[:150]
    comments_block = "\n".join([f"- {c}" for c in sampled_comments])

    # 5. 設計用於留言分析的 System Prompt
    system_prompt = (
        "你是一位精通網路社群輿情觀測與精準數據分析的專家。\n"
        "請仔細閱讀提供的一組 YouTube 影片留言，從中統整並客觀歸納出『觀眾在留言中所表達的批評、抱怨、質疑或反對意見』。\n"
        "注意：如果留言大部分是正面的，請精確挑出少數具建設性的批評；如果充斥大量謾罵，請將其提煉為具體的抱怨原因。\n"
        "必須使用『繁體中文（Traditional Chinese）』回答。\n"
        "請直接輸出符合以下 JSON 格式的內容，不要包含任何額外的解釋或 Markdown 標籤：\n"
        "{\n"
        '  "main_criticisms": ["主要批評點 1", "主要批評點 2"],\n'
        '  "discontent_reasons": ["不滿的底層原因 1", "不滿的底層原因 2"],\n'
        '  "suggestions": ["改進建議 1", "改進建議 2"]\n'
        "}"
    )
    
    user_prompt = f"影片標題: {title}\n觀眾留言清單:\n\"\"\"\n{comments_block}\n\"\"\""

    # 6. 呼叫 Ollama 進行分析與結果解析
    try:
        ollama = Client(host='http://host.docker.internal:11434')
        response = ollama.generate(
            model=model_name,
            system=system_prompt,
            prompt=user_prompt,
            format="json",  # 強制 Ollama 模式輸出 JSON
            options={
                "temperature": 0.2, # 降低隨機性，確保分析結果穩定且基於事實
            }
        )
        
        raw_content = response.get("response", "{}").strip()
        
        # --- 整合解析邏輯：處理 Llama 3 可能多給的 Markdown 程式碼區塊標籤 ---
        # 如果模型回傳包含了 ```json ... ``` 標籤，使用正則表達式將其濾除，只保留內部的 JSON 字串
        if raw_content.startswith("```"):
            raw_content = re.sub(r"^json)?\n|```$", "", raw_content, flags=re.IGNORECASE).strip()
        
        # 將字串轉換為 Python 字典
        data = json.loads(raw_content)
        
        # 將解析結果灌入 CommentCriticismResult 物件
        return CommentCriticismResult(
            video_id=video_id,
            title=title,
            url=video_url,
            main_criticisms=data.get("main_criticisms", []),
            discontent_reasons=data.get("discontent_reasons", []),
            suggestions=data.get("suggestions", []),
        )
        
    except Exception as e:
        return CommentCriticismResult(
            video_id=video_id, 
            title=title, 
            url=video_url, 
            error=f"Ollama 輿情分析解析失敗: {str(e)}"
        )