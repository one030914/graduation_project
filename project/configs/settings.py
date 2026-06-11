from pathlib import Path

# 專案根目錄：configs/ 的上一層
ROOT = Path(__file__).resolve().parents[1]

BOT_DIR = ROOT / "bot"
MODEL_DIR = ROOT / "model" / "models"