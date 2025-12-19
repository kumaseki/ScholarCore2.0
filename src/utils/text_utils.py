import json
import re
import logging
from src.core.exceptions import LLMParseError

logger = logging.getLogger("utils.text")

def clean_and_parse_json(text: str):
    '''
    清理并解析 JSON 字符串。
    1. 预处理：移除 Markdown 代码块
    2. 尝试直接解析 JSON
    3. 暴力提取：寻找最外层的 [...] 或 {...}
    '''
    if not text:
        raise LLMParseError("Empty response from LLM")
    
    cleaned = re.sub(r"^```(?:json)?\s*", "", text.strip(), flags=re.MULTILINE)
    cleaned = re.sub(r"\s*```$", "", cleaned, flags=re.MULTILINE)
    
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass
    
    try:
        # 寻找第一个 '[' 或 '{'
        start_match = re.search(r'[\[\{]', cleaned)
        if start_match:
            start_idx = start_match.start()
            # 寻找最后一个 ']' 或 '}'
            end_match = re.search(r'[\]\}]', cleaned[::-1])
            if end_match:
                end_idx = len(cleaned) - end_match.start()
                candidate = cleaned[start_idx:end_idx]
                return json.loads(candidate)
    except Exception:
        pass
        
    logger.error(f"JSON Parse Failed. Content snippet: {cleaned[:100]}...")
    raise LLMParseError("Malformed JSON")

def normalize_list(data: any) -> list:
    """
    工具函数：无论 AI 返回什么，都试图把它变成一个 List。
    """
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        # 尝试寻找可能是列表的 value
        for key in ['papers', 'results', 'items', 'list']:
            if key in data and isinstance(data[key], list):
                return data[key]
        # 如果找不到，就把 dict 当作 list 的唯一元素
        return [data]
    return []
