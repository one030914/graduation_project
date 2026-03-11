from __future__ import annotations

import torch
import torch.nn as nn
from transformers import BertTokenizer
import torch.amp as amp
from typing import List

from model.embedding.loader import get_en_summary_model

def _batch_probs(
    sentences: List[str],
    tokenizer: BertTokenizer,
    model: nn.Module,
    device: torch.device,
    *,
    batch_size: int = 16,
    max_length: int = 256,
) -> List[float]:
    sigmoid = nn.Sigmoid()
    probs: List[float] = []

    use_amp = device.type == "cuda"

    for i in range(0, len(sentences), batch_size):
        batch = sentences[i:i + batch_size]
        enc = tokenizer(
            batch,
            return_tensors="pt",
            padding=True,
            truncation=True,
            max_length=max_length
        )
        enc = {k: v.to(device) for k, v in enc.items()}

        with torch.no_grad():
            if use_amp:
                with amp.autocast(device_type="cuda"):
                    logits = model(enc["input_ids"], enc["attention_mask"])
            else:
                logits = model(enc["input_ids"], enc["attention_mask"])

            p = sigmoid(logits).detach().float().cpu().tolist()

        probs.extend([float(x) for x in p])

    return probs

def summarize_en(
    comments: List[str],
    *,
    topk: int = 5,
    threshold: float = 0.5,
    batch_size: int = 16,
    max_length: int = 256,
    model_folder_name: str = "BERTSUM_english_finetuned",
    fallback_mode: str = "first",  # "first" or "toplen"
) -> List[str]:
    """
    Input: cleaned English comments
    Output: topk extractive summary sentences
    """
    comments = [str(s).strip() for s in (comments or []) if str(s).strip()]
    if not comments:
        return []

    filtered = [s for s in comments if len(s.split()) >= 3]
    if not filtered:
        filtered = comments

    try:
        tokenizer, model, device = get_en_summary_model(model_folder_name=model_folder_name)
        probs = _batch_probs(sentences=filtered, tokenizer=tokenizer, model=model, device=device, batch_size=batch_size, max_length=max_length)

        picked = [(s, p) for s, p in zip(filtered, probs) if p >= threshold]
        if len(picked) < topk:
            ranked = sorted(zip(filtered, probs), key=lambda x: x[1], reverse=True)
            seen = {s for s, _ in picked}
            for s, p in ranked:
                if s not in seen:
                    picked.append((s, p))
                    seen.add(s)
                if len(picked) >= topk:
                    break

        picked = sorted(picked, key=lambda x: x[1], reverse=True)[:topk]
        return [s for s, _ in picked]

    except Exception:
        if fallback_mode == "toplen":
            ranked = sorted(filtered, key=lambda s: len(s), reverse=True)
            return ranked[:topk]
        return filtered[:topk]
