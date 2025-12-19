import re
import logging
from pathlib import Path

logger = logging.getLogger("utils.file")

def sanitize_filename(name: str, max_length: int = 200) -> str:
    """
    清洗文件名，移除非法字符，防止文件系统错误。
    User Space Rule: Never trust input strings for file paths.
    """
    if not name:
        return "untitled_file"
    
    # 1. 替换非法字符 (Windows/Linux 通用: \ / : * ? " < > |)
    # 将它们替换为下划线
    safe_name = re.sub(r'[\\/*?:"<>|]', '_', name)
    
    # 2. 移除控制字符 (如换行符)
    safe_name = "".join(c for c in safe_name if c.isprintable())
    
    # 3. 去除首尾空格和点 (Windows 不喜欢文件名以点结尾)
    safe_name = safe_name.strip().strip('.')
    
    # 4. 截断长度 (保留后缀名的前提下)
    # 简单的截断，防止文件名过长导致 OSError
    if len(safe_name) > max_length:
        safe_name = safe_name[:max_length]
        
    return safe_name

def ensure_dir(path: Path):
    """确保目录存在，如果不存在则创建"""
    if not path.exists():
        path.mkdir(parents=True, exist_ok=True)
        logger.debug(f"Created directory: {path}")