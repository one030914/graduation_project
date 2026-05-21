import json
from ollama import Client
import re
from .collect import collect_comments
from configs.schema import CommentCriticismResult

def analyze_comment_criticism(
    video_url: str, 
    pages: int = 100, 
    page_size: int = 100, 
    min_likes: int = 0, 
    model_name: str = "llama3.2"
) -> CommentCriticismResult:
    """
    抓取 YouTube 影片留言，經過預處理後，使用 Ollama 模型分析觀眾集體的批評、不滿與改進建議。
    """
    comments = collect_comments(url=video_url, pages=pages, page_size=page_size, min_likes=min_likes)
    return analyze_comment_criticism_from_dataset(
        comments,
        model_name=model_name,
    )

def analyze_comment_criticism_from_dataset(
    comments,
    *,
    model_name: str = "llama3.2",
) -> CommentCriticismResult:
    """
    使用已收集與預處理的 YouTube 留言資料，分析觀眾集體的批評、不滿與改進建議。
    """
    if comments.error:
        return CommentCriticismResult(
            video_id=comments.video_id,
            title=comments.title,
            url=comments.url,
            error=comments.error,
        )

    df = comments.df.copy()

    if len(df) < 5:
        return CommentCriticismResult(
            video_id=comments.video_id,
            title=comments.title,
            url=comments.url,
            error="Not enough comments to analyze",
        )
    
    comments_block = "\n".join([f"- {c}" for c in df["clean_text"].dropna().tolist()])

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
    
    user_prompt = f"影片標題: {comments.title}\n觀眾留言清單:\n\"\"\"\n{comments_block}\n\"\"\""

    try:
        ollama = Client(host='http://host.docker.internal:11434')
        response = ollama.generate(
            model=model_name,
            system=system_prompt,
            prompt=user_prompt,
            format="json",
            options={
                "temperature": 0.2,
            }
        )
        
        raw_content = response.get("response", "{}").strip()
        
        if raw_content.startswith("```"):
            raw_content = re.sub(r"^json)?\n|```$", "", raw_content, flags=re.IGNORECASE).strip()
        
        data = json.loads(raw_content)
        
        return CommentCriticismResult(
            video_id=comments.video_id,
            url=comments.url,
            title=comments.title,
            main_criticisms=data.get("main_criticisms", []),
            discontent_reasons=data.get("discontent_reasons", []),
            suggestions=data.get("suggestions", []),
        )
        
    except Exception as e:
        return CommentCriticismResult(
            video_id=comments.video_id,
            url=comments.url,
            title=comments.title,
            error=f"Ollama 輿情分析解析失敗: {str(e)}"
        )
