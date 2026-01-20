# utils/logger.py
import logging
import sys

def setup_logger(name):
    """返回一个配置好的 logger"""
    logger = logging.getLogger(name)
    
    # 如果已经有 handler 就不加了，防止重复打印
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            '%(asctime)s | %(levelname)s | [%(name)s] %(message)s',
            datefmt='%H:%M:%S'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    
    return logger