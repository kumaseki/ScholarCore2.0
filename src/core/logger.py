# src/core/logger.py
import logging
import sys
from pathlib import Path

# 单例标记，防止多次配置导致日志重复打印
_LOGGING_CONFIGURED = False

def configure_logging(level=logging.INFO):
    """
    全局日志配置。只在 main.py 启动时调用一次。
    配置 Root Logger，这样所有模块都能自动使用。
    """
    global _LOGGING_CONFIGURED
    if _LOGGING_CONFIGURED:
        return
    
    # 获取 Root Logger (不带参数就是 Root)
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG) # 捕获所有，由 Handler 决定显示什么

    # 格式
    formatter = logging.Formatter(
        '%(asctime)s - [%(name)s] - %(levelname)s - %(message)s',
        datefmt='%H:%M:%S'
    )

    # 1. 控制台 (Console): 只看 INFO，清爽
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # 2. 文件 (File): 记录 DEBUG，用于尸检
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    file_handler = logging.FileHandler(log_dir / "scholar_core.log", encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)
    
    # 把第三方库的啰嗦日志关掉
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    
    # 🔇 新增：让 arxiv 库闭嘴，除非它报错
    logging.getLogger("arxiv").setLevel(logging.WARNING) 

    _LOGGING_CONFIGURED = True
    # logging.info("📝 Logging system configured successfully.")