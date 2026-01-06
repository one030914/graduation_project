from __future__ import annotations

from functools import lru_cache
from typing import List, Tuple

import torch
import torch.nn as nn
from torch import amp
from transformers import BertTokenizer, BertModel

from configs.settings import MODEL_DIR


def _get_device() -> torch.device:
    return torch.device("cuda" if torch.cuda.is_available() else "cpu")


class BERTSentenceClassifier(nn.Module):
    """
    你的 BERTSUM sentence selector（extractive）：輸出每句是否入摘要的 logits
    """
    def __init__(self, pretrained_model: str = "bert-base-chinese"):
        super().__init__()
        self.bert = BertModel.from_pretrained(pretrained_model)
        self.classifier = nn.Linear(self.bert.config.hidden_size, 1)

    def forward(self, input_ids: torch.Tensor, attention_mask: torch.Tensor) -> torch.Tensor:
        outputs = self.bert(input_ids=input_ids, attention_mask=attention_mask)
        cls_output = outputs.last_hidden_state[:, 0, :]  # [CLS]
        logits = self.classifier(cls_output)             # (B, 1)
        return logits.squeeze(-1)                        # (B,)


@lru_cache(maxsize=1)
def _load_bertsum_zh(
    model_folder_name: str = "BERTSUM_chinese_finetuned",
    pretrained_model: str = "bert-base-chinese",
) -> Tuple[BertTokenizer, nn.Module, torch.device]:
    """
    載入 tokenizer + fine-tuned 權重（只載一次），並自動搬到 GPU（若可用）
    """
    device = _get_device()

    model_dir = MODEL_DIR / model_folder_name
    tokenizer = BertTokenizer.from_pretrained(model_dir)

    model = BERTSentenceClassifier(pretrained_model=pretrained_model)
    weights_path = model_dir / "pytorch_model.bin"

    state = torch.load(weights_path, map_location=device)
    model.load_state_dict(state)
    model.to(device)
    model.eval()

    return tokenizer, model, device


def _batch_predict_probs(
    sentences: List[str],
    tokenizer: BertTokenizer,
    model: nn.Module,
    device: torch.device,
    *,
    batch_size: int = 16,
    max_length: int = 256,
) -> List[float]:
    probs: List[float] = []
    sigmoid = nn.Sigmoid()

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


def summarize_zh(
    comments: List[str],
    *,
    topk: int = 5,
    threshold: float = 0.5,
    batch_size: int = 16,
    max_length: int = 256,
    model_folder_name: str = "BERTSUM_chinese_finetuned",
) -> List[str]:
    """
    輸入：中文留言（清理後）
    輸出：摘要句 topk（extractive）
    """
    comments = [str(s).strip() for s in (comments or []) if str(s).strip()]
    if not comments:
        return []

    filtered = [s for s in comments if len(s) >= 4]
    if not filtered:
        filtered = comments

    tokenizer, model, device = _load_bertsum_zh(model_folder_name=model_folder_name)

    probs = _batch_predict_probs(
        filtered, tokenizer, model, device,
        batch_size=batch_size, max_length=max_length
    )

    picked = [(s, p) for s, p in zip(filtered, probs) if p >= threshold]

    if len(picked) < topk:
        ranked = sorted(zip(filtered, probs), key=lambda x: x[1], reverse=True)
        seen = set(s for s, _ in picked)
        for s, p in ranked:
            if s not in seen:
                picked.append((s, p))
                seen.add(s)
            if len(picked) >= topk:
                break

    picked = sorted(picked, key=lambda x: x[1], reverse=True)[:topk]
    return [s for s, _ in picked]
