"""
PRD Studio - Streamlit 應用程式入口

一鍵部署到 Render 的 PRD 生成工具
"""
import streamlit as st

# 頁面配置（必須在最頂層）
st.set_page_config(
    layout="wide",
    page_title="PRD Studio",
    page_icon="📋",
    initial_sidebar_state="expanded"
)

import time
import zipfile
from io import BytesIO

# 導入 core 模組
from core.config import is_api_key_configured, get_model_name
from core.prompts import CHAT_SYSTEM_PROMPT, PLAN_SYSTEM_PROMPT, EXAMPLE_SCENARIOS
from core.gemini_client import (
    get_client,
    get_chat_response_stream,
    update_memory_summary,
    quick_update_plan,
    run_deep_reflection
)
from core.version_manager import save_version, show_diff
from core.utils import convert_markdown_to_html, create_download_section

# ==========================================
# 檢查 API Key 是否設定
# ==========================================
if not is_api_key_configured():
    st.error("""
    ## ⚠️ API Key 未設定
    
    請設定環境變數 `GEMINI_API_KEY` 後重新啟動應用程式。
    
    ### 本地開發
    ```bash
    # Windows PowerShell
    $env:GEMINI_API_KEY = "your-api-key"
    streamlit run app.py
    
    # Linux/Mac
    export GEMINI_API_KEY="your-api-key"
    streamlit run app.py
    ```
    
    ### Render 部署
    在 Render Dashboard 的 Environment Variables 中設定：
    - `GEMINI_API_KEY` = 您的 Gemini API Key
    """)
    st.stop()

# ==========================================
# CSS 樣式
# ==========================================
st.markdown("""
<style>
    /* 主題色彩變數 */
    :root {
        --primary-gradient: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        --secondary-gradient: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        --success-gradient: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
        --dark-bg: #0e1117;
        --card-bg: rgba(255, 255, 255, 0.05);
        --glass-border: rgba(255, 255, 255, 0.1);
    }
    
    /* 隱藏 Streamlit 預設元素 */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* 側邊欄按鈕樣式 */
    [data-testid="collapsedControl"] {
        display: flex !important;
        visibility: visible !important;
        opacity: 1 !important;
        color: #667eea !important;
        background: rgba(102, 126, 234, 0.1) !important;
        border: 2px solid #667eea !important;
        border-radius: 8px !important;
        padding: 8px !important;
        margin: 10px !important;
        z-index: 999999 !important;
        position: fixed !important;
        top: 10px !important;
        left: 10px !important;
        cursor: pointer !important;
        transition: all 0.3s ease !important;
    }
    
    [data-testid="collapsedControl"]:hover {
        background: rgba(102, 126, 234, 0.3) !important;
        transform: scale(1.1) !important;
    }
    
    [data-testid="collapsedControl"] svg {
        width: 24px !important;
        height: 24px !important;
        stroke: #667eea !important;
    }
    
    [data-testid="stSidebarCollapseButton"] {
        visibility: visible !important;
        opacity: 1 !important;
    }
    
    /* 主標題動畫 */
    .main-title {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 50%, #f093fb 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        font-size: 2.5rem;
        font-weight: 800;
        text-align: center;
        margin-bottom: 0.5rem;
        animation: titleGlow 3s ease-in-out infinite;
    }
    
    @keyframes titleGlow {
        0%, 100% { filter: brightness(1); }
        50% { filter: brightness(1.2); }
    }
    
    .subtitle {
        text-align: center;
        color: #a0a0a0;
        font-size: 1rem;
        margin-bottom: 1.5rem;
    }
    
    /* 玻璃態卡片效果 */
    .glass-card {
        background: rgba(255, 255, 255, 0.03);
        backdrop-filter: blur(10px);
        border-radius: 16px;
        border: 1px solid rgba(255, 255, 255, 0.1);
        padding: 1.5rem;
        margin-bottom: 1rem;
        transition: all 0.3s ease;
    }
    
    .glass-card:hover {
        border-color: rgba(102, 126, 234, 0.5);
        box-shadow: 0 8px 32px rgba(102, 126, 234, 0.15);
    }
    
    /* 按鈕增強樣式 */
    .stButton > button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        border-radius: 12px;
        padding: 0.75rem 1.5rem;
        font-weight: 600;
        transition: all 0.3s ease;
        box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(102, 126, 234, 0.5);
    }
    
    /* 聊天訊息美化 */
    .stChatMessage {
        background: rgba(255, 255, 255, 0.02);
        border-radius: 16px;
        border: 1px solid rgba(255, 255, 255, 0.05);
        margin-bottom: 0.5rem;
    }
    
    /* Tabs 樣式 */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background: rgba(255, 255, 255, 0.02);
        padding: 0.5rem;
        border-radius: 12px;
    }
    
    .stTabs [data-baseweb="tab"] {
        background: transparent;
        border-radius: 8px;
        color: #a0a0a0;
        padding: 0.5rem 1rem;
        transition: all 0.3s ease;
    }
    
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white !important;
    }
    
    /* 區域標題卡片 */
    .section-banner {
        border-radius: 12px;
        padding: 14px;
        margin-bottom: 16px;
        text-align: center;
        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
    }
    
    .section-banner h3 {
        color: white;
        margin: 0;
        font-size: 18px;
        font-weight: 600;
    }
    
    .section-banner-left {
        background: linear-gradient(135deg, #fa709a 0%, #fee140 100%);
    }
    
    .section-banner-right {
        background: linear-gradient(135deg, #30cfd0 0%, #330867 100%);
    }
    
    /* 美化檔案上傳區 */
    [data-testid="stFileUploader"] {
        border: 2px dashed #667eea !important;
        border-radius: 16px !important;
        padding: 20px !important;
        background: linear-gradient(135deg, rgba(102,126,234,0.05) 0%, rgba(118,75,162,0.05) 100%) !important;
        transition: all 0.3s ease !important;
    }
    
    [data-testid="stFileUploader"]:hover {
        border-color: #764ba2 !important;
        background: linear-gradient(135deg, rgba(102,126,234,0.12) 0%, rgba(118,75,162,0.12) 100%) !important;
    }
    
    /* 分隔線美化 */
    hr {
        border: none;
        height: 1px;
        background: linear-gradient(90deg, transparent, rgba(255,255,255,0.1), transparent);
        margin: 1.5rem 0;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 初始化 Session State
# ==========================================
if "messages" not in st.session_state:
    st.session_state.messages = []
if "plan_content" not in st.session_state:
    st.session_state.plan_content = ""
if "critique_log" not in st.session_state:
    st.session_state.critique_log = ""
if "final_code" not in st.session_state:
    st.session_state.final_code = ""
if "workflow_stage" not in st.session_state:
    st.session_state.workflow_stage = 0
if "prefill_text" not in st.session_state:
    st.session_state.prefill_text = ""
if "auto_submit" not in st.session_state:
    st.session_state.auto_submit = False
if "versions" not in st.session_state:
    st.session_state.versions = []
if "current_version_index" not in st.session_state:
    st.session_state.current_version_index = -1
if "show_sidebar_hint" not in st.session_state:
    st.session_state.show_sidebar_hint = True
if "show_download_dialog" not in st.session_state:
    st.session_state.show_download_dialog = False
if "memory_summary" not in st.session_state:
    st.session_state.memory_summary = ""
if "user_turn_count" not in st.session_state:
    st.session_state.user_turn_count = 0

# ==========================================
# 版本管理輔助函式（包裝 session_state）
# ==========================================
def save_version_wrapper(version_type: str, content: str, note: str = ""):
    """包裝版本保存函式，直接操作 session_state"""
    return save_version(st.session_state.versions, version_type, content, note)

# ==========================================
# UI 佈局
# ==========================================

# === 頂部標題區 ===
st.markdown('<h1 class="main-title">📋 PRD Studio</h1>', unsafe_allow_html=True)
st.markdown('<p class="subtitle">從需求對話到規格文件，快速生成專業 PRD｜深度審核 + 多格式下載</p>', unsafe_allow_html=True)

# === 側邊欄提示（首次使用者） ===
if st.session_state.get('show_sidebar_hint', True):
    hint_col1, hint_col2 = st.columns([8, 1])
    with hint_col1:
        st.info("💡 **首次使用？** 請查看左側的「專案控制台」側邊欄，可管理版本歷史。若側邊欄收起了，請點擊左上角「>」按鈕展開。")
    with hint_col2:
        if st.button("✕", key="dismiss_hint", help="不再顯示此提示"):
            st.session_state.show_sidebar_hint = False
            st.rerun()

# === 工作流程狀態指示器 ===
stage_names = ["💬 需求訪談", "📝 規格撰寫", "🔍 深度審核"]
cols = st.columns(3)
for i, (col, name) in enumerate(zip(cols, stage_names)):
    with col:
        if i <= st.session_state.workflow_stage:
            st.markdown(f"""
            <div style="text-align: center; padding: 0.5rem; 
                background: linear-gradient(135deg, rgba(102, 126, 234, 0.2) 0%, rgba(118, 75, 162, 0.2) 100%);
                border-radius: 8px; border: 1px solid rgba(102, 126, 234, 0.3);">
                <span style="font-weight: 600; color: #667eea;">{name}</span>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div style="text-align: center; padding: 0.5rem; 
                background: rgba(255, 255, 255, 0.02);
                border-radius: 8px; border: 1px solid rgba(255, 255, 255, 0.05);">
                <span style="color: #666;">{name}</span>
            </div>
            """, unsafe_allow_html=True)

st.markdown("---")

# === 側邊欄：版本管理 ===
with st.sidebar:
    st.markdown("# 🎯 專案控制台")
    st.caption("💡 提示：可以點擊左上角「<」收起側邊欄，點擊「>」重新展開")
    st.markdown("---")
    
    # === 版本歷史區塊 ===
    st.markdown("## 📚 版本歷史")
    
    if st.session_state.versions:
        st.info(f"共 **{len(st.session_state.versions)}** 個版本")
        
        # 版本列表（由新到舊）
        for i in range(len(st.session_state.versions) - 1, -1, -1):
            v = st.session_state.versions[i]
            actual_index = i
            is_current = (st.session_state.current_version_index == -1 and i == len(st.session_state.versions) - 1) or \
                        (st.session_state.current_version_index == actual_index)
            
            # 版本展開區
            with st.expander(
                f"{'🔵 ' if is_current else '⚪ '}v{v['version_number']} - {v['timestamp']}", 
                expanded=False
            ):
                st.markdown(f"**類型**: `{v['type']}`")
                st.markdown(f"**字數**: {v['word_count']}")
                if v.get('note'):
                    st.markdown(f"**備註**: {v['note']}")
                
                col_view, col_restore = st.columns(2)
                
                with col_view:
                    if st.button("👁️ 查看", key=f"view_v{actual_index}", use_container_width=True):
                        st.session_state.current_version_index = actual_index
                        st.session_state.plan_content = v['content']
                        st.rerun()
                
                with col_restore:
                    if not is_current:
                        if st.button("↩️ 回滾", key=f"restore_v{actual_index}", use_container_width=True):
                            st.session_state.plan_content = v['content']
                            st.session_state.current_version_index = -1
                            save_version_wrapper('manual', v['content'], f"從 v{v['version_number']} 回滾")
                            st.success(f"✅ 已回滾到 v{v['version_number']}")
                            st.rerun()
        
        # 回到最新版按鈕
        if st.session_state.current_version_index != -1:
            if st.button("🔄 回到最新版", use_container_width=True, type="primary"):
                st.session_state.current_version_index = -1
                if st.session_state.versions:
                    st.session_state.plan_content = st.session_state.versions[-1]['content']
                st.rerun()
    else:
        st.info("📝 尚無版本記錄\n\n開始對話後會自動保存版本")
    
    st.markdown("---")

# === 主要內容區 ===
col1, col2 = st.columns([1, 1], gap="large")

# --- 左側：對話區 ---
with col1:
    st.markdown("""
    <div class="section-banner section-banner-left">
        <h3>💬 需求訪談室</h3>
    </div>
    """, unsafe_allow_html=True)
    
    # === 從需求文件開始（收合式）===
    if not st.session_state.messages:
        with st.expander("📄 從需求文件快速開始", expanded=False):
            st.caption("已有需求文件？上傳 TXT/MD 自動產生規格書")
            
            uploaded_doc = st.file_uploader(
                "拖曳檔案到此處",
                type=['txt', 'md'],
                key="doc_uploader",
                label_visibility="collapsed"
            )
            
            if uploaded_doc:
                try:
                    content = uploaded_doc.read().decode('utf-8')
                    
                    if len(content) > 50000:
                        st.error("⚠️ 檔案過大，請上傳小於 50KB 的文件")
                    else:
                        st.success(f"✅ 已讀取：{uploaded_doc.name} ({len(content)} 字)")
                        
                        if st.button("🚀 分析並產生 PRD", use_container_width=True, type="primary", key="analyze_doc_btn"):
                            st.session_state.messages = []
                            st.session_state.critique_log = ""
                            
                            with st.spinner("📝 正在分析文件..."):
                                try:
                                    from google.genai import types
                                    client = get_client()
                                    model_name = get_model_name()
                                    
                                    analysis_prompt = f"""
以下是使用者上傳的需求文件，請分析並產生完整的 PRD：

{content}

請：
1. 理解文件中的需求
2. 補充缺漏的細節
3. 產出完整的軟體需求規格書
"""
                                    
                                    response = client.models.generate_content(
                                        model=model_name,
                                        contents=analysis_prompt,
                                        config=types.GenerateContentConfig(
                                            system_instruction=CHAT_SYSTEM_PROMPT,
                                            temperature=0.5
                                        )
                                    ).text
                                    
                                    st.session_state.messages.append({
                                        "role": "user",
                                        "content": f"[上傳文件] {uploaded_doc.name}"
                                    })
                                    st.session_state.messages.append({
                                        "role": "assistant",
                                        "content": response
                                    })
                                    
                                    prd = quick_update_plan(st.session_state.messages)
                                    st.session_state.plan_content = prd
                                    save_version_wrapper('quick_update', prd, f"從文件產生: {uploaded_doc.name}")
                                    
                                    st.success("✅ PRD 已生成！請查看右側規格書")
                                    st.rerun()
                                
                                except Exception as e:
                                    st.error(f"分析失敗：{e}")
                
                except Exception as e:
                    st.error(f"讀取檔案失敗：{e}")
        
        st.markdown("---")
    
    # 聊天容器
    chat_container = st.container(height=520)

    # 顯示歷史訊息
    for msg in st.session_state.messages:
        with chat_container.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # 歡迎訊息（只在沒有對話時顯示）
    if not st.session_state.messages and not st.session_state.get("auto_submit", False):
        with chat_container:
            st.info("👋 **歡迎使用 PRD Studio！**\n\n請告訴我您想開發什麼樣的軟體，我會協助您釐清需求。")

    # 處理自動送出（範例按鈕觸發）
    if st.session_state.get("auto_submit", False):
        st.session_state.auto_submit = False
        prompt = st.session_state.get("prefill_text", "")
        st.session_state.prefill_text = ""
        
        if prompt:
            st.session_state.messages.append({"role": "user", "content": prompt})
            st.session_state.user_turn_count += 1
            
            with chat_container.chat_message("user"):
                st.markdown(prompt)
            
            with chat_container.chat_message("assistant"):
                try:
                    prd_context = st.session_state.plan_content if st.session_state.workflow_stage >= 1 else ""
                    mem_context = st.session_state.memory_summary
                    stream = get_chat_response_stream(st.session_state.messages, prd_context, mem_context)
                    response = st.write_stream(stream)
                    st.session_state.messages.append({"role": "assistant", "content": response})
                except Exception as e:
                    error_msg = f"⚠️ 無法連接到 Gemini API。\n\n錯誤詳情: {e}"
                    st.error(error_msg)
                    st.session_state.messages.append({"role": "assistant", "content": error_msg})
            
            # 每三次對話更新摘要
            if st.session_state.user_turn_count % 3 == 0:
                try:
                    st.session_state.memory_summary = update_memory_summary(
                        st.session_state.messages,
                        st.session_state.memory_summary
                    )
                except Exception:
                    pass
            
            # 自動更新 PRD
            if len(st.session_state.messages) >= 2:
                st.session_state.workflow_stage = max(st.session_state.workflow_stage, 1)
                with st.spinner("📝 正在同步更新規格書..."):
                    try:
                        new_plan = quick_update_plan(st.session_state.messages)
                        st.session_state.plan_content = new_plan
                        save_version_wrapper('quick_update', new_plan, f"對話輪次: {len(st.session_state.messages)}")
                    except Exception as e:
                        st.session_state.plan_content = f"更新失敗: {e}"
            
            st.rerun()

    # 聊天輸入區
    input_col, clear_col = st.columns([6, 1])
    
    with clear_col:
        if st.button("🗑️ 清除", key="clear_btn", help="清除所有內容，重新開始", use_container_width=True):
            st.session_state.show_clear_confirm = True
            st.rerun()
    
    # 二次確認對話框
    if st.session_state.get('show_clear_confirm', False):
        with st.container(border=True):
            st.warning("⚠️ **確認清除所有內容？**")
            st.caption("這將清除對話、規格書、審核紀錄及所有版本。此操作無法復原。")
            
            _, cancel_col, confirm_col = st.columns([2, 1, 1])
            
            with cancel_col:
                if st.button("❌ 取消", use_container_width=True, key="cancel_clear"):
                    st.session_state.show_clear_confirm = False
                    st.rerun()
            
            with confirm_col:
                if st.button("✅ 確認清除", use_container_width=True, type="primary", key="confirm_clear"):
                    st.session_state.messages = []
                    st.session_state.plan_content = ""
                    st.session_state.critique_log = ""
                    st.session_state.final_code = ""
                    st.session_state.workflow_stage = 0
                    st.session_state.versions = []
                    st.session_state.current_version_index = -1
                    st.session_state.show_clear_confirm = False
                    st.session_state.prefill_text = ""
                    st.session_state.auto_submit = False
                    st.session_state.memory_summary = ""
                    st.session_state.user_turn_count = 0
                    st.success("✅ 已清除所有內容！")
                    time.sleep(1)
                    st.rerun()
    
    with input_col:
        prompt = st.chat_input("💭 請輸入您的需求或想法...", key="chat_input")
    
    # 處理聊天輸入
    if prompt:
        st.session_state.messages.append({"role": "user", "content": prompt})
        st.session_state.user_turn_count += 1
        
        with chat_container.chat_message("user"):
            st.markdown(prompt)
        
        with chat_container.chat_message("assistant"):
            try:
                prd_context = st.session_state.plan_content if st.session_state.workflow_stage >= 1 else ""
                mem_context = st.session_state.memory_summary
                stream = get_chat_response_stream(st.session_state.messages, prd_context, mem_context)
                response = st.write_stream(stream)
                st.session_state.messages.append({"role": "assistant", "content": response})
            except Exception as e:
                error_msg = f"⚠️ 無法連接到 Gemini API。\n\n錯誤詳情: {e}"
                st.error(error_msg)
                st.session_state.messages.append({"role": "assistant", "content": error_msg})
        
        # 每三次對話更新摘要
        if st.session_state.user_turn_count % 3 == 0:
            try:
                st.session_state.memory_summary = update_memory_summary(
                    st.session_state.messages,
                    st.session_state.memory_summary
                )
            except Exception:
                pass
        
        # 自動更新 PRD
        if len(st.session_state.messages) >= 2:
            st.session_state.workflow_stage = max(st.session_state.workflow_stage, 1)
            with st.spinner("📝 正在同步更新規格書..."):
                try:
                    new_plan = quick_update_plan(st.session_state.messages)
                    st.session_state.plan_content = new_plan
                    save_version_wrapper('quick_update', new_plan, f"對話輪次: {len(st.session_state.messages)}")
                except Exception as e:
                    st.session_state.plan_content = f"更新失敗: {e}"
        
        st.rerun()
    
    # 下一步操作
    if st.session_state.plan_content:
        st.markdown("---")
        st.markdown("### 🎯 下一步操作")
        
        op_col1, op_col2 = st.columns(2)
        
        with op_col1:
            if st.button("🔍 CTO 深度審核", use_container_width=True, type="primary", disabled=len(st.session_state.plan_content) < 20, key="cto_review_left"):
                st.session_state.workflow_stage = 2
                with st.status("🔄 正在進行 AI 審核...", expanded=True) as status:
                    st.write("👀 **CTO** 正在檢視計畫書...")
                    critique, refined_plan = run_deep_reflection(st.session_state.plan_content, status_callback=st.warning)
                    st.write("🔧 **資深編輯** 正在修訂...")
                    st.session_state.critique_log = critique
                    st.session_state.plan_content = refined_plan
                    save_version_wrapper('deep_review', refined_plan, "經 CTO 審核並修訂")
                    status.update(label="✅ 審核完成！", state="complete", expanded=False)
                st.rerun()
        
        with op_col2:
            if st.session_state.critique_log:
                st.success("✅ 已完成審核")
                st.caption("👉 請至右側「👀 審核紀錄」分頁查看")
            else:
                st.info("💡 審核後可查看建議")

# --- 右側：計畫書與操作 ---
with col2:
    st.markdown("""
    <div class="section-banner section-banner-right">
        <h3>📋 智慧規格書</h3>
    </div>
    """, unsafe_allow_html=True)
    
    # === 顯示區 (Tabs) ===
    tab1, tab2, tab3 = st.tabs(["📄 規格書", "👀 審核紀錄", "📊 品質分析"])
    
    with tab1:
        st.markdown("### 📋 產品需求規格書（PRD）")
        
        # 版本比較功能（收合式）
        if len(st.session_state.versions) >= 2:
            with st.expander("🔍 比較版本差異"):
                col_old, col_new = st.columns(2)
                
                version_options = [f"v{v['version_number']} ({v['timestamp']})" 
                                  for v in st.session_state.versions]
                
                with col_old:
                    old_idx = st.selectbox(
                        "舊版本",
                        range(len(st.session_state.versions)),
                        format_func=lambda i: version_options[i],
                        key="diff_old"
                    )
                
                with col_new:
                    new_idx = st.selectbox(
                        "新版本",
                        range(len(st.session_state.versions)),
                        index=len(st.session_state.versions) - 1,
                        format_func=lambda i: version_options[i],
                        key="diff_new"
                    )
                
                if st.button("📊 顯示差異", use_container_width=True):
                    if old_idx == new_idx:
                        st.warning("請選擇不同的版本進行比較")
                    else:
                        old_content = st.session_state.versions[old_idx]['content']
                        new_content = st.session_state.versions[new_idx]['content']
                        diff_html = show_diff(old_content, new_content)
                        st.markdown(diff_html, unsafe_allow_html=True)
        
        # 規格書內容
        with st.container(height=520, border=True):
            if st.session_state.plan_content:
                edit_mode = st.session_state.get("edit_mode", False)
                
                if edit_mode:
                    if "prd_draft" not in st.session_state:
                        st.session_state.prd_draft = st.session_state.plan_content
                    
                    st.markdown("#### ✏️ 編輯 PRD（Markdown）")
                    st.caption("📝 編輯區域（Markdown 原始內容）")
                    
                    draft = st.text_area(
                        "編輯 PRD 內容",
                        value=st.session_state.prd_draft,
                        height=420,
                        key="prd_editor_single",
                        label_visibility="collapsed"
                    )
                    st.session_state.prd_draft = draft
                    
                    st.markdown("---")
                    save_col, cancel_col, word_count_col = st.columns([2, 2, 1])
                    
                    with word_count_col:
                        st.caption(f"📊 {len(draft) if draft else 0:,} 字")
                    
                    with save_col:
                        if st.button("💾 儲存修改", use_container_width=True, type="primary", key="save_edit_btn"):
                            if draft != st.session_state.plan_content:
                                save_version_wrapper("manual", draft, "手動編輯 PRD")
                                st.session_state.plan_content = draft
                                st.success("✅ 已儲存修改")
                            else:
                                st.info("ℹ️ 內容未變更")
                            
                            st.session_state.edit_mode = False
                            st.session_state.prd_draft = st.session_state.plan_content
                            time.sleep(0.5)
                            st.rerun()
                    
                    with cancel_col:
                        if st.button("❌ 取消", use_container_width=True, key="cancel_edit_btn"):
                            st.session_state.edit_mode = False
                            st.session_state.prd_draft = st.session_state.plan_content
                            st.rerun()
                
                else:
                    st.markdown(st.session_state.plan_content)
            
            else:
                st.info("📝 規格書尚未生成\n\n請先與 PM 對話，系統會自動產生規格書。")
        
        # 編輯按鈕
        if st.session_state.plan_content and not st.session_state.get("edit_mode", False):
            if st.button("✏️ 編輯 PRD", use_container_width=True, key="edit_prd_btn"):
                st.session_state.edit_mode = True
                st.session_state.prd_draft = st.session_state.plan_content
                st.rerun()
        
        # 下載區域
        if st.session_state.plan_content:
            st.markdown("---")
            st.markdown("### 📥 下載規格書")
            
            download_row1 = st.columns([2, 2, 1])
            
            with download_row1[0]:
                if st.session_state.versions:
                    version_options_dl = [f"v{v['version_number']} - {v.get('note', '初版')[:15]}..." if len(v.get('note','')) > 15 else f"v{v['version_number']} - {v.get('note', '初版')}" for v in st.session_state.versions]
                    selected_version_idx = st.selectbox(
                        "選擇版本",
                        range(len(st.session_state.versions)),
                        index=len(st.session_state.versions) - 1,
                        format_func=lambda i: version_options_dl[i],
                        key="download_version_select"
                    )
                    selected_content = st.session_state.versions[selected_version_idx]['content']
                    selected_version_num = st.session_state.versions[selected_version_idx]['version_number']
                else:
                    selected_content = st.session_state.plan_content
                    selected_version_num = 1
            
            with download_row1[1]:
                download_type = st.radio(
                    "下載內容",
                    options=["只下載 PRD", "只下載審核紀錄", "打包下載（PRD + 審核）"],
                    key="download_content_type",
                    horizontal=True,
                    label_visibility="collapsed"
                )
            
            with download_row1[2]:
                if st.button("📥 下載", use_container_width=True, type="primary"):
                    st.session_state.show_download_dialog = True
            
            # 下載對話框
            if st.session_state.show_download_dialog:
                with st.container(border=True):
                    timestamp = time.strftime('%Y%m%d_%H%M%S')
                    
                    if download_type == "只下載 PRD":
                        st.markdown(f"#### 選擇 PRD v{selected_version_num} 下載格式")
                        dl_cols = st.columns(3)
                        
                        with dl_cols[0]:
                            st.download_button("📄 Markdown", data=selected_content, 
                                             file_name=f"PRD_v{selected_version_num}_{timestamp}.md",
                                             mime="text/markdown", use_container_width=True)
                        with dl_cols[1]:
                            html_content = convert_markdown_to_html(selected_content, "PRD")
                            st.download_button("🌐 HTML", data=html_content,
                                             file_name=f"PRD_v{selected_version_num}_{timestamp}.html",
                                             mime="text/html", use_container_width=True)
                        with dl_cols[2]:
                            plain_text = selected_content.replace('#', '').replace('*', '').replace('`', '')
                            st.download_button("📝 TXT", data=plain_text,
                                             file_name=f"PRD_v{selected_version_num}_{timestamp}.txt",
                                             mime="text/plain", use_container_width=True)
                    
                    elif download_type == "只下載審核紀錄":
                        if st.session_state.critique_log:
                            st.markdown("#### 選擇審核紀錄下載格式")
                            dl_cols = st.columns(3)
                            
                            with dl_cols[0]:
                                st.download_button("📄 Markdown", data=st.session_state.critique_log,
                                                 file_name=f"CTO審核報告_{timestamp}.md",
                                                 mime="text/markdown", use_container_width=True)
                            with dl_cols[1]:
                                html_content = convert_markdown_to_html(st.session_state.critique_log, "CTO審核報告")
                                st.download_button("🌐 HTML", data=html_content,
                                                 file_name=f"CTO審核報告_{timestamp}.html",
                                                 mime="text/html", use_container_width=True)
                            with dl_cols[2]:
                                plain_text = st.session_state.critique_log.replace('#', '').replace('*', '').replace('`', '')
                                st.download_button("📝 TXT", data=plain_text,
                                                 file_name=f"CTO審核報告_{timestamp}.txt",
                                                 mime="text/plain", use_container_width=True)
                        else:
                            st.warning("⚠️ 尚未進行審核，無法下載審核紀錄")
                    
                    else:  # 打包下載
                        if st.session_state.critique_log:
                            st.markdown("#### 📦 打包下載（ZIP）")
                            
                            zip_buffer = BytesIO()
                            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                                zip_file.writestr(f"PRD_v{selected_version_num}.md", selected_content)
                                zip_file.writestr(f"CTO審核報告.md", st.session_state.critique_log)
                            
                            st.download_button(
                                label="📦 下載 ZIP 檔案",
                                data=zip_buffer.getvalue(),
                                file_name=f"PRD_Project_v{selected_version_num}_{timestamp}.zip",
                                mime="application/zip",
                                use_container_width=True
                            )
                        else:
                            st.warning("⚠️ 尚未進行審核，無法打包下載")
                    
                    st.info("💡 **Word 格式**：下載 HTML 後，用 Word 開啟再另存為 .docx")
                    
                    if st.button("✕ 關閉", key="close_download_dialog"):
                        st.session_state.show_download_dialog = False
                        st.rerun()
    
    with tab2:
        st.markdown('<div id="cto-review-anchor"></div>', unsafe_allow_html=True)
        st.markdown("### 👔 CTO 審核紀錄")
        
        if not st.session_state.plan_content:
            st.warning("⚠️ 請先生成規格書")
        else:
            if not st.session_state.critique_log:
                st.info("💡 CTO 會從技術、安全、風險等角度審核 PRD，提出改進建議")
                st.info("👆 請在「規格書」分頁點擊「深度審核」按鈕")
            else:
                with st.container(height=450, border=True):
                    st.markdown(st.session_state.critique_log)
                
                st.success("✅ 系統已根據上述意見自動修訂計畫書。")
                st.info("💡 若需下載審核報告，請至「規格書」分頁選擇「只下載審核紀錄」")
    
    with tab3:
        st.markdown("### 📊 專案品質分析")
        
        if not st.session_state.plan_content and not st.session_state.messages:
            st.info("📝 開始對話後，這裡會顯示專案的品質指標")
        else:
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric(
                    label="💬 對話輪次",
                    value=len(st.session_state.messages),
                    delta=None
                )
            
            with col2:
                st.metric(
                    label="📄 PRD 字數",
                    value=len(st.session_state.plan_content) if st.session_state.plan_content else 0,
                    delta=None
                )
            
            with col3:
                st.metric(
                    label="📚 版本數量",
                    value=len(st.session_state.versions),
                    delta=None
                )
            
            st.markdown("---")
            
            with st.container(height=350, border=True):
                if st.session_state.plan_content:
                    st.markdown("#### 📋 PRD 完整度檢查")
                    
                    prd_content = st.session_state.plan_content.lower()
                    
                    required_sections = {
                        "專案概述": ["專案概述", "專案說明", "背景", "概述"],
                        "功能需求": ["功能需求", "核心功能", "功能清單", "功能列表", "功能"],
                        "技術架構": ["技術架構", "技術選型", "架構設計", "架構"],
                        "資料結構": ["資料結構", "資料模型", "數據結構", "資料"],
                        "使用流程": ["使用流程", "操作流程", "用戶流程", "流程"]
                    }
                    
                    section_status = {}
                    for section_name, keywords in required_sections.items():
                        found = any(keyword in prd_content for keyword in keywords)
                        section_status[section_name] = found
                    
                    completeness = sum(section_status.values()) / len(section_status)
                    
                    st.progress(completeness, text=f"完整度：{completeness*100:.0f}%")
                    
                    col_left, col_right = st.columns(2)
                    
                    with col_left:
                        st.markdown("**✅ 已包含章節**")
                        for section, status in section_status.items():
                            if status:
                                st.success(f"✓ {section}")
                    
                    with col_right:
                        st.markdown("**⚠️ 缺少章節**")
                        missing = [s for s, status in section_status.items() if not status]
                        if missing:
                            for section in missing:
                                st.warning(f"✗ {section}")
                        else:
                            st.success("無缺漏章節！")
                
                st.markdown("---")
                
                if st.session_state.critique_log:
                    st.markdown("#### 🔍 CTO 審核統計")
                    
                    critique_text = st.session_state.critique_log
                    critique_points = len([line for line in critique_text.split('\n') if line.strip().startswith(('1.', '2.', '3.', '4.', '5.', '6.', '7.', '8.', '9.', '0.'))])
                    
                    col_a, col_b = st.columns(2)
                    
                    with col_a:
                        st.metric("⚠️ 發現問題數", critique_points)
                    
                    with col_b:
                        review_versions = len([v for v in st.session_state.versions if v['type'] == 'deep_review'])
                        st.metric("🔄 審核輪次", review_versions)
                    
                    if critique_points > 0:
                        st.info(f"💡 經過 CTO 審核，發現並改進了 {critique_points} 個潛在問題。")
                
                st.markdown("---")
                
                st.markdown("#### 🔄 工作流程進度")
                
                stages = ["💬 需求對話", "📝 生成 PRD", "🔍 CTO 審核"]
                stage_status = [
                    len(st.session_state.messages) > 0,
                    bool(st.session_state.plan_content),
                    bool(st.session_state.critique_log)
                ]
                
                cols = st.columns(3)
                for i, (col, stage, completed) in enumerate(zip(cols, stages, stage_status)):
                    with col:
                        if completed:
                            st.success(f"**{stage}**\n\n✅ 已完成")
                        else:
                            st.info(f"**{stage}**\n\n⏳ 待執行")

# === 底部資訊 ===
st.markdown("---")
st.markdown(f"""
<div style="text-align: center; color: #666; font-size: 0.85rem;">
    <p>📋 PRD Studio | 專注於需求釐清 → PRD 生成 → CTO 審核</p>
    <p style="font-size: 0.75rem;">多角色協作：PM 對話 → PRD 產生 → CTO 審核 → 多格式下載</p>
    <p style="font-size: 0.7rem; color: #555;">Model: {get_model_name()}</p>
</div>
""", unsafe_allow_html=True)
