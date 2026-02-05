"""
版本管理模組：處理 PRD 版本的保存與差異比較
"""
import hashlib
import difflib
from datetime import datetime


def save_version(versions: list, version_type: str, content: str, note: str = "") -> bool:
    """
    保存新版本
    
    Args:
        versions: 版本列表（會直接修改）
        version_type: 'quick_update' | 'deep_review' | 'manual'
        content: PRD 內容
        note: 版本備註
        
    Returns:
        是否成功保存（若內容與最新版相同則不保存）
    """
    # 計算內容 hash 避免重複保存相同內容
    content_hash = hashlib.md5(content.encode()).hexdigest()[:8]
    
    # 檢查是否與最新版本相同
    if versions and versions[-1]['content'] == content:
        return False  # 內容相同，不保存
    
    version = {
        'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'type': version_type,
        'content': content,
        'note': note,
        'hash': content_hash,
        'word_count': len(content),
        'version_number': len(versions) + 1
    }
    
    versions.append(version)
    return True


def show_diff(old_content: str, new_content: str) -> str:
    """
    產生 unified diff 格式的差異
    
    Returns:
        HTML 格式的 diff 顯示
    """
    old_lines = old_content.splitlines(keepends=True)
    new_lines = new_content.splitlines(keepends=True)
    
    diff = difflib.unified_diff(
        old_lines, 
        new_lines,
        fromfile='舊版本',
        tofile='新版本',
        lineterm=''
    )
    
    diff_text = '\n'.join(diff)
    
    if not diff_text:
        return "⚪ 兩個版本內容相同"
    
    # 簡單的顏色高亮
    lines = diff_text.split('\n')
    html_lines = []
    
    for line in lines:
        # HTML escape
        escaped_line = line.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        if line.startswith('+++') or line.startswith('---'):
            html_lines.append(f'<span style="color: #888;">{escaped_line}</span>')
        elif line.startswith('+'):
            html_lines.append(f'<span style="color: #2ed573; background: rgba(46,213,115,0.1);">{escaped_line}</span>')
        elif line.startswith('-'):
            html_lines.append(f'<span style="color: #ff4757; background: rgba(255,71,87,0.1);">{escaped_line}</span>')
        elif line.startswith('@@'):
            html_lines.append(f'<span style="color: #5352ed;">{escaped_line}</span>')
        else:
            html_lines.append(escaped_line)
    
    return '<pre style="background: #1e1e1e; padding: 1rem; border-radius: 8px; overflow-x: auto; font-size: 0.85rem;">' + \
           '\n'.join(html_lines) + '</pre>'
