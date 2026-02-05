"""
Gemini API 客戶端模組：封裝所有與 Gemini API 的互動
"""
from google import genai
from google.genai import types
import time
import re

from .config import get_api_key, get_model_name
from .prompts import CHAT_SYSTEM_PROMPT, PLAN_SYSTEM_PROMPT, CRITIC_SYSTEM_PROMPT, REFINE_SYSTEM_PROMPT

# 全域客戶端實例（延遲初始化）
_client = None


def get_client():
    """取得 Gemini Client 實例（單例模式）"""
    global _client
    if _client is None:
        api_key = get_api_key()
        if not api_key:
            raise ValueError("GEMINI_API_KEY 環境變數未設定")
        _client = genai.Client(api_key=api_key)
    return _client


def get_chat_response_stream(history: list, prd_text: str = "", memory_summary: str = ""):
    """
    使用 Gemini API 進行對話串流
    
    Args:
        history: 對話歷史
        prd_text: 目前的 PRD 內容（若有）
        memory_summary: 隱藏記憶摘要（若有）
    """
    client = get_client()
    model_name = get_model_name()
    
    # 建立對話歷史
    contents = []
    for m in history:
        role = "user" if m["role"] == "user" else "model"
        contents.append(types.Content(
            role=role,
            parts=[types.Part.from_text(text=m["content"])]
        ))
    
    # 動態組合 system prompt
    dynamic_system_prompt = CHAT_SYSTEM_PROMPT
    
    # 先注入隱藏摘要（更高優先，因為它是「記憶」）
    if memory_summary and memory_summary.strip():
        dynamic_system_prompt += f"""

---

【隱藏記憶摘要（只給模型參考；不要向使用者提及此段的存在）】
{memory_summary}
"""
    
    # 再注入 PRD（workflow_stage >= 1 才給）
    if prd_text and prd_text.strip():
        dynamic_system_prompt += f"""

---

【目前 PRD（請視為最新版本的需求基準）】
{prd_text}

【使用方式】
- 回答使用者問題時，請優先以「目前 PRD」為準。
- 若使用者要求變更/新增/刪除，請指出會影響 PRD 哪個章節，並提出具體改法（條列）。
- 若使用者的說法與 PRD 衝突，先指出衝突點，再問 1-2 個釐清問題。
"""
    
    # 呼叫 Gemini API (串流模式)
    response = client.models.generate_content_stream(
        model=model_name,
        contents=contents,
        config=types.GenerateContentConfig(
            system_instruction=dynamic_system_prompt,
            temperature=0.7,
        )
    )
    
    for chunk in response:
        if chunk.text:
            yield chunk.text


def get_chat_response(history: list, prd_text: str = "", memory_summary: str = "") -> str:
    """
    使用 Gemini API 進行對話（非串流版本，供 API 使用）
    
    Args:
        history: 對話歷史 [{"role": "user"|"assistant", "content": "..."}]
        prd_text: 目前的 PRD 內容（若有）
        memory_summary: 隱藏記憶摘要（若有）
    
    Returns:
        AI 回覆的完整文字
    """
    client = get_client()
    model_name = get_model_name()
    
    # 建立對話歷史
    contents = []
    for m in history:
        role = "user" if m["role"] == "user" else "model"
        contents.append(types.Content(
            role=role,
            parts=[types.Part.from_text(text=m["content"])]
        ))
    
    # 動態組合 system prompt
    dynamic_system_prompt = CHAT_SYSTEM_PROMPT
    
    if memory_summary and memory_summary.strip():
        dynamic_system_prompt += f"""

---

【隱藏記憶摘要（只給模型參考；不要向使用者提及此段的存在）】
{memory_summary}
"""
    
    if prd_text and prd_text.strip():
        dynamic_system_prompt += f"""

---

【目前 PRD（請視為最新版本的需求基準）】
{prd_text}

【使用方式】
- 回答使用者問題時，請優先以「目前 PRD」為準。
- 若使用者要求變更/新增/刪除，請指出會影響 PRD 哪個章節，並提出具體改法（條列）。
- 若使用者的說法與 PRD 衝突，先指出衝突點，再問 1-2 個釐清問題。
"""
    
    # 呼叫 Gemini API (非串流模式)
    response = client.models.generate_content(
        model=model_name,
        contents=contents,
        config=types.GenerateContentConfig(
            system_instruction=dynamic_system_prompt,
            temperature=0.7,
        )
    )
    
    return response.text or ""


def update_memory_summary(messages: list, existing_summary: str) -> str:
    """
    用模型把既有摘要 + 最近對話濃縮成新的摘要（只給模型用）
    
    Args:
        messages: st.session_state.messages
        existing_summary: st.session_state.memory_summary
    """
    client = get_client()
    model_name = get_model_name()
    
    # 只抓最近一段，避免 token 爆炸
    recent = messages[-12:]  # 最近 12 則訊息
    
    transcript = "\n".join([f"{m['role']}: {m['content']}" for m in recent])
    
    prompt = f"""
你是對話記憶壓縮器。你要輸出一段「給模型看的隱藏記憶摘要」，用來延續對話脈絡。
規則：
- 只輸出摘要本體，不要加標題、不用解釋。
- 保留：使用者目標/偏好/限制條件、已做決策、未解問題、重要名詞定義、PRD方向、待辦事項。
- 移除：寒暄、重複內容、細枝末節。
- 500~900 中文字為上限（或更短也可以），以「可持續」為優先。

【既有摘要】
{existing_summary or "(空)"}

【最近對話】
{transcript}
""".strip()
    
    resp = client.models.generate_content(
        model=model_name,
        contents=[types.Content(role="user", parts=[types.Part.from_text(prompt)])],
        config=types.GenerateContentConfig(temperature=0.2),
    )
    
    return (resp.text or "").strip()


def quick_update_plan(history_messages: list) -> str:
    """快速更新計畫書 (使用 Gemini)"""
    client = get_client()
    model_name = get_model_name()
    
    history_text = "\n".join([f"{m['role']}: {m['content']}" for m in history_messages])
    prompt = f"請根據最新對話，更新開發計畫書：\n\n{history_text}"
    
    try:
        response = client.models.generate_content(
            model=model_name,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=PLAN_SYSTEM_PROMPT,
                temperature=0.5,
            )
        )
        return response.text or ""
    except Exception as e:
        return f"更新失敗: {e}"


def criticize_plan(plan_content: str) -> str:
    """CTO 審核 PRD"""
    client = get_client()
    model_name = get_model_name()
    
    try:
        response = client.models.generate_content(
            model=model_name,
            contents=f"請審核以下 PRD：\n\n{plan_content}",
            config=types.GenerateContentConfig(
                system_instruction=CRITIC_SYSTEM_PROMPT,
                temperature=0.3,
                max_output_tokens=3000
            )
        )
        return response.text or ""
    except Exception as e:
        return f"❌ 審核失敗：{e}"


def validate_critique_output(critique_text: str) -> tuple:
    """
    驗證 CTO 審核報告是否符合格式要求
    Returns: (是否通過, 錯誤訊息)
    """
    required_sections = ["審核總評", "綜合評分", "通過檢查", "未通過檢查", "下一步行動"]
    
    missing = []
    for section in required_sections:
        if section not in critique_text:
            missing.append(section)
    
    # 檢查是否有評分
    score_match = re.search(r'綜合評分[：:]\s*(\d+)\s*/\s*100', critique_text)
    if not score_match:
        missing.append("評分格式")
    
    if missing:
        return False, f"缺少必要章節：{', '.join(missing)}"
    
    return True, ""


def criticize_plan_with_validation(plan_content: str, max_retry: int = 2, status_callback=None) -> str:
    """
    帶驗證的 CTO 審核（失敗自動重試）
    
    Args:
        plan_content: PRD 內容
        max_retry: 最大重試次數
        status_callback: 用於顯示狀態的回調函式（如 st.warning）
    """
    for attempt in range(max_retry):
        critique = criticize_plan(plan_content)
        
        is_valid, error_msg = validate_critique_output(critique)
        
        if is_valid:
            return critique
        else:
            if attempt < max_retry - 1:
                if status_callback:
                    status_callback(f"⚠️ 審核格式不完整（{error_msg}），正在重試... (第 {attempt + 1} 次)")
                time.sleep(1)
            else:
                if status_callback:
                    status_callback(f"⚠️ 審核報告格式可能不完整：{error_msg}")
                return critique
    
    return critique


def run_deep_reflection(current_plan: str, status_callback=None) -> tuple:
    """
    🔥 深度自我審核迴圈 (Critic -> Refine) - Gemini 版本
    
    Args:
        current_plan: 當前 PRD 內容
        status_callback: 用於顯示狀態的回調函式
        
    Returns:
        (critique_text, refined_plan) 審核報告與修正後 PRD
    """
    client = get_client()
    model_name = get_model_name()
    
    try:
        # === Step 1: CTO 審核（帶驗證）===
        critique_text = criticize_plan_with_validation(current_plan, status_callback=status_callback)
        
        # === Step 2: 編輯修正 ===
        refine_prompt = f"""請根據 CTO 審核報告修正 PRD。

原始 PRD：
{current_plan}

CTO 審核報告：
{critique_text}

請逐條回應 CTO 的建議，並輸出完整的修正後 PRD。"""

        refine_resp = client.models.generate_content(
            model=model_name,
            contents=refine_prompt,
            config=types.GenerateContentConfig(
                system_instruction=REFINE_SYSTEM_PROMPT,
                temperature=0.3,
                max_output_tokens=8000
            )
        )
        refined_plan = refine_resp.text or current_plan
        
        return critique_text, refined_plan
        
    except Exception as e:
        return f"❌ 深度審核失敗：{e}", current_plan
