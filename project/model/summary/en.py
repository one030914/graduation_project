from __future__ import annotations

from functools import lru_cache
from typing import List

import torch
import torch.nn as nn
from transformers import BertTokenizer, BertModel

from configs.settings import MODEL_DIR

class BERTSentenceClassifier(nn.Module):
    """
    English extractive selector: outputs logits for each sentence.
    """
    def __init__(self, pretrained_model: str = "bert-base-uncased"):
        super().__init__()
        self.bert = BertModel.from_pretrained(pretrained_model)
        self.classifier = nn.Linear(self.bert.config.hidden_size, 1)

    def forward(self, input_ids: torch.Tensor, attention_mask: torch.Tensor) -> torch.Tensor:
        outputs = self.bert(input_ids=input_ids, attention_mask=attention_mask)
        cls = outputs.last_hidden_state[:, 0, :]
        logits = self.classifier(cls)
        return logits.squeeze(-1)


@lru_cache(maxsize=1)
def _load_bertsum_en(
    model_folder_name: str = "BERTSUM_english_finetuned",
    pretrained_model: str = "bert-base-uncased",
):
    """
    Loads tokenizer + fine-tuned weights once.
    Expected folder:
      model/BERTSUM_english_finetuned/
        - pytorch_model.bin
        - tokenizer files saved by tokenizer.save_pretrained()
    If folder doesn't exist / missing files, caller should handle exceptions (fallback).
    """
    model_dir = MODEL_DIR / model_folder_name
    tokenizer = BertTokenizer.from_pretrained(model_dir)

    model = BERTSentenceClassifier(pretrained_model=pretrained_model)
    weights_path = model_dir / "pytorch_model.bin"
    state = torch.load(weights_path, map_location="cpu")
    model.load_state_dict(state)
    model.eval()

    return tokenizer, model


def _batch_probs(
    sentences: List[str],
    tokenizer: BertTokenizer,
    model: nn.Module,
    *,
    batch_size: int = 16,
    max_length: int = 256,
) -> List[float]:
    sigmoid = nn.Sigmoid()
    probs: List[float] = []

    for i in range(0, len(sentences), batch_size):
        batch = sentences[i:i + batch_size]
        enc = tokenizer(
            batch,
            return_tensors="pt",
            padding=True,
            truncation=True,
            max_length=max_length
        )
        with torch.no_grad():
            logits = model(enc["input_ids"], enc["attention_mask"])
            p = sigmoid(logits).detach().cpu().tolist()
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

    If english fine-tuned model is not ready yet, this function can fallback.
    """
    comments = [str(s).strip() for s in (comments or []) if str(s).strip()]
    if not comments:
        return []

    # filter super-short noise (e.g., "lol", "nice")
    filtered = [s for s in comments if len(s.split()) >= 3]
    if not filtered:
        filtered = comments

    # Try load model; fallback if not available
    try:
        tokenizer, model = _load_bertsum_en(model_folder_name=model_folder_name)
        probs = _batch_probs(filtered, tokenizer, model, batch_size=batch_size, max_length=max_length)

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
        # Fallback: return something reasonable so pipeline never breaks
        if fallback_mode == "toplen":
            ranked = sorted(filtered, key=lambda s: len(s), reverse=True)
            return ranked[:topk]
        return filtered[:topk]
