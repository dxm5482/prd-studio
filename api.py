"""
PRD Studio API - FastAPI 版本

使用 uvicorn 部署到 Render 的 PRD 生成 API
"""
from fastapi import FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional
import os
import logging
# 設定日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 導入 core 模組
from core.config import is_api_key_configured, get_model_name
from core.gemini_client import (
    get_chat_response,
    quick_update_plan,
    criticize_plan,
    run_deep_reflection,
)
from core.utils import convert_markdown_to_html, convert_markdown_to_txt, create_prd_zip

# ==========================================
# FastAPI App 初始化
# ==========================================
app = FastAPI(
    title="PRD Studio API",
    description="AI 驅動的產品需求規格書（PRD）生成與審核 API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS 中介軟體（允許所有來源，方便前端接入）
def _get_cors_origins():
    raw = os.getenv("ALLOWED_ORIGINS", "*").strip()
    if raw in ("", "*"):
        return ["*"]
    return [o.strip() for o in raw.split(",") if o.strip()]

def _get_bool_env(name: str, default: bool) -> bool:
    val = os.getenv(name)
    if val is None:
        return default
    return val.strip().lower() in {"1", "true", "yes", "y", "on"}

cors_origins = _get_cors_origins()
allow_credentials = _get_bool_env("ALLOW_CREDENTIALS", default=("*" not in cors_origins))
if "*" in cors_origins and allow_credentials:
    logger.warning("ALLOW_CREDENTIALS=true with wildcard origins is invalid; forcing allow_credentials=False.")
    allow_credentials = False

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==========================================
# Pydantic Models（請求/回應格式）
# ==========================================

class Message(BaseModel):
    """單則對話訊息"""
    role: str = Field(..., description="角色：'user' 或 'assistant'")
    content: str = Field(..., description="訊息內容")


class ChatRequest(BaseModel):
    """POST /chat 請求"""
    messages: List[Message] = Field(..., description="對話歷史")
    prd_context: Optional[str] = Field(None, description="目前的 PRD 內容（可選）")
    memory_summary: Optional[str] = Field(None, description="隱藏記憶摘要（可選）")


class ChatResponse(BaseModel):
    """POST /chat 回應"""
    reply: str = Field(..., description="AI 回覆")


class GeneratePRDRequest(BaseModel):
    """POST /generate_prd 請求"""
    messages: List[Message] = Field(..., description="對話歷史")


class GeneratePRDResponse(BaseModel):
    """POST /generate_prd 回應"""
    prd_markdown: str = Field(..., description="生成的 PRD（Markdown 格式）")


class CritiquePRDRequest(BaseModel):
    """POST /critique_prd 請求"""
    prd_markdown: str = Field(..., description="要審核的 PRD 內容")


class CritiquePRDResponse(BaseModel):
    """POST /critique_prd 回應"""
    critique_markdown: str = Field(..., description="CTO 審核報告（Markdown 格式）")


class DeepReviewRequest(BaseModel):
    """POST /deep_review 請求"""
    prd_markdown: str = Field(..., description="要審核的 PRD 內容")


class DeepReviewResponse(BaseModel):
    """POST /deep_review 回應"""
    critique_markdown: str = Field(..., description="CTO 審核報告")
    refined_prd_markdown: str = Field(..., description="修正後的 PRD")


class DownloadZipRequest(BaseModel):
    """POST /download_zip 請求"""
    prd_markdown: str = Field(..., description="PRD 內容")
    critique_markdown: Optional[str] = Field(None, description="審核報告（可選）")


class HealthResponse(BaseModel):
    """GET /health 回應"""
    status: str
    api_key_configured: bool
    model_name: str


class ErrorResponse(BaseModel):
    """錯誤回應"""
    error: str
    detail: str


# ==========================================
# 輔助函式
# ==========================================

def check_api_key():
    """檢查 API Key 是否已設定，若未設定則抛出 HTTPException"""
    if not is_api_key_configured():
        raise HTTPException(
            status_code=500,
            detail="GEMINI_API_KEY 環境變數未設定。請在 Render Dashboard 或本地環境設定此變數。"
        )


# ==========================================
# API 端點
# ==========================================

@app.get("/health", response_model=HealthResponse, tags=["System"])
async def health_check():
    """
    健康檢查端點
    
    回傳系統狀態、API Key 設定狀態、模型名稱
    """
    return HealthResponse(
        status="ok",
        api_key_configured=is_api_key_configured(),
        model_name=get_model_name()
    )


@app.post("/chat", response_model=ChatResponse, tags=["Chat"])
async def chat(request: ChatRequest):
    """
    對話端點
    
    輸入對話歷史，回傳 AI 回覆。
    可選傳入 prd_context 讓 AI 參考目前的 PRD。
    """
    check_api_key()
    
    try:
        # 轉換 Pydantic model 為 dict
        messages = [{"role": m.role, "content": m.content} for m in request.messages]
        
        reply = get_chat_response(
            history=messages,
            prd_text=request.prd_context or "",
            memory_summary=request.memory_summary or ""
        )
        
        return ChatResponse(reply=reply)
    
    except Exception as e:
        logger.error(f"Chat API error: {e}")
        raise HTTPException(
            status_code=502,
            detail=f"Gemini API 呼叫失敗：{str(e)}"
        )


@app.post("/generate_prd", response_model=GeneratePRDResponse, tags=["PRD"])
async def generate_prd(request: GeneratePRDRequest):
    """
    生成 PRD 端點
    
    根據對話歷史生成產品需求規格書（PRD）
    """
    check_api_key()
    
    try:
        messages = [{"role": m.role, "content": m.content} for m in request.messages]
        
        prd = quick_update_plan(messages)
        
        return GeneratePRDResponse(prd_markdown=prd)
    
    except Exception as e:
        logger.error(f"Generate PRD error: {e}")
        raise HTTPException(
            status_code=502,
            detail=f"Gemini API 呼叫失敗：{str(e)}"
        )


@app.post("/critique_prd", response_model=CritiquePRDResponse, tags=["PRD"])
async def critique_prd(request: CritiquePRDRequest):
    """
    CTO 審核端點
    
    輸入 PRD，回傳 CTO 審核報告
    """
    check_api_key()
    
    try:
        critique = criticize_plan(request.prd_markdown)
        
        return CritiquePRDResponse(critique_markdown=critique)
    
    except Exception as e:
        logger.error(f"Critique PRD error: {e}")
        raise HTTPException(
            status_code=502,
            detail=f"Gemini API 呼叫失敗：{str(e)}"
        )


@app.post("/deep_review", response_model=DeepReviewResponse, tags=["PRD"])
async def deep_review(request: DeepReviewRequest):
    """
    深度審核端點
    
    執行 CTO 審核 + 自動修正，回傳審核報告與修正後的 PRD
    """
    check_api_key()
    
    try:
        critique, refined_prd = run_deep_reflection(request.prd_markdown)
        
        return DeepReviewResponse(
            critique_markdown=critique,
            refined_prd_markdown=refined_prd
        )
    
    except Exception as e:
        logger.error(f"Deep review error: {e}")
        raise HTTPException(
            status_code=502,
            detail=f"Gemini API 呼叫失敗：{str(e)}"
        )


@app.post("/download_zip", tags=["Download"])
async def download_zip(request: DownloadZipRequest):
    """
    下載 ZIP 端點
    
    將 PRD（及審核報告）打包為 ZIP 檔案下載。
    包含：prd.md, prd.html, prd.txt（若有審核報告則也包含 critique.*）
    """
    try:
        zip_bytes = create_prd_zip(
            prd_content=request.prd_markdown,
            critique_content=request.critique_markdown
        )
        
        return Response(
            content=zip_bytes,
            media_type="application/zip",
            headers={
                "Content-Disposition": "attachment; filename=prd_package.zip"
            }
        )
    
    except Exception as e:
        logger.error(f"Download ZIP error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"建立 ZIP 檔案失敗：{str(e)}"
        )


# ==========================================
# 啟動入口（本地開發用）
# ==========================================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)
