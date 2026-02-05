"""
配置模組：從環境變數讀取 API Key 與設定
"""
import os

def get_api_key() -> str:
    return os.environ.get("GEMINI_API_KEY", "")

def get_model_name() -> str:
    return os.environ.get("MODEL_NAME", "gemini-3-pro-preview")

def is_api_key_configured() -> bool:
    return bool(get_api_key())
