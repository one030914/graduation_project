from __future__ import annotations

from functools import lru_cache
from typing import Tuple
import torch
import torch.nn as nn
from sentence_transformers import SentenceTransformer
from transformers import BertTokenizer, BertModel

from configs.settings import MODEL_DIR

def get_device() -> torch.device:
    return torch.device("cuda" if torch.cuda.is_available() else "cpu")

def get_device_str() -> str:
    return "cuda" if torch.cuda.is_available() else "cpu"

# Minilm Embedder

@lru_cache(maxsize=1)
def get_zh_embedder(model_folder_name: str = "minilm_chinese_finetuned") -> SentenceTransformer:
    device = get_device_str()
    model_dir = MODEL_DIR / model_folder_name
    return SentenceTransformer(str(model_dir), device=device)

@lru_cache(maxsize=1)
def get_en_embedder(model_folder_name: str = "minilm_english_finetuned") -> SentenceTransformer:
    device = get_device_str()
    model_dir = MODEL_DIR / model_folder_name
    return SentenceTransformer(str(model_dir), device=device)

# BERTSUM Embedder

class BERTSentenceClassifier(nn.Module):
    def __init__(self, pretrained_model: str):
        super().__init__()
        self.bert = BertModel.from_pretrained(pretrained_model)
        self.classifier = nn.Linear(self.bert.config.hidden_size, 1)

    def forward(self, input_ids, attention_mask):
        outputs = self.bert(input_ids=input_ids, attention_mask=attention_mask)
        cls_output = outputs.last_hidden_state[:, 0, :]
        logits = self.classifier(cls_output)
        return logits.squeeze(-1)

@lru_cache(maxsize=1)
def get_zh_summary_model(
    model_folder_name: str = "BERTSUM_chinese_finetuned",
    pretrained_model: str = "bert-base-chinese",
) -> Tuple[BertTokenizer, nn.Module, torch.device]:
    device = get_device()
    model_dir = MODEL_DIR / model_folder_name

    tokenizer = BertTokenizer.from_pretrained(model_dir)
    model = BERTSentenceClassifier(pretrained_model=pretrained_model)

    state = torch.load(model_dir / "pytorch_model.bin", map_location=device)
    model.load_state_dict(state)
    model.to(device)
    model.eval()

    return tokenizer, model, device

@lru_cache(maxsize=1)
def get_en_summary_model(
    model_folder_name: str = "BERTSUM_english_finetuned",
    pretrained_model: str = "bert-base-uncased",
) -> Tuple[BertTokenizer, nn.Module, torch.device]:
    device = get_device()
    model_dir = MODEL_DIR / model_folder_name

    tokenizer = BertTokenizer.from_pretrained(model_dir)
    model = BERTSentenceClassifier(pretrained_model=pretrained_model)

    state = torch.load(model_dir / "pytorch_model.bin", map_location=device)
    model.load_state_dict(state)
    model.to(device)
    model.eval()

    return tokenizer, model, device