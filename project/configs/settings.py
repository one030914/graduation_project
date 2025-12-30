from pathlib import Path

# 專案根目錄：configs/ 的上一層
ROOT = Path(__file__).resolve().parents[1]

DATA_DIR = ROOT / "data"
CACHE_DIR = ROOT / "data" / "cache"
MODEL_DIR = ROOT / "model"
BOT_DIR = ROOT / "bot"