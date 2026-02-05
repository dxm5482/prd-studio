# PRD Studio API

📋 AI 驅動的產品需求規格書（PRD）生成與審核 API，使用 FastAPI 建構，可一鍵部署到 Render。

## ✨ 功能特色

- 💬 **對話式需求訪談**：透過 `/chat` 端點與 AI PM 對話
- 📝 **自動生成 PRD**：`/generate_prd` 根據對話生成結構化 PRD
- 🔍 **CTO 深度審核**：`/critique_prd` 和 `/deep_review` 進行技術審核
- 📦 **多格式下載**：`/download_zip` 打包 Markdown / HTML / TXT

## 🚀 Render 一鍵部署

### 步驟 1：建立新服務

1. 在 [Render Dashboard](https://dashboard.render.com/) 建立新的 **Web Service**
2. 連接您的 GitHub Repository

### 步驟 2：設定 Build & Start 命令

| 設定項目 | 值 |
|---------|---|
| **Build Command** | `pip install -r requirements.txt` |
| **Start Command** | `uvicorn api:app --host 0.0.0.0 --port $PORT` |

### 步驟 3：設定環境變數

| 變數名稱 | 說明 | 必填 |
|---------|------|-----|
| `GEMINI_API_KEY` | Google Gemini API Key | ✅ |
| `MODEL_NAME` | 模型名稱（預設：`gemini-3-pro-preview`）| ❌ |
| `ALLOWED_ORIGINS` | CORS 允許來源（逗號分隔，預設：`*`）| ❌ |
| `ALLOW_CREDENTIALS` | 是否允許帶 cookies/授權（`true`/`false`）| ❌ |

## 💻 本地開發

### 安裝依賴

```bash
pip install -r requirements.txt
```

### 設定環境變數

**Windows PowerShell：**
```powershell
$env:GEMINI_API_KEY = "your-api-key"
```

**Linux / Mac：**
```bash
export GEMINI_API_KEY="your-api-key"
```

### 啟動開發伺服器

```bash
uvicorn api:app --reload
```

啟動後訪問：
- API 文件（Swagger UI）：http://localhost:8000/docs
- ReDoc 文件：http://localhost:8000/redoc

## 📡 API 端點

### 系統

| 方法 | 路徑 | 說明 |
|-----|------|------|
| GET | `/health` | 健康檢查 |

### 對話

| 方法 | 路徑 | 說明 |
|-----|------|------|
| POST | `/chat` | 對話（輸入 messages，回傳 reply） |

### PRD 生成與審核

| 方法 | 路徑 | 說明 |
|-----|------|------|
| POST | `/generate_prd` | 根據對話生成 PRD |
| POST | `/critique_prd` | CTO 審核 PRD |
| POST | `/deep_review` | 深度審核（審核 + 修正） |

### 下載

| 方法 | 路徑 | 說明 |
|-----|------|------|
| POST | `/download_zip` | 打包下載 PRD（ZIP） |

## 🧪 curl 測試範例

### 健康檢查

```bash
curl http://localhost:8000/health
```

回應：
```json
{"status":"ok","api_key_configured":true,"model_name":"gemini-3-pro-preview"}
```

### 對話

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"role": "user", "content": "我想做一個記帳 APP"}
    ]
  }'
```

回應：
```json
{"reply":"好的！先確認幾個問題：..."}
```

### 生成 PRD

```bash
curl -X POST http://localhost:8000/generate_prd \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"role": "user", "content": "我想做一個記帳 APP，個人用，記錄花費、分類、月統計"},
      {"role": "assistant", "content": "了解！那資料存在哪？手機本地還是雲端？"},
      {"role": "user", "content": "先存本地就好"}
    ]
  }'
```

### CTO 審核

```bash
curl -X POST http://localhost:8000/critique_prd \
  -H "Content-Type: application/json" \
  -d '{
    "prd_markdown": "# 記帳 APP PRD\n\n## 功能\n- 記錄收支\n- 分類\n- 月統計"
  }'
```

## 📁 專案結構

```
.
├── api.py                 # FastAPI 入口
├── requirements.txt       # Python 依賴
├── README.md              # 本文件
└── core/
    ├── __init__.py        # 模組初始化
    ├── config.py          # 環境變數
    ├── prompts.py         # AI 系統提示詞
    ├── gemini_client.py   # Gemini API 封裝
    └── utils.py           # 工具函式
```

## 📂 Legacy 檔案

以下為舊版 Streamlit 版本的檔案，已移至 `legacy/` 目錄：

- `legacy/app.py` - 舊版 Streamlit 入口
- `legacy/.streamlit/` - Streamlit 配置

## 🔑 取得 Gemini API Key

1. 前往 [Google AI Studio](https://aistudio.google.com/app/apikey)
2. 點擊「Create API Key」
3. 複製並設定環境變數

## 📄 授權

MIT License
