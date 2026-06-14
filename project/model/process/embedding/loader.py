from __future__ import annotations

from functools import lru_cache
from typing import Tuple
import torch
import torch.nn as nn
from sentence_transformers import SentenceTransformer
from transformers import BertConfig, BertTokenizer, BertModel, pipeline
from huggingface_hub import snapshot_download

from configs.settings import MODEL_DIR

# Minilm Embedder

def get_device_str() -> str:
    return "cuda" if torch.cuda.is_available() else "cpu"

def _resolve_model_source(model_folder_name: str, fallback_model_name: str) -> str:
    model_dir = MODEL_DIR / model_folder_name
    if model_dir.exists() and any(model_dir.iterdir()):
        return str(model_dir)
    return fallback_model_name

def _resolve_bert_source(pretrained_model: str) -> str:
    model_dir = MODEL_DIR / pretrained_model
    if model_dir.exists() and any(model_dir.iterdir()):
        return str(model_dir)
    return pretrained_model

@lru_cache(maxsize=1)
def get_zh_embedder(model_folder_name: str = "minilm_chinese_finetuned") -> SentenceTransformer:
    device = get_device_str()
    model_source = _resolve_model_source(
        model_folder_name=model_folder_name,
        fallback_model_name="paraphrase-multilingual-MiniLM-L12-v2",
    )
    return SentenceTransformer(model_source, device=device)

@lru_cache(maxsize=1)
def get_en_embedder(model_folder_name: str = "minilm_english_finetuned") -> SentenceTransformer:
    device = get_device_str()
    model_source = _resolve_model_source(
        model_folder_name=model_folder_name,
        fallback_model_name="all-MiniLM-L6-v2",
    )
    return SentenceTransformer(model_source, device=device)

# BERTSUM Embedder

def get_device() -> torch.device:
    return torch.device("cuda" if torch.cuda.is_available() else "cpu")

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

    @classmethod
    def from_config(cls, config_source: str):
        model = cls.__new__(cls)
        nn.Module.__init__(model)
        config = BertConfig.from_pretrained(config_source)
        model.bert = BertModel(config)
        model.classifier = nn.Linear(model.bert.config.hidden_size, 1)
        return model

def _build_summary_classifier(model_dir, pretrained_model: str) -> BERTSentenceClassifier:
    if (model_dir / "config.json").exists():
        return BERTSentenceClassifier.from_config(str(model_dir))
    return BERTSentenceClassifier(pretrained_model=_resolve_bert_source(pretrained_model))

@lru_cache(maxsize=1)
def get_zh_summary_model(
    model_folder_name: str = "BERTSUM_chinese_finetuned",
    pretrained_model: str = "bert-base-chinese",
) -> Tuple[BertTokenizer, nn.Module, torch.device]:
    device = get_device()
    model_dir = MODEL_DIR / model_folder_name

    tokenizer = BertTokenizer.from_pretrained(model_dir)
    model = _build_summary_classifier(model_dir, pretrained_model)

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
    model = _build_summary_classifier(model_dir, pretrained_model)

    state = torch.load(model_dir / "pytorch_model.bin", map_location=device)
    model.load_state_dict(state)
    model.to(device)
    model.eval()

    return tokenizer, model, device

# Emotion Embedder

def get_hf_device() -> int:
    return 0 if torch.cuda.is_available() else -1

def get_hf_inference_dtype() -> torch.dtype:
    return torch.float16 if torch.cuda.is_available() else torch.float32

def _resolve_or_download_emotion_source(model_folder_name: str, fallback_model_name: str) -> str:
    model_dir = MODEL_DIR / model_folder_name
    if (model_dir / "config.json").exists():
        return str(model_dir)

    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    snapshot_download(
        repo_id=fallback_model_name,
        local_dir=str(model_dir),
    )
    return str(model_dir)

@lru_cache(maxsize=1)
def get_en_emotion_model(
    model_folder_name: str = "emotion_english_distilroberta_base",
):
    model_source = _resolve_or_download_emotion_source(
        model_folder_name=model_folder_name,
        fallback_model_name="j-hartmann/emotion-english-distilroberta-base",
    )
    return pipeline(
        "text-classification",
        model=model_source,
        tokenizer=model_source,
        device=get_hf_device(),
        torch_dtype=get_hf_inference_dtype(),
    )

@lru_cache(maxsize=1)
def get_zh_emotion_model(
    model_folder_name: str = "emotion_chinese_small",
):
    model_source = _resolve_or_download_emotion_source(
        model_folder_name=model_folder_name,
        fallback_model_name="Johnson8187/Chinese-Emotion-Small",
    )
    zh = pipeline(
        "text-classification",
        model=model_source,
        tokenizer=model_source,
        device=get_hf_device(),
        torch_dtype=get_hf_inference_dtype(),
    )
    
    # Johnson8187/Chinese-Emotion(-Small) 官方 label mapping
    # 0: 平淡語氣, 1: 關切語調, 2: 開心語調, 3: 憤怒語調,
    # 4: 悲傷語調, 5: 疑問語調, 6: 驚奇語調, 7: 厭惡語調

    id2label = {
        0: "Neutral",
        1: "Neutral",
        2: "Joy",
        3: "Angry",
        4: "Sad",
        5: "Neutral",
        6: "Surprised",
        7: "Disgusted",
    }
    zh.model.config.id2label = id2label
    zh.model.config.label2id = {v: k for k, v in id2label.items()}
    return zh
