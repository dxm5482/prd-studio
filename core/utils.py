"""
工具函式模組：Markdown 轉換等通用函式（無 Streamlit 依賴）
"""
import time
import zipfile
from io import BytesIO


def convert_markdown_to_html(md_content: str, title: str = "文檔") -> str:
    """將 Markdown 轉換為格式化的 HTML"""
    html_template = f"""
<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        body {{
            font-family: "Microsoft JhengHei", "微軟正黑體", Arial, sans-serif;
            max-width: 900px;
            margin: 40px auto;
            padding: 20px;
            line-height: 1.8;
            color: #333;
        }}
        h1 {{ color: #2c3e50; border-bottom: 3px solid #3498db; padding-bottom: 10px; }}
        h2 {{ color: #34495e; margin-top: 30px; border-left: 4px solid #3498db; padding-left: 10px; }}
        h3 {{ color: #555; margin-top: 20px; }}
        code {{
            background: #f4f4f4;
            padding: 2px 6px;
            border-radius: 3px;
            font-family: "Consolas", monospace;
        }}
        pre {{
            background: #f8f8f8;
            padding: 15px;
            border-radius: 5px;
            overflow-x: auto;
            border-left: 4px solid #3498db;
        }}
        table {{
            border-collapse: collapse;
            width: 100%;
            margin: 20px 0;
        }}
        th, td {{
            border: 1px solid #ddd;
            padding: 12px;
            text-align: left;
        }}
        th {{
            background: #3498db;
            color: white;
        }}
        .footer {{
            margin-top: 50px;
            padding-top: 20px;
            border-top: 1px solid #ddd;
            text-align: center;
            color: #999;
            font-size: 0.9em;
        }}
    </style>
</head>
<body>
{md_content.replace(chr(10), '<br>')}
<div class="footer">
    文檔產生時間：{time.strftime('%Y-%m-%d %H:%M:%S')}<br>
    由 PRD Studio API 自動生成
</div>
</body>
</html>
"""
    return html_template


def convert_markdown_to_txt(md_content: str) -> str:
    """將 Markdown 轉換為純文字（移除 Markdown 符號）"""
    return md_content.replace('#', '').replace('*', '').replace('`', '')


def create_prd_zip(prd_content: str, critique_content: str = None) -> bytes:
    """
    建立包含 PRD 及審核報告的 ZIP 檔案
    
    Args:
        prd_content: PRD Markdown 內容
        critique_content: CTO 審核報告（可選）
    
    Returns:
        ZIP 檔案的 bytes
    """
    zip_buffer = BytesIO()
    
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        # PRD 三種格式
        zip_file.writestr("prd.md", prd_content)
        zip_file.writestr("prd.html", convert_markdown_to_html(prd_content, "PRD"))
        zip_file.writestr("prd.txt", convert_markdown_to_txt(prd_content))
        
        # 審核報告（若有）
        if critique_content:
            zip_file.writestr("critique.md", critique_content)
            zip_file.writestr("critique.html", convert_markdown_to_html(critique_content, "CTO 審核報告"))
    
    return zip_buffer.getvalue()
